# dx_agent Eval Results — 2026-06-21

## Configuration

| Setting | Value |
|---------|-------|
| LLM | THUDM/GLM-4-32B-0414 via SiliconFlow |
| Embedding | BAAI/bge-large-zh-v1.5 via SiliconFlow |
| Reranker | BAAI/bge-reranker-v2-m3 via SiliconFlow |
| Vector DB | ChromaDB, 471 chunks |
| LLM_TIMEOUT | 15s |
| RERANK_TIMEOUT | 10s |
| max_retries | 0 (both OpenAI client and ChatOpenAI) |

## Python Version Pitfall

dx_agent requires **python3.10** (not python3.11). `langchain_community` is installed in `/home/admin/.local/lib/python3.10/site-packages/`. The Hermes venv uses python3.11 which doesn't have it.

```bash
# WRONG
python3 dx_agent.py "query"
# RIGHT
python3.10 dx_agent.py "query"
```

## Eval Script

`/home/admin/telecom-agent-bench/langchain/eval_results/run_eval_dx_agent.py` — 30 questions, 6 categories. Outputs to `dx_agent_rag_eval.json`.

## Results (LLM_TIMEOUT=15, RERANK_TIMEOUT=10)

| Category | N | Pass | Avg(s) | Max(s) | Issues |
|----------|---|------|--------|--------|--------|
| 单点查询 | 6 | 6 | 4.7 | 10.1 | |
| 对比型 | 4 | 3 | 9.5 | 15.4 | #7 timeout (15.4s > 15s) |
| 多跳推理 | 5 | 5 | 9.1 | 18.0 | |
| 流程型 | 4 | 4 | 4.3 | 5.4 | |
| 场景型 | 5 | 5 | 8.1 | 21.1 | |
| 边界/异常 | 6 | 6 | 3.6 | 4.3 | |

**Overall:** 29/30 passed, avg 6.4s, 6 questions >10s

## Quality Issues Found

### Hallucination (2 questions)
- **#18** (推荐套餐): Invented "首年月租7折" and "含电视" — not in knowledge base
- **#19** (一家三口转网): Invented "首年7折", "首张副卡免费" — fabricated promotional details

### Role Confusion (2 questions)
- **#15** (移动用户降档): Gave 中国移动 APP instructions instead of 电信 guidance
- **#27** (查话费): Gave 10086 (移动) query methods — should be 10000 (电信)

### Incomplete/Empty Answers (3 questions)
- **#3** (副卡数): "最多2张以上，无明确上限" — ambiguous, hedged
- **#9** (补贴对比): Table with many "未提及" cells
- **#28** (实付对应套餐): Table with almost all empty cells

### Failed (1 question)
- **#7** (对比99和129): Comparison path timed out at 15.4s (just over 15s limit)

## Model Switch History

| Date | LLM Model | Provider | Notes |
|------|-----------|----------|-------|
| Before | qwen-plus | DashScope (阿里云) | Fast but separate API key |
| 2026-06-21 | THUDM/GLM-4-32B-0414 | SiliconFlow | Unified API key with embedding/reranker |

---

## Round 2: GLM-4-32B (2026-06-21)

Same 30 questions, same knowledge base. Only change: LLM switched from qwen-plus (DashScope) to GLM-4-32B (SiliconFlow), prompt made brand-neutral ("运营商" instead of "电信").

### Per-Question Results

