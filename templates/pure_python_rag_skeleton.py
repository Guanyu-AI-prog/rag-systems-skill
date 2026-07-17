# Pure Python RAG Skeleton
# Replace XXX markers with your actual values
# Dependencies: # Dependencies: pip install chromadb rank_bm25 pymupdf requests python-dotenvv

import os
import sys
import time
import pickle
import json
import re
import unicodedata
import logging
import threading
import requests
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# 1. CONFIG
# ============================================================
YOUR_API_KEY_HERE = "<your-api-key>"  # Set via env var or .env file  # XXX: for embeddings + rerank
YOUR_API_KEY_HERE = "YOUR_API_KEY"  # Set via environment variable                  # XXX: for LLM

LLM_BASE_URL = "XXX"           # e.g. "https://open.bigmodel.cn/api/paas/v4/"
LLM_MODEL = "XXX"              # e.g. "glm-4.5-air"
EMBED_MODEL = "XXX"            # e.g. "BAAI/bge-large-en-v1.5"
EMBED_BASE_URL = "XXX"         # e.g. "https://api.siliconflow.cn/v1"
RERANK_MODEL = "XXX"           # e.g. "BAAI/bge-reranker-v2-m3"

DOC_PATH = "XXX"               # e.g. "/home/admin/arxiv_papers_md"
PERSIST_DIR = "XXX"            # e.g. "/home/admin/vector_dbs/my_rag_db"
COLLECTION_NAME = "XXX"        # e.g. "my_docs"


# ============================================================
# 2. Document dataclass
# ============================================================
@dataclass
class Document:
    page_content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# 3. LLM Client
# ============================================================
@dataclass
class LLMResponse:
    content: str

class LLMClient:
    def __init__(self, api_key, base_url, model, temperature=0.1, max_tokens=1536, timeout=60.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def invoke(self, messages):
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": messages,
                   "temperature": self.temperature, "max_tokens": self.max_tokens}
        resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return LLMResponse(content=resp.json()["choices"][0]["message"]["content"])


# ============================================================
# 4. Embedding Client
# ============================================================
class EmbeddingClient:
    def __init__(self, api_key, base_url, model, chunk_size=16, timeout=60.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.chunk_size = chunk_size
        self.timeout = timeout

    def _call_api(self, texts):
        resp = requests.post(f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "input": texts}, timeout=self.timeout)
        resp.raise_for_status()
        return [item["embedding"] for item in sorted(resp.json()["data"], key=lambda x: x["index"])]

    def embed_documents(self, texts):
        all_embs = []
        for i in range(0, len(texts), self.chunk_size):
            batch = texts[i:i+self.chunk_size]
            try:
                all_embs.extend(self._call_api(batch))
            except Exception as e:
                logger.warning(f"Embedding batch failed, per-item retry: {e}")
                for t in batch:
                    try:
                        all_embs.append(self._call_api([t])[0])
                    except:
                        all_embs.append([0.0] * 1024)
        return all_embs

    def embed_query(self, text):
        return self._call_api([text])[0]


# ============================================================
# 5. Reranker
# ============================================================
class SiliconFlowReranker:
    def __init__(self, model="BAAI/bge-reranker-v2-m3", top_n=3):
        self.model = model
        self.top_n = top_n
        self.api_url = "https://api.siliconflow.cn/v1/rerank"
        self.api_key = "<your-api-key>"  # Set via env var or .env file
        self.timeout = float("your-api-key")

    def rerank(self, documents, query):
        if not documents or not self.api_key:
            return documents[:self.top_n]
        resp = requests.post(self.api_url,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "query": query,
                  "documents": [d.page_content for d in documents],
                  "top_n": self.top_n, "return_documents": False},
            timeout=self.timeout)
        resp.raise_for_status()
        return [Document(page_content=documents[r["index"]].page_content,
                         metadata={**documents[r["index"]].metadata,
                                   "relevance_score": r.get("relevance_score", 0.0)})
                for r in resp.json()["results"]]


