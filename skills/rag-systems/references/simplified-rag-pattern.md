# Simplified RAG Pattern (lc_lx.py)

Single-file RAG implementation for lightweight deployments.

## Key Differences from Full Version

| Feature | Full (api.py) | Simplified (lc_lx.py) |
|---------|---------------|----------------------|
| API Service | FastAPI on port 8001 | Interactive CLI |
| Embeddings | Local HuggingFace or API | SiliconFlow API only |
| Reranking | Optional | Removed |
| BM25 | Hybrid search | Vector only |
| Caching | Yes | No |
| Session History | Yes | No |

## Required Modifications After Migration

When moving `lc_lx.py` to a new server:

1. **Update paths**:
```python
# Old (original server)
DOC_PATH = "/home/admin/Desktop/郑寅文.md"
PERSIST_DIR = "/home/admin/Desktop/chroma_db_zyw"

# New (target server)
DOC_PATH = "/home/rag_lx/郑寅文.md"
PERSIST_DIR = "/home/rag_lx/chroma_db_zyw"
```

2. **Replace HuggingFace embeddings** with SiliconFlow API (see main skill)

3. **Update imports** for new LangChain API:
```python
# Remove:
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

# Add:
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
```

## Running the Simplified Version

```bash
cd /home/rag_lx
source /path/to/venv/bin/activate
python lc_lx.py
```

**Why use virtual environment Python?**
- `python` (system) → no langchain installed
- `/path/to/venv/bin/python` → has all dependencies

Alternative without activating:
```bash
/root/langchain_rag_code/venv/bin/python lc_lx.py
```

**IMPORTANT**: Interactive scripts (with `input()`) MUST run in foreground terminal, not background. Background mode has no stdin, so the script exits immediately.

```bash
# Wrong - exits immediately
terminal(command="python lc_lx.py", background=true)

# Correct - user runs this themselves in SSH
cd /home/rag_lx && source venv/bin/activate && python lc_lx.py
```

## Environment Variables

The script checks for `YOUR_API_KEY_HERE` in:
1. Environment variable
2. your `.env` file file

## Document Processing

- Chunk size: 100 chars (smaller than full version's 300-500)
- Chunk overlap: 10 chars
- Separators: `\n\n`, `\n`, `。`, `！`, `？`, `；`, `，`, ` `, ``

## Vector Database

- Collection name: `zhengyinwen`
- Auto-creates if not exists
- Persists to `PERSIST_DIR`
