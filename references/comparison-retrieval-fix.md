# Comparison Retrieval Fix — Per-Entity Search Pattern

## Problem

When comparing entities (e.g., "59套餐 vs 99套餐"), a naive approach searches with the full comparison query and filters by entity metadata. This fails because:

1. Vector search returns docs semantically similar to the **full query** ("59 vs 99"), which are mostly about entity A
2. Entity B's documents have low similarity to the full comparison query
3. After metadata filtering, entity B has only 2 low-quality docs vs entity A's 6

## Symptom

- Comparison query returns detailed data for one entity but "未提供" for the other
- Vector search logs show asymmetric hit counts per entity

## Fix

```python
# WRONG: Search with full comparison query, filter by tier
docs = workflow._hybrid_search(
    "59套餐对比99套餐",  # Full query biases toward one entity
    plan_tier=tier
)

# RIGHT: Generate entity-specific queries for each tier
for tier in tiers:
    tier_query = f"{tier}元套餐 流量 通话 宽带 副卡 月租"
    tier_docs = workflow._hybrid_search(
        tier_query,
        vector_k=Config.VECTOR_TOP_K,
        bm25_k=Config.BM25_TOP_K,
        plan_tier=tier
    )
    # Merge with dedup
    for d in tier_docs:
        key = d.page_content.strip()
        if key not in seen:
            seen.add(key)
            docs.append(d)
```

Key insight: the retrieval query for each entity must be **entity-specific**, not the full comparison query. Adding domain keywords (流量, 通话, 宽带, 副卡, 月租) ensures comprehensive data retrieval.

## Impact

Before: "59 vs 99" → 99套餐 shows "未提供" for most fields
After: Both entities return complete data with full comparison table

## Related

- Section 3 of SKILL.md: "Comparison Query Splitting"
- Pitfall #17: Data completeness before vector rebuild
