# lw_rag.py vs lw_rag1.py 对比记录

两个文件都是"LangChain RAG → 纯 Python"的实现，分别由不同 Agent + 不同 LLM 生成。

## Agent + LLM 组合

| 文件 | Agent | LLM | 耗时 |
|---|---|---|---|
| lw_rag.py | Hermes | MiMo-v2.5-Pro (小米) | ~30min（含写代码+装依赖+测试+修bug） |
| lw_rag1.py | OpenCode | DeepSeek-V4-Flash | 略快于Hermes |
| (未完成) | OpenClaw | DeepSeek-V4-Flash | 20min未完成 |

## 关键差异

### BM25 分词（最重要 — LLM 质量差异）
- **lw_rag.py (MiMo-v2.5-Pro)**: 中文字按字拆分 + 英文按词拆分 → 学术文档检索效果好
- **lw_rag1.py (DeepSeek-V4-Flash)**: 仅按空格切分 → 中文句子变成一整个 token，BM25 对中文基本失效

Flash 模型在需要领域知识（中文 NLP 分词）的细节上会偷工减料。

### Embedding 维度
- **lw_rag.py**: 零向量 fallback 硬编码 1024（碰巧对了 bge-large-en-v1.5）
- **lw_rag1.py**: 成功获取 embedding 后自动记录维度（更健壮）

### 代码组织
- **lw_rag.py**: LLMResponse 后定义（前向引用），但有 docstring
- **lw_rag1.py**: LLMResponse 先定义（更合理），但有死代码 `_classify_query`

## 结论

- lw_rag.py 整体更好（BM25 分词质量差距大）
- lw_rag1.py 的维度自动记录值得移植
- **代码质量差异主要来自 LLM，不是 Agent 框架**
- Agent 框架影响执行效率（工具调用次数 × 每次推理延迟）
- Flash 版模型在简单任务上够用，涉及领域知识的细节容易翻车
