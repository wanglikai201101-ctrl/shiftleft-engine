---
name: gsd-kb-gen-tests-ui
description: "Generate MCP-Ready UI test cases: orchestrator + template-driven generation"
argument-hint: "--module <name> --output <path> [--req <REQ-ID>] [--page <PageName>] [--force]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Grep
  - Glob
  - Agent
---

<output-spec>
🔒 **MANDATORY:** 本技能生成的所有输出必须符合 `skills/TEST-OUTPUT-SPEC.md` 规范。
在生成每个文件前，加载并遵循该规范的全部约束。违反规范 = 输出无效。

**关键强制点（从 TEST-OUTPUT-SPEC.md 摘要）：**
- type 字段：纯浏览器操作 = `"ui"`
- 顶层必须有 `auth_system` 和 `auth_role` 字段（即使 UI 测试不发 API 请求）
- url 必须是完整 URL（`http://` 开头），禁止 `{{FRONTEND_BASE_URL}}` 等占位符
- 每个 step 必须有 description（非空）+ target（非空）
- target 文本必须使用 DEFAULT_LOCALE 对应语言（data-testid 除外）
- expected_results 至少 1 条，写入操作必须验证业务闭环
- 禁止硬编码 ID — 动态参数用 `{{VAR}}` + prerequisites 声明

**自检时必须执行 TEST-OUTPUT-SPEC.md 第 9 节全部检查项。**
</output-spec>

<critical-rules>
🚫 HALT — 逐条阅读以下规则，违反任何一条 = 输出无效，必须删除重做

1. 🚫 NEVER hardcode `/login` — 必须从 ENV-CONFIG 或 page docs 解析登录路由
2. 🚫 NEVER skip ENV-CONFIG loading — 没有 ENV-CONFIG 就不能生成任何测试
3. 🚫 NEVER generate < 2 steps in auth_system mode（1 nav + 1 business minimum）or < 4 steps in inline login mode（2 login + 1 nav + 1 business minimum）
4. 🚫 NEVER use hardcoded IDs in URL — 动态参数必须用 `{{VARIABLE}}` + prerequisites
5. 🚫 NEVER skip 用户操作流 — 它是 step 生成的首要数据源
6. 🚫 NEVER spawn agent without inlining template + sub-skill content
7. 🚫 NEVER output file without self-validation pass
8. 🚫 NEVER omit auth_system/auth_role — 顶层必须有这两个字段用于测试追踪
9. 🚫 NEVER mix target languages — target 文本必须统一使用 DEFAULT_LOCALE 语言
10. 🚫 NEVER end a run with zero test cases — 全量运行结束若 tests/ui/ 下 0 个 UI-*.json（或枚举了场景但填充 0 产出）→ FAIL LOUDLY（零产出门禁，Step 6c）
11. 🚫 NEVER hard-gate an LLM/external-API step without an escape — step 的关联接口 为 LLM-backed / 外部 API（如 enhance-description → ChatOpenAI → DeepSeek）时，必须满足其一：(a) soft/optional 步骤（API 按文档降级时优雅跳过但仍断言降级 UI，如 Retry 按钮/内联错误）；(b) 步骤级 bounded retries / bounded wait precondition；(c) external-dependent 分类（flaky/低优先级桶，非硬门禁）。禁止把下游 "Connection error."/"AI 增强失败"/上游超时当作应用回归（BUSINESS_BUG）硬性 fail_if_not_appear
12. 🚫 NEVER treat a camelCase-only `dataTestId`/`testId` prop as a DOM locator — 组件可能把 prop 解构吞掉（根节点无 data-testid，如 `DialogContent dataTestId="..."` 仅用于给关闭按钮生成 `...-close`）；使用前必须验证其**透传**到原生元素（如 `data-testid={dataTestId}` / `{...props}`）才可作 element_id / target（见 GEN-SINGLE-UI-TEST「testid 可达性」小节）

每个 Step 完成后必须输出 checkpoint 标记（见下方格式），否则不得进入下一步。
</critical-rules>

<objective>
Orchestrate UI test case generation by:
1. Mapping page docs (元素清单 + 用户操作流) to the executor's ui dispatch format
2. Resolving prerequisites for dynamic data
3. Spawning agents that fill UI-TEST-TEMPLATE.json

Output: MCP-Ready JSON files for the executor's ui dispatch tool.
</objective>

<process>

## Step 1: Parse arguments + load ENV-CONFIG

Extract from `$ARGUMENTS`:
- `--module <name>` (required)
- `--output <path>` (optional, default: `.planning/ontology`)
- `--req <REQ-ID>` (optional): specific requirement only
- `--page <PageName>` (optional): only the named page doc (page doc basename without `.md`)
- `--force` (optional): overwrite existing files

Load `$OUTPUT/$MODULE/tests/ENV-CONFIG.json`:
- `FRONTEND_BASE_URL` — from `environment.frontend_url`
- `FRONTEND_LOGIN_PATH` — from `environment.frontend_login_path`
- `AUTH_USERNAME` — from `auth.username`
- `AUTH_PASSWORD` — from `auth.password`
- `AUTH_SYSTEM` — from `auth.system` (optional — if present, use auth_system mode)
- `AUTH_ROLE` — from `auth.role` (optional, default: "admin")
- `DEFAULT_LOCALE` — from `i18n.default_locale` (no silent "zh" fallback — see locale resolution below)
- `LOCALES_DIR` — from `i18n.locales_dir` (relative to frontend repo root; e.g. "app/i18n/locales")

**🔒 默认语言解析（DEFAULT_LOCALE）— 禁止静默 zh 兜底：**

Resolution priority:
1. ENV-CONFIG `i18n.default_locale` 字段（如果存在）→ 直接使用
2. **自动检测**（如果字段不存在）：grep 前端源码中的 `defaultLocale`/`fallbackLng`/`default_language`
3. **已移除「兜底 zh」** — `i18n.default_locale` 缺失或 locale 文件/key 无法解析时，**不得**默认中文（会产生错误语言的断言）。处理方式：
   - 优先使用 `data-testid` 断言（data-testid **仅当以原生属性出现在 DOM** 时才 locale 无关且可用；camelCase `dataTestId`/`testId` prop 需先验证可达，见 GEN-SINGLE-UI-TEST「testid 可达性」小节）
   - 无法避免可见文本断言时 → 在 `_meta.validation_warnings` 追加 `"locale_unknown"`（warning 暴露契约缺口，不是静默错误语言值）

