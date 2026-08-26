# Sub-skill: Generate Single UI Test Case

> 🔒 **OUTPUT SPEC ENFORCEMENT:** 本 sub-skill 的所有输出必须符合 `skills/TEST-OUTPUT-SPEC.md`。
> 关键约束：顶层必须有 auth_system + auth_role；url 必须完整（http:// 开头，无占位符）；
> target 文本必须使用 DEFAULT_LOCALE 语言；expected_results 写入操作必须验证业务闭环。

## Purpose

Generate ONE UI test case JSON by mapping page doc elements and user operation flows to the executor's ui dispatch format steps.

## Input (provided by orchestrator)

1. **Template** — UI-TEST-TEMPLATE.json content
2. **Page doc** — 页面元素清单, 用户操作流, 接口调用顺序, 数据流转
3. **TP info** — test point with 操作步骤, 预期结果, 关联前端页面
4. **ENV-CONFIG** — frontend_url, backend_url, auth credentials, i18n config
5. **Page route** — resolved from page doc 基本信息
6. **DEFAULT_LOCALE** — resolved system default language (e.g. "en", "zh")

## Execution

### Step 1: Determine test scenario

From TP's 操作步骤 + page doc 用户操作流:
- Map TP operation to specific rows in 用户操作流 table
- Identify: which elements to interact with, what the system should do, how errors are handled

### Step 2: Build prerequisites

From TP's 前置条件 + page URL:
- URL has dynamic params (`{agent_id}`) → need `resource_exists`
- TP requires specific state (e.g. "sandbox running") → need `sandbox_active`
- Creation page / list page → `prerequisites: []`

**🔒 ID 语义验证:**
- Trace what ID the page URL expects (from page doc 接口调用顺序)
- Verify list_endpoint returns the correct entity type
- If mismatch → add id_transform or use correct extract_field

### Step 3: Build page URL

1. Read 路由路径 from page doc 基本信息
2. Must start with `/` (no domain)
3. Preserve ALL query params (?id=, ?mode=, ?tab=)
4. Replace dynamic params with `{{VARIABLE}}` from prerequisites
5. Full URL: 从 ENV-CONFIG 读取 `environment.frontend_url` + route_with_params，直接拼接为完整 URL（如 `http://localhost:3000/dashboard/agent`）。**禁止使用 `{{BASE_URL}}` 或 `{FRONTEND_BASE_URL}` 等占位符**

### Step 3b: FLOW MODE — full_flow 跨页流程用例 (仅 `SCENARIO_TYPE=full_flow`)

当场景是 `full_flow` 时，生成单元从"单页→单用例"升级为"**多页流程→单用例**"。Filler 接收 `FLOW_CONTEXT`（流程入口页文档 + 下游页面文档 + 各页元素清单 + `page_routes`）。

**URL:** 顶层 `url` = **流程入口页**路由（保留单 url 契约，不改 runner）。登录方式与单页一致（auth_system / 内联登录）。

**steps 构建（覆盖 entry→…→exit）：**
1. 入口页导航步骤（auth_system 模式 step 1；内联登录模式为 step 3）
2. 入口页业务操作步骤（来自入口页 用户操作流）
3. **跨页导航步骤**：target = 源页中触发跳转的导航元素（页面元素清单里"触发接口/功能"指向目标路由的元素，按 Target priority 阶梯：静态 data-testid → 前缀选择器（动态 testid 家族）→ DEFAULT_LOCALE 可见文本仅最后手段）；description 写明"跳转 {目标路由}"
4. 目标页业务操作步骤（来自目标页 用户操作流）
5. 重复 3-4 直至流程退出页
6. 最终断言（业务闭环，如"详情页显示创建的资源"）

**每个跨页导航步骤的结构：**
```json
{
  "step": N,
  "description": "{操作} — 跳转 {目标路由}",
  "target": "{源页导航元素 data-testid（静态/前缀）或可见文本(最后手段)}",
  "conditions": { "wait_for_element": true, "fail_if_not_appear": true }
}
```

**_meta（必须，full_flow 时存在）：**
```json
"_meta": {
  "flow": true,
  "flow_id": "FLOW-001",
  "page_routes": ["/entry", "/middle", "/exit"]
}
```

**约束：**
- 每个跨页导航 step 的 target 必须来自**源页** 页面元素清单（导航元素），不能凭空造
- `page_routes` 与 `FLOW_CONTEXT.page_routes` 一致
- 中间页跳转失败视为流程失败（`fail_if_not_appear: true`）

### Step 4: Build steps array

**🔒 MANDATORY TOP-LEVEL FIELDS (both modes):**

Regardless of auth mode chosen below, the output JSON **MUST** always include these top-level fields for test tracking:
- `"auth_system": "{system_name}"` — from ENV-CONFIG `auth.system` or fallback to module name (e.g. "your-project", "sandbox")
- `"auth_role": "{role}"` — from ENV-CONFIG `auth.role` or fallback to "default" or username hint (e.g. "admin", "qa_tester")

