# langchain_lx.py
# Windows-compatible RAG with SiliconFlow API embeddings
# Ready for zero-install deployment
import os
#   # Optional env default
#   # Optional env default

import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as futuresTimeoutError

from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# =================================================
# 1. API Configuration (hardcoded for Windows deployment)
# =================================================
YOUR_API_KEY_HERE = "***"  # Replace with actual key
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
EMBED_MODEL = "BAAI/bge-large-zh-v1.5"
LLM_MODEL = "THUDM/GLM-4-9B-0414"

# =================================================
# 2. LLM Initialization
# =================================================
REQUEST_TIMEOUT = float("your-api-key")

llm = ChatOpenAI(
    api_key=YOUR_API_KEY_HERE,
    base_url=SILICONFLOW_BASE_URL,
    model=LLM_MODEL,
    temperature=0.1,
    max_tokens=512,
    timeout=REQUEST_TIMEOUT,
)

# =================================================
# 3. SiliconFlow Embeddings with Auto-Truncation
# =================================================
import requests
from langchain_core.embeddings import Embeddings

class SiliconFlowEmbeddings(Embeddings):
    """SiliconFlow API embeddings with automatic text truncation for 512-token limit"""
    
    def __init__(self, api_key: str, model: str = "BAAI/bge-large-zh-v1.5"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.siliconflow.cn/v1/embeddings"
        self.max_chars = 300  # ~512 tokens for Chinese text
    
    def _truncate_text(self, text: str) -> str:
        """Truncate text to stay within API limits"""
        if len(text) > self.max_chars:
            return text[:self.max_chars]
        return text
    
    def embed_documents(self, texts: list) -> list:
        """Embed documents with auto-truncation and batching"""
        truncated = [self._truncate_text(t) for t in texts]
        
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(truncated), batch_size):
            batch = truncated[i:i+batch_size]
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"model": self.model, "input": batch},
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            all_embeddings.extend([item["embedding"] for item in data["data"]])
        
        return all_embeddings
    
    def embed_query(self, text: str) -> list:
        """Embed single query"""
        return self.embed_documents([text])[0]

embeddings = SiliconFlowEmbeddings(api_key=YOUR_API_KEY_HERE, model=EMBED_MODEL)
logger.info(f"✅ Embedding model ready: {EMBED_MODEL} (SiliconFlow API)")

# =================================================
# 4. Document Loading and Splitting (relative paths!)
# =================================================
DOC_PATH = os.path.join(os.path.dirname(__file__), "郑寅文.md")
PERSIST_DIR = os.path.join(os.path.dirname(__file__), "chroma_db_zyw")
COLLECTION_NAME = "zhengyinwen"

# Load document
docs_list = []
if os.path.isfile(DOC_PATH):
    loader = TextLoader(DOC_PATH, encoding="utf-8")
    docs_list.extend(loader.load())
    logger.info(f"  Loaded: {DOC_PATH}")
elif os.path.isdir(DOC_PATH):
    for fname in os.listdir(DOC_PATH):
        fpath = os.path.join(DOC_PATH, fname)
        if fname.endswith((".txt", ".md")) and os.path.isfile(fpath):
            try:
                loader = TextLoader(fpath, encoding="utf-8")
                docs_list.extend(loader.load())
                logger.info(f"  Loaded: {fname}")
            except Exception as e:
                logger.warning(f"  Skipped {fname}: {e}")
else:
    logger.error(f"❌ Path not found: {DOC_PATH}")
    sys.exit(1)

if not docs_list:
    logger.error("❌ No documents found")
    sys.exit(1)

logger.info(f"Loaded {len(docs_list)} documents")

# Split documents
splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
    length_function=len,
)
splits = splitter.split_documents(docs_list)
logger.info(f"✅ Split into {len(splits)} chunks")

# =================================================
# 5. Vector Store (load or create)
# =================================================
import chromadb

_db_exists = False
if os.path.isdir(PERSIST_DIR):
    try:
        _client = chromadb.PersistentClient(path=PERSIST_DIR)
        _col = _client.get_collection(COLLECTION_NAME)
        if _col.count() > 0:
            _db_exists = True
            logger.info(f"✅ Found existing vector store: {_col.count()} records")
    except Exception:
        pass

if _db_exists:
    vectorstore = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )
else:
    logger.info(f"Creating new vector store: {PERSIST_DIR}")
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
        collection_name=COLLECTION_NAME,
    )
    logger.info(f"✅ Vector store created: {len(splits)} chunks")

# Create retriever
base_retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

# =================================================
# 6. RAG Chain (using LCEL, no langchain_classic)
# =================================================
system_prompt = """You are an intelligent Q&A assistant. Answer based on the reference materials.

Rules:
1. Only answer based on reference materials, do not fabricate
2. If no relevant information, say "Sorry, no information available"
3. Keep answers concise and direct

Reference materials:
{context}"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}")
])

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": base_retriever | format_docs, "input": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

def ask(question: str, timeout: float | None = None) -> str:
    """Ask a question using RAG"""
    effective_timeout = timeout or 90.0
    logger.info(f"🔍 Question: {question}")

    def _invoke():
        t0 = time.perf_counter()
        result = rag_chain.invoke(question)
        t1 = time.perf_counter()
        logger.info(f"RAG processing time: {(t1-t0)*1000:.0f}ms")
        return result

    with ThreadPoolExecutor() as executor:
        future = executor.submit(_invoke)
        try:
            return future.result(timeout=effective_timeout)
        except futuresTimeoutError:
            logger.error(f"❌ Request timeout ({effective_timeout:.0f}s)")
            return "Sorry, request timed out. Please try again later."

# =================================================
# 7. Interactive Loop
# =================================================
if __name__ == "__main__":
    print("\n🤖 RAG Q&A System Ready! Type your question (type 'exit' to quit)\n")
    while True:
        try:
            user_input = input("👤 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("👋 Goodbye!")
            break

        try:
            answer = ask(user_input)
            print(f"\n🤖 Assistant: {answer}\n")
        except Exception as e:
            logger.error(f"Error: {e}")
            print("⚠️ Sorry, an error occurred. Please try again.\n")