`DEFAULT_LOCALE` 传递给 agent context，影响 target 字段的文本语言选择。

**🔒 消息断言分类（MANDATORY — 验证/错误消息 vs 真实文本验证）：**

**A. 表单验证/错误消息断言 → `element_visible` + 稳定 locator（不做 locale 解析）：**
- 当 expected_result 的目标是表单验证/错误消息（必填校验、内联校验消息 — 由错误态如 `{nameError && ...}`/`{descError && ...}` 渲染，或 `t('...Required')`/`t('...Error')` i18n key）→ 生成 `{"check":"element_visible","element_id":"{prefix}-error-{field}"}`；`{prefix}` = 组件 data-testid 前缀（如 `sandbox-agent-template-dialog`），`{field}` = 输入框语义字段（如 `desc`/`name`）
- 这些 testid 由 enforce-locators 机制自动注入（对齐命名 `{prefix}-error-{field}`）——enforce-locators **保证注入 `{prefix}-error-{field}`**，但**不保证裸 `{prefix}` 根 token**；`{prefix}` 本身若要作 element_id 必须满足原生属性/可达性要求（见 GEN-SINGLE-UI-TEST「testid 可达性」小节）
- **禁止**用 locale 文件解析其文案；**禁止**为验证消息生成携带 locale 字符串的 `text_exists`

**B. 真实文本验证断言（如验证持久化 VALUE 的显示文本）→ locale 探测（仅此类）：**
- 当 value 是真实业务文本（非验证消息）且对应已知 i18n key → 读取 `LOCALES_DIR/<DEFAULT_LOCALE>/<ns>.json`（LOCALES_DIR 相对前端仓库根目录；如 `app/i18n/locales/en/agent.json` → `create.descRequired` = "Agent description is required"）解析**运行时字符串**并内联到 `expected_results[].value`（静态 JSON 携带正确 locale 字符串，runner 无需改动）
- 当 value 是静态页面标签（非 i18n key）→ 保持现有行为

**C. locale 未知处理（禁止静默 zh）：**
- `DEFAULT_LOCALE` 缺失或 locale 文件/key 解析失败时，**不得**默认中文
- 验证消息断言不受影响（它们用 `{prefix}-error-{field}` locator，不依赖 locale）
- 真实文本断言解析失败 → 优先 `data-testid` 断言；无法避免可见文本断言时 → `_meta.validation_warnings: ["locale_unknown"]`（warning 暴露契约缺口，不是静默错误语言值）

**🔒 动态/预填文本禁止 text 断言（MANDATORY）：**
- 预填/回填字段内容（编辑弹窗回显、URL 参数预填、prerequisite 注入的值）、placeholder 占位符文本、任何 data-dependent 动态值 → **禁止** `text_exists` 断言其具体文本
- 正确 = `element_visible` + 字段 data-testid 的 `element_id`（内容本身是数据依赖的，断言存在性而非具体值）
- `text_exists` 仅限静态文本：i18n-key 解析的运行时字符串 / 静态页面标签
- 示例错误：对编辑弹窗预填描述断言 `text_exists "Describe how to modify ..."`（回填内容随数据变化，正确做法 = `{"check":"element_visible","element_id":"{prefix}-desc"}`）

**🔒 登录路由解析优先级（必须按顺序尝试，禁止跳过）：**
1. ENV-CONFIG.json `environment.frontend_login_path` 字段（如果存在）
2. KB page docs 中名为 `login.md` 的文档的 `## 基本信息` → `路由路径` 字段
3. 代码中的实际路由定义（grep frontend 源码中的 login route）
4. 兜底 `/login`（必须标注 `[推断-未验证]`）

```
✅ CHECKPOINT-1: ENV-CONFIG loaded
   MODULE: {name}
   BASE_URL: {url}
   LOGIN_PATH: {path} (来源: {1|2|3|4})
   AUTH_MODE: {auth_system|inline_login}
   AUTH_SYSTEM: {system_name|N/A}
   AUTH_ROLE: {role|N/A}
   AUTH: {username} / ***
   DEFAULT_LOCALE: {locale} (来源: {env_config|auto_detect|locale_unknown})
   LOCALES_DIR: {locales_dir|N/A}
   如果 ENV-CONFIG.json 不存在 → STOP，报错退出
```

## Step 2: Collect source documents

### 2a: Load page docs
`--page` 给定 → 只读 `$OUTPUT/$MODULE/pages/<PageName>.md` 该页文档;未给定 → 读全部 `$OUTPUT/$MODULE/pages/*.md`。提取:
1. 页面元素清单 (data-testid, 元素类型, 功能, 触发接口)
2. 用户操作流 (操作, 触发方式, 系统反应, 异常处理, 关联接口) — **PRIMARY SOURCE**
3. 接口调用顺序 (page lifecycle)
4. 数据流转 (data sources and display)
5. 基本信息 → 路由路径 (must start with `/`)
6. 表单验证模式 (验证模式分类 + 源码证据) — **用于 expected_results 生成**

**UI test step 数据源优先级：**
1. **首选:** 用户操作流 table → each row = one test step
2. **次选:** 页面元素清单 + 接口调用顺序 → derive steps
3. **兜底:** TP 操作步骤 column → derive steps

**表单验证模式处理：**
- 如果页面文档有 `## 表单验证模式` section → 提取验证模式表传递给 agent
- 如果页面文档没有该 section 但页面有表单 → 从前端源码直接提取验证模式
- 该信息决定 expected_results 中验证失败断言的正确写法（disabled vs error text）

### 2b: Load requirements
Read `$OUTPUT/$MODULE/requirements/*.md`:
- Extract TPs with 验证方式 containing "UI"
- Map to pages via 关联前端页面 field
- `--page` 给定 → 只保留 关联前端页面 指向 `<PageName>` 的 TP(叠加 `--req` 过滤);未给定 → 现状

### 2c: Route resolution (per page)
- Read `路由路径` from page 基本信息
- Must start with `/` (prepend if missing)
- Must NOT contain domain (strip if present)
- Preserve ALL query params (?id=, ?mode=, ?tab=)
- Dynamic params → `{{VARIABLE}}` from prerequisites

**🔒 ID 语义验证:**
- Trace what ID the page URL expects (from 接口调用顺序)
- Verify list_endpoint returns correct entity type
- If mismatch → add transform or correct extract_field

