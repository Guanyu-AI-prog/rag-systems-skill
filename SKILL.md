---
name: rag-systems
description: "Build, deploy, evaluate, and optimize RAG systems — LangChain and pure Python implementations, hybrid retrieval (vector+BM25+rerank), evaluation benchmarking, and LangChain-to-pure-Python migration."
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [RAG, LangChain, ChromaDB, BM25, vector-search, evaluation, deployment]
    category: data-science
related_skills: [agent-harness]
---

# RAG Systems

Complete guide for building, deploying, evaluating, and optimizing Retrieval-Augmented Generation systems. Covers both LangChain-based and pure Python implementations.

## When to Use RAG vs Long-Context LLM

| Signal | Use Long-Context | Use RAG |
|--------|-----------------|---------|
| < 10 source documents | ✅ fits in 128k window | ❌ overhead |
| Total < 50k chars | ✅ just send everything | ❌ chunking hurts |
| Thousands+ of documents | ❌ won't fit | ✅ required |
| Multi-user/multi-tenant | ❌ | ✅ each user queries different subsets |
| Documents change frequently | ❌ re-sending is expensive | ✅ re-embedding is cheap |
| Need source citations | ❌ | ✅ returns exact chunks |

**Decision heuristic**: If you can paste all documents into a single prompt under 100k tokens, don't build RAG.

## Agent价值框架：能用 vs 有用

Building any Agent system follows a predictable maturity curve:

| 层级 | 特征 | 谁在做 |
|------|------|--------|
| **能用** | 调通API、返回结果、Demo可演示 | 现在任何人都能做（Workbody等工具） |
| **有用** | 生产环境稳定跑3个月、维护成本<收益 | 踩过坑的人才懂 |

"能用"是技术实现，"有用"是工程落地。中间隔着的全是坑：路由设计错了会崩、Prompt长了会被稀释、降级没做好就傻眼、知识库没更新就胡说。

Agent架构师的价值不在于写Agent，而在于**预见Agent三个月后会在哪里出问题**。详见 `references/agent-harness.md`。

## RAG vs LLM Wiki: When to Route

For systems with **two tiers of knowledge** (FAQ-style + deep-dive), consider hybrid routing:

| Signal | Route to Wiki | Route to RAG |
|--------|---------------|--------------|
| Question frequency | High (常见FAQ) | Low (长尾/深度) |
| Knowledge stability | Stable, curated | Changes frequently |
| Precision need | Verified answer | Source citation |
| Content volume | 几十~几百篇 | 几千~几万份 |
| Maintenance | Manual curation | Auto from docs |

**Three routing strategies** — keyword classifier, LLM classifier, or wiki-first fallback. See `references/rag-vs-wiki-routing.md` for full implementation.

---

## Section 1: Architecture Overview

### Hybrid Retrieval Pipeline (Recommended)

```
User Query
  ├─ [Query Router] detect type (single / comparison / multi-hop)
  │
  ├─ Single → vector_search(k=10) + BM25(k=10) → dedup → rerank(top_n=3)
  │
  └─ Comparison → split into N sub-queries per entity
       ├─ "99元套餐" → vector(k=10) + BM25(k=10) → dedup → rerank(top_n=3)
       └─ "129元套餐" → vector(k=10) + BM25(k=10) → dedup → rerank(top_n=3)
       → merge + dedup → up to 6 docs to LLM
```

### Component Choices

| Component | LangChain | Pure Python |
|-----------|-----------|-------------|
| Document | `Document` class | `@dataclass` with `page_content` + `metadata` |
| LLM | `ChatOpenAI` | `requests.post()` to `/chat/completions` |
| Embeddings | `OpenAIEmbeddings` | `requests.post()` to `/embeddings` |
| Vector Store | `langchain_chroma.Chroma` | `chromadb.PersistentClient` |
| BM25 | `BM25Retriever` | `rank_bm25.BM25Okapi` + tokenizer |
| Rerank | `ContextualCompressionRetriever` | Direct reranker API call |
| State Graph | `StateGraph` (LangGraph) | Manual `while True` state machine |

**Pure Python template**: `templates/pure_python_rag_skeleton.py`
**LangChain Windows template**: `templates/lc_lx_windows_template.py`

---

## Section 2: Building RAG Systems

### Dependencies

```bash
# LangChain approach
pip install langchain  # Install LangChain dependencies langchain-openai langchain-community langchain-chroma chromadb

# Pure Python approach
pip install chromadb  # Install RAG dependencies rank_bm25 pymupdf requests python-dotenv
```

### Key Patterns

