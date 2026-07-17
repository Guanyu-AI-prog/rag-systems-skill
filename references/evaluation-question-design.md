# Evaluation Question Design Patterns

Reference for generating robust RAG evaluation questions from vector DB content.

## Question Type Taxonomy (6 types)

Based on telecom-agent-bench evaluation framework:

| Type | Count | Tests | Example |
|------|:-----:|-------|---------|
| Single-point | 6 | Precise retrieval + factual answer | "How much data in the 29 yuan plan?" |
| Comparison | 4-5 | Multi-doc aggregation + structured comparison | "Compare 99 vs 129 yuan plans" |
| Multi-hop reasoning | 5 | Multi-step retrieval + calculation | "129 yuan plan + 2 supplementary cards, total family data?" |
| Process | 4 | Flow extraction + step organization | "Steps to transfer from Mobile to Telecom?" |
| Scenario | 5 | Intent understanding + recommendation | "Family of 3 wants to switch, which plan?" |
| Boundary/edge | 5-6 | Refusal ability + anomaly handling | "What's the weather today?" |

## How to Generate Questions from Vector DB

### Step 1: Map all content

```python
from langchain_chroma import Chroma
from langchain_core.embeddings import FakeEmbeddings

vs = Chroma(persist_directory=PERSIST_DIR, embedding_function=FakeEmbeddings(size=1))
results = vs._collection.get(limit=vs._collection.count(), include=['documents'])

for i, doc in enumerate(results['documents']):
    first_line = doc.split('\n')[0][:80]
    print(f'{i+1:3d}| {first_line}')
```

### Step 2: Identify uncovered data points

Read the chunk index and find data that existing questions don't test. For example:
- Existing: "99 yuan plan data?" → tested
- Missing: "299 yuan satellite rights?" → not tested
- Missing: "Zhima credit score requirements for installment?" → not tested

### Step 3: Write questions targeting gaps

For each uncovered data point, write a question in the appropriate type category.

### Step 4: Verify answerability

Before running the full evaluation, spot-check 3-5 questions manually to confirm the knowledge base actually contains the answer.

## Pitfalls

- **Don't read full chunk text to write questions** — reading only the first line forces you to write questions that test retrieval, not memory
- **Include 5-6 boundary/edge questions** — these test hallucination control and refusal ability, which matter more than accuracy for production systems
- **Vary phrasing between rounds** — don't just rephrase the same questions; target genuinely different data points
- **Include at least 2 questions that SHOULD be refused** — weather, balance check, etc. to verify the system doesn't hallucinate on out-of-domain queries

## Real-World Results: Two-Round Comparison (Telecom Agent)

| Metric | Round 1 (30 questions) | Round 2 (30 new questions) |
|--------|:----------------------:|:-------------------------:|
| Score rate | 98.7% (148/150⭐) | 96.7% (145/150⭐) |
| Accuracy | 100% | 97% |
| Completeness | 97% | 93% |
| Hallucination | 0% | 0% |
| Avg latency | 17.6s | 19.8s |
| Delta | — | -2.0% |

**Verdict:** Delta ≤3% → evaluation is reliable, system is robust.

### Round 2 failure analysis:
- Q19 (process): Agent refused "APP complaint to downgrade plan" even though KB has it → retrieval miss on semantic paraphrase
- Q9 (comparison): Missing "students only" constraint for 39 yuan plan → Agent organized answer poorly despite correct retrieval
- Q21 (scenario): Same student-only issue → Agent didn't emphasize the constraint

**Lesson:** When multiple questions in the same type fail for the same reason, it's a systematic retrieval or prompt issue, not random failure.