### 2d: Transient state analysis
For UI elements with conditional disabled state:
- Loading/async → test AFTER load completes (瞬态，不测 disabled)
- Backend state dependent → two test cases (met/unmet); **unmet 用例**：条件不成立时元素本就不渲染 → expected_results 输出 `{"check":"element_hidden","element_id":"...","expect_absent":true}`（`expect_absent` 仅合法于 `check:"element_hidden"`、仅用于"永不渲染"语义、值限布尔 `true` / 字符串 `"true"`），**禁止**只写 prose 版 `element_hidden`（引擎不读 description）
- Permission-based → single disabled assertion (永久)

```
✅ CHECKPOINT-2: Source documents collected
   Pages found: {N} (list names)
   Pages with 用户操作流: {N}
   UI TPs found: {N} (list IDs)
   Pages without route: {list} → STOP if any critical page missing route
```

## Step 3: Load template and sub-skill

Read the template and sub-skill files into variables for agent injection:

```bash
SKILL_DIR=""
for candidate in \
  "$HOME/.claude/skills/gsd-kb-gen-tests-ui" \
  "$(pwd)/skills/gsd-kb-gen-tests-ui"; do
  if [ -f "$candidate/templates/UI-TEST-TEMPLATE.json" ]; then
    SKILL_DIR="$candidate"
    break
  fi
done
```

Read `$SKILL_DIR/templates/UI-TEST-TEMPLATE.json` → `$TEMPLATE`
Read `$SKILL_DIR/sub-skills/GEN-SINGLE-UI-TEST.md` → `$SUB_SKILL`

```
✅ CHECKPOINT-3: Template + sub-skill loaded
   SKILL_DIR: {path}
   TEMPLATE: {first 50 chars}...
   SUB_SKILL: {first 50 chars}...
   如果任一为空 → STOP，报错退出
```

## Step 4: Enumerate test scenarios (deterministic manifest)

**🔒 两阶段生成：先枚举清单，再逐个填充。AI 不能跳过清单中的任何场景。**

### Step 4A — Module-level flow enumeration (run ONCE per module, before per-page enumerators)

**🔒 `--page` 模式：跳过模块级枚举** — 直接读取共享 flow-index 文件 `$OUTPUT/$MODULE/tests/_scenarios/.gen/_flow-index.json`(由 workflow 的 flow-index 小步预先生成),取其中本页的 flows / role 注入下方枚举器与填充器上下文;`full_flow` 填充器按该 flow 的 `pages` 数组读取下游页文档构建 FLOW_CONTEXT;未给定 `--page` → 按现状走下方模块级枚举。

Spawn ONE **Flow Enumerator** agent that builds the module's cross-page flow map from ALL page docs. This gives every per-page enumerator a shared, deduplicated view of which pages participate in which flows — so a full_flow scenario is produced exactly once per flow (owned by the flow's entry page), never repeated by each intermediate page.

```
你是一个模块级流程枚举器。读取该模块的全部页面文档，构建跨页流程映射。

## 输入
- MODULE_PAGE_DOCS: {全部页面文档的 用户操作流"跳转目标"列 + 基本信息"路由路径"}
- PAGE_ROUTE_INDEX: {page doc 名 → 路由路径 对照表}

## 任务
1. 对每个页面，从 用户操作流 表的"跳转目标"列收集跳转边（源页 → 目标路由）
2. 把目标路由解析为具体页面（按 PAGE_ROUTE_INDEX 匹配"路由路径"）
3. 把跳转边连成流程链（连通分量）
4. 输出 FLOWS 数组

## 约束
- 只把结构化的"跳转目标"列当一等数据源；自由文本（如 系统反应 列里的"跳管理页"）仅作线索，不作边来源
- 目标路由解析不到具体页面 → 该边保留路由但 pages 不含未知页（target 标 unknown_target）
- 无跳转边的孤立页面 → 不产出 flow
- 动态路由统一用 {{VAR}} 形式（如 /orders/{order_id} → /orders/{{order_id}}）

## 输出 schema
{"flows": [{"flow_id": "FLOW-001", "entry_page": "{page doc name}", "pages": ["A", "B", "C"], "routes": ["/a", "/b", "/c"]}]}
```

`FLOWS` 是后续每个 per-page 枚举器的共享上下文输入；同时写一份 `FLOW-INDEX` 汇总（page → 参与 flows 列表 + 是否入口页）。

**🔒 中间产物目录（所有枚举/清单中间产物统一写到此目录，禁止写入 `tests/ui/` 等扫描目录）：**
- 目录：`$OUTPUT/$MODULE/tests/_scenarios/.gen/`（`_scenarios` 非 api/e2e/ui 扫描子目录，test-inventory 不会把它当测试用例）
- `_flow-index.json` — 模块级 FLOW-INDEX 汇总（本步骤产物）
- `_manifest-{Page}.json` — 每页场景清单（Step 4B 产物）
- `_tp-map.json` — TP↔场景映射（Step 4B 产物）
- 中间产物保留供溯源/重跑，**不删除**；但**绝不允许**写到 `tests/ui/`、`tests/api/`、`tests/e2e/` 下。

### Step 4B — Per-page scenario enumeration (Scenario Enumerator agent)

For each page with UI TPs, spawn a **Scenario Enumerator** agent that ONLY outputs a structured scenario manifest (not test cases). This agent analyzes the KB docs and deterministically lists ALL required test scenarios. **Pass `FLOWS` + `FLOW-INDEX` (本页参与的 flows、是否入口页) as context so the enumerator can emit `full_flow` scenarios.**


