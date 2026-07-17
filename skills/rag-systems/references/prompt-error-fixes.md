# Prompt Error Fixes — Real Examples from Telecom RAG

## Context
dx_agent telecom RAG evaluation with 30 colloquial questions. 5 answers had errors despite correct retrieval. All fixes were SYSTEM_PROMPT additions, not retrieval changes.

## Error 1: 价格混淆 (Price Confusion)

**Question**: "129套餐加装300M宽带，再办3张副卡，一个月要花多少钱？"
**Wrong answer**: "主卡89元 + 3张副卡(10×3) + 宽带9.9元 = 139.9元"
**Problem**: Used "实付89元" (full prepay discount) instead of original 129元
**Root cause**: KB contains both original price and discounted price; LLM picked the wrong one for calculation

**Fix**: Add to SYSTEM_PROMPT:
```
【费用计算规则】计算总费用时，必须使用套餐原价（月基本费），不要使用"实付价"或"优惠后价格"。只有当用户明确问"实付多少"、"优惠后多少"时，才使用对应方案的价格
```

**Result**: After fix, LLM correctly said "套餐本身129元/月" instead of "主卡89元"

## Error 2: 概念混淆 (Concept Confusion)

**Question**: "299套餐的5G网速最高能到多少？"
**Wrong answer**: "千兆级别（1000Mbps）" — copied from broadband 1000M info
**Problem**: Mixed up 5G mobile network speed with broadband speed
**Root cause**: Both numbers appear in KB context; LLM conflated them

**Fix**: The general rule "基于真实数据，不要编造" was sufficient after the price fix — LLM now says "未明确说明5G网速上限，建议咨询运营商" instead of inventing a number.

## Error 3: 幻觉编造 (Hallucination)

**Question**: "一个月不想花超过30块，选哪个套餐好？"
**Wrong answer**: Recommended 25元, 28元 plans — these don't exist in KB
**Problem**: KB only has 29/39/59/79/99/129/169/199/229/299 tiers
**Root cause**: LLM tried to find something cheaper than 29 to meet the "under 30" constraint

**Fix**: Add to SYSTEM_PROMPT:
```
【档位真实性】只能推荐知识库中实际存在的套餐档位，禁止编造不存在的档位。如果30元以内没有合适套餐，如实告知"目前最低档位是29元"
```

**Result**: After fix, LLM correctly said "目前电信最低档位是29元套餐"

## Error 4: 角色越界 (Role Confusion) — Required 3 Iterations!

**Question**: "两个移动号一个联通号都想转过来，月预算200以内，推荐哪个？"
**Wrong answer**: Recommended "移动199元套餐" and "联通198元套餐" alongside telecom
**Problem**: As a telecom assistant, recommended competitor plans

### Iteration 1: Initial rule
```
【角色边界】你是电信套餐助手，只能推荐电信的套餐。当用户提到"移动号"、"联通号"时，是指要转入电信的号码，不是让你推荐移动/联通的套餐
```
**Result**: OVER-CORRECTION — LLM rejected ALL queries mentioning 移动/联通, even valid 携号转网 queries.
Output: "抱歉，我只能回答运营商套餐相关的问题" ❌

### Iteration 2: Added "转过来" keyword
```
【角色边界】你是电信套餐助手，只能推荐电信的套餐。用户提到"移动号想转过来"、"联通号想转过来"，是指携号转网到电信，应推荐电信套餐，不要推荐移动或联通的套餐
```
**Result**: Still over-rejected — LLM matched on bare "移动号" without parsing "转过来"

### Iteration 3: Positive framing + explicit trigger (FINAL)
```
【角色边界】你是电信套餐助手，只能推荐电信的套餐。注意："携号转网"是电信核心业务，用户说"移动号/联通号想转过来"是指要转到电信来，应正常推荐电信套餐并说明转网规则。只有当用户明确问"移动有什么套餐"、"联通套餐推荐"时才拒绝
```
**Result**: ✅ LLM correctly handled 携号转网 as a telecom business query

### Why Iteration 3 worked:
- **"携号转网是电信核心业务"** — reframes boundary as POSITIVE capability, not negative filter
- **"应正常推荐电信套餐并说明转网规则"** — tells LLM what TO do, not just what NOT to do
- **"只有当...才拒绝"** — explicit rejection trigger, not open-ended inference

## Lesson: Prompt Rules Are Surgical, Not Scattershot

Each fix is ONE specific rule addressing ONE specific error pattern. Don't add vague rules like "be more careful" — they don't help. The pattern is:
1. Identify the exact error
2. Write a rule that prevents THAT specific mistake
3. Re-run to verify the fix works
4. Check that the fix didn't break other answers

## Lesson: Boundary Rules Cause Over-Correction — Add Carve-Outs

When adding a "don't do X" rule to SYSTEM_PROMPT, the LLM often over-corrects and rejects valid cases that share surface features with the banned behavior. The fix pattern:
1. Write the initial boundary rule
2. Test with edge cases that SHOULD be allowed
3. If over-correction detected, add explicit carve-outs: "只有当...才拒绝" or "注意：Y是合法场景"
4. Prefer POSITIVE framing ("这是核心业务，应正常处理") over NEGATIVE framing ("不要推荐X")
5. Re-test both the original failing case AND the edge cases

## Complementary Fix: Chunk Splitting (Root Cause of Inconsistent Retrieval)

The prompt fixes above handle LLM reasoning errors AFTER correct retrieval. But some errors (like inconsistent副卡费 answers) are caused by **chunking splitting related data** into separate chunks. The LLM retrieves only ONE chunk per query, giving different answers depending on which chunk wins.

**Root cause fix** (not just prompt patch): Use semantic-aware chunk splitting that respects document structure. For telecom plans: split by "一、销售品内容" (each plan's logical boundary) instead of character count, then merge cross-cutting policies into each plan's chunk.

> Full implementation: see `rag-retrieval-optimization` skill, `references/semantic-chunk-splitting.md`