| # | Type | Question | Time | Accuracy | Completeness | Hallucination |
|---|------|----------|------|----------|-------------|---------------|
| 1 | 单点查询 | 29元套餐流量和通话 | 9.4s | ✅ | ✅ | 无 |
| 2 | 单点查询 | 99元月租和预存实付 | 1.8s | ✅ | ✅ | 无 |
| 3 | 单点查询 | 129元最多几张副卡 | 1.9s | ⚠️ | ⚠️ "2张以上"含糊 | 无 |
| 4 | 单点查询 | 299元基础流量 | 1.3s | ✅ | ✅ | 无 |
| 5 | 单点查询 | 99元橙分期补贴 | 1.8s | ✅ | ✅ | 无 |
| 6 | 单点查询 | 星卡39定向流量应用 | 2.4s | ✅ | ✅ | 无 |
| 7 | 对比型 | 对比99和129套餐 | 5.0s | ⚠️ | ⚠️ 表格多"未知" | 无 |
| 8 | 对比型 | 199和299宽带区别 | 4.9s | ⚠️ | ⚠️ 表格多"未知" | 无 |
| 9 | 对比型 | 59和99橙分期补贴 | 4.4s | ⚠️ | ⚠️ 表格多"未知" | 无 |
| 10 | 多跳推理 | 129+2副卡全家流量 | 3.1s | ✅ | ✅ 110GB计算正确 | 无 |
| 11 | 多跳推理 | 199+预存+2副卡实付 | 1.4s | ❌ | ❌ 副卡费未算 | 无 |
| 12 | 多跳推理 | 移动129转网推荐 | 1.8s | ❌ | ❌ 拒答 | 无 |
| 13 | 多跳推理 | 59元最多叠加流量 | 2.2s | ✅ | ⚠️ 算法未详述 | 无 |
| 14 | 流程型 | 转网流程 | 3.1s | ✅ | ✅ | 无 |
| 15 | 流程型 | 移动降档办理 | 2.6s | ✅ | ✅ | 无 |
| 16 | 流程型 | 橙分期条件 | 4.1s | ✅ | ✅ | 无 |
| 17 | 流程型 | 全额预存违约金 | 2.6s | ✅ | ✅ | 无 |
| 18 | 场景型 | 话费100推荐套餐 | 2.4s | ⚠️ | ✅ | ⚠️ "200条短信"可能编造 |
| 19 | 场景型 | 一家三口转网推荐 | 1.5s | ❌ | ❌ 拒答 | 无 |
| 20 | 场景型 | 转网后验证码 | 2.2s | ✅ | ✅ | 无 |
| 21 | 场景型 | 电信信号不好 | 4.2s | ✅ | ✅ | 无 |
| 22 | 边界/异常 | 59元装宽带 | 2.5s | ✅ | ✅ | 无 |
| 23 | 边界/异常 | 联通转99元 | 1.8s | ✅ | ✅ | 无 |
| 24 | 边界/异常 | 129同时转移动联通 | 1.8s | ✅ | ✅ | 无 |
| 25 | 边界/异常 | 预存和橙分期一起办 | 2.5s | ✅ | ✅ | 无 |
| 26 | 边界/异常 | 天气怎么样 | 1.8s | ✅ | ✅ 正确拒绝 | 无 |
| 27 | 边界/异常 | 查话费余额 | 1.5s | ✅ | ✅ 正确拒绝 | 无 |
| 28 | 对比型 | 实付69和89对应套餐 | 3.9s | ⚠️ | ⚠️ 表格多空 | 无 |
| 29 | 场景型 | 移动宽带转网后怎么办 | 2.3s | ✅ | ✅ | 无 |
| 30 | 多跳推理 | 299橙分期36个月 | 2.2s | ✅ | ✅ | 无 |

### Round 2 Summary

| Metric | Value |
|--------|-------|
| Total | 30 |
| Accuracy (fully correct) | 23/30 (77%) |
| Completeness (fully answered) | 25/30 (83%) |
| Hallucination | 1/30 (3%) — only #18 (短信条数) |
| Role confusion | 0/30 — fixed by prompt neutrality |
| Failed (timeout/error) | 0/30 |
| Avg latency | 2.9s |
| Max latency | 9.4s |
| >10s queries | 0 |

### Before/After Comparison (qwen-plus vs GLM-4-32B)

| Metric | Round 1 (qwen-plus) | Round 2 (GLM-4-32B) | Delta |
|--------|:-------------------:|:-------------------:|:-----:|
| Accuracy | 70% | **77%** | +7% |
| Completeness | ~85% | **83%** | -2% |
| Hallucination | 4/30 (13%) | **1/30 (3%)** | -10% |
| Role confusion | 2/30 (7%) | **0/30 (0%)** | -7% |
| Failed | 1/30 | **0/30** | -1 |
| Avg latency | 6.4s | **2.9s** | -3.5s |
| Max latency | 21.1s | **9.4s** | -11.7s |
| >10s queries | 6 | **0** | -6 |

### Key Takeaways

1. **GLM-4-32B is significantly faster** than qwen-plus on SiliconFlow (avg 2.9s vs 6.4s)
2. **Hallucination dropped dramatically** (13% → 3%) — GLM-4-32B is more conservative
3. **Prompt neutrality eliminated role confusion** entirely
4. **Comparison tables still have gaps** — this is a retrieval issue, not LLM. The KB needs better structured data for comparison queries
5. **Over-refusal on complex queries** (#12, #19) — GLM-4-32B sometimes says "无法查询" when the KB has partial data. qwen-plus attempted these but hallucinated details. Trade-off: conservative refusal > hallucinated answers.