These fields are used as test markers for identifying which system and role context the test runs under. **Never omit them.**

**认证方式（二选一，由 ENV-CONFIG 决定）：**

- **auth_system 模式（推荐）**：如果 ENV-CONFIG 中有 `auth.system` 字段：
  - 模板顶层填充 `"auth_system": "{system_name}"` 和 `"auth_role": "{role}"`
  - `url` 直接指向业务页面（不经过登录页）
  - steps 数组从导航步骤开始，**不生成登录步骤**
  - UI Agent 会通过 storageState 自动注入登录态

- **内联登录模式（兼容旧流程）**：如果 ENV-CONFIG 没有 `auth.system`：
  - steps 1-2 为登录步骤（填写用户名密码）
  - step 3 为导航步骤
  - step 4+ 为业务步骤

**auth_system 模式下的 steps 构建：**

1. **Navigation step** (step 1): navigate to target page
2. **Business steps** (step 2+): from 用户操作流 table rows

**内联登录模式下的 steps 构建：**

1. **Login steps** (step 1-2): always present, resolved from ENV-CONFIG
2. **Navigation step** (step 3): navigate to target page
3. **Business steps** (step 4+): from 用户操作流 table rows

For each operation row in 用户操作流:
```json
{
  "step": N,
  "description": "{操作} — {系统反应的预期}",
  "target": "{element locator}",
  "conditions": {
    "wait_for_element": true/false,
    "fail_if_not_appear": true/false,
    "fail_message": "{from 异常处理 column}"
  }
}
```

**🔒 Target priority (MANDATORY data-testid contract):**

The runner resolves any non-empty step `target` as an EXACT `get_by_test_id` (data-testid) match — a plain visible-text target like `"Edit"` fails "Element not found" deterministically. Generation MUST follow this ladder:

1. **Priority 1 — STATIC data-testid (exact):** `"[data-testid='xxx']"` (most stable, locale-independent). Only when the element's testid is fully static (no runtime id suffix) **AND 可达**（见「🔒 testid 可达性」小节）——该 token 必须以**原生元素的 HTML 属性** `data-testid="..."`（kebab-case）出现在组件源码中，**或**是 enforce-locators 保证注入的 `{prefix}-error-{field}` 模式；其他来源的 token（如仅以 camelCase `dataTestId`/`testId` prop 存在）**不得直接采用**。`aria-label` is NOT a valid standalone step target under the exact-match runner — only data-testid locators resolve.
2. **Priority 2 — DYNAMIC data-testid (CSS prefix):** `"[data-testid^='xxx-']"` for per-entity testid families (e.g. `pm-web-agent-card-btn-edit-${agent.id}` → `[data-testid^='pm-web-agent-card-btn-edit-']`), so the family is targetable without the runtime id. Page-doc "建议:" testids → static exact testid when literal, prefix family when they carry `-{id}` / `${...id}`.
3. **Priority 3 — VISIBLE TEXT (LAST RESORT):** ONLY when the element has NO data-testid at all. Use DEFAULT_LOCALE text (e.g. "Create" not "创建" when locale=en). Every such step MUST (a) be preceded by a step that makes the element visible (e.g. open the container/dropdown first), and (b) append `_meta.validation_warnings: ["no_testid"]` + note it should be flagged for enforce-locators injection.

**🔒 testid 可达性（MANDATORY — 源码 token 必须渲染到 DOM 才是合法定位符）：**

生成器只看到源码 / 页面元素清单里的 testid token，但 runner 只认**渲染后 DOM** 里的 `data-testid`。**源码中存在 ≠ DOM 中存在。** 采用任何 testid 作 `element_id`/`target`/`value` 前必须验证其**可达性**：

- **camelCase `dataTestId=` / `testId=` 组件 prop ≠ 自动 DOM 定位符。** 自定义组件可能把 prop 解构吞掉（例：`<DialogContent dataTestId="sandbox-agent-template-dialog">` 在 dialog/index.tsx 实现里被解构取出，仅用于给关闭按钮生成 `...-close`，**根节点无 data-testid**）→ 直接产出 `element_visible` + `element_id:"sandbox-agent-template-dialog"` 运行时必挂 `'Element not found'`。使用前必须验证组件实现是否把该值**透传**到原生元素（如 `data-testid={dataTestId}` / `{...props}`）→ **只有透传才可作 element_id/target**。
- **裸组件前缀 token 不保证。** `{prefix}-error-{field}` 由 enforce-locators 保证注入（对齐命名），但**裸 `{prefix}`（组件根，如 `sandbox-agent-template-dialog`）没有注入保证**——除非该 token 以原生 `data-testid="..."` 属性存在于组件根，否则**不得**作为 element_id/target。

