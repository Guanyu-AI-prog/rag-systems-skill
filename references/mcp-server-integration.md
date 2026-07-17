# MCP Server Integration for RAG Agents

## When to Use MCP Server

MCP (Model Context Protocol) exposes your RAG as a tool/resource that any MCP-compatible agent (Claude Code, Cursor, Hermes, etc.) can call.

**Best for: domain-specific knowledge that other agents DON'T have.**

| Knowledge Type | MCP Value | Why |
|---------------|-----------|-----|
| Telecom packages (运营商套餐) | ✅ High | Claude/Hermes don't know current plans |
| Company internal docs | ✅ High | Private, not in training data |
| Industry regulations | ✅ High | Region-specific, time-sensitive |
| AI/ML paper summaries | ❌ Low | Claude already knows this |
| General tech tutorials | ❌ Low | Public knowledge, no edge |

**Rule of thumb:** If Claude could answer equally well without your RAG, MCP adds no value. MCP shines when your data is the differentiator.

## Architecture Pattern

```
RAG MCP Server
├── Tools (actions):
│   ├── telecom_query(query) → RAG retrieval + answer
│   ├── plan_calculator(params) → cost computation
│   └── compare_plans(plan_a, plan_b) → structured comparison
├── Resources (data):
│   ├── telecom://knowledge-base → exposes knowledge base content
│   └── telecom://advice → domain expertise (practical guides)
└── Prompts (optional):
    └── recommend_plan(user_profile) → personalized recommendation

Any MCP Client → calls your RAG
├── Claude Code
├── Cursor
├── Hermes
└── Custom agents
```

## Compliance Considerations

### ✅ Safe to include
- Public package info (from official websites/APPs)
- Personal experience sharing (like blog posts)
- Public policy info (工信部 policies, 携号转网 process)
- Pricing calculators (personal tool, like a comparison website)
- Customer service communication tips (personal expertise)

### ⚠️ Do NOT include
- Internal training materials from employer
- Unpublished internal policies
- Employee-only system interfaces/APIs
- Anything that could be mistaken for official carrier service

### Required disclaimer
Add to any public-facing deployment:
> "本服务为个人工具，非运营商官方，仅供参考。"
> (This service is a personal tool, not affiliated with any carrier, for reference only.)

## Geographic Focus Strategy

**Limitation → Feature framing:**

Instead of: "我只在广州，有局限性"
Say: "聚焦广东地区，架构支持按省份扩展"

Why this works:
- Data quality > coverage breadth
- Focused scope = more accurate, easier to maintain
- Architecture supports expansion (add new data directory per province)
- Shows engineering pragmatism in interviews

Data structure for multi-region support:
```
data/
├── guangdong/
│   ├── mobile_plans.json
│   ├── unicom_plans.json
│   ├── telecom_plans.json
│   └── broadband_plans.json
├── README.md  # "当前覆盖广东，架构支持扩展"
└── (future: beijing/, shanghai/, etc.)
```

## Data Preparation Strategy

Before building new data, **check what you already have**:
1. Search existing files for domain-related content
2. Check old project directories (symlinks may point to Desktop files)
3. Measure total lines/chars — often more than expected
4. Import existing data first, iterate later

Phased approach:
1. **Phase 1 (1-2 hours):** Import existing data into vector DB, get basic version running
2. **Phase 2 (ongoing):** Add practical experience docs (口述 → AI整理, 10 min/day)
3. **Phase 3 (optional):** Expand to other carriers/regions

## Interview Talking Points

> "我把运营商工作积累的行业经验——套餐知识、客服沟通技巧、办理流程——加上多运营商的公开数据，做成了 MCP 服务。任何支持 MCP 协议的 AI Agent 都能调用它。这不只是一个查询工具，而是一个可复用的领域知识服务。"

> "我聚焦广东地区确保数据准确性，但架构上支持按省份扩展。数据质量比覆盖面更重要。"

## Decision Advisor Pattern (高级 MCP 形态)

**不只是"查询工具"，而是"决策顾问"。**

普通 MCP：用户问"59套餐多少流量" → 返回套餐信息
决策顾问：用户说"我是移动老用户，流量不够" → 分析情况 → 给出3种方案 → 每种方案附带操作步骤和话术

**核心价值：降低用户行动门槛。**

```
telecom_advisor MCP Server
├── 工具: analyze_situation(运营商, 当前套餐, 需求)
│         → 分析用户情况，给出多种方案（降套餐+流量卡、转网、升级等）
├── 工具: get_solution_guide(方案类型)
│         → 返回详细操作步骤 + 客服话术 + 注意事项 + 预计耗时
├── 工具: compare_plans(运营商A, 运营商B)
│         → 套餐对比表格
└── 资源: telecom_expertise
          → 行业经验库（转网流程、客服沟通技巧、避坑指南）
```

**为什么比单纯推荐更有价值：**
- 用户知道有选择，但觉得麻烦所以不做
- 决策顾问给出"3步搞定"的具体路径，降低心理门槛
- 这是**领域专家知识**，AI 通用模型没有的

**面试话术：**
> "我做的不是查询工具，是决策顾问。用户说流量不够，Agent 不是简单推荐升级，而是分析：降套餐+流量卡能省30元，携号转网能多20GB。选了方案后，给出具体操作步骤和跟客服沟通的话术。"

**合规注意：**
- 离职员工分享工作经验完全合法
- 携号转网是工信部政策，运营商必须配合
- 降套餐是用户合法权利
- 不能泄露在职时的内部系统/未公开政策
- 需加声明："本服务为个人工具，非运营商官方，仅供参考。"
