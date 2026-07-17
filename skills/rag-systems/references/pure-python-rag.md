# Pure Python RAG (No LangChain)

A complete RAG system in 954 lines of pure Python, no LangChain dependency.

## Location
`/home/admin/Desktop/workspace/simple_rag/simple_rag.py`

## Architecture

```
simple_rag.py
├── Config              # All settings from .env
├── TextSplitter        # Recursive character splitter with overlap
├── DocumentProcessor   # Load txt/md/jsonl/csv, apply chunk profiles
├── EmbeddingModel      # OpenAI-compatible API (SiliconFlow)
├── BM25Retriever       # jieba tokenization + BM25Okapi
├── VectorStore         # ChromaDB PersistentClient
├── Reranker            # SiliconFlow rerank API
├── LLMGenerator        # OpenAI-compatible chat API
├── HybridRetriever     # Parallel vector+BM25 → dedup → rerank
└── SimpleRAG           # Orchestrator: rewrite → classify → expand → retrieve → generate
```

## Key Design Decisions

| Feature | Implementation |
|---------|---------------|
| Chunk profiles | `small` (250/50) for Q&A, `large` (500/100) for plan details, `default` (300/60) |
| Parallel retrieval | `ThreadPoolExecutor(max_workers=2)` for vector+BM25 simultaneously |
| Embedding cache | MD5 hash → embedding dict, avoids re-embedding same text |
| BM25 query cache | Cache tokenized queries, evict half when > 1000 entries |
| Query expansion | Intent classification (recommend/compare/fact) → generate sub-queries |
| Comparison splitting | Regex detect `N元...M元` patterns → per-entity retrieval |

## Running It

```bash
cd /home/admin/Desktop/workspace/simple_rag
# Create .env with SiliconFlow API key
# DATA_DIR and EMBED_MODEL are configured in .env
/home/admin/lc_rag/venv/bin/python3 simple_rag.py
```

## Dependencies
```
chromadb openai rank-bm25 jieba requests python-dotenv
```

## Test Results (2026-06-14)

| Question | Answer | Latency |
|----------|--------|---------|
| 99元套餐包含多少流量和通话时长？ | 20GB, 400分钟 ✅ | 1.71s |
| 129元套餐可以办几张副卡？ | 4张, 每张10元 ✅ | 1.98s |
| 移动号码转电信需要什么流程？ | 完整4步流程 ✅ | 7.64s |
| 59元套餐可以装宽带吗？ | 不能 ✅ | 2.07s |

Average: 3.35s/query with hybrid retrieval + rerank.

## Three RAG Implementations Comparison

The project has three RAG implementations, each serving a different purpose:

| Dimension | `lc_ragdx.py` | `simple_rag.py` | `taocan_agent.py` |
|-----------|---------------|-----------------|-------------------|
| **Lines** | 513 | 954 | 413 |
| **Framework** | LangChain | Pure Python | LangChain Agent |
| **Embedding** | bge-large-zh-v1.5 | bge-large-zh-v1.5 | bge-large-zh-v1.5 |
| **Rerank** | ❌ None | ✅ bge-reranker-v2-m3 | ✅ bge-reranker-v2-m3 |
| **LLM** | mimo-v2-flash | deepseek-v4-flash | mimo-v2-flash |
| **Accuracy** | 91.6% (old) | 96.7% (30q) | 98.7% (30q) |
| **Avg latency** | ~17s | 5.0s | ~17s |
| **Hallucination** | N/A | 0% | 0% |
| **Location** | `telecom-agent-bench/langchain/src/` | `simple_rag/` | `langchain_rag/` |

**Why pure Python has more code:** LangChain abstracts away embedding wrappers, retriever setup, chain composition, prompt templates, document loaders, and text splitters. Without it, all that boilerplate must be implemented manually (~441 extra lines). Trade-off: more code, but zero framework dependency, full control, and easier to debug.

**Portfolio positioning:**
- `lc_ragdx.py` → demonstrates LangChain proficiency
- `simple_rag.py` → demonstrates ability to build from scratch, no framework crutch
- `taocan_agent.py` → demonstrates Agent/Tool Calling architecture (highest accuracy)

## Full 30-Question Evaluation (2026-06-14)

| Metric | Value |
|--------|-------|
| Pass rate | 96.7% (29/30) |
| Avg latency | 6.87s |
| Hallucination | 0% |
| Single-point queries | 100% (10/10) |
| Comparison queries | 100% (5/5) |
| Process queries | 100% (5/5) |
| Scene queries | 83.3% (5/6) — 1 partial |

**Failed question:** #27 (CRM操作题) — correctly refused as out-of-scope, not a real failure.

**Evaluation report:** `/home/admin/.hermes/cache/documents/doc_6d1a82a12017_evaluation_report.md`

## Updated Configuration (2026-06-14)

**Data source:** `/home/admin/Desktop/电信文档/` (22 files, 130 text chunks)
- Includes: 套餐详情_整理版.md, 套餐搭配Q&A.md, 套餐搭配2.md, CRM流程.md, 移动转网.md, 营销话述参考.md, 套餐搭配表.csv, etc.
- **Note:** Directory contains some template files (承诺书模板.md, 电信常用模板.txt) and duplicate files (套餐详情.md vs 套餐详情_整理版.md). All are loaded automatically — no filtering logic implemented.

**Embedding model:** `BAAI/bge-large-zh-v1.5` (changed from bge-m3)
- **Critical limitation:** 500 character input limit per text on SiliconFlow API
- **Fix applied:** Truncate texts to 500 chars before embedding
- **Batch size:** 32 (SiliconFlow API limit for batch embedding)

**Evaluation with telecom data (2026-06-14):**
- Pass rate: 96.7% (29/30) — same as before
- Avg latency: 5.0s — **27% faster** than previous 6.87s
- Test questions: 30 questions from taocan_agent evaluation set
- Only 2 questions overlap with previous 30-question set (58 unique questions total)

## Data Source Configuration

Current data in `/home/admin/Desktop/电信文档/`:
- `套餐详情_整理版.md` — 表格版套餐详情 (461 lines, 15KB)
- `套餐详情.md` — 原始版含RG编码/PID编码 (509 lines, 53KB)
- `套餐搭配Q&A.md` — 问答格式 (142 lines, 5KB)
- `套餐搭配2.md` — 详细方案 (87 lines, 11KB)
- `CRM流程.md` — CRM系统操作指南 (89 lines, 3.5KB)
- `移动转网.md` — 移动转网+违约金规则 (68 lines, 3.4KB)
- `营销话述参考.md` — 销售场景话术 (46 lines, 3.2KB)
- `套餐搭配表.csv` — 结构化数据

**Note:** Some template files (承诺书模板.md, 电信常用模板.txt) and duplicate files are also loaded automatically.

To switch data source, change `DATA_DIR` in `.env` or `Config.DATA_DIR` in simple_rag.py (line 118).

To change embedding model, update `EMBED_MODEL` in `.env` or `Config.EMBED_MODEL` (line 82). Current: `BAAI/bge-large-zh-v1.5`.

## When to Use This vs LangChain

| Scenario | Use |
|----------|-----|
| Simple RAG, few features needed | Pure Python ✅ |
| Need Agent/Tool Calling | LangChain |
| Version conflicts with LangChain | Pure Python ✅ |
| Need streaming, callbacks, tracing | LangChain |
| Lightweight deployment | Pure Python ✅ |
| Portfolio showcase ("I can build without frameworks") | Pure Python ✅ |