**不可达时的降级阶梯（按序）：**

1. 改用同组件内**真实可达**的 testid（如对话框关闭按钮 `{prefix}-close`、有原生 data-testid 的子元素）；
2. 无可用 testid → 用 DEFAULT_LOCALE 可见文本 / role 定位（此时按 Priority 3 契约补 `_meta.validation_warnings:["no_testid"]`）；
3. 连文本也没有 → **删除该断言/步骤**，并在 `_meta.validation_warnings` 追加 `"testid_not_reachable"`。

**禁止**把仅以 camelCase prop 存在的 token 写进 `element_id` / `target` / `value`。

**🔒 动态 data-testid 规则 (MANDATORY):**

For per-entity testid families (`...-${entity.id}` / `...-{id}` / `${agent.id}`):
- **DO NOT** emit `"[data-testid='...-{id}']"` — the runtime id is unknowable at generation time, so the literal selector never matches.
- **DO NOT** silently fall back to visible text — the element HAS a data-testid, so visible text is unnecessary and fragile.
- **EMIT** the prefix selector `"[data-testid^='<family-stem>-']"` (Priority 2), which matches the whole family without the runtime id.
- If the runner lacks prefix (`^=` / starts-with) support — note: prefix support depends on the execution engine's capabilities — target a STABLE container ancestor's data-testid instead, and record `_meta.validation_warnings: ["dynamic_testid"]` so the limitation is surfaced.

**🔒 前缀多匹配歧义（MANDATORY）:**

`[data-testid^='...']` 前缀可能匹配页面上多个同家族元素（如多张 agent 卡片、多行）。若该页同家族元素可能有多个，前缀会多匹配 → runner 会抛歧义错误（绝不静默点/选错元素，哲学同 AmbiguousRefError）。生成时必须让前缀**解析到唯一一个元素**：

- 优先：先定位**唯一容器祖先**（如具体某张卡片 / 某行的稳定 testid 前缀）再目标其内部动作，或
- 用**更长/更具体的前缀**收窄到唯一，或
- 仅当测试语义确实是"任选一个"时才显式用 `.first`（并在描述里注明）。

不要假设前缀只命中一个元素而不考虑多匹配。

**🔒 两步下拉/菜单打开模式 (MANDATORY):**

When a target lives inside a dropdown/menu (e.g. an "Edit" menu item):
- The flow MUST first open the container (e.g. the More `⋮` button) with its OWN step + target, then click the menu item in a SEPARATE step — never bundle "open + click" into one step (the menu item is not visible/hittable until the container is opened).
- An icon-only trigger with no aria-label is a component / enforce-locators gap — flag it for data-testid injection, NOT a visible-text target fallback.

**🔒 Target 语言规则 (i18n-aware):**

When `DEFAULT_LOCALE` is set (from ENV-CONFIG `i18n.default_locale`):
- **Visible text targets MUST use the default locale's text**
  - `locale=en`: `"target": "Create button"`, `"target": "Accept"`, `"target": "Cancel"`
  - `locale=zh`: `"target": "创建按钮"`, `"target": "采纳"`, `"target": "取消"`
- **aria-label targets use the default locale's label value**
- **data-testid is locale-independent** — always the default target (Priority 1/2); never fall back to visible text while a data-testid (static or prefix family) exists
- If page doc 页面元素清单 only has Chinese labels, translate common UI terms to the default locale:
  - 创建/新建 → Create / New
  - 编辑/修改 → Edit
  - 删除/移除 → Delete / Remove
  - 保存 → Save
  - 取消 → Cancel
  - 确认/确定 → Confirm / OK
  - 提交 → Submit
  - 搜索 → Search
  - 发布 → Publish
  - 采纳 → Accept
  - 忽略/拒绝 → Reject / Dismiss
  - 关闭 → Close
  - 下一步 → Next
  - 上一步 → Back / Previous

When `DEFAULT_LOCALE` is NOT set (ENV-CONFIG `i18n.default_locale` absent) OR the locale file/key cannot be resolved: **DO NOT default to Chinese** — that produces wrong-language assertions against an English-rendering app. Validation/error-message assertions are unaffected (they use `{prefix}-error-{field}` locators, no locale needed). For genuine text-verification: prefer a `data-testid`-based target/assertion when one exists; for unavoidable visible-text assertions, append `_meta.validation_warnings: ["locale_unknown"]` (surfacing the contract gap, not silently injecting a wrong-language value).

**Description rules:**
- Use Chinese natural language for description (instructions to the AI Agent)
- Describe WHAT to do, not HOW
- Include data to fill (actual values)
- If involves input: specify the value
- **target 字段使用系统默认语言文本，description 字段保持中文**（Agent 理解中文指令，但通过默认语言文本定位元素）

**🔒 一步一动作（MANDATORY — ONE-ACTION-PER-STEP）：**

