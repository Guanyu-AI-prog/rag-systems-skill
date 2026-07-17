# Agent Harness 模式 — 路由、工具、约束

> 用户关彧关于 Agent Harness 的讨论总结。
> Harness = 给 LLM 套缰绳：设计 Prompt 约束、工具定义、路由逻辑，让 Agent 听话不乱跑。

## 三路路由模式 (dx_agent.py 示例)

运营商套餐 Agent 的路由架构，可复用为通用 Agent Harness 模板：

```
classify_query(用户输入)
  ├── "simple"      → fast_path_rag()         # 直接RAG，跳过 Agent
  ├── "comparison"  → fast_path_comparison()  # 每个实体独立检索 + LLM 对比
  └── else          → PurePythonAgent.run()   # 多步推理循环
```

### 分类逻辑 (classify_query)

| 路由 | 触发条件 | 行为 |
|------|----------|------|
| simple | 无对比关键词，单档位，无计算 | 直接 RAG 查询 |
| comparison | 含"对比/区别/差异"或两个档位数字 | 分实体检索 → 合并 → LLM 对比表 |
| complex | 含计算/推荐/2+档位 | 完整 Agent 循环，调用工具 |

**关键设计：** comparison 路由不能直接拿整个查询去搜——向量搜索会偏向一个实体。必须每个实体单独搜（如 `"59元套餐 流量 通话 宽带"` 和 `"99元套餐 流量 通话 宽带"`），合并数据后再让 LLM 对比。

## 降级链 (Fallback Chain)

```
PurePythonAgent.run()
  → 异常 → fast_path_rag()
    → 异常 → "查询失败，请稍后重试"
```

**原则：** Agent 失败不应该让用户看到报错。每层都有兜底。

## 熔断器 (Circuit Breaker)

RAG 连续失败 N 次后自动熔断，返回"知识库暂时不可用"，保护后端不被雪崩请求压垮。

## 工具调用双通道

- **通道1 (OpenAI 原生):** 利用 `tool_calls` 字段，LLM 直接调用注册的工具
- **通道2 (纯文本标签):** 解析 `<tool_call>{"name":"...","arguments":{...}}</tool_call>` 标签

**为什么需要双通道：** 部分模型（特别是通过 API 兼容层接入的）不支持原生 tool_calls。纯文本标签是备胎方案，适用于自制 Agent 框架。

## System Prompt 约束 (Harness 的"缰绳")

Agent 的 `SYSTEM_PROMPT` 应包含：

1. **身份/角色** — "你是XX助手"
2. **行为边界** — 能做什么、不能做什么
3. **工具调用格式** — 如何输出工具调用（原生或 `<tool_call>`）
4. **数据约束** — "数字必须来自工具返回结果，禁止编造"
5. **隔离规则** — "方案A和方案B互斥，不能混算"
6. **角色边界** — "只能回答XX范围的问题，超出范围拒绝"

## Harness 随上下文退化的应对

**问题：** System prompt 在对话开头，聊到 50+ 轮后，模型注意力偏向最新消息，原始约束被稀释。

**解法：**

| 方案 | 怎么做 | 代价 |
|------|--------|------|
| 定期 /new | 聊差不多了开新会话，Harness 满血复活 | 丢对话上下文 |
| 上下文压缩 | 早期内容压缩成摘要 | 细节丢失 |
| 约束再注入 | 回答末尾带一条核心规则自我提醒 | 占 token |
| 工作流拆分 | 一个 session 只干一件事 | 交互割裂 |
| Hermes max_turns | 默认 90 轮自动到顶 | — |

**最佳实践：** 每天工作总结写入 Obsidian 笔记，知识不丢；第二天开新会话，Harness 满血。

## 日常 Harness 实践（关彧对 Hermes 做的）

1. **System Prompt 约束** — 求职教练框架（身份锁定+5模块输出+风格约束）
2. **工具控制** — 通过 `hermes tools` 开关工具集
3. **行为边界** — 角色定义（"我是小鹿，你是关彧"）、输出风格（"回复精简"）、交互纪律（"发完你再做"）
4. **配置层缰绳** — 默认模型、session_reset、Claude Code 模型配置
5. **记忆管理** — 哪些记、哪些不记、记在哪

**本质：** 关彧一直在做 Agent Harness，只不过 Harness 对象是 Hermes Agent 而非代码里的 Agent。

## Profile 概念

Hermes Profile = 一个完全独立的配置分身：

```
~/.hermes/
├── config.yaml           ← default profile
├── state.db              ← default 对话历史
├── skills/               ← default 技能
├── memory/               ← default 记忆
└── profiles/sales/       ← sales profile（完全独立）
     ├── config.yaml      ← 自己的配置
     ├── state.db         ← 自己的对话历史
     └── ...              ← 完全隔离
```

启动时指定：`hermes --profile sales`

## 企业多 Agent 部署

**核心问题：** 同一个微信 bot，不同员工怎么用不同 Harness？

**可行方案：** 单网关 + 按用户 ID 路由到不同 Profile。
**更务实的方案：** 多个 Hermes 实例，各接各的 bot。

关键在于理解：企业部署本质是管理一群 Agent，每个角色一套 Prompt + 工具权限 + 知识库范围。