```
你是一个 UI 测试场景枚举器。分析以下 KB 文档，列出该页面所有必须生成的测试场景。

## 🚫 硬性约束
- 每种适用的测试类型必须至少有 1 个场景
- 输出是 JSON 数组，不是测试用例本身
- 不要生成测试步骤或断言，只列出场景元数据

## 场景类型检查表（逐条扫描，有证据就必须产生对应场景）：

| # | 类型 | 触发证据（KB 文档中的信号） | 最少数量 |
|---|------|---------------------------|---------|
| 1 | happy_path | 用户操作流 中任何 normal row | 1 per distinct flow |
| 2 | error_path | 用户操作流 中 异常处理 列非空 | 1 per error type |
| 3 | network_error | 用户操作流 中提到 网络/离线/超时/loading | 1 if any signal |
| 4 | conditional_state | 页面元素清单 中有 disabled/hidden 条件 | 2 (met + unmet) |
| 5 | decision_branch | 页面有 Accept/Reject/Discard/Cancel 等决策按钮 | 1 per branch |
| 6 | repeated_action | 操作可重复触发（重试/再次生成/重新提交） | 1 if any signal |
| 7 | dialog_branch | 页面有 弹窗/Modal 且有 Confirm+Cancel 出口 | 1 per exit path |
| 8 | write_verify | 有 Create/Update/Delete 写入操作 | 1 per write type (列表验证+详情验证) |
| 9 | full_flow | FLOW-INDEX 中本页是某流程参与者（入口/中间/退出） | 每参与 flow 1 个（归属入口页） |

## 枚举规则：
- 逐行扫描 用户操作流 table，每行对应至少 1 个场景
- 如果某行的 异常处理 列非空 → 额外产生 error_path 场景
- 如果页面有弹窗（从 页面元素清单 判断）→ 每个出口 1 个 dialog_branch
- 如果有写入操作 → 必须产生 write_verify（存储展示闭环）
- 如果页面有决策按钮 → 每个决策选项 1 个 decision_branch
- 如果 FLOW-INDEX 中本页是某流程的**入口页** → 每个参与 flow 产生 1 个 `full_flow` 场景（完整跨页流程用例，覆盖 entry→…→exit）
- 如果本页是流程的中间/退出页但**非入口** → 该 flow 的 full_flow 由入口页 manifest 负责，本页不重复产出（跨 manifest 去重）
- 无流程数据（FLOW-INDEX 为空）→ 不产出 full_flow（数据驱动，不硬造）

---
## Context:
PAGE_DOC: {full page doc content}
PAGE_NAME: {page display name}
TP_LIST: {all TPs for this page}
ELEMENTS: {页面元素清单 relevant rows}
USER_FLOWS: {用户操作流 ALL rows}
FLOWS: {模块级流程映射 — 本页参与的 flows（flow_id/入口页/routes）; 无则 "无"}
FLOW_INDEX: {本页角色: entry|intermediate|exit|none + 参与的 flow_id 列表; 无则 "none"}
```

**中间产物写盘：** `_manifest-{PageName}.json` 写 `$OUTPUT/$MODULE/tests/_scenarios/.gen/`；TP↔场景映射写 `_tp-map.json`（同目录）。

**enum 归一化说明：** `type` 只允许下列 9 个枚举值。若枚举器输出非枚举值（LLM 漂移），必须先按下方 CHECKPOINT-4a 的归一化表映射到枚举内类型再写盘；**不得把非枚举值写进 manifest**。禁止裸 REJECT（会触发重枚举循环）。

**Scenario Manifest Schema (强制):**
```json
{
  "type": "object",
  "properties": {
    "page": { "type": "string" },
    "total_scenarios": { "type": "integer", "minimum": 1 },
    "scenarios": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "type": { "type": "string", "enum": ["happy_path", "error_path", "network_error", "conditional_state", "decision_branch", "repeated_action", "dialog_branch", "write_verify", "full_flow"] },
          "priority": { "type": "string", "enum": ["P0", "P1", "P2"] },
          "description": { "type": "string" },
          "source_row": { "type": "string" },
          "tp_id": { "type": "string" }
        },
        "required": ["id", "type", "priority", "description"]
      }
    },
    "evidence": {
      "type": "object",
      "properties": {
        "user_flow_rows": { "type": "integer" },
        "error_handlers": { "type": "integer" },
        "dialogs": { "type": "integer" },
        "write_operations": { "type": "integer" },
        "decision_buttons": { "type": "integer" },
        "nav_targets": { "type": "integer", "description": "用户操作流中跳转目标列非空的行数" },
        "flow_participant": { "type": "boolean", "description": "FLOW-INDEX 中本页是否流程参与者" }
      }
    }
  },
  "required": ["page", "total_scenarios", "scenarios", "evidence"]
}
```

**🔒 枚举归一化（CHECKPOINT-4a 验证第一步，先归一化再门控）：**

manifest 的 `scenario.type` 必须属于 9 个枚举值（happy_path / error_path / network_error / conditional_state / decision_branch / repeated_action / dialog_branch / write_verify / full_flow）。若枚举器输出非枚举值，**显式映射**而非裸 REJECT：

| 非枚举取值（枚举器输出） | 归一化到（枚举内） | 依据 |
|------------------------|-------------------|------|
| `empty_state` / `loading_state` | `conditional_state` | 空态/加载态 = 条件状态分支 |
| `boundary_value` / `edge_case` | `error_path` | 边界/极端输入 → 异常路径 |
| `error_handler` | `error_path` | 异常处理器 → 异常路径 |
| `permission_role` | `conditional_state`（有权限条件上下文）或 `decision_branch`（有权限决策分支） | 权限角色 → 条件/决策分支 |
| `read_verify` | `write_verify`（有配套写入操作时）或 `happy_path`（纯读取无写入时） | 读校验是写入闭环一部分，或主路径 |
| 其它未列出的非枚举值 | 按语义就近映射到 9 个枚举值之一 | 就近原则 |

**规则：** 先执行归一化映射 → 再跑下方最低数量门控。归一化后若场景仍无法归类到任何枚举值 → 才是 REJECT，重新枚举。

**🔒 最低数量门控（CHECKPOINT-4a 验证，第二步）：**
- `total_scenarios` < `user_flow_rows` → REJECT，重新枚举（操作流每行至少应有一个场景）
- `evidence.dialogs > 0` 但没有 `dialog_branch` 类型场景 → REJECT
- `evidence.write_operations > 0` 但没有 `write_verify` 类型场景 → REJECT
- `evidence.decision_buttons > 0` 但没有 `decision_branch` 类型场景 → REJECT
- `evidence.flow_participant` 为 true（或 `evidence.nav_targets > 0`）但 manifest 无 `full_flow` 场景 → REJECT，重新枚举（数据驱动：仅当流程数据存在时硬门）

```
✅ CHECKPOINT-4a: Scenario manifests generated
   Pages processed: {N}
   Total scenarios enumerated: {N}
   Per-page breakdown:
     {page_name}: {N} scenarios (happy:{h}, error:{e}, decision:{d}, dialog:{dl}, verify:{v}, flow:{fl}, other:{o})
   Evidence: {user_flow_rows} flow rows → {total_scenarios} scenarios (expansion ratio: {ratio}x)
   Gate check: ALL passed / REJECTED {N} (re-enumerated)
```

## Step 4b: Fill test cases from manifest (one agent per scenario)

