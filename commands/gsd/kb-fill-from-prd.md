---
name: gsd-kb-fill-from-prd
description: "Read original requirement docs (PRD/user stories) and enhance KB files with authoritative business context"
argument-hint: "--module <name> --prd <path> --output <path> [--force]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
  - Agent
---



<objective>
Read original requirement documents (PRD, user stories, functional specs) from the project,
then use them to enhance existing KB files with authoritative business context.

This skill bridges the gap between "code-inferred KB" and "real product intent":
- Requirements docs: replace code-guessed names/descriptions with official product language
- API docs: supplement missing business context (use cases, acceptance criteria)
- Page docs: add official page names, user flow descriptions from PRD
- Domain glossary: extract official terminology defined in PRD

Unlike fill-requirements (which reverse-engineers from code), this skill uses the PRD as
the SOURCE OF TRUTH and aligns KB docs to match product intent.
</objective>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name in KB output directory
- `--prd <path>` (required): path to original requirement documents. Accepts:
  - Single file: `--prd docs/PRD-sandbox.md`
  - Directory: `--prd docs/requirements/` (reads all .md/.txt/.docx files inside)
  - Multiple files: `--prd "file1.md,file2.md"`
- `--output <path>` (optional, default: `.planning/ontology`): KB documentation directory (where MODULE.md lives)
- `--force` (optional): overwrite existing content even if not "待补充". Without --force, only enhance "待补充" or empty sections.

If missing required args:
```
Usage: /gsd-kb-fill-from-prd --module <name> --prd <path> --output <path> [--force]

Example:
  /gsd-kb-fill-from-prd --module sandbox --prd docs/PRD-sandbox.md --output docs/test-sandbox7
  /gsd-kb-fill-from-prd --module sandbox --prd docs/requirements/ --output docs/test-sandbox7
```

## Step 2: Parse and index PRD content

Read all PRD files and build a structured index:

**2a. Extract PRD structure:**
- Feature/Epic names → map to REQ names
- User stories / acceptance criteria → map to TP test points
- UI mockup descriptions / page flows → map to page docs
- API specifications (if any) → map to API docs
- Business rules / constraints → map to 业务规则表
- Terminology definitions / glossary → map to 领域术语表

**2b. Build mapping index:**

For each section in the PRD, classify its content:

| PRD 内容类型 | 映射目标 | 匹配策略 |
|-------------|---------|---------|
| Feature/Epic 标题 + 描述 | `requirements/REQ-*.md` 的需求概述 | 按功能域名匹配 |
| User Story / AC | `requirements/REQ-*.md` 的 TP 测试点 | 按 API 路径/页面名匹配 |
| 页面描述 / 交互流程 | `pages/*.md` 的用户操作流 | 按页面名/路由匹配 |
| 接口规格 / 字段描述 | `apis/*.md` 的请求参数/响应结构 | 按 API 路径匹配 |
| 术语定义 / 名词解释 | `requirements/REQ-*.md` 的领域术语表 | 直接提取 |
| 业务规则 / 约束条件 | `requirements/REQ-*.md` 的业务规则表 | 按关联 API/页面匹配 |
| 验收标准 / 测试场景 | `requirements/REQ-*.md` 的 TP 预期结果 | 按功能匹配 |

**2c. PRD 格式自适应解析：**

支持多种 PRD 格式：
- Markdown 结构化文档 → 按 ## 标题层级解析
- User Story 格式 → `As a {role}, I want to {action}, so that {benefit}` 模式
- 表格式需求列表 → `| 需求ID | 描述 | 优先级 |` 模式
- 自由文本 → 按段落 + 关键词（"功能"、"需求"、"规则"、"约束"）切分

## Step 3: Load existing KB files

Read current state of KB docs:
```
REQUIREMENTS = read all $OUTPUT/$MODULE/requirements/REQ-*.md
APIS = read all $OUTPUT/$MODULE/apis/*.md (基本信息 + 测试断言 sections)
PAGES = read all $OUTPUT/$MODULE/pages/*.md (基本信息 + 用户操作流 sections)
```

Build a reverse index: API path → filename, page route → filename, REQ-ID → filename.

## Step 4: Spawn enhancement agents

**🔒 单模块单 agent 规则（与 fill-requirements 一致）：**
- 如果 PRD 只涉及一个模块 → spawn 1 个 agent
- Agent 输出所有增强内容，不自行拆分 sub-agents

