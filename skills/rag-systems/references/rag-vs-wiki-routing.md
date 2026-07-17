# RAG vs LLM Wiki: Hybrid Routing Architecture

## The Pattern

Route queries between two knowledge bases based on question frequency/type:

```
用户提问
   │
   ▼
 分类器/路由器
   │
   ├─ 高频/常见问题 → LLM Wiki（人工整理的结构化知识）
   │
   └─ 低频/深度问题 → RAG（向量检索原始文档）
```

## When to Use This

Use hybrid routing when you have BOTH:

| Signal | Use Wiki path | Use RAG path |
|--------|---------------|--------------|
| Question frequency | High (常见FAQ) | Low (长尾/深度) |
| Knowledge stability | Stable, curated | Changes frequently |
| Precision requirement | Need verified answer | Need source citation |
| Content volume | 几十~几百篇 | 几千~几万份 |
| Maintenance cost | Manual (每篇整理) | Automatic (文档扔进去) |

## How to Route (3 Options)

### Option 1: Keyword-based routing (simplest)

```python
FAQ_KEYWORDS = ["怎么部署", "怎么配置", "如何安装", "常见问题", "OpenClaw"]

def route_by_keywords(query):
    for keyword in FAQ_KEYWORDS:
        if keyword in query:
            return "wiki"    # 走LLM Wiki
    return "rag"             # 走RAG
```

Pros: Zero LLM cost, deterministic.  
Cons: Can't handle novel phrasings.

### Option 2: LLM classifier

```python
def route_by_llm(query):
    prompt = f"""判断以下问题是高频FAQ还是深度检索问题。
回复仅输出"wiki"或"rag"。

问题：{query}"""
    result = llm_call(prompt).strip().lower()
    return result if result in ("wiki", "rag") else "rag"
```

Pros: Flexible, handles any phrasing.  
Cons: Adds latency + token cost.

### Option 3: Wiki-first fallback (recommended)

```python
def hybrid_answer(query):
    # 1. 先查Wiki
    wiki_result = search_wiki(query)
    if wiki_result and confidence_high_enough(wiki_result):
        return wiki_result

    # 2. Wiki没命中或置信度不够 → 走RAG
    rag_result = rag_retrieve_and_answer(query)
    return rag_result
```

Pros: Simple, no explicit router needed, natural degradation.  
Cons: Always hits Wiki first even for obvious RAG queries.

## Real-World Application

The user (关彧) designed this pattern for their own needs:

- **Wiki path**: 高频工作问题（Hermes配置、Agent部署步骤、常用命令）→ 整理成结构化笔记
- **RAG path**: 低频深度问题（法律条款查询、学术论文检索、复杂场景推理）→ 向量检索原文

## Tooling Options

| Component | Option A | Option B |
|-----------|----------|----------|
| Wiki | Karpathy's LLM Wiki (AppImage) | Obsidian vault + search |
| RAG | ChromaDB + LangChain | Pure Python (chromadb + rank_bm25) |
| Router | LangGraph conditional edge | Manual if/else + function call |

## Key Insight

> 大多数RAG场景不需要Wiki。大多数Wiki场景不需要RAG。  
> 只有当你有**高频稳定知识+低频变化知识**两种形态共存时，才值得做混合路由。

This is NOT the default architecture — it's a specialized pattern for when you have a clear split between FAQ-type and deep-research-type questions.