For each scenario in the manifest, spawn an independent **Test Filler** agent that fills the template:

**🔒 幂等/可续跑（重复运行不重复生成）：**
- 填充前先扫描 `$OUTPUT/$MODULE/tests/ui/` 下已有 `UI-*.json`，提取每个文件的 `_meta.scenario_id`（Step 6 写盘时强制打上）。
- 已存在对应 `UI-*.json` 的场景 ID → **跳过**，不重复 spawn filler。
- 只填充缺失的场景 → 支持中断后续跑、重复运行不产生重复用例、也不覆盖已有产物。
- 幂等键 = `_meta.scenario_id`（对应 manifest 场景 id）；无此字段的旧文件不参与跳过判断。

**🔒 批量上限（Batch cap）：**
- 单批最多 spawn `MAX_PARALLEL_FILLERS`（建议 **8**）个 Filler agent 并行（场景间彼此独立，见下"并行执行"）。
- 场景总数超过上限 → 分多批顺序执行；每批完成后校验该批产出（合法 JSON 数）再进下一批。
- 每批进度记录到 CHECKPOINT-4b 汇总，供续跑判断哪些场景已填、哪些缺失。

```
你是一个 UI 测试用例填充器。根据以下场景描述，填充 JSON 模板产出一个完整的测试用例。

## 🚫 硬性约束
- steps 数组最少 4 条（2 login + 1 nav + 1+ business）
- URL 中不得出现硬编码 ID
- 动态参数必须声明 prerequisites
- 输出必须是合法 JSON
- 严格按场景描述生成，不要自行增减场景范围
- expected_results 中的表单验证断言必须基于页面文档的 `## 表单验证模式` section（禁止假设验证模式）
- expected_results 中 text 类 check（`text_exists` / `url_contains`）**必填非空 `value`** — runner 取值链 `value`>`keyword`>`text`>`selector`>`content`（content 兼容但非规范）；空值 = 空断言，运行时显式拒绝。**element_* check（`element_visible`/`element_hidden`/`element_clickable`）优先按 `element_id`（data-testid）定位** — 携带 `element_id` 时可省略 `value`（runner 空断言拦截豁免）；无 `element_id` 时 `value` 必填且只能放人眼可见文本
- **element_* 断言契约（MANDATORY）**：`element_visible`/`element_hidden`/`element_clickable`/`element_disabled`/`element_enabled` 的 `element_id` = 被测元素 data-testid（字面）或动态家族包裹前缀 `[data-testid^='stem-']`（唯一命中时）；`element_disabled`/`element_enabled` 仅字面；`value` 只放人类可读可见文本（按钮标签等），无文本目标则省略 value；**禁止**把 data-testid、裸 testid token、或 `[data-testid='...']` 选择器字符串写进 `value`
- **element_* 类型选择（MANDATORY）**：`element_visible` = 纯可见/错误消息出现（不校验 pointer-events/disabled）；`element_clickable` = 可点击可交互（pointer-events 可用 + 未被禁用）；`element_disabled`/`element_enabled` = 属性状态。**不要用 `element_visible` 断言"可点击"**（disabled 按钮仍"可见"，会静默假阳性）；**不要对被自己打开的弹窗遮挡的页面底层按钮断言 `element_visible`**（会 covered 失败）
- **ROUTE-CONSISTENCY（MANDATORY — 断言必须属于测试 url 的页面）**：所有 `expected_results` 的 `element_id` 必须是测试 `url` 导航到的页面/路由上真实存在的 data-testid（对照该页 page-doc 元素清单 / 变更组件源码）。来自**其他路由**的 testid = WRONG-ROUTE 断言，运行时必挂 `'Element not found'`（例如：在编辑页 `/dashboard/agent/detail` 的测试中断言市场页工具栏按钮 `pm-web-agent-btn-create`）。若想要的 testid 在别的页面 → 要么把 `url` 改成拥有该 testid 的页面，要么删除该断言。**禁止**在某页面的测试中断言另一个页面的页面级按钮。
- **终态 END-STATE 断言规则（MANDATORY）**：最终 `expected_results` = 对最后一步完成后的终态页面做断言；若某步骤打开弹窗/对话框，弹窗覆盖的页面底层元素（如打开弹窗的 launcher 按钮）绝不能放进 expected_results——launcher 可见性用**步骤级 `expect` 动作**，放在点击打开弹窗的步骤之前；弹窗自身内容才是合法的终态断言目标。
- **条件性不存在断言（MANDATORY）**：当元素**本就不渲染**（源码条件渲染，如 `{!editAgentId && ...}` → 编辑模式不渲染仅创建按钮）→ 在 `{"check":"element_hidden","element_id":"{id}"}` 上输出 `"expect_absent": true`（值仅限布尔 `true` 或字符串 `"true"`），并把源码条件表达式记录到 `_meta.code_evidence[element_id]`；`description` 只放人读文本。**NEVER** 用于"先出现后消失"/"动作后关闭"语义（会反转引擎"从不出现=failed"守卫 → 假阳性）——**语义澄清：此处的 `element_hidden` ≠ 「元素不可见」，= 「本就不该渲染/不应存在」；`expect_absent` 只在 `element_hidden` 分支读取（执行引擎契约），配在其他 check 上被静默忽略（幻影字段）**
- **禁止幻影字段（MANDATORY）**：引擎**不读取** `element_state` / `multi_action`——**禁止**输出这两个字段。disabled 元素用现有 `element_disabled` / `element_enabled` check；disabled 但可见的元素合法断言为 `element_visible`（引擎允许 visible-on-disabled）**或** `element_disabled`，**禁止**对同一元素同时输出两者暗示冲突覆盖
- **一步一动作（MANDATORY）**：每个 `step` = **恰好一个**工具动作（fill/click/press/expect/wait_for）；一个多字段填写行必须展开成 N 个相邻 step entry（`step` 序号可重复，无校验器读数字 step）
- **单一最终态纪律（MANDATORY）**：`expected_results` 在最后一步后对最终页面状态**只评估一次**——**禁止**产出步骤绑定/时序断言（"step3 后 hidden + step4 后 visible"、"先出现后消失"）。时序验证 → 拆独立自洽用例 / 步骤级 `expect`/`wait_for` / 推迟生成；产出前自查最终态自洽（互斥断言 = 拒绝生成）
- **最终态渲染可达性（MANDATORY — FINAL-STATE RENDER REACHABILITY）**：`expected_results` 中 `element_*` 断言（`element_disabled`/`element_enabled`/`element_visible`/`element_hidden`/`element_clickable`）的 `element_id` 所指 testid **必须在测试流程的最终态页面（last step 之后的页面状态）确实渲染 / 在 DOM 中可定位**——源码中存在 ≠ 最终态 DOM 中存在（testid 可达性只是必要条件，非充分条件）。若目标元素位于一个**最终态会关闭的容器**内（如对话框 dialog/panel/modal，流程末尾把它取消/关闭），则**禁止**在 `expected_results` 中断言它——因为最终态评估时它已不在 DOM，`Locator.wait_for` 必然超时失败。正确做法：把该断言**降级为 step 级**——在元素可见的那个 step 上用 `{"step":N,"action":"expect"}` 或 `{"step":N,"action":"wait_for"}` 断言（如 step-level expect element_disabled），或在对话框中它可见时断言，而不是放 end-state `expected_results`。若该元素只在"先出现后消失"的时序中存在，则参考 SINGLE-FINAL-STATE 规则：拆成自洽用例或 step 级断言，禁止放 end-state。可用 `_meta.code_evidence` 记录源码中该 testid 的渲染条件（如 `disabled={...}` 表达式、所在容器 `{open && ...}` 条件），辅助判断最终态是否可达。
- **text_exists 持久锚点契约（MANDATORY）**：`text_exists` 的目标文本必须挂在**最终态必然在场**的持久元素上——静态渲染，或条件渲染但由测试自身确定性地保持在场（如测试自己打开且留在终态的弹窗/面板）。**禁止**对仅存在于瞬态/异步阶段挂载节点的文本生成 `text_exists`：deploy-progress 面板、loading 骨架、spinner、toast、以及其他「先出现后消失」的中间态。判据：若源码中该文本处于异步/条件挂载之下（如 `{isDeploying && …}`、`{loading && …}`、`{isSaving && …}` 类 gate 包裹，或组件由这类状态 gate 挂载），不得作为最终态 `text_exists` 目标。需要验证瞬态阶段 → (a) 断言该瞬态容器的**稳定 testid**（`element_visible` + 持久/前缀定位符），或 (b) 拆成独立自洽用例（其终态 = 可确定到达的瞬态态），或 (c) 依赖已验证的步骤（步骤正确 ⇒ 瞬态必然发生）——不进入断言。无法锚定 → **删除该断言**，并在 `_meta.validation_warnings` 追加 `"transient_text"`（值无源码出处时追加 `"text_no_source"`）。与 `expect_absent` 的既有排除对称——「先出现后消失」语义同样不得作为 `text_exists` 最终态目标。
- **验证/错误消息断言 → `element_visible` + locator（MANDATORY，不做 locale 解析）**：当 expected_result 目标是表单验证/错误消息（由错误态如 `{descError && ...}` 渲染，或 `t('...Required')`/`t('...Error')` key）→ 生成 `{"check":"element_visible","element_id":"{prefix}-error-{field}"}`（`{prefix}` = 组件 data-testid 前缀如 `sandbox-agent-template-dialog`，`{field}` = 输入框语义字段如 `desc`/`name`；这些 testid 由 enforce-locators 自动注入，对齐命名 `{prefix}-error-{field}`；enforce-locators **保证注入 `{prefix}-error-{field}`，但不保证裸 `{prefix}` 根 token**——`{prefix}` 本身作 element_id 必须满足原生属性/可达性要求，见 GEN-SINGLE-UI-TEST「testid 可达性」）。**禁止**用 locale 文件解析其文案；**禁止**为验证消息生成 `text_exists` + locale 字符串
- **真实文本验证断言 → locale 探测（仅此类）**：当 value 是真实业务文本（非验证消息）且对应已知 i18n key → 读取 `LOCALES_DIR/<DEFAULT_LOCALE>/<ns>.json`（如 `app/i18n/locales/en/agent.json` → `create.descRequired` = "Agent description is required"）解析**运行时字符串**并内联到 `expected_results[].value`（静态 JSON 携带正确 locale 字符串，runner 无需改动）。若 value 是静态页面标签（非 i18n key）→ 保持现有行为
- **locale 未知处理（禁止静默 zh）**：`DEFAULT_LOCALE` 缺失或 locale 文件/key 解析失败时，**不得**默认中文。验证消息断言不受影响（用 `{prefix}-error-{field}` locator，不依赖 locale）；真实文本断言解析失败 → 优先 `data-testid` 断言；无法避免可见文本断言时 → 在 `_meta.validation_warnings` 追加 `"locale_unknown"`（warning，不是错误语言的静默值）
- **`SCENARIO_TYPE=full_flow` → 必须产出完整跨页流程用例**：`url` = 流程入口页路由；steps 覆盖 entry→…→exit 的跨页导航与各页业务操作（导航 step 的 target = 源页导航元素）；`_meta` 写 `flow:true`、`flow_id`、`page_routes`。参见 GEN-SINGLE-UI-TEST flow 模式

