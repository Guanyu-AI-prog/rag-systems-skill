# RAG Benchmark: Generating Quiz Questions from Knowledge Base

Use this pattern to evaluate RAG quality by generating test questions from the vector database content.

## When to Use

- After building/updating a knowledge base
- After changing retrieval parameters (chunk_size, top_k, reranker)
- After switching embedding models or LLM
- Periodically to catch quality regression

## Method

1. **List knowledge base source files** to understand coverage:
```bash
ls /path/to/source_docs/
```

2. **Generate questions across categories**:
   - **Factual** (40%) — "What is X?", "How does Y work?"
   - **Comparison** (20%) — "What's the difference between X and Y?"
   - **Synthesis** (20%) — "Summarize the trends in Z"
   - **Multi-hop** (20%) — "How did X influence Y's development?"

3. **Each question should include**:
   - The question text
   - Expected source paper/document
   - Difficulty level (basic/advanced)

4. **Run questions through RAG** and evaluate:
   - ✅ Correct answer
   - ✅ Correct source attribution
   - ❌ Hallucination (made up info)
   - ❌ Wrong source
   - ❌ No answer when answer exists

## Example: 30-question benchmark from arxiv papers

```markdown
## Category Distribution
| Category | Questions | Focus |
|----------|-----------|-------|
| Transformer basics | 1-5 | Core architecture concepts |
| GPT series | 6-10 | Model capabilities, RLHF |
| DeepSeek series | 11-17 | MoE, reasoning, architecture |
| RAG methods | 18-21 | Retrieval approaches |
| Code generation | 22-24 | Training data, capabilities |
| Vision multimodal | 25-27 | CLIP, LLaVA, alignment |
| Agents | 28-30 | AutoGPT, Toolformer |
```

## Scoring Template

```
Total: 30 questions
Correct + Source: __/30
Correct + No Source: __/30
Hallucination: __/30
No Answer: __/30
Wrong Answer: __/30

Accuracy: ___%
Source Attribution Rate: ___%
Hallucination Rate: ___%
```

## Tips

- Questions should be answerable from the knowledge base content
- Include some "trap" questions that should return "暂无该信息"
- Test both Chinese and English queries if applicable
- Compare BM25-only vs Vector-only vs Hybrid retrieval results
