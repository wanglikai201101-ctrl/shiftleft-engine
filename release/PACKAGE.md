# GSD Knowledge Base — 开源发布物包（PACKAGE）

> 定稿依据：`.planning/spikes/RESULTS.md`（综合报告 §0 / §3.5 / §4）、`.planning/spikes/002-min-wheels-footprint/RESULTS.md`、`.planning/spikes/MANIFEST.md`；边界为 **2026-08-24 用户定稿**。
> 本目录是「最终开源发布物边界」的**落地副本**（`cp -R` 自仓库），源文件一律未删改。**未提交 git**。

---

## 1. 是什么

一个**可独立使用的领域自动化工具链**发布包：把用户自研的 gsd-kb 轮子（知识库工程 + 测试用例生成）+ 9 个 gsd-core（MIT）研发技能，拼成「研发 + 测试 + 文档 + 用例生成」全链条。放进 `~/.claude/` 即用，Python 引擎零第三方依赖。

- **目标读者**：使用 Claude Code 的知识库 / 测试工程师；想给项目搭建 KB 工程化与测试治理流水线的开发者。
- **安装入口**：`bash install-kb.sh`（把 `release/skills/` 下 `gsd-kb-*` 装到 `~/.claude/skills/`，copy/link 模式，默认 safe copy）；Windows 用 `install-kb.ps1`。
- **Python 引擎**：在 `release/knowledge-base/` 下 `python -m packages.cli`（12 个子命令已冒烟验证，`pyproject.toml` 为可选 pip 安装）。
- **一句话边界**：开源「领域轮子」，保留「自研编排引擎 + 完整测试执行系统」在仓库边界外——与 gsd-core 是分工（它给研发方法论，包给知识库 + 测试治理），不是替代。

---

## 2. 目录树（实际建成，2026-08-24）

```
release/                                        (10M, 含 gsd-core 引擎快照 7.5M;其余 ≈2.5M)
├── PACKAGE.md                                  # 本文件
├── install-kb.sh                               # 一键安装器（copy/link 模式，来源 scripts/install-kb.sh）
├── install-kb.ps1                              # Windows 版安装器（RESULTS.md §3.5 提及）
├── commands/
│   └── gsd/
│       ├── kb-gen-tests-api.md                 # gsd-core（MIT）命令包装层，gen-tests 父 skill 的分派入口
│       ├── kb-gen-tests-e2e.md
│       └── kb-gen-tests-ui.md
├── samples/
│   └── ENV-CONFIG.sample.json                  # deploy→test 契约脱敏占位样本（gen-tests 等下游按 schema 生成）
├── skills/                                     # 27 个 gsd-kb-*（用户自研，来源仓库 skills/，去 QA 系统 5 个）
│   ├── gsd-kb-absorb/
│   ├── gsd-kb-branch/
│   ├── gsd-kb-deploy/                          # 纯 SKILL.md + sub-skills，无脚本（可随包）
│   ├── gsd-kb-enforce-locators/
│   ├── gsd-kb-fill/  gsd-kb-fill-ai/
│   ├── gsd-kb-fill-{apis,config,error-handling,from-prd,graph,graph-links,
│   │   integration,jobs,pages,permissions,requirements,storage,tech}/
│   ├── gsd-kb-gen-tests/                       # 用例生成父入口（分派器）
│   ├── gsd-kb-gen-tests-{api,e2e,ui}/          # 纯用例生成（RESULTS.md 明确保留）
│   ├── gsd-kb-init/  gsd-kb-install/  gsd-kb-query/  gsd-kb-repair-orphans/
├── release-skills/                             # 9 个 gsd-core（MIT）研发 skills，来源仓库 skills/ + gsd-core workflows
│   ├── gsd-code-review/  gsd-debug/  gsd-fast/  gsd-new-project/
│   ├── gsd-quick/  gsd-secure-phase/  gsd-spike/  gsd-plan-phase/  gsd-execute-phase/
├── contracts/                                  # 2 个 gsd-core 协议模板（契约模板方式，供编排 plan-research/plan-review 复用）
│   ├── plan-research-contract.md               # 改编自 gsd-phase-researcher（只读研究协议）
│   └── plan-checker-contract.md                # 改编自 gsd-plan-checker（执行前计划评审协议）
└── knowledge-base/                             # Python 引擎最小子集（来源仓库 knowledge-base/）
    ├── __init__.py                             # packages import 锚点
    ├── pyproject.toml                          # 可选（pip 安装用；python -m packages.cli 不需要）
    ├── README.md
    ├── assets/d3.v7.min.js                     # graph/visualize.py 离线 D3 依赖（276K）
    └── packages/                               # 命名空间包（已修正：cli/core 包回 packages 层）
        ├── cli/                                # __main__.py，12 子命令
        └── core/                               # 全量子包 + __init__.py
            ├── batch/  detail_filler/  generators/  graph/  indexing/  models/
            ├── parsers/  regression/  requirement_decomposer/  scaffold/
            └── skeleton_generator/  validators/
```

