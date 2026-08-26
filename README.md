# ShiftLeft Engine · 左移·来福

> **输入需求,剩下交给 AI。**

> 一套需求驱动的测试左移工程平台 —— 从源代码与需求出发,自动产出可追溯的知识库文档(10 维度)、双向追溯图谱与 MCP-Ready 测试用例。本期以「GSD Knowledge Base 开源子集」形式发布。

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python](https://img.shields.io/badge/Python-3-blue.svg)](https://www.python.org/)
[![Claude Code Skills](https://img.shields.io/badge/Claude%20Code-Skills-orange.svg)](https://claude.com/claude-code)

> **🌐 多语言版本 / Languages**: 简体中文 · [繁體中文](README.zh-TW.md) · [English](README.en.md) · [日本語](README.ja.md)

## 🎬 演示视频

[点击观看完整演示](https://youtu.be/stfLoSjn8Go)

> 🧪 **一次完整流水线实测:130 个 agent · 耗时 1h01m · 状态 done(非 fail)** —— 编码前调查 → 前后端开发+自动检查 → 文档/图谱维护 → 自动运维部署 → 冒烟测试 → 真实 UAT → 报告,全流程真实跑通,截图见下。

## 🧩 什么是 ShiftLeft Engine?

ShiftLeft Engine 是一套**需求驱动的测试左移工程平台**(持续更新中),本期开源的是其中真实可用、可独立部署的一环:**GSD Knowledge Base** —— 把"从需求到验证"里最根基的工程能力开放出来,让每个团队都能在自己的项目上落地 **需求 → 研发 → 文档 → 图谱 → 测试用例** 的自动化链路:27 个自研 `gsd-kb-*` skills 覆盖 需求/文档/图谱/测试用例 的知识库工程与用例生成;另含 **9 个 gsd-core(MIT)研发技能**(quick/debug/spike/code-review/plan-phase/execute-phase 等,启发自 gsd-core、按需取用、未完整沿用),补足 研发/工程方法 侧面。

### 核心理念

> **输入一句话,剩下的交给 AI。**
>
> 这是 AI 时代下的新范式:**AI 是执行的主力**——从需求到编码、测试、文档、部署,由 AI 全程自动执行、自动维护、自动自愈。
>
> 人只负责输入需求与验收结果。**由 AI 驱动的测试左移**,让质量从源头被保障,全链路可追溯。

### 🚧 当前状态

> 以下为**完整工程已实现**的能力(本开源子集只含其中的 KB 工程层,见「本期开放能力」与「为什么只开源轮子」)。

- ✅ **完整流水线**:输入需求 → 确认变更模块 → 扩写需求(现状调查) → 代码调查产出 Plan → 按 Plan 快速开发(过程中首次自动检查)→ 开发完成后并行 Fill(图谱 + 文档 + 自动运维 + 元素指纹追加)→ 冒烟测试(失败则持续修复)→ UAT 测试(忠于需求 / 忠于质量)→ 报告
- ✅ 图谱可视化(离线 D3 交互式图谱)
- ✅ AI 辅助修复(冒烟 / UAT 失败自动修复)
- 🔄 持续优化:测试覆盖率分析
- 📋 规划中:更多语言支持;后期再增一轮 UAT,失败则二次修复轮询

### 🎯 未来规划

- **Phase 1**: 测试左移工程平台(当前)
- **Phase 2**: 应用到 App 开发层(规划中)
  - 将此模式扩展到移动端开发
  - 实现需求 → 编码 → 测试 → 发布 的完整闭环
  - 支持 iOS/Android/Flutter 等跨平台开发

> **这是一个持续演进的项目,欢迎关注和参与!**

---

## 🖼️ 完整流水线跑通截图(真实运行证据)

> 以下截图来自一次完整流水线实测(**130 个 agent · 1h01m · 状态 done**),按阶段排列。
> 注:「编码→部署→冒烟→UAT→报告」闭环属产品完整愿景(自动化部署能力本期未随开源子集发布),截图用于展示完整产品真实跑通;本开源子集可独立运行的能力见「本期开放能力」。

| ① 编码前调查 | ② 前后端开发 + check | ③ 文档维护 |
|---|---|---|
| ![编码前调查](docs/101编码前的调查.jpg) | ![前后端开发+check](docs/102前后端开发+check.jpg) | ![文档维护](docs/103文档维护.jpg) |

| ④ 图谱维护 | ⑤ 自动运维部署 | ⑥ 冒烟测试 |
|---|---|---|
| ![图谱维护](docs/104维护图谱.jpg) | ![自动运维部署](docs/105自动运维部署.jpg) | ![冒烟测试](docs/106冒烟测试.jpg) |

| ⑦ 真实 UAT 测试 | ⑧ UAT 测试结果 | ⑨ 产生报告 |
|---|---|---|
| ![真实UAT测试](docs/107真实UAT测试.jpg) | ![UAT测试结果](<docs/111 UAT-测试结果.jpg>) | ![产生报告](docs/108产生报告.jpg) |

| ⑩ 知识库 + 图谱 | ⑪ 文档具像化 | ⑫ 完整报文 |
|---|---|---|
| ![知识库+图谱](docs/109知识库+图谱.jpg) | ![文档具像化](docs/110文档具像化.jpg) | ![完整报文](docs/113完整报文.jpg) |

| ⑬ trce 为证 | ⑭ 视频为证 |
|---|---|
| ![trce为证](docs/111视频-trce为证.jpg) | ![视频为证](docs/112视频为证.jpg) |

---

## 🧩 为什么只开源"轮子"?——拼图,完整地放在这里

不是不想交付整列火车,而是刻意只开源这一层:**我把整列「测试左移工程平台」的火车拆成一张完整拼图,每一块拼图(轮子)都放到这里**——「需求 → 研发 → 文档 → 图谱 → 测试用例」自动化链路的所有可复用组件:27 个 `gsd-kb-*` skills + Python 引擎 + 9 个 gsd-core(MIT)研发技能。每一块都能独立安装、独立使用。

> 把这些轮子一块块拼起来,搭出来的,就是上面视频里那列**真实跑过 130 个 agent · 61 分钟 · 全链路 done** 的测试左移工程平台——一张拼图,一辆完整的火车。

> 把拼图完整地放在这里,不为别的,是为了找到**志同道合的人**:看得见这列「测试左移工程平台」火车,也愿意动手把拼图一块块拼上轨道的人。

> 轮子已经给到大家了。如果明知道拼起来就是一列完整的火车,却只想看看、不想动手——那这列火车,就只好从你身边开走了 😄

**这列火车长什么样?** → [演示视频](https://youtu.be/stfLoSjn8Go) + 上文 14 张真实运行截图。

> **本期范围**:上面的拼图(轮子)都已在本仓库交付、可独立拼装;更上游的「端到端自动编排与部署」车头,属于完整产品的后续迭代。想拼整列火车的人,从这些拼图动手,就是上车最快的路。

---

## 🎯 为什么需要 Fill?

### 痛点:传统开发的问题

```
❌ 口头约定:PM说"这里要加个字段"
   → 开发加了
   → 测试不知道
   → 三个月后没人记得为什么

❌ AI 项目黑盒:
   → AI 做了半年项目
   → 代码能跑
   → 但没人知道为什么这么设计
   → 无法维护,只能重写

❌ 无法溯源:
   → 需求变更了
   → 不知道影响哪些接口
   → 不知道影响哪些测试
   → 只能全量回归,浪费时间
```

### 解决方案:Fill 双向追溯图谱

```
需求 (REQ-xxx)
    │
    ├──→ 接口 (API-xxx)
    │       │
    │       ├──→ 数据库 (Table-xxx)
    │       │       │
    │       │       └──→ 字段级读写追溯
    │       │
    │       └──→ 前端页面 (Page-xxx)
    │               │
    │               └──→ UI 元素 (data-testid)
    │
    └──→ 测试点 (TP-xxx)
            │
            ├──→ API 测试用例
            ├──→ UI 测试用例
            └──→ E2E 测试用例
```

### Fill 的真正价值

| 追溯方向 | 价值 | 服务对象 |
|---------|------|----------|
| 需求 → 接口 | 这个需求实现了哪些接口? | 开发、测试、PM |
| 接口 → 数据库 | 这个接口读写了哪些表? | 开发、DBA |
| 接口 → 页面 | 哪些页面调用了这个接口? | 前端、测试 |
| 需求 → 测试点 | 这个需求需要测什么? | 测试 |
| 变更 → 影响 | 改了这个接口,影响哪些需求? | 全员 |
| 测试 → 回归 | 这个测试覆盖了哪些需求? | 测试、PM |

### 为什么 Fill 放在中间?

- **编码后**:有代码可以提取文档
- **测试前**:图谱决定测试范围
- **维护时**:图谱记录设计决策

### 核心价值

> **让 AI 的执行全链路可追溯。**
>
> - 需求有据可查
> - 研发有图可依
> - 测试有谱可循
>
> **这就是为什么中间放 Fill 阶段的原因!**

---

## ⚖️ 诚实性原则

测试左移有一个关键的**诚实性问题**:

### 两种测试策略

| 策略 | 做法 | 首次成功率 | 说明 |
|------|------|-----------|------|
| **忠于需求** | 没说的不测 | ~95% | 只测需求明确要求的 |
| **追求质量** | 自由发挥 | ~70% | 还要测边界、异常、性能等 |

### 为什么忠于需求能有 95% 成功率?

```markdown
# 需求说:创建订单成功后返回 order_id
✅ 测试:POST /api/orders → 200 + order_id

# 需求没说:并发创建怎么办
❌ 不测:并发冲突处理(除非需求明确要求)

# 需求没说:超大金额怎么办
❌ 不测:金额边界(除非需求明确要求)
```

### 建议

- ✅ 需求明确要求的 → 100% 测试
- ⚠️ 需求隐含的 → 95% 覆盖
- ❌ 需求没说的 → 不测(除非单独约定)

**为什么?**
- 测试左移的目标是"快速验证需求是否实现"
- 不是"追求代码完美"
- 如果要追求质量,需要额外的"质量增强"阶段

---

## 🔄 本期开放能力 · KB 工程化工作流

完整的「需求 → 编码 → 部署 → 冒烟 → UAT → 报告」自动化闭环是 ShiftLeft Engine 的**产品完整愿景**,其编排流水线按完整产品节奏迭代,**本期不随本仓库发布**。本期开放的是这条闭环里最根基的「知识库 + 图谱 + 测试用例生成」工程层,由 **27 个 `gsd-kb-*` skills** 与 **9 个 gsd-core(MIT)研发技能** 组成,可直接落地:

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1 · 初始化 KB + 图谱                                        │
│  /gsd-kb-init --source <代码> --module <模块> --output docs/kb   │
├─────────────────────────────────────────────────────────────────┤
│  Step 2 · 多维度 Fill(文档 + 图谱)                              │
│  /gsd-kb-fill + 14 个 fill 子技能(10 维度文档 + 图谱)           │
├─────────────────────────────────────────────────────────────────┤
│  Step 3 · 测试用例生成(MCP-Ready JSON)                           │
│  /gsd-kb-gen-tests-{api,e2e,ui}                                 │
├─────────────────────────────────────────────────────────────────┤
│  Step 4 · 元素指纹注入                                            │
│  /gsd-kb-enforce-locators(data-testid 标准化)                   │
├─────────────────────────────────────────────────────────────────┤
│  Step 5 · 查询 · 修复 · 增量吸收                                  │
│  /gsd-kb-query · /gsd-kb-repair-orphans · /gsd-kb-absorb         │
└─────────────────────────────────────────────────────────────────┘
```

### Step 1:初始化(init)

```
源代码 → 反向扫描 API/表/页面/任务 → 生成文档骨架 + 图谱
/gsd-kb-init --source C:/Code/your-project --module your-project --output docs/kb
```

### Step 2:多维度填充(fill)

```
文档骨架
    │
    ├──→ Phase 1:/gsd-kb-fill-tech      ← Python 引擎 batch-fill(秒级 AST 静态提取)
    └──→ Phase 2:/gsd-kb-fill-ai        ← AI multi-agent 编排(分钟级深度语义填充)
          ├── 10 维度文档:requirements · apis · storage · pages · jobs
          │             config · permissions(认证授权)· error-handling · integration · tech
          ├── 扩展:from-prd(需求原文吸收,填充权威业务上下文)
          └── 图谱:graph(构建 + 离线 D3 可视化)· graph-links(双向追溯链回填)
```

### Step 3:测试用例生成(gen-tests)

```
/gsd-kb-gen-tests-api    → 多步骤串联的 API 契约用例(MCP-Ready JSON)
/gsd-kb-gen-tests-e2e    → 基于 depends_on DAG 的业务流 / 边缘场景 / 回滚一致性用例
/gsd-kb-gen-tests-ui     → 基于 data-testid 的 UI 用例(Playwright 语义选择器)
```

模板驱动:每个子 skill 读 `templates/{API,E2E,UI}-TEST-TEMPLATE.json`,输出 MCP-Ready 结构化 JSON。执行端在完整产品中由 **QA 多 agent 编排执行系统**承接(准入 → 集群分发 → 真实环境执行 → 结果回流);本期开源子集只开放「用例生成」,执行系统不随包(后期视开源情况再定)。

### Step 4:元素指纹注入(enforce-locators)

```
扫描前端组件 → 注入标准化 data-testid(交互元素 + 校验/错误提示元素)
→ 让真实浏览器的 UI 测试"快如闪电、稳如磐石"
```

### Step 5:查询 · 修复 · 吸收

```
/gsd-kb-query            → 图谱查询:影响分析 / 需求追溯 / 文档定位,精确上下文
/gsd-kb-repair-orphans   → 修复图谱孤立链接(孤儿节点,report-only 式核对)
/gsd-kb-absorb           → 把 .planning/ 产物增量吸收进 KB 文档(增量补丁,不整篇重写)
```

---

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                  ShiftLeft Engine · 开源子集架构                  │
├─────────────────────────────────────────────────────────────────┤
│  输入                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  源代码       │  │   需求文档    │  │  ENV-CONFIG   │          │
│  │ (多语言代码)  │  │  (REQ-xxx)   │  │  (JSON 契约)  │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         ▼                 ▼                 ▼                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  SKILL 层 · 27 个 gsd-kb-*(Claude Code Skills,Markdown) │   │
│  │  init → fill(+14 子技能) → gen-tests-{api,e2e,ui}      │   │
│  │  enforce-locators → query · repair-orphans · absorb     │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│  ┌──────────────────────┴──────────────────────────────────┐   │
│  │  Python 引擎层 · knowledge-base(packages,12 子命令)     │   │
│  │  零第三方依赖 · scaffold / batch-fill / decompose /     │   │
│  │  fill / check / trace / index / graph / regression      │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│  ┌──────────────────────┴──────────────────────────────────┐   │
│  │  gsd-core(MIT)研发 skills · 9 个                        │   │
│  │  quick · debug · spike · code-review · plan-phase · ... │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  输出                                                    │   │
│  │  KB 文档(10 维度)· graph.json + graph.html(D3)          │   │
│  │  测试用例 JSON(API/UI/E2E,MCP-Ready)· ENV-CONFIG.json    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

> 完整产品的「🧠 编排层 (Pipeline Orchestrator) + MCP Agent 集群」属完整产品能力,本期不随本仓库发布(演示见上文视频,边界见「为什么只开源轮子」)。

---

## 🎯 核心能力

| 能力 | 评分 | 说明 |
|------|------|------|
| Fill 双向追溯图谱 | ⭐⭐⭐⭐⭐ | 10 维度全息映射,需求 → 接口 → 存储 → 页面 → 测试点全链路可追溯 |
| 恒定元素指纹 | ⭐⭐⭐⭐⭐ | data-testid 自动注入(enforce-locators),真实浏览器测试快而稳 |
| 测试用例生成 | ⭐⭐⭐⭐⭐ | API / UI / E2E 三格式,模板驱动,MCP-Ready JSON 直接可执行 |
| JSON 契约 | ⭐⭐⭐⭐⭐ | ENV-CONFIG.sample.json 定义部署 → 测试标准契约,下游统一解析 |
| 图谱查询 + 影响分析 | ⭐⭐⭐⭐⭐ | gsd-kb-query:变更影响范围、需求追溯、文档定位,秒级出答案 |
| 孤儿链接修复 | ⭐⭐⭐⭐☆ | graph repair-orphans 自动补边,排查残留孤立节点 |
| 增量吸收 | ⭐⭐⭐⭐☆ | gsd-kb-absorb 增量补丁式吸收,不整篇重写已有文档 |
| 零第三方依赖引擎 | ⭐⭐⭐⭐⭐ | Python 引擎 12 子命令,纯标准库,一处安装到处运行 |
| 多栈源解析 | ⭐⭐⭐⭐☆ | scaffold 反向扫描多语言(API/ORM/Page/Job),子项目自动发现 |

---

## 📦 产品组件(设计,随完整产品迭代公开)

以下 4 个组件是**完整产品**「ShiftLeft Engine」的组件接口设计(随完整产品迭代公开,未在本仓库交付):

- **`@shiftleft-engine/fill-graph`** — Fill 双向图谱的类型定义与查询接口(设计)
- **`@shiftleft-engine/locator-generator`** — 元素定位符自动注入工具(设计)
- **`@shiftleft-engine/cli-interface`** — CLI 命令解析与参数校验规范(设计)
- **`@shiftleft-engine/report-formatter`** — 综合报告生成模板(设计)

> 早期版本 README 展示的 TypeScript 代码、npm 包接口与 `shiftleft-engine` 命令行用法,均属完整产品设计稿(按产品节奏随后续版本公开)—— 本仓库真实可用的能力见下方「快速开始」。

---

## 🚀 快速开始

### 安装

```bash
git clone <本仓库地址>
cd <本仓库>
bash install-kb.sh  # 发布仓库根直接运行; 源码克隆内为 bash release/install-kb.sh 或 bash scripts/install-kb.sh
```

- 默认 **copy** 模式(安全,仓库移动不产生断链);`--link` 符号链接(开发模式,改源码即生效);`--target` 可改目标目录
- 安装内容:`gsd-kb-*` skills + 9 个 gsd-core(MIT)研发 skills → `~/.claude/skills`;gsd-core 引擎 → `~/.claude/gsd-core`;Python 引擎 → `~/.claude/knowledge-base`
- 位置说明:27 个 `gsd-kb-*` 在仓库根 `skills/`;9 个 gsd-core(MIT)研发技能随发布包提供(源码克隆为 `release/release-skills/`,发布包根为 `release-skills/`)——仓库根 `skills/` 只含 27 个 `gsd-kb-*`。完整边界见 `release/PACKAGE.md`

**安装完成后重启 Claude Code**,即可使用 `/gsd-kb-*` 斜杠命令。

> 本工程首次开源,安装或使用中遇到问题,欢迎反馈(提 issue),我会尽快处理。

### 最小可用路径(init → fill-ai → gen-tests-e2e)

```bash
# 1. 初始化 KB + 图谱(反向扫描生成文档骨架)
/gsd-kb-init --source C:/Code/your-project --module your-project --output docs/kb

# 2. AI 多代理深度填充(10 维度文档 + 图谱)
/gsd-kb-fill-ai --module your-project --source C:/Code/your-project/backend \
                --frontend C:/Code/your-project/frontend --output docs/kb

# 3. 生成 MCP-Ready E2E 测试用例
/gsd-kb-gen-tests-e2e --module your-project --output docs/kb
```

### Python 引擎

```bash
cd knowledge-base         # 发布仓库根; 源码克隆内为 cd release/knowledge-base
python3 -m packages.cli --help    # 12 个子命令:decompose / fill / check / trace /
                                  # scaffold / batch-fill / graph / index / regression / ...
```

### ENV-CONFIG 契约

部署 → 测试的 JSON 契约样例见 [`samples/ENV-CONFIG.sample.json`](samples/ENV-CONFIG.sample.json);完整发布物边界见 [`PACKAGE.md`](PACKAGE.md)（源码克隆内为 `release/PACKAGE.md`）。

---

## 📐 技术栈

- **引擎语言**:Python 3(零第三方依赖,纯标准库)
- **Skill 层**:Claude Code Skills(Markdown 指令 + 模板)
- **数据契约**:JSON(ENV-CONFIG / 测试用例 / graph.json)
- **图谱可视化**:D3.js(离线,graph.html 交互式力导向图)
- **安装器**:bash(install-kb.sh,开源即装)

---

## 🤝 贡献指南

欢迎贡献!请先阅读 [`release/PACKAGE.md`](release/PACKAGE.md) 了解开源发布物边界。

### 开发环境

```bash
# 克隆仓库(发布时填写实际仓库地址)
git clone git@github.com:<your-org>/<repo>.git

# 双副本同步(重要!)
# skills/ 是源码,release/skills/ 是发布副本 —— 改 skill 时必须两处同步,
# 否则发布物与源码不一致(仓库 skills 与 ~/.claude 全局副本同理)

# Python 引擎直接在 knowledge-base/ 下运行
cd knowledge-base
python3 -m packages.cli --help
```

---

## 📄 许可证

本项目采用 [Apache License 2.0](LICENSE) 许可证。

**为什么选择 Apache-2.0?**
- 宽松许可,最大化采用率与社区传播
- 内含专利授权与商标保护条款,兼顾贡献者权益
- 与启发本项目的 gsd-core(MIT)许可证兼容,可保留归属声明

> 本项目包含衍生自 [gsd-core](https://github.com/open-gsd/gsd-core)(MIT License)的内容,详见 [NOTICE](NOTICE)。

---

## 📊 项目统计

- **Skills**:27 个 `gsd-kb-*`(其中 14 个 fill 子技能,覆盖 10 维度文档 + 图谱)
- **Python 引擎**:12 个子命令,零第三方依赖
- **知识图谱**:10 维度双向追溯 + 离线 D3 可视化
- **测试用例**:三格式生成(API / UI / E2E),MCP-Ready JSON
- **研发技能**:内置 9 个 gsd-core(MIT)开发技能

---

## 🔗 相关链接

- [演示视频](https://youtu.be/stfLoSjn8Go)
- [开源发布物说明](release/PACKAGE.md)

---

## 🙏 致谢

### 灵感来源

本项目的架构设计和部分工具函数借鉴了以下优秀开源项目:

- **[GSD Core](https://github.com/open-gsd/gsd-core)** - 元提示、上下文工程和规范驱动开发系统
  - 本项目的知识图谱查询、文档生成等能力受 GSD Core 启发
  - 研发侧 skills(gsd-quick / gsd-debug / gsd-spike / gsd-code-review / gsd-plan-phase 等 9 个)直接内嵌自 gsd-core
  - GSD Core 采用 MIT 许可证,本项目对其致以诚挚感谢

### 技术栈致谢

感谢以下开源项目:
- [Python](https://www.python.org/)
- [D3.js](https://d3js.org/)
- [Claude Code](https://claude.com/claude-code)
- [Bash](https://www.gnu.org/software/bash/)

---

## 🗺️ 路线图

### 已完成

- ✅ 需求驱动 KB 工程化流水线(gsd-kb-init → fill → graph)
- ✅ Fill 双向追溯图谱(10 维度 + 离线 D3 可视化)
- ✅ 图谱可视化(graph.html 交互式力导向图)
- ✅ 恒定元素指纹(data-testid 注入,enforce-locators)
- ✅ API / UI / E2E 测试用例生成(MCP-Ready JSON)
- ✅ AI 辅助修复(冒烟 / UAT 失败自动修复)
- ✅ Python 引擎 12 子命令(零第三方依赖)
- ✅ 一键安装器(install-kb.sh)

### 进行中

- 🔄 测试覆盖率分析(coverage 深化)

### 规划中

- 📋 QA 多 agent 编排执行系统(测试左移执行端,后续视开源情况决定)
- 📋 npm 分发 `@shiftleft-engine` 组件(开源子集 → 独立包)
- 📋 更多语言支持
- 📋 后期:UAT 通过后再增一轮 UAT,失败则二次修复轮询
- 📋 性能测试集成(K6)
- 📋 移动端 App 开发支持(Phase 2)
- 📋 多人协作模式

### 未来愿景(Phase 2)

> **将此模式应用到 App 开发层**
>
> - 实现需求 → 编码 → 测试 → 发布 的完整闭环
> - 支持 iOS/Android/Flutter 等跨平台开发
> - 集成 CI/CD 流水线
> - 支持多团队协作

---

## 💬 联系方式

- **邮箱**: wanglikai201101@gmail.com
- **GitHub**: [@wanglikai201101-ctrl](https://github.com/wanglikai201101-ctrl)

---

## 📌 版权声明

**© 2026 ShiftLeft Engine · Licensed under the Apache License 2.0**

*本仓库为个人独立项目,不涉及任何公司商业秘密。*

*基于 GSD Core 的启发进行架构设计,感谢原作者的开源贡献。*