## 场景信息:
SCENARIO_ID: {scenario.id}
SCENARIO_TYPE: {scenario.type}
SCENARIO_PRIORITY: {scenario.priority}
SCENARIO_DESCRIPTION: {scenario.description}
SOURCE_ROW: {scenario.source_row}
FLOW_ID: {scenario.type === "full_flow" ? scenario.flow_id : null}

## SUB-SKILL 指令:
{$SUB_SKILL full content}

---
## Template (输出必须符合此结构):
{$TEMPLATE full content}

---
## Context:
PAGE_DOC: {full page doc content}
TP: {test point — 操作步骤, 预期结果, 前置条件}
PAGE_NAME: {page display name}
PAGE_URL: {FRONTEND_BASE_URL + resolved route with params}
LOGIN_URL: {FRONTEND_BASE_URL + FRONTEND_LOGIN_PATH}
ENV_CONFIG: {BASE_URL, LOGIN_PATH, USERNAME, PASSWORD}
AUTH_MODE: {auth_system|inline_login}
AUTH_SYSTEM: {system_name from ENV-CONFIG, or empty}
AUTH_ROLE: {role from ENV-CONFIG, default "admin"}
ELEMENTS: {页面元素清单 relevant rows}
USER_FLOWS: {用户操作流 relevant rows}
FORM_VALIDATION_PATTERN: {表单验证模式 section content — or "无表单验证" if page has no forms}
DEFAULT_LOCALE: {resolved locale, e.g. "en" or "zh" — target text must use this language}
LOCALES_DIR: {i18n.locales_dir from ENV-CONFIG, e.g. "app/i18n/locales" — relative to frontend repo root; used to resolve i18n-keyed expected_results values}
FLOW_CONTEXT: {full_flow 专用 — 流程入口页文档 + 下游页面文档 + 各页元素清单 + page_routes; 非 full_flow 场景为 "无"; --page 模式下按 flow-index 该 flow 的 `pages` 数组读取下游页文档构建}
```

**🔒 并行执行：** 同一页面的所有 scenarios 可以 parallel 生成（彼此独立）。

```
✅ CHECKPOINT-4b: Test cases generated (from manifest)
   Total scenarios: {N} (from manifests)
   Skipped (已有 UI-*.json, 幂等): {N}
   Agents spawned this run: {N} (batches: {B}, 每批 ≤ {MAX_PARALLEL_FILLERS})
   Results received: {N}
   Valid JSON: {N} / Failed: {N}
   Per-page breakdown:
     {page_name}: {N} tests (happy: {h}, error: {e}, network: {n}, decision: {d}, verify: {v}, flow: {fl})
   Manifest coverage: {generated}/{total_scenarios} scenarios filled (100% = no gaps)
