# Engineering Knowledge Base — 工程知识库文档体系

> **核心理念：业务需求是知识库的权威源，代码是需求的实现。**

一套需求驱动的结构化工程文档体系，包含文档规范（Skills）、自动化工具链（packages）、AI 多代理填充管线（kb-fill）、以及示范模块（logistics-order）。通过"需求 → 文档 → 代码 → 校验"的正向数据流，实现全链路可追溯。

## 需求驱动数据流

```
需求文档（REQ-xxx）
  │  decompose
  ▼
文档骨架生成（按 Skill 规范）
  │  batch-fill (Phase 1: AST/Regex)
  ▼
技术细节填充（参数、类型、路由元数据）
  │  kb-fill-ai (Phase 2: AI multi-agent)
  ▼
深度语义填充（业务规则、追溯链、数据流）
  │  check
  ▼
一致性校验（代码必须匹配文档）
  │  graph build
  ▼
知识图谱（可视化追溯 + 影响分析）
```

## 项目架构

> 以下为完整引擎视角;`skills/`（10 个 engineering-doc-* 文档规范）、`modules/`（示范模块 logistics-order）、`tests/` 与 `knowledge_base/` 兼容层**不随开源发布包**。本发布目录仅包含 `packages/`、`assets/`、`pyproject.toml` 与 `README.md`。

```
.
├── packages/                        # 🔧 自动化工具链（分层架构）
│   ├── core/                        #   核心层：与框架无关的纯业务逻辑
│   │   ├── requirement_decomposer/  #     ① 需求分解器（核心入口）
│   │   ├── skeleton_generator/      #     ② 文档骨架生成器（按 Skill 渲染）
│   │   ├── detail_filler/           #     ③ 技术细节填充器（代码 → 文档辅助）
│   │   ├── validators/              #     ④ 一致性检查器（代码必须匹配文档）
│   │   ├── indexing/                #     ⑤ 文档索引与追溯链查询
│   │   ├── graph/                   #     ⑥ 知识图谱构建器 + D3 可视化
│   │   ├── scaffold/                #     ⑦ 代码反向扫描（API/ORM/Page/Job）
│   │   ├── batch/                   #     ⑧ 批量填充（多线程 AST 提取）
│   │   ├── models/                  #     数据模型（dataclass）
│   │   ├── parsers/                 #     代码解析器（多语言，Registry 模式）
│   │   └── generators/              #     文档生成器（兼容旧流程）
│   ├── mcp_server/                  #   ⚠️ 不随包发布（MCP Server，仅内部工具链使用）
│   └── cli/                         #   CLI：命令行工具
│       └── __main__.py              #     decompose / fill / check / trace / scaffold / batch-fill / graph
│
├── assets/                          # 📦 静态资源
│   └── d3.v7.min.js                #   D3 图谱可视化（离线用）
│
├── pyproject.toml                   # 项目配置
└── README.md
```

## GSD AI Fill 管线（kb-fill 子 skill 体系）

```
/gsd-kb-fill                         ← 总入口（Phase 1 + Phase 2）
  ├── Phase 1: /gsd-kb-fill-tech     ← CLI batch-fill（秒级，AST/Regex）
  └── Phase 2: /gsd-kb-fill-ai      ← Orchestrator（分钟级，AI multi-agent）
        ├── Wave 1 (并行):
        │   ├── /gsd-kb-fill-storage     ← ORM + DDL + API反向 存储发现
        │   └── /gsd-kb-fill-jobs        ← celery + asyncio + timer 任务发现
        ├── Wave 2:
        │   └── /gsd-kb-fill-requirements ← 需求推断 + TP 测试点
        ├── Wave 3 (并行):
        │   ├── /gsd-kb-fill-pages       ← 前端组件分析 + data-testid
        │   └── /gsd-kb-fill-apis        ← API 深度语义填充
        └── Wave 4:
            └── /gsd-kb-fill-graph       ← 知识图谱构建 + D3 可视化
```

每个子 skill 独立运行，上下文精确聚焦（~120-150行 prompt），避免单体 monolith 的上下文膨胀问题。

### 使用示例

```bash
# 完整流程（scaffold → Phase 1 → Phase 2）
/gsd-kb-init --source C:/Code/your-project/backend --module your-project --output docs/kb

# 只跑 Phase 2 AI 填充
/gsd-kb-fill-ai --module sandbox --source C:/Code/your-project/backend/app/presentation/api/sandbox --output docs/kb --frontend C:/Code/your-project/frontend

# 只重跑某个子 skill
/gsd-kb-fill-graph --module sandbox --output docs/kb
/gsd-kb-fill-requirements --module sandbox --source ... --output docs/kb
```

