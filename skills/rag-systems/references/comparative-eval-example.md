# Comparative Evaluation Example: dx_agent vs simple_rag

## Context

Two RAG systems evaluated head-to-head on 30 telecom (运营商套餐) questions:
- **dx_agent**: Agent-based (OpenAI tool calling + RAGWorkflow), knowledge base with 橙分期/全额预存/达人包, uses `python3.10`, `run_single()` returns `TypedDict(answer, success, processing_time)`
- **simple_rag**: Pure Python RAG (ChromaDB + BM25 + reranker), limited KB (套餐详情 + 转网规则 only), uses `python3`, `rag.query()` returns `QueryResult(answer, sources, success, processing_time)`. **Note**: After vector DB sharing fix, now uses dx_agent's 471-chunk knowledge base.

## Results Summary

| Metric | dx_agent | simple_rag | Winner |
|--------|----------|------------|--------|
| Success rate | 30/30 | 30/30 | tie |
| Accuracy | 73% | 70% | dx_agent |
| Hallucination | 13% (4/30) | 7% (2/30) | **simple_rag** |
| Retrieval failure | 0% (0/30) | 20% (6/30) | **dx_agent** |
| Completeness | 67% | 60% | dx_agent |
| Avg latency | 3.0s | 14.8s | **dx_agent** |
| Weighted total | 78 | 65 | dx_agent |

## Key Findings

### dx_agent strengths
- Hybrid retrieval (vector + BM25 + graph traversal) — zero retrieval failures
- 5x faster (3.0s vs 14.8s)
- Agent architecture supports tool calling (calculations, stats)
- Broader knowledge base (橙分期, 全额预存, etc.)

### dx_agent weaknesses
- Higher hallucination (13%) — especially on 29元套餐 data (claimed 1GB instead of 10GB)
- Returns Markdown tables for comparison questions — poor WeChat display
- Confused 主卡 vs 副卡 携号转网 process (Q23)

### simple_rag strengths
- Lower hallucination (7%) — prefers to refuse rather than fabricate
- Plain text answers — better for chat display
- No format issues

### simple_rag weaknesses
- 20% retrieval failure — misses data that IS in the KB (29元套餐, 299卫星权益)
- 5x slower, worst case 141.8s
- Weaker multi-hop reasoning and calculation

## Scoring Dimensions Used

1. **准确率 (Accuracy)**: Factually correct based on KB
2. **幻觉率 (Hallucination Rate)**: Fabricated info not in KB (lower is better)
3. **检索能力 (Retrieval)**: Successfully found relevant KB content
4. **完整性 (Completeness)**: Covered all aspects of the question
5. **耗时 (Latency)**: Response time

Weights: 准确率30% + 幻觉率20% + 检索能力25% + 完整性15% + 耗时10%

## Lesson: Hallucination vs Retrieval Failure

These are distinct failure modes that require different fixes:
- **Hallucination**: System returns plausible but wrong info → fix: better prompts, stricter grounding
- **Retrieval failure**: System says "找不到" when info exists → fix: improve retrieval pipeline, chunk strategy, embedding model

A system can have LOW hallucination but HIGH retrieval failure (simple_rag pattern: refuses when uncertain).
A system can have LOW retrieval failure but HIGH hallucination (dx_agent pattern: always finds something, sometimes fabricates details).

## Post-Eval Fix: Vector DB Sharing (2026-06-22)

After the initial eval revealed simple_rag had 20% retrieval failure (6/30 questions missed data that was in the KB), we investigated and found:

1. **Root cause**: simple_rag had only 144 document chunks (套餐详情.txt + 转网规则.txt), while dx_agent had 471 chunks (comprehensive telecom data including 橙分期, 搭配表, etc.)
2. **Both systems used the same embedding model** (`bge-large-zh-v1.5` via SiliconFlow API) — verified by checking .env files (NOT code defaults, which were different: bge-small vs bge-large)
3. **Collection name mismatch**: dx_agent stored vectors under `telecom_rag`, simple_rag looked for `langchain_collection` (default). Fixed by adding `COLLECTION_NAME=telecom_rag` to simple_rag's .env
4. **Configuration change**: Added `VECTOR_DB_PATH=/home/admin/vector_dbs/rag_telecom_db` to simple_rag's .env

**Result after fix**: Previously failed questions now work:
- 29元套餐流量: ❌ → ✅ (10GB, 100分钟)
- 299卫星权益: ❌ → ✅ (20分钟语音, 20条短信)
- 59vs99转网: ❌ → ✅ (59不能转, 99只能转1个移动)

**Key lesson**: Retrieval failure is often a DATA problem, not a RETRIEVAL algorithm problem. Before optimizing the retrieval pipeline, check if the data is actually in the vector DB.

## Post-Fix Cleanup: Model Config Hardcoding (2026-06-22)

After the vector DB sharing fix, we also cleaned up the `.env` files for both systems:

**Removed from .env, hardcoded in Config class:**
- `LLM_MODEL` (dx_agent: `GLM-4-32B-0414`, simple_rag: `DeepSeek-V4-Flash`)
- `EMBED_MODEL` (both: `bge-large-zh-v1.5`)
- `LLM_TEMPERATURE` (both: `0.3`)
- `LLM_MAX_TOKENS` (both: `1024`)

**Rationale**: These configs are coupled to data (EMBED_MODEL → vector DB dimensions) or core behavior (LLM_MODEL → answer quality). Putting them in `.env` implies flexibility to change, but changing them silently breaks the system. Hardcoding makes the system self-documenting and prevents accidental misconfiguration.

**Final .env contents (both systems):** Only API keys and vector DB paths — nothing else.