```

## Step 5: Generate agent-prompts (chat format)

For each REQ with UI TPs, generate an exploratory prompt at `tests/agent-prompts/REQ-{ID}.json`:
- Natural language instructions covering all UI TPs for that requirement
- Includes: login info, page URLs, expected behaviors, edge cases
- Format: `{ "prompt": "...", "metadata": { "req_id": "...", "tp_ids": [...] } }`

```
✅ CHECKPOINT-5: Agent prompts generated
   Prompts written: {N}
   Requirements covered: {list IDs}
```

## Step 6: Write output files + self-validate

Write to `$OUTPUT/$MODULE/tests/ui/`:
- `UI-{REQ}-{TP}_{scenario}.json` — normal test
- `UI-{REQ}-{TP}_ERROR-{slug}.json` — error variant
- `UI-{REQ}-{TP}_NETWORK-{slug}.json` — network error test
- `UI-{REQ}-{TP}_FLOW-{flow_id}.json` — full_flow cross-page flow test (only for `full_flow` scenarios)

**🔒 写入位置（与中间产物隔离）：**
- 最终测试用例**只写** `$OUTPUT/$MODULE/tests/ui/`（扫描目录，test-inventory 会收录）。
- 中间产物（`_manifest-*` / `_flow-index*` / `_tp-map*`）在 `tests/_scenarios/.gen/`，**禁止**写回 `tests/ui/` 等扫描目录。
- 每个测试用例的 `_meta.scenario_id` 必填（= 对应 manifest 场景 id），作为幂等续跑键（Step 4b 跳过判断依赖它）。

Write to `$OUTPUT/$MODULE/tests/agent-prompts/`:
- `REQ-{ID}.json` — exploratory chat prompt

**🔒 Self-validation (per file, MUST pass before write):**
1. ✅ Valid JSON (parseable)
2. ✅ `steps` array length >= 2 (auth_system mode) or >= 4 (inline login mode)
3. ✅ Every step has non-empty `description` and `target`
4. ✅ `expected_results` has >= 1 entry
5. ✅ `url` starts with `http` (fully resolved, no template vars)
6. ✅ No hardcoded UUIDs/numeric IDs in url (must use `{{VAR}}`)
7. ✅ If URL has dynamic params → `prerequisites` is non-empty array
8. ✅ If `auth_system` is set → no login steps in `steps`; if not set → login step URL matches ENV-CONFIG login path (not hardcoded `/login`)

Any file failing validation → log error, do NOT write, report in summary.

```
✅ CHECKPOINT-6: Files written + validated
   Files written: {N}
   Validation passed: {N}
   Validation failed: {N} (details: ...)