### 产出结构

```
{output}/{module}/
├── MODULE.md              ← 模块总览（业务概述、核心数据流、需求追溯表、资产清单）
├── requirements/          ← REQ-xxx（含 TP 测试点分解 + 追溯链）
├── apis/                  ← API 端点文档（参数来源、响应流向、业务规则）
├── storage/               ← 数据表文档（字段级读写追溯）
├── pages/                 ← 前端页面文档（元素清单、接口调用顺序、数据流转）
├── jobs/                  ← 定时/后台任务文档
└── graph/
    ├── graph.json         ← 结构化关系图数据
    ├── graph.html         ← 交互式 D3 力导向图可视化
    └── d3.v7.min.js       ← 离线 D3 库
```

## 分层设计

```
┌─────────────────────────────────────────────────────────────┐
│  入口层（可替换，互不依赖）                                    │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ CLI      │  │ MCP Server   │  │ GSD Skills   │          │
│  └────┬─────┘  └──────┬───────┘  └──────┬───────┘          │
│       └────────────────┼───────────────────┘                 │
│                        ▼                                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Core 层（纯 Python 标准库，零外部依赖）                │  │
│  │  scaffold → batch_fill → graph_builder →               │  │
│  │  requirement_decomposer → detail_filler → validators    │  │
│  └───────────────────────────────────────────────────────┘  │
│                        ▼                                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Models 层（dataclass 数据模型）                        │  │
│  └───────────────────────────────────────────────────────┘  │
│                        ▲                                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Skills 层（10 个 SKILL.md 文档规范，只读输入）         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

```bash
# 安装（开发模式）
pip install -e ".[dev]"

# 需求驱动工作流
python -m packages.cli decompose --req modules/logistics-order/requirements/REQ-LO-001.md
python -m packages.cli fill --doc modules/logistics-order/apis/POST-orders.md --code service/api/order.py --function create_order
python -m packages.cli check --all --strict
python -m packages.cli trace --id REQ-LO-001
python -m packages.cli index --output docs-index.json

# 存量模块补全（从代码反向生成文档骨架）
python -m packages.cli scaffold --source src/billing/ --module billing --output modules

# 批量填充（Phase 1 静态提取）
python -m packages.cli --kb-path modules batch-fill --module billing --source /project-root --workers 8

# 知识图谱构建
python -m packages.cli --kb-path modules graph build --output modules/billing/graph
```

> 命令示例中的 `modules/logistics-order/`、`modules/billing` 均为完整引擎的示范数据路径，不随本开源发布包;发布包内请以 `python -m packages.cli --help` 查看可用子命令。

## MCP 集成

> **`mcp_server` 不随本发布包提供。** MCP Server 仅面向内部工具链（对内部 AI IDE 暴露工具），未包含在发布包中（见 `release/PACKAGE.md`）。对应能力已由 CLI（`python -m packages.cli`）、GSD Skills 与脚本工具链覆盖。

## 文档规范（Skills）

> `engineering-doc-*`（10 个）与 `frontend-testability` 文档编写规范 skills **不随本发布包**。该规范由 GSD 技能库（`gsd-kb-fill-*` 等）按需加载，本发布包仅提供 packages 工具链。

## 开发计划

| 阶段 | 状态 | 内容 |
|------|------|------|
| Phase 1 | ✅ 已完成 | 旧架构（代码驱动）：分层重组、core 层、CLI、单元测试 |
| Phase R1 | ✅ 已完成 | 需求驱动架构重写：RequirementDecomposer、SkeletonGenerator、DetailFiller、一致性检查方向修正、追溯链增强、MCP/CLI 重新设计 |
| Phase 2 | ✅ 已完成 | scaffold 反向扫描、batch-fill 静态提取、graph 图谱构建、GSD kb-fill 子 skill 体系 |
| Phase 3 | 📋 计划中 | tree-sitter 多语言解析、LLM 集成、存量迁移工具 |

## 许可证

本目录为 GSD Knowledge Base CLI 的 Python 引擎发布副本，供 `gsd-kb-*` skills 调用。

本目录随 ShiftLeft Engine 以 Apache-2.0 发布，内含衍生自 gsd-core(MIT) 的内容，详见发布物根 LICENSE/NOTICE。
