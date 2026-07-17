# SiliconFlow Embeddings with Auto-Truncation

The `BAAI/bge-large-zh-v1.5` model on SiliconFlow has a **500 character input limit** (tested 2026-06-14). Texts over 500 chars trigger `400 Bad Request` with error code 20015. Use this class for automatic truncation:

```python
import requests
from langchain_core.embeddings import Embeddings

class SiliconFlowEmbeddings(Embeddings):
    """SiliconFlow API embeddings with automatic text truncation"""

    def __init__(self, api_key: str, model: str = "BAAI/bge-large-zh-v1.5"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.siliconflow.cn/v1/embeddings"
        self.max_chars = 500  # SiliconFlow hard limit for bge-large-zh-v1.5

    def _truncate_text(self, text: str) -> str:
        if len(text) > self.max_chars:
            return text[:self.max_chars]
        return text

    def embed_documents(self, texts: list) -> list:
        truncated = [self._truncate_text(t) for t in texts]
        batch_size = 32  # Keep batches small to avoid timeouts
        all_embeddings = []
        for i in range(0, len(truncated), batch_size):
            batch = truncated[i:i+batch_size]
            response = requests.post(
                self.api_url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "input": batch},
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            all_embeddings.extend([item["embedding"] for item in data["data"]])
        return all_embeddings

    def embed_query(self, text: str) -> list:
        return self.embed_documents([text])[0]
```

**When using the OpenAI Python client instead of raw requests**, the same limit applies. Add truncation before sending:

```python
# In embed_documents method with openai client:
batch_texts = [t[:500] if len(t) > 500 else t for t in batch_texts]
response = self.client.embeddings.create(model=self.model, input=batch_texts)
```

## Text Chunking Parameters

For RAG chunking, keep `chunk_size` moderate even with auto-truncation:

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,        # Safe for most documents
    chunk_overlap=50,      # Moderate overlap for context
    separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
    length_function=len,
)
```

**Pitfall**: Large `chunk_size` (e.g. 800) works for text splitting but the embedding API will truncate at 500 chars anyway. Keep chunks meaningful at 200-500 chars.

**Note**: `BAAI/bge-m3` has NO character limit — use it if you need longer inputs.

## Replacing langchain_classic with langchain_core

Newer versions of langchain removed `langchain_classic`. Use `langchain_core` directly:

```python
# OLD - broken in newer versions
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

# NEW - use LCEL directly
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | format_docs, "input": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)
```

## Browser-Based Terminal Pitfalls

When deploying via browser terminals (Alibaba Cloud Workbench, etc.):
- **ESC key intercepted** — Use `Ctrl+[` instead
- **Vim unusable** — Use `nano` or edit via agent's `patch` tool
- **Prefer SSH** for editing; browser terminals are for running commands only

## Interaction Style Notes

- User prefers to **do things themselves** — provide instructions, don't execute everything
- Keep responses **concise** — avoid lengthy explanations
- When user says "暂停一下" (pause), stop immediately
- User works in **网吧 (internet cafe)** — restricted Windows environment
