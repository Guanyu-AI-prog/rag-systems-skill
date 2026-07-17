# RAG Evaluation Testing — Quiz-Based Approach

Test RAG system quality by generating quiz questions from the vector database and measuring retrieval + answer accuracy.

## When to Use

- After building or updating a vector database
- After changing embedding model, chunk size, or retrieval parameters
- Before deploying to production
- Benchmarking different RAG configurations

## Step 1: Generate Quiz Questions from Knowledge Base

Scan the knowledge base documents to identify topics, then generate questions across difficulty levels:

| Level | Type | Example |
|-------|------|---------|
| Factual | Direct lookup | "What is X?" / "X 的参数是什么？" |
| Comparison | Cross-document | "Compare X and Y" / "X 和 Y 的区别？" |
| Synthesis | Multi-document | "Summarize trends in X" / "X 的发展趋势？" |
| Technical detail | Formula/evidence | "What is the formula for X?" |

Coverage rule: aim for questions spanning ALL major documents/topics in the knowledge base, not just the popular ones.

## Step 2: Write a Test Script

```python
#!/home/admin/lc_rag/venv/bin/python3  # USE THE VENV PYTHON, not system python3
"""RAG quiz test script — runs ask() for each question, saves JSON results."""
import sys, os, time, json
sys.path.insert(0, "/path/to/rag/project")

from your_rag_module import ask  # import the ask() function

questions = [
    "Question 1?",
    "Question 2?",
    # ... 20-30 questions recommended
]

results = []
for i, q in enumerate(questions, 1):
    start = time.time()
    try:
        answer = ask(q)
        elapsed = time.time() - start
        results.append({"id": i, "question": q, "answer": answer,
                        "time_seconds": round(elapsed, 1), "status": "ok"})
    except Exception as e:
        results.append({"id": i, "question": q, "answer": None,
                        "time_seconds": round(time.time() - start, 1),
                        "status": f"error: {str(e)[:200]}"})

with open("rag_quiz_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
```

### Critical: Use the venv Python

System Python won't have langgraph/langchain/chromadb installed. Always use:
```bash
/path/to/rag/venv/bin/python test_script.py
```

NOT `python3 test_script.py` — it will fail with `ModuleNotFoundError: No module named 'langgraph'`.

## Step 3: Run as Background Process

```bash
# Run in Hermes background (will notify on completion)
terminal(background=true, notify_on_complete=True, command="cd /path && venv/bin/python test_script.py")
```

30 questions × ~15-20s each = ~10-15 minutes total.

## Step 4: Analyze Results

```python
import json
with open('rag_quiz_results.json') as f:
    results = json.load(f)

total = len(results)
ok = sum(1 for r in results if r['status'] == 'ok')
avg_time = sum(r['time_seconds'] for r in results) / total

# Quality metrics
no_info = [r['id'] for r in results if '暂无' in r.get('answer','') or '无法' in r.get('answer','')]
has_source = [r['id'] for r in results if '来源' in r.get('answer','')]

print(f"Success: {ok}/{total}, Avg time: {avg_time:.1f}s")
print(f"Retrieval failures: {len(no_info)} → {no_info}")
print(f"Source citations: {len(has_source)}/{total}")
```

## Metrics to Track

| Metric | Good | Acceptable | Bad |
|--------|------|-----------|-----|
| Success rate | >90% | 70-90% | <70% |
| Avg response time | <15s | 15-30s | >30s |
| Retrieval failures | <10% | 10-20% | >20% |
| Source citation rate | >80% | 60-80% | <60% |

## Common Pitfalls in Batch Testing

### API Rate Limiting (429 Errors)

**Symptom:** First ~20 questions pass, then remaining questions all fail with `429 Too Many Requests`.

**Cause:** Each question makes 3+ API calls (embedding + rerank + LLM). With 30 questions and no delay, that's 90+ rapid requests. SiliconFlow free tier limits to ~5-10 requests/minute.

**Fix:** Add delay between questions:
```python
import time
for i, q in enumerate(questions, 1):
    answer = ask(q)
    results.append(...)
    if i < len(questions):
        time.sleep(3)  # 3s delay avoids 429
```

30 questions × 3s delay = ~90s overhead, total ~3-5 minutes. Worth it to avoid 8+ failed questions.

### retrieve_k Too Large

**Symptom:** Slow responses, higher API costs, no accuracy improvement.

**Cause:** Setting `retrieve_k=30` sends 30 documents to the reranker each time. The reranker's value is in re-ranking a reasonable candidate set, not processing the entire DB.

**Fix:** Use `retrieve_k=10, rerank_top=3` as default. Only increase if recall@10 is too low.

## Common Findings

1. **Math/formula questions fail** — arxiv markdown conversion often loses LaTeX formulas. Vector search can't match what wasn't indexed properly.
2. **Short document names cause retrieval misses** — if the knowledge base has sparse content on a topic, BM25 + vector search may both miss.
3. **Comparison questions score well** — if multiple related documents exist, the reranker excels at cross-document synthesis.
4. **Source citation accuracy** — the LLM sometimes cites the wrong paper. Check that `来源` field matches the actual retrieval context.

## Example: ArXiv Papers RAG Test Results (41 papers, 13935 chunks)

- 30/30 questions answered successfully
- Average 17.4s per question
- 3 retrieval failures (formula-heavy questions)
- 26/30 correctly cited sources
- Best performance: DeepSeek series (dedicated papers in KB)
- Worst performance: Self-Attention formula, CLIP details (sparse coverage)
