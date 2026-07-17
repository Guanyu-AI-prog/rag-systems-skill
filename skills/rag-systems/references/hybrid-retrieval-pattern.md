# Hybrid Retrieval Pattern: Vector + BM25 + Dedup + Rerank

## When to Use

Add BM25 keyword search alongside vector search when:
- Queries contain exact terms, product names, or numbers that vector similarity might miss
- You have a Chinese-language knowledge base (jieba tokenization helps BM25 a lot)
- Retrieval accuracy is below expectations on keyword-heavy queries (e.g., "59套餐", "129元")

## Dependencies

```bash
# Install dependencies: rank-bm25 jieba
```

## Pattern

```python
from rank_bm25 import BM25Okapi
import jieba


def deduplicate_docs(docs):
    """去重：基于文本内容去重，保留顺序"""
    seen = set()
    unique = []
    for text in docs:
        normalized = text.strip()
        if normalized not in seen:
            seen.add(normalized)
            unique.append(text)
    return unique


class BM25Retriever:
    """BM25 关键词检索：基于 jieba 分词（带缓存）"""

    def __init__(self, corpus):
        self.corpus = corpus
        tokenized = [list(jieba.cut(doc)) for doc in corpus]
        self.bm25 = BM25Okapi(tokenized)

    def search(self, query, top_k=10):
        tokenized_query = list(jieba.cut(query))
        scores = self.bm25.get_scores(tokenized_query)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [self.corpus[i] for i, _ in ranked[:top_k]]


# BM25 索引缓存（避免每次查询都重建 — Agent 模式下每题调用多次）
_bm25_cache = {'corpus_hash': None, 'retriever': None}


def get_bm25_retriever(corpus):
    """获取 BM25 检索器（带缓存）"""
    corpus_hash = hash(tuple(corpus))
    if _bm25_cache['corpus_hash'] != corpus_hash or _bm25_cache['retriever'] is None:
        _bm25_cache['retriever'] = BM25Retriever(corpus)
        _bm25_cache['corpus_hash'] = corpus_hash
    return _bm25_cache['retriever']


def advanced_retriever(query, retrieve_k=10, rerank_top=3):
    """
    核心检索函数：向量检索 + BM25 关键词检索 + 去重 + Rerank 重排序
    返回 rerank 后的 top-N 文档内容列表
    """
    from langchain_chroma import Chroma

    vs = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=SimpleEmb(),
        collection_name=COLLECTION_NAME,
    )

    # 1. 向量检索
    vector_docs = vs.similarity_search_with_score(query, k=retrieve_k)
    vector_texts = [doc.page_content for doc, _ in vector_docs]

    # 2. BM25 关键词检索（Top K 与向量检索一致，带缓存）
    try:
        all_data = vs.get(include=['documents'])
        all_corpus = all_data.get('documents', [])
    except Exception:
        all_corpus = vector_texts

    if all_corpus:
        bm25_retriever = get_bm25_retriever(all_corpus)
        bm25_texts = bm25_retriever.search(query, top_k=retrieve_k)
    else:
        bm25_texts = []

    # 3. 合并 + 去重
    combined = vector_texts + bm25_texts
    unique_docs = deduplicate_docs(combined)

    if not unique_docs:
        return []

    # 4. Rerank 重排序
    reranked = rerank(query, unique_docs, top_n=rerank_top)
    return [text for _, _, text in reranked]
```

## Architecture

```
用户问题
  ↓
① 向量检索 (k=10)        ← semantic similarity
② BM25 检索 (k=10)      ← keyword matching (jieba tokenization)
  ↓
③ 合并 + 去重            ← deduplicate_docs()
  ↓
④ BGE Reranker (top_n=3) ← SiliconFlow API rerank endpoint
  ↓
返回 top-N 文档
```

## Key Design Decisions

1. **BM25 Top K = Vector Top K**: Both retrievers fetch the same number of candidates (retrieve_k). This ensures neither dominates the merge.

2. **Dedup before Rerank**: Merging two retrievers produces duplicates. Dedup reduces the candidate pool, saving rerank API calls.

3. **Full corpus for BM25**: BM25 needs the full corpus to build its index. We fetch all documents from ChromaDB via `vs.get(include=['documents'])`. For very large corpora (>10K docs), consider caching the BM25 index.

4. **Fallback to vector-only**: If ChromaDB get() fails, fall back to vector results only. This ensures the pipeline never breaks.

## Performance Notes

- **CRITICAL: Cache the BM25 index.** The naive pattern rebuilds BM25 on every call. In Agent mode (multiple tool calls per question), this causes extreme slowness — the process appeared "stuck" for 10+ minutes on a single question. Always use the `get_bm25_retriever()` cached version.
- ChromaDB `vs.get(include=['documents'])` returns ALL documents. With 100+ chunks this is fine; with 10K+ chunks, consider pagination or pre-caching.
- jieba has a small startup cost (~0.5s) on first import. Subsequent calls are fast.
- Agent mode is significantly slower than direct RAG mode (avg 17.6s vs 6.0s) because each question may trigger multiple tool calls, each with its own retrieval + rerank cycle.

## Benchmarking Results (taocan_agent.py)

Real-world comparison on 30-question telecom package evaluation:

| Metric | Vector-only | Vector+BM25 | Improvement |
|--------|:-----------:|:-----------:|:-----------:|
| Overall score | 74% | **98.7%** | +24.7% |
| Accuracy | 73% | 100% | +27% |
| Completeness | 63% | 97% | +34% |
| Comparison questions | 40% | 100% | +60% |
| Process/flow questions | 25% | 100% | +75% |
| Scenario questions | 40% | 100% | +60% |

BM25 excels at matching exact terms: "实付69元", "违约金", "转网流程", "联通不能转" — queries where vector similarity fails due to semantic distance.