每个 `step` = **恰好一个**工具动作（`fill` / `click` / `press` / `expect` / `wait_for`）。平台按每次工具调用记录 1 条动作——一个 step 塞多个动作会与实际动作数错位，并可能触发步骤计数误判（"步骤已满"误拦合法重复）。

- **多字段填写必须展开成 N 个独立 step entry（相邻数组顺序）**：如"填写名称 + 描述" → `{ "step": N, "action": "fill", "target": "[data-testid='...-input-name']" }` 和 `{ "step": N, "action": "fill", "target": "[data-testid='...-textarea-description']" }` 两条相邻 step
- 相邻 step 允许 `step` 序号重复——链条上无校验器读数字 `step`，**数组顺序即执行顺序**
- **禁止**在一条 step 的 description 里捆绑多个动作（如"在名称输入框输入…。在描述输入框输入…"）

### Step 5: Build expected_results

From TP's 预期结果 + 用户操作流 "系统反应" column:
```json
{
  "description": "{预期结果描述}",
  "verify_url": "{optional: URL to navigate for verification}",
  "wait_strategy": "等待元素出现|等待 N 秒|等待 URL 变化"
}
```

🔒 **表单验证模式感知（MANDATORY）：**

生成涉及表单验证的 expected_results 时，**必须**查阅页面文档中的 `## 表单验证模式` section，按实际验证模式生成正确的预期断言：

| 验证模式 | check 映射 | 正确的 expected_result | 禁止的 expected_result |
|----------|-----------|----------------------|----------------------|
| `DISABLE_UNTIL_VALID` | `element_disabled`（正向"可点击/可操作/可交互" → `element_clickable`） | 按钮处于 disabled 状态 / 按钮不可点击 / button has disabled attribute | ❌ 出现错误提示文字 |
| `ERROR_ON_SUBMIT` | 错误消息 → `element_visible` + `{prefix}-error-{field}` | 点击提交后出现错误提示文字 / error message 出现 | ❌ 按钮 disabled |
| `ERROR_ON_BLUR` | 错误消息 → `element_visible` + `{prefix}-error-{field}` | 离开输入框后出现错误提示 / error appears after field blur | ❌ 按钮 disabled / ❌ 提交后出现错误 |
| `INLINE_REALTIME` | 实时反馈 → `element_visible` + `{prefix}-error-{field}` | 输入时实时显示验证反馈 / validation feedback appears while typing | ❌ 按钮 disabled / ❌ 提交后出现错误 |
| `REQUIRED_MARKER` | 星号标记 → `element_visible` + marker testid | 必填字段旁显示星号 (*) | ❌ 出现错误提示（仅标记，非阻止提交） |
| `DISABLE_UNTIL_VALID + REQUIRED_MARKER` | `element_disabled` + 星号标记 `element_visible` | 按钮 disabled AND 必填字段有星号标记 | ❌ 出现错误文字 |

**check 映射（对应 expected_results 的 `check` 字段）：**
- 禁用态/不可点击 → `{"check":"element_disabled","element_id":"{prefix}-submit"}`
- 正向"可点击/可操作/可交互" → `{"check":"element_clickable","element_id":"{prefix}-submit"}`
- 验证/错误消息出现 → `{"check":"element_visible","element_id":"{prefix}-error-{field}"}`

**🔒 条件性不存在（MANDATORY — `expect_absent` 契约）：**

`expect_absent` 是 expected_results 中**唯一**新增的引擎可读字段，**仅合法**于 `check:"element_hidden"`，且**仅**用于「本就不该渲染」的条件性非存在语义：

```json
{
  "check": "element_hidden",
  "element_id": "...-btn-enhance",
  "expect_absent": true,
  "description": "编辑模式（源码 `{!editAgentId && ...}` 条件渲染）下不渲染仅创建模式可用的按钮"
}
```

- 🔍 **语义澄清：`element_hidden` ≠ 「元素不可见」。** 它表达**「元素本就不该渲染/不应存在」**——是比「不可见」更强的语义。`element_hidden` 实际是三态：①`count==0`（元素不在 DOM）→ 无标记时等出现再消失、从未出现即 failed，有 `expect_absent:true` 则直接 passed；② 存在且可见 → failed；③ 存在但 CSS 隐藏 → passed。`expect_absent` 只在 `element_hidden` 分支读取（执行引擎契约），配在其他 check 上被引擎静默忽略（= 幻影字段）。
- 取值只允许布尔 `true` 或字符串 `"true"`（引擎双通道都认）；其余值非法
- 触发证据 = 源码条件渲染条件（如 `{!editAgentId && ...}`）→ 该模式永不渲染该元素 → `count==0` 即 passed
- **把源码条件表达式记录到 `_meta.code_evidence[element_id]`**——复用已读到的 code_evidence，把语义转成结构化契约，不只塞进 description
- `description` 保留人读文本（仅报告可读性），不再是语义载体
- **NEVER** 用于「先出现后消失」/「动作后关闭」语义（如"接受后预览卡片关闭"）——那会反转引擎"从不出现 = failed"守卫，制造假阳性
- **NEVER** 用于时序断言（见 END-STATE / 单一最终态规则）