**BM25 Chinese tokenization** (critical for Chinese RAG):
```python
def _tokenize(self, text):
    tokens = []
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            tokens.append(char)  # Chinese: char-by-char
        elif char.isalnum():
            tokens.append(char.lower())
    words = re.findall(r'[a-zA-Z]+', text.lower())
    tokens.extend(words)
    return tokens
```

**Safe embedding client** (batch + retry):
```python
def embed_documents(self, texts):
    all_embeddings = []
    for i in range(0, len(texts), self.chunk_size):
        batch = texts[i:i + self.chunk_size]
        try:
            embs = self._call_api(batch)
            all_embeddings.extend(embs)
        except Exception:
            for t in batch:
                try:
                    all_embeddings.append(self._call_api([t])[0])
                except:
                    all_embeddings.append([0.0] * 1024)
    return all_embeddings
```

**ChromaDB metadata constraints**: Values must be `str|int|float|bool`. No `None`, no nested dicts.

**State machine** (replaces LangGraph):
```python
def run(initial_state):
    state = dict(initial_state)
    state.update(_translate_node(state))
    state.update(_classify_node(state))
    while True:
        route = _route_by_type(state)
        state.update(_retrieve_node(state, route))
        if _evaluate_retrieval(state) == "rewrite":
            state.update(_rewrite_query(state))
            continue
        state.update(_answer_node(state))
        break
    return state
```

### SiliconFlow Embedding/BM25/Rerank

API at `https://api.siliconflow.cn/v1/`. Key models:
- Embedding: `BAAI/bge-m3` (no char limit), `BAAI/bge-large-zh-v1.5` (500-char limit!)
- Rerank: `BAAI/bge-reranker-v2-m3`

**Pitfall**: `bge-large-zh-v1.5` returns HTTP 400 for inputs > 500 chars. Truncate or use `bge-m3`.
**Pitfall**: Batch embedding calls in groups of ≤32 to avoid 400 errors.
**Pitfall**: Model names change — always verify available models first:
```bash
# # curl example (add your own auth) [print(m['id']) for m in json.load(sys.stdin)['data'] if 'bge' in m['id'].lower()]"
```

---

## Section 3: Retrieval Optimization

### BM25 Hybrid Search

Vector search (semantic) misses exact keyword matches. BM25 (lexical) catches them. Run in parallel:

```python
from concurrent.futures import ThreadPoolExecutor

def hybrid_search(query, vector_k=10, bm25_k=10):
    with ThreadPoolExecutor(max_workers=2) as pool:
        v_future = pool.submit(vectorstore.similarity_search, query, k=vector_k)
        b_future = pool.submit(bm25_retriever.search, query, top_k=bm25_k)
        vector_docs = v_future.result()
        bm25_docs = b_future.result()
    return deduplicate_docs(vector_docs + bm25_docs)
```

**Pitfall**: Always cache the BM25 index. Rebuilding on every query causes 10+ min delays in Agent mode.

### Comparison Query Splitting

When comparing entities (e.g., "99元 vs 129元套餐"), split into per-entity queries **with domain-specific expansion**:

```python
import re

def split_comparison(query):
    numbers = re.findall(r'(\d+)', query)
    return [f'{num}元套餐 流量 通话 宽带 副卡 月租' for num in numbers]
```

**Critical**: Don't just split the number — generate **entity-specific retrieval queries** with domain keywords (流量, 通话, 宽带). Searching with the full comparison query biases vector search toward one entity. Search each entity separately, merge with dedup, then send to LLM.

**Impact**: Pushed comparison-type questions from 40% → 100% accuracy in real-world telecom RAG.

See `references/comparison-retrieval-fix.md` for the full debugging trace.

### Rerank Tuning

```python
def rerank(query, docs, top_n=3):
    resp = requests.post(f'{BASE_URL}/rerank',
        headers={'Authorization': f'Bearer {API_KEY}'},
        json={'model': RERANK_MODEL, 'query': query, 'documents': docs, 'top_n': top_n},
        timeout=10)  # 10s sweet spot — 5s is too aggressive
    return resp.json().get('results', [])
```

**Pitfall**: Rerank failure must degrade gracefully — return unranked docs, don't fail the whole query.

### Speed Optimization Checklist

```
□ Parallel vector + BM25 retrieval (ThreadPoolExecutor, max_workers=2)
□ Rerank timeout ≤ 10s (NOT 5s), max_retries ≤ 1
□ LLM timeout = 15s with max_retries=0 (prevents timeout×retries multiplication)
□ Rerank failure degrades gracefully (returns unranked docs)
□ No nested ThreadPoolExecutor deadlock
```