统计：97 个目录 / 133 个 `.md` 文件（均不含 `release/gsd-core/` 引擎快照）；`skills/` 600K、`knowledge-base/` 824K、`release-skills/` 1.0M、`contracts/` 16K、`commands/` 32K。

---

## 3. 发布清单对照表

### ✅ 列入

| 项 | 来源 | 说明 / 原因 |
|---|---|---|
| `skills/` 27 个 `gsd-kb-*` | 仓库 `skills/` | 用户自研轮子（fill 文档 + 图谱 + 用例生成 + 修复），去 QA 系统 5 个后全量 |
| `skills/gsd-kb-gen-tests{,-api,-e2e,-ui}` | 仓库 `skills/` | 测试**用例生成**（纯生成不执行），RESULTS.md 明确保留；父 skill 为分派器入口一并保留 |
| `skills/gsd-kb-deploy/branch/install` | 仓库 `skills/` | 纯 SKILL.md + sub-skills，无 `.sh/.py` 脚本，文档型（RESULTS.md §3.5：可随包） |
| `knowledge-base/{__init__.py,packages/(cli,core)/,assets/d3.v7.min.js,pyproject.toml,README.md}` | 仓库 `knowledge-base/` | 最小自足子集（spike 002 B3 实测必需项），零第三方 pip 依赖；`cli/`、`core/` 已包回 `packages/` 层以对齐内部 `packages.core.*` import |
| `release-skills/` 9 个 gsd-core | `~/.claude/skills/` + `gsd-core/workflows/` | quick/debug/spike/secure-phase/code-review/new-project/fast（RESULTS.md §3.5 定稿随包）+ plan-phase/execute-phase（新增，自包含 workflow/references 闭包）；**MIT 归属**（§4） |
| `contracts/` 2 个协议模板 | `gsd-core` agents/ | 改编自 `gsd-phase-researcher` / `gsd-plan-checker`，文字化「只读研究 / 执行前计划评审」协议，供编排 Route 阶段 plan-research / plan-review 复用；**MIT**（§4） |
| `install-kb.sh`（+ `install-kb.ps1`） | 仓库 `scripts/` | 一键安装器，对标 gsd-core `npx` 的门面命令（RESULTS.md §3.5 / §4） |
| `commands/gsd/kb-gen-tests-{api,e2e,ui}.md` | 仓库 `commands/gsd/` | gsd-core（MIT）命令包装层，`commands/` 排除的**唯一例外**（spike 002 C2）；父 skill 分派经此 |
| `samples/ENV-CONFIG.sample.json` | 仓库 `samples/` | deploy→test 契约脱敏占位样本（`process-compose.yaml` 含机器绝对路径不发布） |

### ❌ 不列入