**🔒 禁止幻影字段（MANDATORY — engine 不读 `element_state` / `multi_action`）：**

引擎**不读取** `element_state` 或 `multi_action`——全引擎零命中。**禁止**向 expected_results 输出这两个字段（死契约，产出即误导）。

- disabled 元素语义必须用现有 `element_disabled` / `element_enabled` check
- 一个 disabled 但可见的元素，合法断言为 `element_visible`（引擎允许 visible-on-disabled，元素实际渲染即可见）**或** `element_disabled` —— **二选一**；**禁止**对同一元素同时断言两者而暗示冲突覆盖

**🔒 动态 per-entity 断言目标（MANDATORY）：**
- 动态 per-entity 断言目标：`element_id` 可用包裹前缀形式 `[data-testid^='stem-']`（如 `[data-testid^='pm-web-agent-card-btn-edit-']`），仅当该家族在上下文中唯一命中（如下拉打开后菜单项唯一）
- **禁止**把裸动态家族 stem 直接作为 `element_id`（如 `"pm-web-agent-card-link-name-"`）——runner 把裸 element_id 当作**精确字面量** `[data-testid="..."]`，而动态家族永远带实体 id 后缀渲染（`...-${agent.id}`），精确字面量**永远匹配不到**；必须用包裹前缀形式 `[data-testid^='stem-']`（与 §6.3 的 target 负向规则对称）
- 多匹配 → runner 抛 AmbiguousElementError，**绝不静默 `.first`**
- `element_disabled`/`element_enabled` 保持字面 testid（状态检查不支持前缀形式）

**判断流程：**
1. 检查页面文档是否有 `## 表单验证模式` section
2. 如果有 → 按表中对应模式生成 expected_results
3. 如果没有 → 从前端组件源码直接提取验证模式（查看 submit button disabled prop、error state 渲染方式），然后再生成
4. **禁止假设验证模式** — 不可在没有证据的情况下默认生成 "出现错误提示文字"

🔒 **终态断言 vs 弹窗覆盖（MANDATORY — END-STATE 规则）：**

主流程若含"点击打开弹窗"步骤：launcher 按钮的可见性 → 前置步骤 `expect`；最终 expected_results 只断言弹窗内容（变更组件的 data-testid）。不要对会被本用例自己打开的弹窗遮住的页面按钮断言 `element_visible`。

**END-STATE 页面 = 流程的最后一页，不是 `url` 入口页（MANDATORY）：**

expected_results 在全部步骤完成后**只评估一次**，对**最后一页**的页面状态做断言——**单一最终态 = 引擎的全部能力**：`expected_results` 无法表达步骤绑定/时序断言（"step3 后 hidden + step4 后 visible"、"先出现后消失"在单一最终态下要么互斥、要么语义上不可描述）。需要时序验证 → 拆独立用例 / 步骤级 `expect` / `wait_for` / 推迟生成（见 Step 6 单一最终态纪律）。因此：
- 列表页的"列表非空"（某张卡片可见）检查 → **步骤级** `wait_for`/`expect`，放在列表页上（如 step 1 `{"action":"wait_for","target":"[data-testid^='pm-web-agent-card-link-name-']"}`）
- **NEVER** 放进 expected_results —— 当流程随后导航到详情页（`detail?id=X&mode=edit`）时，end-state 是详情页，列表页元素**不在场**，断言必超时
- 同理，任何只存在于流程中**前序页面**的元素，都不得进入 expected_results（end-state 页面没有它）；要么在它可见的页面上用步骤级 `expect` 断言，要么从 expected_results 删除
- 对照 ROUTE-CONSISTENCY 规则：那条规则按 `url` 页校验，但 end-state 路由可能不同（多路由流程）——**以流程最后一页为准**

🔒 **最终态渲染可达性（MANDATORY — FINAL-STATE RENDER REACHABILITY）：**

`expected_results` 中 `element_*` 断言（`element_disabled`/`element_enabled`/`element_visible`/`element_hidden`/`element_clickable`）的 `element_id` 所指 testid **必须在测试流程的最终态页面（last step 之后的页面状态）确实渲染 / 在 DOM 中可定位**——**源码中存在 ≠ 最终态 DOM 中存在**（「🔒 testid 可达性」只保证源码 token 能透传到原生元素，不保证它在最终态页面被渲染出来）。若目标元素位于一个**最终态会关闭的容器**内（如对话框 dialog/panel/modal，流程末尾把它取消/关闭），则**禁止**在 `expected_results` 中断言它——最终态评估时它已不在 DOM，`Locator.wait_for` 必然超时失败。正确处理：