**Critical**: OpenAI Python client `timeout × (max_retries+1)` multiplication. `timeout=8, max_retries=2` = 24s worst case, not 8. Always set `max_retries=0`.

---

## Section 4: Evaluation & Benchmarking

### 6-Type Question Taxonomy

| Type | Tests | Example |
|------|-------|---------|
| 单点查询 | Precise retrieval | "29元套餐包含多少流量？" |
| 对比型 | Multi-doc aggregation | "99元和129元套餐区别？" |
| 多跳推理 | Multi-step computation | "129元套餐+300M宽带+2张副卡总价？" |
| 流程型 | Step extraction | "如何办理携号转网？" |
| 场景型 | Intent + recommendation | "一家三口推荐什么套餐？" |
| 边界/异常 | Refusal + edge cases | "联通套餐多少钱？" |

Generate 30 questions (5 per type). Create TWO phrasing variants: formal and colloquial.

### Eval Script Pattern

```python
# Incremental save after EACH question — crash at Q28 won't lose Q1-Q27
# Thread-based timeout (signal.alarm doesn't work in subprocesses)
# Resume from completed IDs
# 3-second delay between questions (rate-limit protection)
```

See `templates/eval_script.py` for the complete template.

### Scoring Dimensions

| Dimension | Weight | What to check |
|-----------|--------|---------------|
| 准确率 | 30% | Facts and numbers correct |
| 幻觉率 | 20% | Fabricated info (lower = better) |
| 检索能力 | 25% | Retrieved relevant docs |
| 完整性 | 15% | All parts of question answered |
| 平均耗时 | 10% | Response time |

### Error Taxonomy for Post-Eval Analysis

| Error Type | Fix Location |
|------------|-------------|
| 概念混淆 (concept mixing) | Prompt: add disambiguation rules |
| 价格混淆 (price confusion) | Prompt: "use original price, not discounted" |
| 幻觉编造 (hallucination) | Prompt: "only recommend plans that exist in KB" |
| 角色越界 (role confusion) | Prompt: add explicit role boundary |
| 检索失败 (retrieval failure) | Retrieval: add BM25, query expansion |
| 不完整回答 (incomplete) | Prompt: "cover all aspects" |

**Key insight**: Most RAG errors are NOT retrieval failures — they're LLM reasoning errors after correct retrieval. Fix is almost always in the SYSTEM_PROMPT.

### Overfitting Detection

| Signal | Risk | Check |
|--------|------|-------|
| Questions designed FROM KB content | 🟡 | Were questions written by reading vector DB? |
| Retrieval tuned ON test set | 🔴 | Did you add BM25 after seeing failures? |
| Only clean phrasing | 🟡 | Are all questions grammatically perfect? |
| No adversarial questions | 🟡 | Did you test trick questions? |
| Single test round | 🟡 | Run 2nd round with independent questions |

---

## Section 5: Deployment

### LangChain RAG Deployment

```bash
# Project structure:
# api.py (FastAPI), workflow_langchain.py, build_vectors.py, config.py, .env

# Build vector DB
python build_vectors.py --force

# Start API service
python api.py  # Default: http://localhost:8001

# Test
curl -X POST "http://localhost:8001/query" -H "Content-Type: application/json" \
  -d '{"question": "有哪些套餐？"}'
```

### Performance Tuning (4-core 8GB server)

```env
MAX_WORKERS=2
CACHE_TTL=300
CHUNK_SIZE=500
RETRIEVAL_K=3
```

### When to use direct context instead of RAG

For small datasets (< 100K chars), direct context window reading is MORE accurate than RAG. RAG loses accuracy because: chunking loses cross-chunk context, vector similarity misses implicit connections.

---

## Section 6: LangChain → Pure Python Migration

### Component Mapping

| LangChain | Pure Python |
|-----------|-------------|
| `Document` | `@dataclass` with `page_content: str` + `metadata: dict` |
| `ChatOpenAI` | `requests.post()` to `/chat/completions` |
| `OpenAIEmbeddings` | `requests.post()` to `/embeddings`, batch by chunk_size |
| `PyMuPDFLoader` | `pymupdf` (fitz) — `page.get_text()` |
| `RecursiveCharacterTextSplitter` | Manual recursive splitter |
| `Chroma` | `chromadb.PersistentClient` native API |
| `BM25Retriever` | `rank_bm25.BM25Okapi` with custom tokenizer |
| `ChatPromptTemplate` | `format_prompt()` returning `List[Dict]` |
| `StateGraph` | Manual state machine with `while True` loop |

See `references/langchain-to-pure-python.md` for the full migration guide.
See `templates/pure_python_rag_skeleton.py` for the complete file structure.

