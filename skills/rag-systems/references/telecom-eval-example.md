# Telecom Agent Evaluation — Full Example

## Project: telecom-agent-bench

Three frameworks evaluated on the same 30 questions and same telecom plan knowledge base:

| Framework | File | Type |
|-----------|------|------|
| Dify Agent | Dify platform | Low-code ReAct agent |
| LangChain RAG | `lc_ragdx.py` | Pure RAG (Chroma + BM25 + Rerank) |
| LangChain Agent | `taocan_agent.py` | AgentExecutor + Tool Calling |

## Knowledge Base Structure (190 chunks in ChromaDB)

Key data categories:
- **套餐详情** (10 plans: 29/39/59/79/99/129/169/199/229/299元)
- **全额预存方案** (24/36个月, 不同档位预存金额/月到账)
- **橙分期购机方案** (24/36个月, 直降金额/月权益金)
- **流量叠加包** (10GB/12个月, 30GB/36个月, 60GB/36个月, 达人升级包)
- **副卡规则** (减免规则, 99元以下只能2张, 129+可4张)
- **家庭共享包** (最多19人, 省内互打免费)
- **携号转网规则** (不同套餐的转网限制)
- **移动违约金计算** (5种合约类型的违约金公式)
- **移动取消合约流程** (APP投诉步骤)
- **宽带规则** (99→100M城中村, 129→300M老旧小区, 199→300M/1000M)
- **IPTV** (100元接入费, 10元/月)
- **优惠互斥规则** (全额预存 vs 橙分期不可叠加)
- **特殊套餐对应关系** (实付价格→原价映射)
- **芝麻信用分要求** (550/600/650/700分对应不同额度)

## Evaluation Results

### Round 1 — Final (Agent + BM25, 2026-06-11)

| Metric | Value |
|--------|-------|
| Total | **148 / 150 ⭐** |
| Score Rate | **98.7%** |
| Accuracy | 100% (30/30) |
| Completeness | 97% (29/30) |
| Hallucination | 0% |
| Avg Response Time | 17.6s |

### Round 2 — New 30 Questions (2026-06-13)

| Metric | Value |
|--------|-------|
| Total | **145 / 150 ⭐** |
| Score Rate | **96.7%** |
| Accuracy | 97% (29/30) |
| Completeness | 93% (28/30) |
| Hallucination | 0% |
| Avg Response Time | 19.8s |

### Combined: 60 Questions → 97.7% Score Rate, Zero Hallucination

### Round 2 Deductions (3 issues)

1. **Q19 (流程型)**: "How to lower plan via APP complaint?" → Agent refused ("not in KB") but KB doc 27 contains the exact process. **Root cause**: semantic gap between "APP投诉降套餐" and "移动取消合约或者降低套餐的流程". BM25 didn't match the paraphrase.
2. **Q9 (对比型)**: 29元 vs 39元 card rules → missed "39元星卡仅限在校学生" restriction. Agent found card pricing but skipped eligibility metadata.
3. **Q21 (场景型)**: Same student-only gap — agent said "can apply" without restriction.

### By Question Type (Round 1)

| Type | Count | Full Score Rate |
|------|:-----:|:--------------:|
| 单点查询 | 6 | 100% |
| 对比型 | 4 | 100% |
| 多跳推理 | 5 | 80% |
| 流程型 | 4 | 100% |
| 场景型 | 5 | 100% |
| 边界/异常 | 6 | 100% |

### By Question Type (Round 2 — independent questions, new data points)

| Type | Count | Full Score Rate | Notes |
|------|:-----:|:--------------:|-------|
| 单点查询 | 6 | 100% | 79元, 卫星权益, 169元会员, 芝麻信用分, 流量达人, IPTV |
| 对比型 | 5 | 80% | Q9 missed student-only restriction on 39元星卡 |
| 多跳推理 | 5 | 100% | 流量叠加计算, 信用分+补贴, 违约金公式 |
| 流程型 | 4 | 75% | Q19 refused but answer was in KB (semantic paraphrasing gap) |
| 场景型 | 5 | 80% | Q21 missed student eligibility on 39元 |
| 边界/异常 | 5 | 100% | 29元宽带限制, 联通转网规则, 优惠互斥 |

### Before/After Optimization

| Metric | Before (vector only) | After (+BM25) | Improvement |
|--------|:-------------------:|:-------------:|:-----------:|
| Overall Score | 74% | 98.7% | +24.7% |
| 对比型 Full Score | 40% | 100% | +60% |
| 流程型 Full Score | 25% | 100% | +75% |
| 场景型 Full Score | 40% | 100% | +60% |

### Key Optimization: BM25 Hybrid Retrieval

```
Vector Search (k=10) + BM25 (k=10) → Dedup → Rerank (top_n=3) → LLM Generate
```

## Three Framework Comparison