1. **降级为 step 级断言**：在元素可见的那个 step 上用 `{"step":N,"action":"expect"}` 或 `{"step":N,"action":"wait_for"}` 断言（如 step-level expect element_disabled），或断言发生在对话框仍打开的时刻；
2. **拆成自洽用例**：若元素只在"先出现后关闭"的时序中存在（如"打开对话框 → 表单重置 → 提交按钮 disabled → 取消关闭"），把「对话框内断言」放独立用例（终态 = 对话框仍打开），或把「关闭后最终态」放另一用例断言**最终态仍在场**的元素（如页面列表）；
3. **从 expected_results 删除**：无法在最终态定位该元素时直接删除，改用最终态可验证的等价断言。

可用 `_meta.code_evidence` 记录源码中该 testid 的渲染条件（如 `disabled={...}` 表达式、所在容器 `{open && ...}` 条件），辅助判断最终态是否可达。

**示例 — 空表单取消后重开对话框（历史缺陷模式）：** 流程「打开对话框 → 提交按钮 disabled → 取消 → 重开对话框」最后一步是取消关闭对话框，最终态对话框已关闭 → **禁止**在 `expected_results` 中断言对话框内的 `{prefix}-btn-submit` disabled 态；应把 disabled 断言降级为对话框可见时刻的 step 级 `expect`，end-state 只断言对话框关闭后最终态仍在场的元素（如 launcher 按钮可见 / 列表非空）。

**示例 — DISABLE_UNTIL_VALID 模式下的空表单验证测试：**
```json
"expected_results": [
  { "description": "必填字段为空时，提交/确认按钮处于 disabled 状态，不可点击", "check": "element_disabled", "element_id": "{prefix}-submit" },
  { "description": "填写所有必填字段后，按钮变为可点击状态", "check": "element_clickable", "element_id": "{prefix}-submit" }
]
```

**示例 — ERROR_ON_SUBMIT 模式下的空表单验证测试：**
```json
"expected_results": [
  { "description": "点击提交按钮后，必填字段下方出现错误提示文字" },
  { "description": "修正错误后重新提交，表单提交成功" }
]
```

🔒 **ROUTE-CONSISTENCY（MANDATORY — 断言必须属于测试 url 的页面）：**

所有 `expected_results` 的 `element_id` 必须是测试 `url` 导航到的页面/路由上真实存在的 data-testid —— 对照该页 page-doc 元素清单（`页面元素清单`）和/或变更组件源码。来自**其他路由**的 testid = WRONG-ROUTE 断言，运行时必挂 `'Element not found'`（例如：在编辑页 `/dashboard/agent/detail` 的测试中断言市场页工具栏按钮 `pm-web-agent-btn-create`）。处理方式：
- 若想要的 testid 属于**另一页面/路由** → 要么把 `url` 改为拥有该 testid 的页面，要么**删除**该断言
- **禁止**在某页面的测试中断言另一个页面的页面级按钮

🔒 **消息断言分类（MANDATORY — 验证/错误消息 vs 真实文本验证）：**

**A. 表单验证/错误消息断言 → `element_visible` + 稳定 locator（不做 locale 解析）：**
- When the expected_result's target is a form-validation/error message (required-field error, inline validation message — rendered from an error-state like `{nameError && ...}`/`{descError && ...}`, or an i18n key like `t('...Required')`/`t('...Error')`), emit `{"check":"element_visible","element_id":"{prefix}-error-{field}"}` where `{prefix}` is the component's data-testid prefix (e.g. `sandbox-agent-template-dialog`) and `{field}` is the input's semantic field (e.g. `desc`, `name`). The testid goes in `element_id`, NEVER in `value` — `value` may only hold human-readable visible text (or be omitted); a data-testid / `[data-testid='...']` selector in `value` is a malformed assertion the runner resolves as plain text and fails.
- These testids are AUTO-INJECTED by the enforce-locators mechanism (aligned naming `{prefix}-error-{field}`).
- **DO NOT** resolve their text via locale files. **DO NOT** emit `text_exists` with a locale-resolved string for validation messages.

**B. 真实文本验证断言（如验证持久化 VALUE 的显示文本）→ locale 探测（仅此类）：**
- When the value is GENUINE business text (NOT a validation message) backed by an i18n key (e.g. grepping frontend source for `t('create.descRequired')`-style keys):
  1. Resolve the exact runtime string by READING `<LOCALES_DIR>/<DEFAULT_LOCALE>/<ns>.json` (LOCALES_DIR is relative to the frontend repo root; e.g. `app/i18n/locales/en/agent.json` → `create.descRequired` = "Agent description is required").
  2. **Inline that resolved value** into `expected_results[].value`. The test stays a static JSON carrying the correct locale's string — no runner change.
  3. When the value is a label from a static page (NOT an i18n key), keep the existing behavior.