### Critical Pitfalls for Migration

1. **BM25 Chinese tokenization** — `text.split()` breaks BM25 for Chinese. Must use character-level tokenization.
2. **ChromaDB metadata** — values must be `str|int|float|bool`, no `None`.
3. **Embedding dimension auto-detection** — don't hardcode; record from first successful call.
4. **.env model/base URL mismatch** — `LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash` with 智谱AI base URL → 400 error.
5. **Flash models cut corners** — DeepSeek-V4-Flash wrote broken `text.split()` tokenizer; MiMo-v2.5-Pro wrote correct character-level tokenizer.

---

## Pitfalls (Consolidated)

1. **Rate limiting**: Always 3s delay between eval questions. Free-tier APIs will 429.
2. **Questions from imagination**: Always read vector DB content first.
3. **Only happy path**: Include boundary/异常 questions.
4. **Ignoring per-type breakdown**: Overall score masks weak spots.
5. **.env overrides code defaults**: `DATA_DIR` in `.env` overrides code changes.
6. **ChromaDB collection name mismatch**: Check `client.list_collections()`.
7. **Embedding model incompatibility**: Different models = different dimensions = incompatible vector DBs.
8. **Chunking splits related data**: Merge related sections into same chunk.
9. **Prompt boundary over-correction**: Prefer positive framing over negative.
10. **Python version mismatch**: Check `python3.X -c "import <dep>"` before running.
11. **HuggingFace blocked on Chinese servers**: Use `HF_ENDPOINT=https://hf-mirror.com`.
12. **LangChain version conflicts**: `langchain-core` 0.3.0+ removed pydantic_v1 shim.
13. **When NOT to use RAG**: < 100K chars → use direct context.
14. **Provider mismatch in .env**: Comment out `LLM_API_KEY` → silent fallback to wrong provider key.
15. **Hardcoded model names in config.py**: `LLM_MODEL = "step-3.5-flash"` (hardcoded string) ignores the `.env` value. When migrating to a server with a different `.env`, all queries fail with "Model does not exist". Fix: `LLM_MODEL = "your-api-key"` for ALL model names — `LLM_MODEL`, `QUERY_REWRITE_MODEL`, `EMBED_MODEL`, `RERANK_MODEL`.
16. **QUERY_REWRITE_MODEL provider mismatch**: Query rewrite uses a separate model config (`QUERY_REWRITE_MODEL`). If this defaults to a model that doesn't exist on the current provider (e.g. `step-3.5-flash` on SiliconFlow), every query rewrite silently fails and falls back to the original query. Set `QUERY_REWRITE_MODEL` in `.env` to match your `LLM_MODEL` provider.
17. **Data completeness before vector rebuild**: Always verify ALL expected data files exist in the data directory before running `build_vectors.py`. Missing documents (e.g. `套餐详情.md`) cause the vector DB to lack critical data, and comparison/retrieval queries fail silently with "暂无信息". Use `ls -lh data/` and compare against expected file list before rebuilding.
18. **Embedding 400 errors are content-dependent**: `bge-large-zh-v1.5`'s 500-char limit is token-based, not character-based. Some 749-char texts fail while others pass. If you get intermittent 400 errors, reduce truncation limit to 500 chars and also check for special content patterns (repeated fields, codes like `YD4G03-xxx`).
19. **Comparison retrieval must use per-entity queries**: Searching with the full comparison query ("A vs B") biases vector search toward one entity. Generate entity-specific queries (e.g., `f"{tier}元套餐 流量 通话 宽带"`) and search separately per entity, then merge results. See `references/comparison-retrieval-fix.md`.
20. **Metadata substring matching bug in tier filtering**: If `plan_tier` metadata stores comma-separated values like `"99,199"`, using `plan_tier in metadata_string` does substring matching — `"99"` matches `"199"`. Fix: `plan_tier in [t.strip() for t in metadata.split(",")]`. Always use list membership, never string containment for multi-value metadata fields.
21. **ContextVar in async generators**: Python `ContextVar.set()` called outside an `async def event_generator()` creates the token in the parent scope. The generator runs in a different context, causing `"was created in a different Context"` errors. Fix: call `_session_ctx.set()` INSIDE the generator function, not outside.
22. **GLM-4-32B speed advantage**: On SiliconFlow, `THUDM/GLM-4-32B-0414` is 4-5x faster than `deepseek-ai/DeepSeek-V4-Flash` for RAG tasks (1.8s vs 7-8s simple, 4s vs 31s comparison). Supports function calling. Good choice when speed matters more than reasoning depth.
23. **Streaming output changes the comparison UX**: Non-streaming comparison queries feel slow (15-30s wait). Streaming SSE makes the same query feel fast (first token in ~1s). See `references/fastapi-sse-streaming.md` for the full pattern.
24. **RAG simple queries return full text at once — no real streaming**: When RAG retrieves context and formats the answer directly (no LLM call), the entire answer is one `data: {"type":"token","content":"..."}` event. Frontend receives it instantly — no streaming effect. Fix options: (a) **Server-side chunking**: split answer by sentences (`re.split(r'(?<=[。！？])', answer)`) and yield each chunk with `asyncio.sleep(0.05-0.1)`, (b) **Frontend typewriter**: render text character-by-character with `setInterval(18ms)`. Option (a) gives real SSE streaming; option (b) is cosmetic but works for any backend. See `references/fastapi-sse-streaming.md`.
25. **Never edit JS/HTML via Python string replacement on remote**: Python `str.replace()` on multi-line JS/HTML is fragile — unclosed braces, regex special chars, and indentation mismatches cause silent syntax errors. Pitfalls encountered: (a) `}}` double-brace from function close + replacement boundary, (b) `\n` inside `r'(?<=...)'` regex treated as literal newline in bash heredoc, causing `SyntaxError: unterminated string literal`. **Safer approach**: write a complete Python script that reads the file, finds the function by start/end markers, and replaces the entire function body. Validate with `node --check` after any JS edit.
26. **Check HTML element IDs before referencing in JS**: When rewriting frontend JS, always `grep` for the actual element IDs (`grep 'id=' file.html`). Common mismatch: code uses `getElementById('msgs')` but actual ID is `getElementById('msgBox')`. Causes `Cannot read properties of null (reading 'appendChild')` at runtime — silent failure, no JS error visible in page.
27. **Regex in bash heredoc — escape sequences**: When writing regex patterns containing `\n` via bash heredoc (`<< 'EOF'`), the `\n` is preserved as literal `\n`. But when using `python3 << 'PYEOF'` with an f-string or raw string containing `\n`, the shell may interpret it. Always use `\\n` in the Python source, or avoid heredoc — write the script to a file first with `write_file`, then `scp` it.