Agent prompt:
```
You are enhancing existing KB documentation using an authoritative PRD (Product Requirements Document).

Your role: the PRD is the SOURCE OF TRUTH for business intent. The existing KB docs were
reverse-engineered from code — they are technically accurate but may lack business context,
use wrong terminology, or miss acceptance criteria. Your job is to ENRICH (not replace)
the KB docs with PRD content.

## Original PRD content:
{full PRD text, indexed by section}

## Existing KB documents to enhance:
### Requirements (current state):
{summary of each REQ: ID, name, TP count, 是否有术语表/业务规则}

### API docs (current state):
{list of API files with their 基本信息 path + 是否有测试断言}

### Page docs (current state):
{list of page files with their 路由路径 + 是否有用户操作流}

## 🔒 Enhancement rules (增强，不替代):

1. **需求名称和描述**：如果 PRD 中有官方名称 → 覆盖代码反推的名称
   - 代码反推: "REQ-SB-001 — Agent 构建与部署" → PRD 官方: "REQ-SB-001 — 智能体创建与发布"
   - 保留 REQ-ID 不变，只更新名称和描述

2. **领域术语表**：从 PRD 提取所有明确定义的术语
   - PRD 中有专门的"术语表"/"名词解释" → 直接使用
   - PRD 中使用的业务名词（加粗/引号/首次出现有解释） → 提取为术语
   - 术语表列增加 `PRD 来源` 列：标注 PRD 中的原文出处

3. **业务规则与约束**：从 PRD 的 AC/规则描述中提取
   - "当 X 时，系统应该 Y" → 业务规则
   - "不允许 Z" / "必须满足 W" → 约束条件
   - 标注来源：`PRD:{section_title}`

4. **测试点增强**：用 PRD 的验收标准补充 TP 的预期结果
   - 如果 PRD AC 比代码推导的 TP 更详细 → 更新 TP 预期结果列
   - 如果 PRD 有测试场景但 KB 中没有对应 TP → 新增 TP

5. **页面文档增强**：用 PRD 的页面描述补充
   - 页面官方名称（PRD 中的叫法 vs 代码中的组件名）
   - 用户操作流的业务场景描述（PRD 比代码推断更准确）
   - 页面间的导航关系（PRD 中的用户旅程）

6. **API 文档增强**：
   - 补充"业务场景"描述（这个 API 在哪个用户操作中被触发）
   - 补充字段的业务含义（PRD 中对字段的解释比代码注释更权威）
   - 验收标准转为测试断言的预期值补充

## 🔒 不做什么（边界）:
- ❌ 不删除 KB 中已有的技术细节（错误码、DB 操作、代码来源标注）
- ❌ 不修改从代码确认的 HTTP 状态码（PRD 可能写错）
- ❌ 不新建 API 文档或 Page 文档（只增强已有的）
- ❌ 不修改 graph.json 或 test JSON 文件（这些由其他 skill 负责）

## 🔒 PRD-代码冲突检测（强制 — 不静默覆盖）:

PRD 的验收标准/接口规格可能与代码实际行为矛盾。增强时必须检测并标记冲突：

**检测范围：**
1. **HTTP 状态码冲突** — PRD 写"不存在返回 404"但代码实际抛 422（FastAPI 路径参数校验）
2. **字段必填性冲突** — PRD 标"必填"但代码有默认值（实际非必填）
3. **枚举值冲突** — PRD 列出的状态枚举和代码 Enum 定义不一致
4. **权限模型冲突** — PRD 写"所有用户可访问"但代码有 owner 检查

**处理规则：**
- 技术行为（状态码、字段约束）→ **以代码为准**，PRD 内容标记 `[CONFLICT]` 存疑
- 业务语义（名称、流程描述）→ **以 PRD 为准**，代码可能是旧命名未更新
- 冲突不阻塞增强流程，但必须在输出中标记

**标记格式（写入增强后的文档中）：**
```markdown
| 422 | agent_id 非 UUID 格式 | `[CONFLICT: PRD 标注 404，代码确认 422]` Pydantic Path 校验 |
```

**Agent 输出额外段落 — 冲突清单：**
```
===CONFLICTS===
| 文件 | 冲突点 | PRD 说法 | 代码实际 | 裁定 |
|------|--------|---------|---------|------|
| apis/POST-build.md | 错误码 | 404 (资源不存在) | 422 (Pydantic 校验) | 以代码为准 |
| requirements/REQ-SB-001.md | 状态枚举 | draft/active/done | draft/building/running/stopped | 以代码为准 |
===END_CONFLICTS===
```

**🔒 冲突输出到报告（Step 6）：**
- 在 enhancement diff report 中增加 `冲突项: N 处 PRD-代码不一致`
- 每条冲突附带：文件路径 + 冲突描述 + 裁定依据
- 目的：通知产品经理更新 PRD，或让开发确认代码是否需要改

## Output format:

For each enhanced file, output:
===FILE: {relative_path}===
{complete updated content of the file}
===END===

Only output files that were actually enhanced (had content to add from PRD).
If a file has no matching PRD content, skip it.
```