**C. locale 未知处理（禁止静默 zh）：**
- When `DEFAULT_LOCALE` is absent OR the locale file/key cannot be resolved: **never guess the language, never fall back to zh.** Validation-message assertions are unaffected (they use `{prefix}-error-{field}` locators, no locale needed). For genuine text-verification: prefer a `data-testid`-based assertion when one exists; for unavoidable visible-text assertions append `_meta.validation_warnings: ["locale_unknown"]`.

**D. 动态/预填文本禁止 text 断言（MANDATORY）：**
- 预填/回填字段内容（编辑弹窗回显、URL 参数预填、prerequisite 注入值）、placeholder 占位符文本、任何 data-dependent 动态值 → **禁止** `text_exists` 断言其具体文本
- 正确 = `element_visible` + 字段 data-testid 的 `element_id`（回填内容随数据变化，断言存在性而非具体值）
- `text_exists` 仅限静态文本：i18n-key 解析的运行时字符串 / 静态页面标签
- 示例错误：对编辑弹窗预填描述断言 `text_exists "Describe how to modify ..."`（应改为 `{"check":"element_visible","element_id":"{prefix}-desc"}`）
- **动态 per-entity 断言目标（MANDATORY）**：`element_id` 可用包裹前缀形式 `[data-testid^='stem-']`（如 `[data-testid^='pm-web-agent-card-btn-edit-']`），仅当该家族在上下文中唯一命中（如下拉打开后菜单项唯一）；多匹配 → runner 抛 AmbiguousElementError，**绝不静默 `.first`**；**禁止裸动态家族 stem 作 element_id**（runner 视为精确字面量，永远匹配不到动态 `...-${id}`）；`element_disabled`/`element_enabled` 保持字面 testid（状态检查不支持前缀形式）

**E. text_exists 持久锚点契约（MANDATORY）：**

- `text_exists` 的目标文本必须挂在**最终态必然在场**的持久元素上——静态渲染，或条件渲染但由测试自身确定性地保持在场（如测试自己打开且留在终态的弹窗/面板）。**禁止**对仅存在于瞬态/异步阶段挂载节点的文本生成 `text_exists`：deploy-progress 面板、loading 骨架、spinner、toast、以及其他「先出现后消失」的中间态。判据：若源码中该文本处于异步/条件挂载之下（如 `{isDeploying && …}`、`{loading && …}`、`{isSaving && …}` 类 gate 包裹，或组件由这类状态 gate 挂载），不得作为最终态 `text_exists` 目标。
- 需要验证瞬态阶段 → (a) 断言该瞬态容器的**稳定 testid**（`element_visible` + 持久/前缀定位符），或 (b) 拆成独立自洽用例（其终态 = 可确定到达的瞬态态），或 (c) 依赖已验证的步骤（步骤正确 ⇒ 瞬态必然发生）——不进入断言。
- 无法锚定 → **删除该断言**，并在 `_meta.validation_warnings` 追加 `"transient_text"`（值无源码出处时追加 `"text_no_source"`）。与 `expect_absent` 的既有排除对称——「先出现后消失」语义同样不得作为 `text_exists` 最终态目标。

🔒 **业务闭环验证（MANDATORY）：**

如果测试的操作发生在弹窗（dialog/modal）或表单（form）内，expected_results **必须**包含至少一条验证该弹窗/表单提交后的业务结果断言。仅验证中间交互状态不算测试完成。

闭环验证的判断规则：
- 操作涉及「创建/新建/添加」→ 必须验证：新资源出现在列表中 / 跳转到详情页 / 成功 toast 出现
- 操作涉及「编辑/修改/更新」→ 必须验证：修改后的值在页面上可见 / 保存成功提示
- 操作涉及「删除/移除」→ 必须验证：资源从列表消失 / 确认提示后列表刷新
- 操作涉及「提交表单」→ 必须验证：表单关闭 + 业务数据已落地（列表/详情可查）

例外情况（可以只验证中间状态）：
- TP 明确只测试「取消/忽略/关闭」操作的回退行为（如本例的 reject 场景）
- 但即使是取消场景，也应验证：弹窗关闭后页面恢复到操作前状态

示例 — 一个完整的弹窗创建测试应包含：
```json
"expected_results": [
  { "description": "弹窗中表单填写完成后，点击确认按钮" },
  { "description": "弹窗关闭，页面返回列表" },
  { "description": "列表中出现新创建的资源项（名称与填写值一致）" }
]
```

### Step 6: Handle transient/conditional states

