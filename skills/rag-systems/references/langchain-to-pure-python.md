# LangChain → Pure Python RAG Migration Guide

Systematic component-by-component migration from a LangChain/LangGraph RAG to pure Python.

## Migration Checklist

### Phase 1: Data Layer

- [ ] Replace `langchain_core.documents.Document` → `@dataclass`
- [ ] Replace `PyMuPDFLoader` → `pymupdf` native API
- [ ] Replace `TextLoader` → `open()` + `f.read()`
- [ ] Replace `RecursiveCharacterTextSplitter` → custom class
- [ ] Replace `langchain_chroma.Chroma` → `chromadb.PersistentClient`
- [ ] Replace `BM25Retriever` → `rank_bm25.BM25Okapi`

### Phase 2: API Layer

- [ ] Replace `ChatOpenAI` → direct `requests.post()` to `/chat/completions`
- [ ] Replace `OpenAIEmbeddings` → direct `requests.post()` to `/embeddings`
- [ ] Keep `SiliconFlowReranker` as-is (already uses direct API)

### Phase 3: Chain Layer

- [ ] Replace `ChatPromptTemplate` → string formatting
- [ ] Replace `create_stuff_documents_chain` → manual context injection
- [ ] Replace `prompt | llm` chain → `llm.invoke(messages)`

### Phase 4: Orchestration Layer

- [ ] Replace `StateGraph` (LangGraph) → hand-rolled state machine
- [ ] Keep all node functions (translate, classify, retrieve, answer)
- [ ] Keep conditional routing logic

---

## Document Dataclass

```python
from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass
class Document:
    page_content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**Why**: LangChain's Document is just a container with `page_content` and `metadata`. A dataclass is identical and has zero dependencies.

---

## LLM Client (replaces ChatOpenAI)

```python
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
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return LLMResponse(content=data["choices"][0]["message"]["content"])
```

**Key difference from ChatOpenAI**: No retry logic, no streaming, no function calling. Add those if needed.

---

## Embedding Client (replaces OpenAIEmbeddings)

```python
class EmbeddingClient:
    def __init__(self, api_key, base_url, model, chunk_size=16, timeout=60.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.chunk_size = chunk_size
        self.timeout = timeout

    def _call_api(self, texts):
        url = f"{self.base_url}/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "input": texts}
        resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in sorted_data]

    def embed_documents(self, texts):
        # Batch in chunks, retry per-item on failure
        all_embeddings = []
        for i in range(0, len(texts), self.chunk_size):
            batch = texts[i:i + self.chunk_size]
            try:
                embs = self._call_api(batch)
                all_embeddings.extend(embs)
            except Exception as e:
                logger.warning(f"Batch failed, retrying per-item: {e}")
                for t in batch:
                    try:
                        all_embeddings.append(self._call_api([t])[0])
                    except:
                        all_embeddings.append([0.0] * 1024)  # zero-vector fallback
        return all_embeddings

    def embed_query(self, text):
        return self._call_api([text])[0]
```

**Critical**: Always sort by `index` — API may return embeddings in any order.

---

## Text Splitter (replaces RecursiveCharacterTextSplitter)

```python
class RecursiveCharacterTextSplitter:
    def __init__(self, chunk_size=400, chunk_overlap=80, separators=None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", "! ", "? ", "; ", ": ", " "]

    def split_text(self, text):
        # Find the first separator that exists in text
        separator = self.separators[-1]
        for sep in self.separators:
            if sep in text:
                separator = sep
                break
        splits = text.split(separator)
        # Merge small splits, recurse on large ones
        # ... (see full implementation in lw_rag.py)
```

**Strategy preserved**: Two-layer splitting (small 400/80 + big 800/150) with different separator sets.

---

## Vector Store (replaces langchain_chroma.Chroma)

```python
class VectorStore:
    def __init__(self, persist_dir, collection_name, embedding_client):
        import chromadb
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self.embedding_client = embedding_client

    def add_documents(self, documents, batch_size=100):
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            texts = [doc.page_content for doc in batch]
            metadatas = [self._sanitize_meta(doc.metadata) for doc in batch]
            ids = [f"doc_{i+j}" for j in range(len(batch))]
            embeddings = self.embedding_client.embed_documents(texts)
            self._collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

    def similarity_search(self, query, k=12):
        query_embedding = self.embedding_client.embed_query(query)
        results = self._collection.query(query_embeddings=[query_embedding], n_results=k,
                                          include=["documents", "metadatas"])
        return [Document(page_content=d, metadata=m or {})
                for d, m in zip(results["documents"][0], results["metadatas"][0])]

    @staticmethod
    def _sanitize_meta(meta):
        clean = {}
        for k, v in meta.items():
            if v is None:
                clean[k] = ""
            elif isinstance(v, (str, int, float, bool)):
                clean[k] = v
            else:
                clean[k] = str(v)
        return clean
```

---

## Prompt Formatting (replaces ChatPromptTemplate)

```python
def format_prompt(system_msg, human_msg, **kwargs):
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": human_msg},
    ]
    for msg in messages:
        for key, value in kwargs.items():
            msg["content"] = msg["content"].replace(f"{{{key}}}", str(value))
    return messages
```

**Note**: Use `"user"` role, not `"human"` — OpenAI-compatible APIs expect `user`.

---

## State Machine (replaces LangGraph StateGraph)

```python
def run(initial_state):
    state = dict(initial_state)
    # Linear nodes
    state.update(_translate_node(state))
    state.update(_classify_node(state))
    # Loop with conditional routing
    while True:
        route = _route_by_type(state)
        retrieve_fn = {
            "comparison_retrieve": _comparison_retrieve_node,
            "multi_hop_retrieve": _multi_hop_retrieve_node,
        }.get(route, _standard_retrieve_node)
        state.update(retrieve_fn(state))
        # Evaluate: retry or answer
        if not state.get("docs") and state["retry_count"] < state["max_retries"]:
            state.update(_rewrite_query(state))
            state.update(_translate_node(state))
            state.update(_classify_node(state))
            continue
        state.update(_answer_node(state))
        break
    return state
```

---

## Migration Order (Recommended)

1. **Document dataclass** — zero risk, immediate
2. **Text splitter** — test with same input, verify chunk counts match
3. **Embedding client** — verify same dimensions (1024 for bge-large-en-v1.5)
4. **Vector store** — can reuse existing ChromaDB, just change access layer
5. **BM25** — depends on Document dataclass
6. **LLM client** — test with same prompt, verify output quality
7. **Prompt formatting** — test with same context
8. **State machine** — last, as it orchestrates everything

Each step can be tested independently before moving to the next.
