# Semantic-Aware Chunk Splitting for Structured Documents

## Problem

When a knowledge base has "detail" and "policy/discount" sections for the same entity (e.g., 副卡月费10元 in plan details vs 副卡费减免至0元 in discount policies), aggressive chunking splits them into separate chunks. The RAG system retrieves only ONE chunk per query, giving different answers on different runs.

**Symptom**: Same question answered inconsistently — "10元/张" vs "免费" depending on which chunk wins the similarity race.

**Diagnosis**: Search vector DB for all chunks containing the keyword:
```python
results = col.query(query_texts=["副卡费 副卡月费"], n_results=10)
for i, doc in enumerate(results['documents'][0]):
    print(f"[{i}] {doc[:150]}")
```
If "10元" and "减免" appear in different chunks → confirmed.

## Root Cause

RecursiveCharacterTextSplitter splits by character count, not by semantic boundaries. A file like `套餐详情.md` may contain:

```
（三）副卡资费说明
2.月功能费：10元/月/张          ← chunk A ends here
...
(YD5G03-014-1-1)副卡功能费减免至0元  ← chunk B starts here
```

The fix: use **semantic separators** that match the document's logical structure.

## Solution: Semantic-Aware Splitting

### Step 1: Identify the document's natural structure

Look for repeated structural markers:
- Chinese numbered sections: `一、`, `二、`, `（一）`, `（二）`
- Markdown headers: `##`, `###`
- Entity boundaries: plan names, product names, section titles

### Step 2: Use semantic separators instead of character-count splitting

```python
import re

# For telecom plans: split by "一、销售品内容" which marks each plan
PLAN_SEPARATOR = r"(?=一、\s*销售品内容)"

sections = re.split(PLAN_SEPARATOR, content)
sections = [s.strip() for s in sections if s.strip()]
```

Each section now contains ONE plan's complete info (details + sub-card rules + policies).

### Step 3: Extract cross-cutting policies and merge them

Some policies apply to MULTIPLE entities (e.g., "59元、79元、99元、129元...这些套餐才可以做副卡减免"). These policies are in a separate section, not inside any single plan's detail.

**Strategy**: Extract policies first, then merge relevant ones into each plan's chunk.

```python
def extract_policies(sections):
    """Extract cross-cutting policies from sections."""
    policies = []
    for section in sections:
        if '副卡功能费减免' in section or '这些套餐才可以做' in section:
            # Extract applicable entities
            applicable = re.findall(r'(\d+)元', section[:5000])
            valid = [p for p in applicable if int(p) in KNOWN_TIERS]
            
            # Extract policy summary
            summary = []
            if '副卡功能费减免至0元' in section:
                summary.append('副卡功能费可减免至0元')
            if '129及以上' in section:
                summary.append('129元及以上可开通2张以上副卡')
            
            if summary and valid:
                policies.append({
                    'applicable': valid,
                    'summary': '；'.join(summary)
                })
    return policies

def merge_policies_into_chunks(sections, policies):
    """For each plan chunk, append relevant policies."""
    chunks = []
    for section in sections:
        plan_tier = extract_plan_tier(section)  # e.g., "129"
        
        if plan_tier and '副卡' in section:
            for policy in policies:
                if plan_tier in policy['applicable']:
                    section += "\n\n【优惠政策】\n" + policy['summary']
                    break
        
        chunks.append(section)
    return chunks
```

### Step 4: Handle large sections with sub-title splitting

If a single plan section exceeds max chunk size, split by sub-titles but keep related info together:

```python
MAX_CHUNK = 1500

def split_by_subtitles(section):
    # Split by （一）（二）（三）etc.
    subs = re.split(r"(?=（[一二三四五六七八九十]）)", section)
    subs = [s.strip() for s in subs if s.strip()]
    
    # Merge small subs into previous chunk
    merged, current = [], ""
    for sub in subs:
        if len(current) + len(sub) > MAX_CHUNK and current:
            merged.append(current)
            current = sub
        else:
            current = current + "\n" + sub if current else sub
    if current:
        merged.append(current)
    return merged
```

### Step 5: Rebuild vector DB

After changing the chunking strategy, the vector DB must be rebuilt:

```python
# Clear existing DB
import shutil
shutil.rmtree(VECTOR_DB_PATH, ignore_errors=True)

# Rebuild with new chunks
workflow = RAGWorkflow()
workflow.load_documents(DATA_DIR)
```

## Real-World Impact

**Before** (RecursiveCharacterTextSplitter, chunk_size=300):
- 129元套餐: chunk A has "副卡月功能费10元/月/张"
- Chunk B has "副卡功能费减免至0元" (in a different plan's context)
- LLM retrieves only chunk A → "每张副卡10元"

**After** (semantic splitting with policy merging):
- 129元套餐: single chunk has both "副卡月功能费10元/月/张" AND "【优惠政策】副卡功能费可减免至0元"
- LLM sees both → "副卡月功能费10元，可申请减免至0元"

## When to Use This Approach

- Document has **repeated structural sections** (plans, products, services)
- Each section has **sub-components** (details, policies, pricing rules)
- Some policies are **cross-cutting** (apply to multiple entities)
- Inconsistent answers on the same topic across different runs

## Pitfalls

1. **Semantic separators are document-specific**: `一、销售品内容` works for this telecom KB but not for all documents. Inspect the actual document structure before choosing separators.
2. **Policy extraction regex is fragile**: If the policy text format changes, the regex breaks. Add fallback: if no policies extracted, fall back to normal splitting.
3. **Chunk count may increase**: Merging policies into each plan chunk adds ~50-100 chars per chunk. Monitor total chunk count to ensure it doesn't explode.
4. **Still need vector DB rebuild**: Changing chunk strategy requires clearing and rebuilding the entire vector DB. This takes minutes and costs embedding API calls.
5. **Large policy sections**: If a single policy section is 10,000+ chars (like 橙分期 details), it needs its own splitting strategy — don't blindly merge it into every plan chunk.