| Metric | Dify Agent | LangChain RAG | LangChain Agent |
|--------|:----------:|:-------------:|:---------------:|
| Accuracy | 5.00/5 | 4.47/5 | 4.73/5 |
| Completeness | 4.87/5 | 4.40/5 | 4.60/5 |
| Hallucination | 5.00/5 | 4.87/5 | 4.90/5 |
| Overall | **97.3%** | 91.6% | **94.9%** |
| Avg Time | 9.02s | **2.86s** | 14.65s |

## Overfitting Analysis

### Evidence of Fitting
- Both Round 1 and Round 2 questions were designed by reading vector DB content
- BM25 keywords and comparison-query-split logic were tuned after seeing Round 1 failures
- All questions are "clean" — no typos, no ambiguous phrasing

### Evidence of Genuine Quality
- Round 2 (completely new questions) scored 96.7% — only 2% drop from Round 1
- Zero hallucination across 60 questions (retrieval + prompt constraints work)
- Correct refusal of out-of-domain questions (weather, balance check)
- BM25 hybrid retrieval is a general improvement, not question-specific

### Verdict
The system is **moderately robust**. The 2% drop between rounds is within acceptable range, but real-world validation with user traffic is needed. The biggest risk is semantic paraphrasing gaps (as seen in Q19 — "APP投诉降套餐" vs "移动取消合约或者降低套餐的流程").

### How to Report in Interviews
> "Our evaluation covers 6 question types across 60 questions, scoring 97.7% with zero hallucination. However, test questions were derived from knowledge base content, which introduces evaluation bias. Production validation requires real user traffic to measure true hit rates and satisfaction."

## Cross-Implementation: Pure Python RAG Evaluation (2026-06-14)

Using the same `eval_results.json` (30 questions from LangChain Agent) to test `simple_rag.py` — a 954-line pure Python RAG with no LangChain dependency.

### Configuration

| Component | Value |
|-----------|-------|
| Embedding | `BAAI/bge-large-zh-v1.5` (SiliconFlow) |
| Rerank | `BAAI/bge-reranker-v2-m3` |
| LLM | `deepseek-ai/DeepSeek-V4-Flash` |
| Vector DB | ChromaDB, 130 chunks |
| Data Source | `/home/admin/Desktop/电信文档/` (22 files) |

### Results

| Metric | Value |
|--------|-------|
| Pass Rate | **29/30 (96.7%)** |
| Avg Response Time | **5.0s** |
| Hallucination | 0 (on tested questions) |
| Failed Q | #7 (对比型 — missing flow/voice data in comparison) |

### Per-Type Breakdown

| Type | Pass | Notes |
|------|:----:|-------|
| 单点查询 | 6/6 | All correct |
| 对比型 | 3/4 | Q7 partial (missing 20GB/30GB flow data) |
| 多跳推理 | 4/4 | All correct |
| 流程型 | 4/4 | All correct |
| 场景型 | 4/4 | All correct (including 2 correct refusals) |
| 边界/异常 | 6/6 | All correct (including 2 correct refusals) |

### Cross-Implementation Comparison

| Metric | LangChain Agent | Pure Python RAG | Delta |
|--------|:--------------:|:--------------:|:-----:|
| Pass Rate | 98.7% | 96.7% | -2.0% |
| Avg Time | 17.6s | 5.0s | **-72%** |
| Hallucination | 0% | 0% | — |
| Code Size | 413 lines | 954 lines | +131% |
| LangChain Dep | Yes | No | — |

**Key insight:** Pure Python RAG is 72% faster (no LangChain overhead) at the cost of 2% accuracy and 2x code size. The speed advantage comes from direct API calls without framework abstraction layers.

### SiliconFlow bge-large-zh-v1.5 Gotcha

During this evaluation, discovered that `bge-large-zh-v1.5` has a **500-character input limit** on SiliconFlow's API. Texts longer than 500 chars return HTTP 400 (`code: 20015`). This is NOT documented in SiliconFlow's API docs. The `bge-m3` model has no such limit.

**Fix applied:** Truncate texts in `embed_documents()` before sending to API:
```python
batch_texts = [t[:500] if len(t) > 500 else t for t in batch_texts]
```

## Lessons Learned

1. **BM25 is critical for Chinese telecom data** — exact keyword matching catches pricing terms that vector search misses
2. **3-second delays between questions** prevent API rate limiting
3. **Agent mode with tool calling** handles multi-step questions better than pure RAG
4. **Dedup before rerank** prevents duplicate chunks from biasing scores
5. **Per-type analysis matters** — overall score can hide weak question types
6. **Second-round eval validates generalization** — 96.7% on different questions confirms robustness
7. **"Refusal trap" is real** — agent may refuse questions whose answers ARE in the KB, due to semantic paraphrasing gaps
8. **Eligibility restrictions need explicit checking** — metadata-level constraints (e.g., "student-only") can be missed even when product features match