From code analysis or page doc hints:
- Loading state (seconds) → test AFTER loading (don't assert disabled during load)
- Conditional state (needs backend status) → two test cases (met/unmet)
- Permanent state (permission) → single disabled assertion

**🔒 条件性不存在的 unmet 用例（MANDATORY）：**

条件性状态拆两个用例时：
- **met 用例**：条件成立（资源/权限/模式存在）→ 正常操作 + 业务闭环断言
- **unmet 用例**：条件不成立，某元素**本就不渲染**（如编辑模式不渲染仅创建按钮）→ expected_results 输出 `{"check":"element_hidden","element_id":"...","expect_absent":true}`（契约见 Step 5）；**禁止**只写 prose 版 `element_hidden`——引擎不读 description，"从不出现 = passed"必须靠 `expect_absent` 显式声明
- `expect_absent` 仅限"永不渲染"语义；「出现后又消失/动作后关闭」语义**不得**标 `expect_absent`（会反转引擎守卫 → 假阳性）

**🔒 单一最终态纪律（MANDATORY — SINGLE-FINAL-STATE）：**

`expected_results` 在最后一步完成后对最终页面状态**只评估一次**：**禁止**产出步骤绑定/时序断言（"step3 后 hidden + step4 后 visible"、"先出现后消失"）——这类断言在单一最终态下必然自相矛盾（互斥），且引擎根本不支持。若确实需要时序验证，三选一：
1. **拆成独立用例** —— 每个用例单一最终态自洽（一个验证"某操作后消失"，另一个验证"重新出现/重新打开后可见"）
2. **降级为步骤级 `expect` / `wait_for` 动作** —— 在具体 step 上断言（步骤级动作机制已存在）
3. **推迟生成** —— 等引擎支持步骤级断言后再产出

产出前自校验：同一用例的 `expected_results` 必须最终态自洽（互斥断言 = 拒绝生成）。

**🔒 LLM / 外部 API 步骤规则（MANDATORY — 禁止把外部依赖硬门禁成 P0/P1 应用回归）：**

当某步骤的 关联接口 是 LLM-backed 或外部 API 端点（如 `enhance-description` → ChatOpenAI/DeepSeek 上游）时，步骤结果取决于 SUT 之外的外部服务——上游不可达 ≠ 应用回归。生成时必须对此类步骤应用**三选一**：

1. **soft/optional step（软步骤，可优雅跳过）** — 当 API 返回其**文档化降级**（页面文档 异常处理 列：error + Retry UI / 内联错误 / 非阻断提交）时，步骤可跳过，但**仍必须断言降级 UI**（如 Retry 按钮可见 / `{prefix}-error-{field}` 错误提示出现），`fail_if_not_appear: false`；
2. **step-level retry precondition（步骤级有界重试前置）** — 在 `fail_if_not_appear` 硬失败**之前**先做有界重试 / 有界等待（bounded retries / bounded wait，覆盖慢 LLM 调用的数十秒延迟），`fail_message` 注明"外部依赖不可达"，而非首试即硬失败；
3. **external-dependent classification（外部依赖分级）** — 从 P0/P1 硬门禁中剔除，默认标为 flaky / 低优先级用例。

**禁止（NEGATIVE RULE）：** 无上述任一逃生通道（无降级断言、无有界重试、无分级标记）时，**禁止**用 `fail_if_not_appear: true` 把 LLM/外部 API 步骤硬门禁成 P0/P1 应用回归——外部依赖抖动不是应用缺陷。

### Step 7: Generate error path variant

From 用户操作流 rows with 异常处理 column filled:
- Each error row → separate test case or additional expected_result
- Name: `UI-{REQ}-{TP}_ERROR-{scenario}.json`

### Step 8: Self-validate

1. Output is valid JSON
2. `steps` array has >= 2 entries (auth_system mode: 1 nav + 1 business) or >= 4 entries (inline login mode: 2 login + 1 nav + 1 business)
3. Every step has `description` and `target` (non-empty)
4. `expected_results` has >= 1 entry
5. `url` starts with `http` (resolved from ENV-CONFIG `environment.frontend_url`, no placeholders)
6. No hardcoded IDs in url or steps (must use `{{VARIABLE}}`)
7. `prerequisites` declared if URL has dynamic params
8. If `auth_system` is set → no login steps in `steps` array; if not set → login step URL matches ENV-CONFIG login path
9. **`auth_system` field exists and is non-empty** (system name for test tracking)
10. **`auth_role` field exists and is non-empty** (role identifier for test tracking)
11. **If `SCENARIO_TYPE=full_flow`**: `_meta.flow === true`、`_meta.flow_id` 非空、`_meta.page_routes.length >= 2`、steps 中包含与 `page_routes` 对齐的跨页导航步骤（target 来自源页元素清单）、顶层 `url` 为入口页路由

## Output

Valid JSON file content — ready to write to `tests/ui/UI-{REQ}-{TP}_{scenario}.json`.
For error variants: additional `UI-{REQ}-{TP}_ERROR-{slug}.json` files.
For full_flow: `UI-{REQ}-{TP}_FLOW-{flow_id}.json`.