## Support Files

### References
- `references/skill-sharing-desensitization.md` — How to safely share skills with others (path masking, API key removal)
- `references/telecom-eval-example.md` — Full 2-round evaluation example
- `references/comparative-eval-example.md` — Two-system head-to-head comparison
- `references/prompt-error-fixes.md` — Iterative prompt debugging examples
- `references/evaluation-question-design.md` — Question generation patterns
- `references/dx-agent-eval-2026-06.md` — Real-world eval data
- `references/semantic-chunk-splitting.md` — Structure-aware chunking
- `references/pure-python-rag.md` — Pure Python implementation details
- `references/langchain-to-pure-python.md` — Full migration guide
- `references/lw-rag-comparison.md` — LangChain vs pure Python comparison
- `references/advanced-rag-langgraph.md` — LangGraph orchestration
- `references/hybrid-retrieval-pattern.md` — Vector+BM25+Rerank implementation
- `references/simplified-rag-pattern.md` — Lightweight single-file RAG
- `references/rag-vs-wiki-routing.md` — RAG vs LLM Wiki hybrid routing (高频→Wiki, 低频→RAG)
- `references/rag-evaluation-testing.md` — Quiz-based quality testing
- `references/rag-benchmark-quiz.md` — Benchmark methodology
- `references/mcp-server-integration.md` — Expose RAG as MCP server
- `references/windows-portable-deployment.md` — Embedded Python for Windows
- `references/siliconflow-api.md` — SiliconFlow API reference
- `references/siliconflow-truncation-and-windows-nuances.md` — Model limits
- `references/comparison-retrieval-fix.md` — Per-entity search pattern for comparison queries
- `references/file-delivery-fallback.md` — HTTP file delivery workaround
- `references/skill-sharing-and-desensitization.md` — How to safely share this skill with others (path redaction, API key check, packaging)
- `references/hand-typed-code-errors.md` — Common hand-typed code mistakes
- `references/agent-harness.md` — Agent Harness设计模式：Prompt约束、工具定义、路由逻辑、行为控制、降级熔断

### Templates
- `templates/eval_script.py` — Eval script with incremental save, timeout, resume
- `templates/pure_python_rag_skeleton.py` — Complete pure Python RAG template
- `templates/lc_lx_windows_template.py` — LangChain RAG for Windows deployment
- `templates/codex-rag-reference.md` — Compact RAG reference for Codex/Claude Code (architecture, code snippets, pitfalls)