## Step 5: Merge results

For each enhanced file:
1. Parse agent output (split by `===FILE:`)
2. Compare with existing file content
3. Apply enhancements:
   - **Without --force:** only fill "待补充" sections or append new sections (术语表、业务规则)
   - **With --force:** overwrite PRD-sourced sections (名称、描述、术语、规则、AC), preserve code-sourced sections (错误码、DB 操作、代码来源)
4. **🔒 Preserve code-derived content:** sections with `<!-- code-traced -->` or code line references (如 `router.py:45`) never overwritten by PRD content
5. **🔒 人工修正保护：** `<!-- manual -->` 标记的段落永远不覆盖

## Step 6: Generate enhancement diff report

Output a summary of what was enhanced:

```
GSD > KB-FILL-FROM-PRD Complete
════════════════════════════════════════════════════════════
Module:       {module}
PRD source:   {prd_path}
────────────────────────────────────────────────────────────
Requirements enhanced:
  Names updated:        {N} (PRD official names replaced code-guessed names)
  术语表 entries added: {N}
  业务规则 added:       {N}
  TP enriched:          {N} (AC → 预期结果)
  TP new:               {N} (from PRD scenarios not in code)

Pages enhanced:
  Official names set:   {N}
  用户操作流 enriched:  {N}

APIs enhanced:
  Business context:     {N} (场景描述 added)
  Field meanings:       {N} (字段业务含义 from PRD)

Skipped (no PRD match): {N} files
════════════════════════════════════════════════════════════
```

## Step 7: Update MODULE.md (🔒 全量同步刷新)

After enhancement, MODULE.md 必须反映 PRD 增强后的最新状态：

**7a. 业务概述（PRD 覆盖）：**
- 用 PRD 中的模块/功能描述替换"待补充"或代码反推的泛化描述
- 如果 PRD 有产品定位、目标用户、核心价值说明 → 写入业务概述
- 3-5 句话，回答"这个模块为用户解决什么问题"

**7b. 需求追溯表（全量刷新）：**
- 扫描所有 REQ 文件，用 PRD 增强后的名称重建需求追溯表
- 确保 REQ 名称列和 REQ 文件中的 `## 需求概述` 名称一致

**7c. 领域术语表汇总（MODULE 级别）：**
- 从所有 REQ 的 `### 领域术语` 段合并去重
- 写入 `## 领域术语（模块级汇总）`：
  ```markdown
  ## 领域术语（模块级汇总）

  | 术语 | 业务含义 | 来源 |
  |------|---------|------|
  | {术语} | {PRD 中的定义} | PRD / REQ-SB-001 |
  ```

**7d. 核心业务规则汇总：**
- 从所有 REQ 的 `### 业务规则与约束` 段提取，按优先级排序取前 10 条
- 写入 `## 核心业务规则`

**7e. 模块资产清单（重新计数）：**
- 计数所有目录下实际文件数，更新表格

**7f. PRD 来源追溯：**
- 追加或更新 `## PRD 来源` 段：
  ```markdown
  ## PRD 来源
  | 文档 | 路径 | 最后同步日期 |
  |------|------|-------------|
  | {prd_filename} | {prd_path} | {today} |
  ```

**7g. 最后同步时间戳：**
```markdown
> 版本：v1.0 | 创建时间：{existing} | 负责人：{existing} | 最后同步：{today}
```

</process>

<notes>
- This skill ENHANCES existing KB docs, it does not generate from scratch
- Run kb-fill-requirements + kb-fill-apis + kb-fill-pages FIRST to have a baseline
- Then run this skill to overlay authoritative PRD content on top
- Safe to re-run: tracks PRD source + sync date, only updates changed content
- PRD content takes priority over code-inferred content for: names, descriptions, terminology, AC
- Code content takes priority for: error codes, DB operations, HTTP methods, paths
- Use --force to refresh all PRD-sourced fields even if already filled
</notes>