## Pitfall: Empty Vector Store Returns 0 Results

**Symptom**: Hybrid retriever returns 0 results for ALL queries. BM25 and vector both empty.

**Root cause**: Wrong `PERSIST_DIR` pointing to an empty Chroma DB (e.g., `./chroma_db` with 0 documents instead of `./taocan_rag_db` with 190 documents).

**Debug steps**:
```python
# Check document count in the vector store
from langchain_chroma import Chroma
vs = Chroma(persist_directory="./chroma_db", collection_name="langchain")
print(f"Documents: {vs._collection.count()}")  # Should be > 0
```

**Fix**: Find the correct chroma_db directory:
```bash
find /path/to/project -name "chroma_db" -type d 2>/dev/null
# Check each one for document count
```

This happened because the code was copied from a different project directory where the DB path was different. Always verify the persist_directory matches the actual data location.

## Pitfall: rerank_top=3 Is Insufficient for Comparison Queries

**Symptom**: Comparison questions (e.g., "对比99元和129元套餐") get high scores in evaluation but the Agent makes 5-10 tool calls per question, taking 30-60 seconds per answer. Individual queries seem fine, but the process is slow.

**Root cause**: Each套餐's information is spread across **multiple document segments** (6+ for a typical套餐: basic info, promo plans, full prepay, installment, sub-card rules, carrier transfer rules). With `rerank_top=3`, the reranker can only select 3 documents total. For a comparison of TWO套餐, you'd need ~6-12 documents to cover both fully.

**How the Agent compensates**: When first retrieval doesn't cover all details, the Agent detects gaps in its answer and makes additional tool calls with different queries (e.g., "129元套餐副卡费用计算", "99元套餐宽带详情"). This works (98.7% accuracy) but is expensive.

**Evidence from 30-question benchmark**:
- Single-hop queries: 1 tool call, ~13s (fine)
- Comparison queries: 5 tool calls, ~26s (slow but correct)
- Complex scenarios: 10 tool calls, ~59s (very slow)

**Solutions** (pick one based on your needs):
1. **Increase rerank_top to 5-6**: Simple fix, slightly more context for LLM
2. **Detect comparison queries and split**: Extract entity names, retrieve separately, merge results
3. **Rely on Agent decomposition** (recommended): In Agent/Tool Calling mode, the LLM naturally decomposes comparison queries into separate tool calls. This was validated in testing — 3/4 comparison queries were correctly decomposed by the Agent without any special detection code.

**Recommended approach: Use Option 2 as a safety net + let Agent decompose naturally.**

The Agent handles most comparisons itself (e.g., "对比99和129" → Agent calls tool twice with "99元套餐 宽带" and "299元套餐 宽带"). The comparison detection in the tool acts as a fallback for direct queries where no Agent decomposition happens.

```python
# Validated implementation (taocan_agent.py, tested 2026-06-11)
def taocan_knowledge_query(query: str) -> str:
    """查询运营商套餐知识库"""
    # Detect comparison queries: extract multiple plan numbers
    comparison_pattern = r'(\d+)\s*元?\s*套餐.*?(\d+)\s*元?\s*套餐|(\d+).*?和.*?(\d+)|(\d+).*?对比.*?(\d+)'
    match = re.search(comparison_pattern, query)

    all_docs = []
    if match:
        numbers = [g for g in match.groups() if g]
        if len(numbers) >= 2:
            for num in numbers:
                docs = advanced_retriever(f'{num}元套餐', retrieve_k=10, rerank_top=3)
                all_docs.extend(docs)
            all_docs = deduplicate_docs(all_docs)

    if not all_docs:
        all_docs = advanced_retriever(query, retrieve_k=10, rerank_top=3)

    if not all_docs:
        return "知识库中未找到相关信息。"
    parts = []
    for i, text in enumerate(all_docs):
        parts.append(f"【资料{i+1}】\n{text}")
    return "\n\n".join(parts)
```

**Key differences from naive approach**:
- Regex includes `对比` keyword in addition to `和`
- Uses `retrieve_k=10` (not 5) per entity — each plan has 6+ document segments, need enough candidates
- No artificial cap on merged docs — dedup + rerank handles it naturally
- Results: comparison queries return up to 6 docs (3 per plan) instead of 3 total

**Tested Agent decomposition behavior** (4 comparison queries):
| Query | Agent behavior | Tool calls | Result |
|-------|---------------|:----------:|:------:|
| 对比99和129套餐区别 | API connection error (timeout) | 0 | ❌ (infra issue) |
| 199和299宽带区别 | Self-decomposed: "199元套餐 宽带" + "299元套餐 宽带" | 2 | ✅ |
| 59和99橙分期补贴 | Self-decomposed: "59元套餐 橙分期 补贴" + "99元套餐 橙分期 补贴" | 2 | ✅ |
| 实付69和89对应套餐 | Self-decomposed: "实付69元套餐" + "实付89元套餐" | 2 | ✅ |

The Agent naturally breaks multi-entity queries into per-entity tool calls. Comparison detection is a **double insurance** — rarely triggered in Agent mode but valuable for direct RAG mode.

## Testing

```bash
# Verify dependencies
python3 -c "from rank_bm25 import BM25Okapi; import jieba; print('OK')"

# Test hybrid retrieval vs vector-only
# Compare results for keyword-heavy queries like "59套餐", "129元宽带"

# Check document segmentation (how many docs per entity)
python3 -c "
from langchain_chroma import Chroma
vs = Chroma(persist_directory='./taocan_rag_db', collection_name='langchain')
docs = vs.get(include=['documents'])['documents']
print(f'Total docs: {len(docs)}, Avg len: {sum(len(d) for d in docs)//len(docs)} chars')
"
```
