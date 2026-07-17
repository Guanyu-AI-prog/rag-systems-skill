# Advanced RAG Pattern (lc_raglw.py)

Full-featured RAG with LangGraph orchestration, BM25+Vector hybrid retrieval, and SiliconFlow reranking.

## Architecture Overview

```
User Query
    ↓
[_translate_node] → 中文→英文翻译（提升英文文档库检索效果）
    ↓
[_classify_node] → 规则分类（factual/comparison/synthesis/multi_hop）
    ↓
[_route_by_type] → 按类型路由到不同检索策略
    ↓                    ↓                    ↓
[standard_retrieve] [comparison_retrieve] [multi_hop_retrieve]
    ↓                    ↓                    ↓
[_evaluate_retrieval] → 空结果？→ [_rewrite_query] → 重试（最多2次）
    ↓
[_answer_node] → LLM 生成回答 + 来源标注
```

## Key Components

### 1. Dual Retriever (BM25 + Vector)
```python
# BM25 — keyword-based, k=15
bm25_retriever = BM25Retriever.from_documents(splits, k=15)

# Vector — semantic search, k=12
base_retriever = vectorstore.as_retriever(search_kwargs={"k": 12})
```

### 2. SiliconFlow Reranker
```python
class SiliconFlowReranker:
    """Rerank via SiliconFlow API, top_n=8"""
    api_url = "https://api.siliconflow.cn/v1/rerank"
    model = "BAAI/bge-reranker-v2-m3"
```

### 3. Multi-size Chunking
```python
# Small chunks — precise matching
small_splitter = RecursiveCharacterTextSplitter(
    chunk_size=400, chunk_overlap=80)

# Big chunks — context preservation
big_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800, chunk_overlap=150)

# Both stored in same vector DB with metadata tags
for doc in small_splits:
    doc.metadata["chunk_type"] = "small"
for doc in big_splits:
    doc.metadata["chunk_type"] = "big"
```

### 4. Query Classification (Rule-based, zero LLM call)
```python
comparison_kw = ["区别", "对比", "比较", "差异", "vs", "不同", "异同", "优劣"]
synthesis_kw = ["总结", "归纳", "综述", "概述", "概括", "发展趋势", "进展"]
multi_hop_kw = ["如何影响", "导致", "发展历程", "演进", "演变", "因果"]
```

### 5. Safe Embeddings Wrapper
```python
class SafeEmbeddings:
    """Batch embedding with fallback: retry single items, use zero vector on failure"""
    def embed_documents(self, texts):
        try:
            return _base_embeddings.embed_documents(texts)
        except:
            # Retry one-by-one, zero vector [0.0]*1024 for failures
```

## Configuration

| Setting | Value | Source |
|---------|-------|--------|
| LLM | glm-4.5-air (智谱AI) | ZHIPUAI_API_KEY |
| Embedding | BAAI/bge-large-en-v1.5 (SiliconFlow) | YOUR_API_KEY_HERE |
| Reranker | BAAI/bge-reranker-v2-m3 (SiliconFlow) | YOUR_API_KEY_HERE |
| Vector DB | ChromaDB | /home/admin/vector_dbs/rag_chroma_db_arxiv_pdf_v2 |
| Source docs | arxiv papers (.md/.pdf) | /home/admin/arxiv_papers_md |
| BM25 k | 15 | environment variable for BM25 top_k |
| Vector k | 12 | search_kwargs |
| Rerank top_n | 8 | SiliconFlowReranker init |
| Chunk cache | splits.pkl | In vector DB dir |

## Differences from Simplified Version (lc_lx.py)

| Feature | lc_raglw.py (Advanced) | lc_lx.py (Simplified) |
|---------|----------------------|----------------------|
| Framework | LangGraph StateGraph | Direct chain |
| Retrieval | BM25 + Vector hybrid | Vector only |
| Reranking | SiliconFlow reranker | None |
| Query routing | 4 types (factual/comparison/synthesis/multi_hop) | None |
| Query rewrite | LLM-based retry on empty results | None |
| Query translation | 中文→英文 | None |
| LLM provider | 智谱AI (GLM-4.5-air) | SiliconFlow (GLM-4-9B) |
| Embedding model | bge-large-en-v1.5 | bge-large-zh-v1.5 |
| Chunk sizes | 400 + 800 (dual) | 100 |
| Thread pool | 2 workers (singleton) | None |