# ============================================================
# 6. Text Splitter
# ============================================================
class RecursiveCharacterTextSplitter:
    def __init__(self, chunk_size=400, chunk_overlap=80, separators=None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", "! ", "? ", "; ", ": ", " "]

    def split_text(self, text):
        separator = self.separators[-1]
        for sep in self.separators:
            if sep in text:
                separator = sep
                break
        splits = text.split(separator)
        chunks = []
        current = []
        current_len = 0
        for s in splits:
            if len(s) < self.chunk_size:
                current.append(s)
            else:
                if current:
                    chunks.extend(self._merge(separator.join(current), separator))
                    current = []
                chunks.extend(self.split_text(s))
        if current:
            chunks.extend(self._merge(separator.join(current), separator))
        return chunks

    def _merge(self, text, separator):
        chunks, start = [], 0
        while start < len(text):
            end = start + self.chunk_size
            if end >= len(text):
                chunks.append(text[start:].strip())
                break
            best_end = end
            for sep in self.separators:
                pos = text.rfind(sep, start + self.chunk_size // 2, end + 50)
                if pos > start:
                    best_end = pos + len(sep)
                    break
            chunk = text[start:best_end].strip()
            if chunk:
                chunks.append(chunk)
            start = best_end - self.chunk_overlap
            if start <= 0:
                start = best_end
        return chunks

    def split_documents(self, documents):
        result = []
        for doc in documents:
            for text in self.split_text(doc.page_content):
                if text.strip():
                    result.append(Document(page_content=text, metadata=dict(doc.metadata)))
        return result


# ============================================================
# 7. Document Loaders
# ============================================================
def load_pdf(path):
    import pymupdf
    docs = []
    pdf = pymupdf.open(path)
    for i, page in enumerate(pdf):
        text = page.get_text()
        if text.strip():
            docs.append(Document(page_content=text, metadata={"source": path, "page": i}))
    pdf.close()
    return docs

def load_text(path, encoding="utf-8"):
    with open(path, "r", encoding=encoding) as f:
        text = f.read()
    return [Document(page_content=text, metadata={"source": path})] if text.strip() else []


# ============================================================
# 8. BM25 Searcher
# ============================================================
class BM25Searcher:
    def __init__(self, documents, k=15):
        self.documents = documents
        self.k = k
        from rank_bm25 import BM25Okapi
        corpus = [self._tokenize(d.page_content) for d in documents]
        self._bm25 = BM25Okapi(corpus)

    def _tokenize(self, text):
        tokens = []
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                tokens.append(char)
            elif char.isalnum():
                tokens.append(char.lower())
        tokens.extend(re.findall(r'[a-zA-Z]+', text.lower()))
        return tokens

    def invoke(self, query):
        scores = self._bm25.get_scores(self._tokenize(query))
        top = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:self.k]
        return [self.documents[i] for i in top if scores[i] > 0]


# ============================================================
# 9. Vector Store
# ============================================================
class VectorStore:
    def __init__(self, persist_dir, collection_name, embedding_client):
        import chromadb
        self.embedding_client = embedding_client
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"})

    @property
    def count(self):
        return self._collection.count()

    def add_documents(self, documents, batch_size=100):
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            texts = [d.page_content for d in batch]
            metas = [self._clean(d.metadata) for d in batch]
            ids = [f"doc_{i+j}" for j in range(len(batch))]
            embs = self.embedding_client.embed_documents(texts)
            self._collection.add(ids=ids, embeddings=embs, documents=texts, metadatas=metas)

    def similarity_search(self, query, k=12):
        if self.count == 0:
            return []
        qemb = self.embedding_client.embed_query(query)
        res = self._collection.query(query_embeddings=[qemb], n_results=min(k, self.count),
                                     include=["documents", "metadatas"])
        return [Document(page_content=d, metadata=m or {})
                for d, m in zip(res["documents"][0], res["metadatas"][0])]

    def as_retriever(self, search_kwargs=None):
        k = (search_kwargs or {}).get("k", 12)
        return VectorRetriever(self, k)

    @staticmethod
    def _clean(meta):
        return {k: ("" if v is None else v if isinstance(v, (str,int,float,bool)) else str(v))
                for k, v in meta.items()}


class VectorRetriever:
    """Wraps VectorStore to match BM25Searcher's .invoke() interface."""
    def __init__(self, vectorstore, k=12):
        self.vectorstore = vectorstore
        self.k = k

    def invoke(self, query):
        return self.vectorstore.similarity_search(query, k=self.k)


# ============================================================
# 10. Prompt Helper
# ============================================================
def format_prompt(system_msg, human_msg, **kwargs):
    msgs = [{"role": "system", "content": system_msg}, {"role": "user", "content": human_msg}]
    for msg in msgs:
        for k, v in kwargs.items():
            msg["content"] = msg["content"].replace(f"{{{k}}}", str(v))
    return msgs


# ============================================================
# 11. State Machine Nodes (customize these for your use case)
# ============================================================
def _translate_node(state):
    # XXX: implement query translation if needed
    return {}

def _classify_node(state):
    # XXX: implement query classification
    return {"query_info": {"type": "factual"}}

def _retrieve_node(state):
    # XXX: implement retrieval (vector + BM25 + rerank)
    return {"docs": []}

def _answer_node(state):
    # XXX: implement answer generation
    if not state.get("docs"):
        return {"answer": "No relevant documents found."}
    context = "\n\n".join(d.page_content for d in state["docs"])
    msgs = format_prompt("Answer based on context:\n{context}", "{input}",
                         context=context, input=state["question"])
    return {"answer": state.get("llm").invoke(msgs).content}


# ============================================================
# 12. Main Entry
# ============================================================
_rag_initialized = False
_init_lock = threading.Lock()

def _init_rag():
    global _rag_initialized, llm, embeddings, vectorstore, bm25, retriever, reranker
    if _rag_initialized:
        return
    with _init_lock:
        if _rag_initialized:
            return
        llm = LLMClient(api_key=YOUR_API_KEY_HERE, base_url=LLM_BASE_URL, model=LLM_MODEL)
        embeddings = EmbeddingClient(api_key=YOUR_API_KEY_HERE, base_url=EMBED_BASE_URL, model=EMBED_MODEL)
        # ... load docs, build vectorstore, bm25 ...
        reranker = SiliconFlowReranker(model=RERANK_MODEL, top_n=8)
        _rag_initialized = True

def ask(question, timeout=None):
    _init_rag()
    state = {"question": question, "docs": [], "answer": ""}
    state.update(_translate_node(state))
    state.update(_classify_node(state))
    state.update(_retrieve_node(state))
    state.update(_answer_node(state))
    return state.get("answer", "No answer")

if __name__ == "__main__":
    print("🤖 Pure Python RAG ready. Type 'exit' to quit.\n")
    while True:
        try:
            q = input("👤 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ("exit", "quit"):
            break
        if q:
            print(f"\n🤖 {ask(q)}\n")