| 项 | 原因 |
|---|---|
| `skills/gsd-kb-regression`、`gsd-kb-regression-{analyze,generate,execute}` | **QA 测试系统**：回归链路，执行端为完整产品能力，本发布物仅含生成与计划 |
| `skills/gsd-kb-loop` | **QA 测试系统**：需求驱动开发循环，执行端为完整产品能力，本发布物仅含生成与计划 |
| `scripts/kb/`（遗留探测脚本） | 开发者遗留工具（响应结构探测），`gsd-kb-gen-tests-api` 已内联探测规则，非发布物组件 |
| `knowledge-base/skills/`（含 `gsd-kb-pipeline*` 4 个编排 skill + 非同步镜像拷贝） | 编排层（完整产品能力，不在本发布物）；镜像拷贝与顶层 `skills/` 已有 diff |
| `knowledge-base/mcp_server/` | 无 skill / CLI import（spike 实测可省） |
| `knowledge-base/knowledge_base/`（顶层包，doc_guardian 等） | `packages/` 零引用 |
| `knowledge-base/docs/`、`modules/`、`tests/`、`docs-index.json`、`assets/graph-template.html` | 运行期不读 / 用户样例 / 仅开发 / index 输出 / legacy |
| `src/` | 编排引擎（自研，不公开 = 能力护城河） |
| `gsd-core/` | 上游引擎 |
| 除上述 9 个外的全部非 kb `gsd-*` skills（60+） | 上游 gsd-core 作品 |
| `commands/`（除 3 个 kb-gen-tests 包装 md） | 上游命令层 |
| `process-compose.yaml` | 含机器绝对路径，非公开样本 |

---

## 4. 授权与归属声明

### 本包授权：Apache License 2.0
本包（`gsd-kb-*` skills + `knowledge-base/` 引擎 + 打包结构）采用 **Apache License 2.0**（见同目录 `LICENSE`）。选择理由：宽松许可最大化采用与传播、内置专利授权与商标保护、与 gsd-core（MIT）兼容且可携带归属声明。

### gsd-core（MIT）归属声明
本包包含来自 [open-gsd/gsd-core](https://github.com/open-gsd/gsd-core)（**MIT License**）的内容：

1. **`release-skills/`** 下 9 个 skill（`gsd-code-review` / `gsd-debug` / `gsd-fast` / `gsd-new-project` / `gsd-quick` / `gsd-secure-phase` / `gsd-spike` / `gsd-plan-phase` / `gsd-execute-phase`）——gsd-core MIT 内容的便携副本（plan-phase / execute-phase 为 self-contained 副本，含 workflow/references/templates 闭包）；
2. **`contracts/`** 下 2 个协议模板（`plan-research-contract.md` / `plan-checker-contract.md`）——改编自 gsd-core 的 `gsd-phase-researcher` / `gsd-plan-checker` agent 契约，以**契约模板方式**（文字化引用，非调用 agent）供编排引擎的 plan-research / plan-review 步骤复用；
3. **`commands/gsd/kb-gen-tests-{api,e2e,ui}.md`**——gsd-core 命令包装层（MIT）。

上述 gsd-core 内容按 **MIT License** 随包再分发，完整版权与许可声明见同目录 **`NOTICE`** 文件。不得暗示 gsd-core / open-gsd 为本包作者或赞助方。

本包自身资产（`gsd-kb-*` skills + `knowledge-base/` 引擎）为用户自研，与 gsd-core 为**分工关系**（它提供研发方法论，本包提供知识库 + 测试治理）。

---

## 5. 备注

- 包内 skill 对 `gsd-core` 的引用多数为候选路径搜索（`~/gsd-core/...` 等旧位置），但**部分步骤(如 STATE.md 表维护)在引擎缺失时会发生 in 操作失败/硬退出**（实测 gsd-fast `log_to_state` 无引擎即 `exit 1`）。请用安装器一并安装 `gsd-core` 引擎与 `scripts/` 兄弟目录,不要单独裸拷 `release-skills/`。