## Pitfalls

1. **Embedding model mismatch** — lc_raglw uses `bge-large-en-v1.5` (English), not `bge-large-zh-v1.5` (Chinese). If you built the vector DB with one model, you MUST use the same model for queries.
2. **Two API providers** — LLM uses 智谱AI, embeddings/reranking use SiliconFlow. Both keys must be set.
3. **splits.pkl caching** — If you change chunk_size or overlap, you MUST delete `splits.pkl` in the vector DB directory to force re-chunking.
4. **Content truncation at 500 chars** — After chunking, all text is cleaned and truncated to MAX_CHARS=500. This means big chunks (800) get cut to 500.
5. **Paused process** — lc_raglw.py can end up in `T` (stopped) state if background-launched. Use `ps aux | grep lc_raglw` to check and `kill` to clean up.
6. **Model-to-provider mismatch** — If .env says `glm-4.5-air` but BASE_URL is SiliconFlow, you get "Model does not exist". Always match model names to the API provider.

---

## Variant: telecom_agent.py (All-SiliconFlow, Domain-Specific)

A simpler LangGraph agent for telecom package queries. All APIs use SiliconFlow (no 智谱AI dependency).

**Key differences from lc_raglw.py:**

| Feature | telecom_agent.py | lc_raglw.py |
|---------|-----------------|-------------|
| LLM provider | SiliconFlow (DeepSeek-V4-Flash) | 智谱AI (GLM-4.5-air) |
| Embedding | bge-large-zh-v1.5 | bge-large-en-v1.5 |
| Query translation | Rule-based keyword expansion | Chinese→English translation |
| Intent types | standard / comparison / multi_hop | factual / comparison / synthesis / multi_hop |
| BM25 | Optional (requires rank_bm25) | Required |
| Self-healing | ✅ LLM-based query rewrite | ✅ LLM-based query rewrite |
| Calculator tool | ✅ Built-in (simpleeval) | ❌ |
| Document source | Telecom docs (套餐/转网/搭配) | arxiv papers |

**Architecture:**
```
translate_query (rule-based keyword expansion)
    ↓
classify_intent (standard / comparison / multi_hop)
    ↓
retrieve_docs (vector + BM25 + rerank)
    ↓
evaluate_quality (score < 0.5?)
    ↓ yes              ↓ no
rewrite_query → retry   generate_answer → END
```

**Run with:**
```bash
/home/admin/lc_rag/fresh_env/bin/python3 /home/admin/lc_rag/telecom_agent.py "59元套餐多少流量"
```

**Pitfall:** BM25 requires `rank_bm25` package. If not installed, BM25 is skipped silently (vector-only retrieval).

**Pitfall: venv activation on 无影云电脑** — `source venv/bin/activate` may fail silently or activate the wrong venv (hermes-agent's) because it's already in PATH. Always use the full path to the venv's python binary:
```bash
# ❌ Don't rely on activate
source venv/bin/activate && python3 telecom_agent.py

# ✅ Use full path
/home/admin/lc_rag/fresh_env/bin/python3 /home/admin/lc_rag/telecom_agent.py
```

**Pitfall: SiliconFlow model availability** — Not all models listed on SiliconFlow are enabled. Some return 403 "Model disabled" (e.g., `THUDM/glm-4-9b-chat`). Always verify before hardcoding model names. Confirmed working: `deepseek-ai/DeepSeek-V4-Flash`, `deepseek-ai/DeepSeek-V3`, `Qwen/Qwen2.5-7B-Instruct`.

**Pitfall: .env model-provider mismatch** — If `.env` has `LLM_MODEL=glm-4.5-air` (智谱) but code uses SiliconFlow base URL, you get "Model does not exist". When switching all APIs to SiliconFlow, update `.env` to use SiliconFlow-compatible models like `deepseek-ai/DeepSeek-V4-Flash`.