```

## Step 6b: Static validation (post-generation sanity check)

**目的：** UI 测试无法 dry-run（需要浏览器环境），但可以执行静态验证捕获结构性错误。

**Process:**

1. **URL 格式验证：**
   - 所有 `url` 字段以 `http` 开头（完全解析后的 URL）
   - 不含硬编码域名占位符（如 `{{FRONTEND_BASE_URL}}`）
   - 动态参数使用 `{{VARIABLE}}` 语法

2. **路由存在性验证：**
   - 对每个测试的目标 URL 路径，验证是否与某个 page doc 的路由匹配
   - 提取 URL 中的 path（去掉 domain 和 query params）
   - 与 `pages/*.md` 中 `基本信息 → 路由路径` 比对
   - 不匹配 → 标记 `"_validation": "warning:route_not_in_kb"`

3. **Target 文本语言验证：**
   - 所有 step 的 `target` 字段必须使用 `DEFAULT_LOCALE` 对应的语言
   - `DEFAULT_LOCALE=zh` → target 应为中文（data-testid 格式除外）
   - `DEFAULT_LOCALE=en` → target 应为英文（data-testid 格式除外）
   - 混合语言 → 标记 `"_validation": "warning:mixed_locale"`

4. **Prerequisites 完整性验证：**
   - URL 含 `{{VAR}}` → 验证 `prerequisites` 中有定义如何获取 `VAR`
   - prerequisites 中引用的 API endpoint → 验证该 API 在 KB docs 中存在
   - 缺失 prerequisite → 标记 `"_validation": "warning:missing_prerequisite"`

5. **流程覆盖验证（warning 级，数据驱动）：**
   - 对本模块流程参与者页面（FLOW-INDEX 中 entry/intermediate/exit），检查产物是否至少 1 个 `_meta.flow:true` 的 full_flow 测试覆盖其参与的 flow（按 `flow_id`）
   - 页面是流程参与者但产物无对应 flow 的 full_flow 测试 → 标记 `"_validation": "warning:missing_flow_test::<page>"`（与 route_not_in_kb 同级 warning，**不 REJECT**）
   - 仅当页面文档有跳转数据（FLOW-INDEX 非空）时检查；无流程数据跳过

6. **写入验证状态到 _meta：**
   ```json
   {
     "_meta": {
       "validated": "static_only",
       "validated_at": "2026-07-28T10:30:00Z",
       "validation_warnings": []
     }
   }
   ```
   有警告时：
   ```json
   {
     "_meta": {
       "validated": "static_only",
       "validated_at": "2026-07-28T10:30:00Z",
       "validation_warnings": ["route_not_in_kb::/settings/advanced", "mixed_locale::step_3"]
     }
   }
   ```

**注意：** 完整的运行时验证在执行引擎执行时进行。此处的静态检查目的是尽早捕获结构性错误，减少执行时的失败率。

```
✅ CHECKPOINT-6b: Static validation complete
   Files checked: {N}
   All checks passed: {N}
   With warnings: {N} (list: file → warning type)
   Warning types: route_not_in_kb:{N}, mixed_locale:{N}, missing_prerequisite:{N}, missing_flow_test:{N}, locale_unknown:{N}, transient_text:{N}, text_no_source:{N}
```

## Step 6c: Zero-output hard gate (零产出门禁 — 独立运行的最后防线)

**🔒 全量运行收尾时强制执行。不满足 = 运行失败，必须 FAIL LOUDLY（报错退出 / 返回 failed），不得静默结束。**

统计三项：
- `F` = `$OUTPUT/$MODULE/tests/ui/` 下测试用例文件（`UI-*.json`）总数
- `S` = 本轮全部 `_manifest-*.json` 的 `total_scenarios` 之和（从 `tests/_scenarios/.gen/` 读取）
- `W` = 本轮实际新写出的测试用例数（Step 4b/6 累计写盘数）

**门禁判定：**
1. 若 `F == 0` → **FAIL LOUDLY**：`tests/ui/` 下 0 个测试用例，报 `ZERO-OUTPUT-GATE: FAILED`，以非零状态退出。
2. 若 `S > 0` 且 `W == 0` → **FAIL LOUDLY**：枚举了 `{S}` 个场景但填充未产出任何用例（典型停在 Step 4A/4B），报 `ZERO-OUTPUT-GATE: FAILED`，提示按 Step 4b 幂等续跑。
3. 两者都不触发 → 门禁通过，进入 Step 7 正常收尾。

**FAIL 输出格式：**
```
❌ ZERO-OUTPUT-GATE: FAILED
   enumerated_scenarios: {S}
   written_this_run: {W}
   total_ui_test_files: {F}
   reason: Step 4b 填充未执行或未完成 / tests/ui/ 无测试用例
   action: 按此提示续跑（Step 4b 幂等，跳过已有场景）或排查枚举/填充
```

## Step 7: Final report

**🔒 仅当 Step 6c 零产出门禁通过后才能输出 Complete 报告；FAIL 则输出失败报告并以非零状态退出。**

```
GSD > KB-GEN-TESTS-UI Complete
────────────────────────────────────────────────────────────
Module:        {module}
Pages:         {N} with UI tests
Test files:    {total} (happy: {h}, error: {e}, network: {n})
Agent prompts: {p} generated
TP coverage:   {covered}/{total} UI test points
Validation:    {passed}/{total} files passed self-check
Zero-output gate: PASSED (F: {F}, S: {S}, W: {W})
────────────────────────────────────────────────────────────
```

</process>

<validation>
执行结束后，对照以下清单做最终检查。任何 FAIL 项必须修复后重新输出：

| # | Check | FAIL condition |
|---|-------|----------------|
| 1 | Login URL | 任何文件的 url 字段以 `/login` 结尾但 ENV-CONFIG 中 login_path 不是 `/login` |
| 2 | Step count | auth_system 模式下 steps < 2；inline login 模式下 steps < 4 |
| 3 | Hardcoded ID | URL 中出现 UUID 格式或纯数字 ID（非 `{{VAR}}` 包裹） |
| 4 | Missing prereqs | URL 含动态参数但 prerequisites 为空数组 |
| 5 | Empty target | 任何 step 的 target 为空字符串 |
| 6 | 用户操作流未使用 | page doc 中有 用户操作流 table 但 steps 没有从中提取 |
| 7 | Template vars残留 | 输出 JSON 中仍存在 `{{TEMPLATE_VAR}}` 未替换的变量 |
| 8 | 业务闭环缺失 | 操作在弹窗/表单内（创建/编辑/删除/提交），但 expected_results 没有验证最终业务结果（资源落地/页面跳转/成功提示） |
| 9 | Target 语言不匹配 | DEFAULT_LOCALE=en 但 target 字段含中文可见文字（data-testid 除外）；或 DEFAULT_LOCALE=zh 但 target 用了英文文字 |
| 10 | Validation status | 所有文件必须有 `_meta.validated` 字段（"static_only"） |
| 11 | Route existence | `_meta.validation_warnings` 含 `route_not_in_kb` 且该路由是核心页面 → 需确认路由正确性 |
| 12 | 验证模式不匹配 | 页面文档有 `表单验证模式` section 标注 `DISABLE_UNTIL_VALID`，但 expected_results 断言了 "出现错误提示文字"；或标注 `ERROR_ON_SUBMIT` 但断言了 "按钮 disabled" |
| 13 | Zero-output gate | Step 6c 未通过（tests/ui/ 下 0 用例，或枚举场景但填充 0 产出）却报告了 success |
| 14 | 验证消息断言错误 | 表单验证/错误消息断言用了 `text_exists` + locale 字符串 而非 `element_visible` + `{prefix}-error-{field}` locator；或真实文本断言 i18n key 未按 `locales_dir/<default_locale>/<ns>.json` 解析；或 locale 未知时未优先 data-testid / 未标 `_meta.validation_warnings:["locale_unknown"]`；或把"可点击/可操作/可交互"断言写成 `element_visible`（应使用 `element_clickable`） |
| 15 | LLM/外部依赖步骤无逃生通道 | 任一 step 的 关联接口 为 LLM-backed/外部 API，但既非 soft/optional（降级时跳过+断言降级 UI）、又无步骤级 bounded retries/wait precondition、也未归入 external-dependent/flaky 低优先级分类；或将下游 "Connection error."/"AI 增强失败"/上游超时写成对应用回归（BUSINESS_BUG）的硬性 fail_if_not_appear |
| 16 | expect_absent 合法性 | `expect_absent` 用在非 `element_hidden` check；值不是布尔 `true` / 字符串 `"true"`；语义是"先出现后消失/动作后关闭"（非"永不渲染"）；同一元素同时断言 `element_visible` 与 `element_disabled`（冲突覆盖）；或产出了 `element_state`/`multi_action` 幻影字段 |
| 17 | 最终态自洽 | 同一用例 `expected_results` 含互斥/时序断言（如"hidden after step3 + visible after step4"、"先出现后消失"）——单一最终态下必然互斥，产出即必然失败 |
</validation>
