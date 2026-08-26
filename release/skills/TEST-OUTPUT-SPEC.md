# TEST-OUTPUT-SPEC.md — 测试用例 JSON 输出规范

> **Canonical reference for all gen-tests skills.**
> 违反本规范的任何输出 = 无效，必须删除重做。
> 所有 gen-tests 子技能（api / e2e / ui）在生成和自检时必须引用本文件。

---

## 1. 顶层字段（必填）

每个测试用例 JSON 文件的根级别必须包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `_meta` | object | YES | 元数据，含 source、priority、tool、生成信息 |
| `name` | string | YES | 测试用例名称，格式：`{METHOD}-{api-stem}_{TP-ID}` 或 `E2E-{REQ}_{slug}` 或 `UI-{REQ}-{TP}_{scenario}` |
| `type` | string | YES | 分类标识，见下方分类规则 |
| `auth_system` | string | YES | 目标系统认证名（如 "your-project"）— 执行引擎根据此字段注入登录态 |
| `auth_role` | string | YES | 认证角色（如 "admin", "qa_tester"）— 决定注入哪个用户的 token |
| `steps` | array | YES | 测试步骤数组（API/E2E）或操作步骤数组（UI） |

**API/E2E 额外字段：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `prerequisites` | array | YES | 前置条件（可为空数组 `[]`） |

**E2E 额外字段：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `cleanup` | array | YES | 清理步骤（对应每个创建操作的 DELETE） |

**UI 额外字段：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | YES | 目标页面完整 URL（`http://` 开头，无占位符） |
| `expected_results` | array | YES | 预期结果验证列表（至少 1 条） |
| `options` | object | YES | 执行选项（如 `max_retry`） |

---

## 2. type 分类规则

**只有 3 种合法 type 值，错误分类 = 输出无效。**

| type 值 | 含义 | 判定条件 | 对应执行工具 |
|---------|------|---------|---------------|
| `api` | API 测试 | 单步或多步 API 请求（含 prerequisite/regression pairs），步骤间可有 extract/变量传递 | 执行引擎的 api 分派工具 |
| `e2e` | 端到端场景 | 完整业务链路：多步 API 串联 + 依赖链（depends_on DAG）+ 可能含异步等待/DB 验证/跨服务调用 | 执行引擎的 e2e 分派工具 |
| `ui` | 纯浏览器操作 | 所有步骤都是 UI 交互（click/input/navigate），由执行引擎的 Agent 执行 | 执行引擎的 ui 分派工具 |

**分类决策树：**

```
步骤全是浏览器操作？
  ├─ YES → type: "ui"
  └─ NO → 是否有基于 depends_on 的业务链路（跨 TP/跨 REQ）？
       ├─ YES → type: "e2e"
       └─ NO → type: "api"（无论单步还是多步 prerequisite + main）
```

**关键区分：**
- `api` vs `e2e` 的本质区别：`e2e` 来自 TP 之间的 `depends_on` 依赖关系，形成完整业务场景链路；`api` 是对单个 API 端点的验证（即使有 prerequisite 步骤获取 ID，仍然是 `api`）
- 混合 API + UI → type: "e2e"

**生成对应关系：**
- `gsd-kb-gen-tests-api` 输出 `type: "api"`
- `gsd-kb-gen-tests-e2e` 输出 `type: "e2e"`
- `gsd-kb-gen-tests-ui` 输出 `type: "ui"`

---

## 3. Auth Header 规则

### 3.1 核心原则

当测试用例顶层声明了 `auth_system` 字段且该系统使用 **token 认证**时，所有 API steps 的 headers 必须包含认证头。

**认证方式由 ENV-CONFIG 中的 `auth` 配置决定：**

| 认证方式 | headers 中的认证字段 | 适用场景 |
|---------|---------------------|---------|
| Bearer Token（默认） | `"Authorization": "Bearer {{token}}"` | OAuth2、JWT 等 token 体系 |
| API Key | `"X-API-Key": "{{api_key}}"` 或其他自定义 header | 第三方服务集成 |
| Session/Cookie | 无需显式 header（由运行时管理） | 传统 session 认证 |

**当认证方式为 Bearer Token（最常见情况）时：**

所有 API steps 必须带 `"Authorization": "Bearer {{token}}"` — 适用于：
- 主测试步骤
- Prerequisite 步骤
- 错误/边界场景步骤
- 验证步骤
- Cleanup 步骤

### 3.2 例外情况

- 明确标记为公开端点的步骤（如 `/health`、`/ping`），可在 step 中声明 `"auth_required": false` 来豁免
- 非 token 认证体系的系统，按其实际认证方式配置 headers

### 3.3 违规判定（token 认证体系下）

以下任何情况 = auth header 违规，文件无效：
- step 的 `headers` 为空字符串 `"{}"`
- step 的 `headers` 为空对象 `{}`
- step 的 `headers` 中缺少认证相关键（如 `Authorization`）
- 认证头格式与 ENV-CONFIG 声明的认证方式不匹配

### 3.4 `{{token}}` 的来源

- **auth_system 模式：** 执行引擎运行时根据 `auth_system` + `auth_role` 自动注入。`{{token}}` 是执行引擎的保留运行时变量。
- **内联登录模式：** 由第一个 login step 的 `extract` 产出。

---

## 4. headers/body 格式规范

### 4.1 执行引擎强制要求

执行引擎对 api/e2e 分派工具的要求：

- **headers 必须是 JSON 字符串**（不是 JSON 对象）
- **body 必须是 JSON 字符串**（不是 JSON 对象）或 `null`

### 4.2 正确格式

```json
{
  "request": {
    "url": "http://localhost:8000/api/v1/agents",
    "method": "POST",
    "headers": "{\"Authorization\": \"Bearer {{token}}\", \"Content-Type\": \"application/json\"}",
    "body": "{\"name\": \"test-agent\", \"description\": \"for testing\"}"
  }
}
```

### 4.3 错误格式（无效）

```json
{
  "request": {
    "url": "http://localhost:8000/api/v1/agents",
    "method": "POST",
    "headers": {"Authorization": "Bearer {{token}}", "Content-Type": "application/json"},
    "body": {"name": "test-agent", "description": "for testing"}
  }
}
```

### 4.4 GET 请求的 body

GET 请求的 body 应为 `null`（JSON 字符串格式则为 `"null"` 或直接 `null`）。

### 4.5 UI 测试豁免

`type: "ui"` 的测试用例（ui 分派工具格式）不涉及 headers/body — 它们使用 `steps[].description` + `steps[].target` 结构。此规则仅适用于 API 和 E2E 测试。

---

## 5. 变量引用规范

### 5.1 变量类型

| 语法 | 来源 | 说明 |
|------|------|------|
| `{{token}}` | 执行引擎运行时注入 | 基于 auth_system/auth_role 自动获取的认证 token |
| `{{variable_name}}` | 前序 step 的 `extract` 产出 | 如 `{{agent_id}}`、`{{session_id}}` |

### 5.2 合法变量清单

在输出文件中，只有以下 `{{...}}` 变量是合法的：

1. `{{token}}` — 执行引擎保留变量，运行时注入
2. 前序 step 中 `extract[].name` 声明的变量 — 如 `{{agent_id}}`

### 5.3 禁止出现的变量（违规 = 输出无效）

以下变量**不得**出现在最终输出 JSON 中：

- `{{BASE_URL}}` / `{{API_BASE_URL}}` / `{{FRONTEND_BASE_URL}}`
- `{{AUTH_USERNAME}}` / `{{AUTH_PASSWORD}}` / `{{AUTH_TOKEN}}`
- `{{LOGIN_URL}}` / `{{LOGIN_PATH}}`
- `{{PLACEHOLDER}}` / 任何大写的模板占位符
- 任何未在前序 step 中 extract 定义的 `{{...}}` 变量

### 5.4 检测正则

```regex
\{\{([^}]+)\}\}
```

提取所有匹配项，与合法清单对比。不在清单中的 = 违规。

### 5.5 `{{var}}` 替换范围（执行引擎契约 — 生成时必须遵守）

执行引擎运行时的 `{{var}}` 替换范围：

- ✅ 替换：`request.url`、`request.headers`、`request.body`、`db_verify.conditions[].value`、**`assert[].expected`、`assert[].path`**
- ❌ **不替换（按字面量处理）**：`extract[].path` — 内嵌 `{{var}}` → 提取为空 → 下游变量链断裂

**防御性策略：生成时统一禁止** `assert[].expected` / `assert[].path` / `extract[].path` 内嵌 `{{...}}`，保证跨 runner 可跑、不依赖执行引擎行为版本。需要回引前序 step 变量的断言，必须改为两步式：

1. 前序 step 用**固定路径** extract 出目标值（如 `$.items[0].id` → `{{agent_id}}`）
2. 断言只比较固定字段 — `{"type":"jsonpath","path":"$.id","operator":"==","expected":"{{agent_id}}"}` 依赖执行引擎断言侧替换，跨 runner 不稳，统一禁止

无法固定路径时 → **删掉该断言**，保留 status / not_empty 已覆盖意图。

---

## 6. Steps 结构完整性

### 6.1 API 测试 steps 结构

每个 step 必须包含：

```json
{
  "name": "步骤名称",
  "request": {
    "url": "http://...",
    "method": "GET|POST|PUT|DELETE|PATCH",
    "headers": "{\"Authorization\": \"Bearer {{token}}\", \"Content-Type\": \"application/json\"}",
    "body": "{...}" 或 null
  },
  "extract": [],
  "assert": []
}
```

| 子字段 | 必填 | 说明 |
|--------|------|------|
| `name` | YES | 步骤描述 |
| `request.url` | YES | 完整 URL（`http://` 开头，无模板占位符） |
| `request.method` | YES | HTTP 方法 |
| `request.headers` | YES | JSON 字符串，必须含 Authorization |
| `request.body` | YES | JSON 字符串或 null |
| `extract` | NO | 变量提取数组（可省略或为 `[]`） |
| `assert` | YES | 断言数组，至少 1 条 |

### 6.2 E2E 测试 steps 结构

同 API 测试 steps 结构，但：
- 步骤数 >= 2（auth_system 模式，不含 login）
- 变量传递必须连贯：step N extract → step N+1 使用 `{{var}}`
- 必须有 cleanup 对应每个 POST 创建

### 6.3 UI 测试 steps 结构

```json
{
  "step": 1,
  "description": "操作描述（中文）",
  "target": "[data-testid='pm-web-agent-template-btn-ai-enhance']",
  "conditions": {
    "wait_for_element": true,
    "fail_if_not_appear": false,
    "fail_message": "异常提示"
  }
}
```

| 子字段 | 必填 | 说明 |
|--------|------|------|
| `step` | YES | 步骤序号 |
| `description` | YES | 操作描述（非空） |
| `target` | YES | 元素定位：必须为 `[data-testid='...']`（静态）或 `[data-testid^='...']`（动态 testid 前缀）；仅当元素无 data-testid 时才允许 DEFAULT_LOCALE 可见文本，且必须前置使其可见的步骤 + `_meta.validation_warnings:["no_testid"]`（应标记给 enforce-locators 补 testid）。 |
| `conditions` | NO | 等待/失败条件 |
| `element_id` | NO | 目标元素的字面 data-testid（如 `pm-web-agent-template-btn-ai-enhance`）— 增强定位精度，推荐动作 step 携带 |

**一步一动作（MANDATORY）**: 一个 `step` 条目 = 一次工具动作（一次 fill / 一次 click / 一次 navigate）。**禁止**把多个动作压缩进单个 step（如一个 step 同时 fill 名称输入框 + fill 描述输入框，靠 description 描述多个动作）。多字段 fill 行展开为 N 个**相邻** step 条目，**允许重复 `step` 序号**（如 `"step": 2` × 2 条 fill 条目）。原因：执行引擎按每次工具调用记录 1 条动作；一步多动作 → 动作记录数与步骤数错位 → 合法的重复步骤被误判「步骤已满」拦截。**不要**把动作语义塞进 description 自然语言企图绕过 —— 引擎不读 description 执行动作，结构才是契约。

**前缀多匹配歧义（MANDATORY）**: `[data-testid^='...']` 前缀可能匹配多个同家族元素（多卡片/多行/多用户等）。runner 对多匹配会抛歧义错误（绝不静默点/选错元素）。生成时须保证前缀解析到唯一元素：先定位唯一容器祖先再目标其内部动作；或用更长/更具体前缀收窄；仅当语义为"任选一个"时才显式 `.first`。不要假设前缀唯一命中。**element_id 断言同样歧义**：断言对多匹配前缀同样抛 AmbiguousElementError——只在该家族在上下文中解析为 ≤1 个元素时用前缀 element_id；状态检查（`element_disabled`/`element_enabled`）保持字面 testid，不用前缀。

### 6.4 UI expected_results 结构

```json
{
  "check": "text_exists",
  "description": "预期结果描述（中文，非空）",
  "value": "期望出现的文本 / URL 片段"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `check` | YES | 校验类型（见 7.7 词汇枚举） |
| `description` | YES | 预期结果描述（非空） |
| `element_id` | **条件必填** | **所有 element_* check（`element_visible`/`element_hidden`/`element_disabled`/`element_enabled`/`element_clickable`）优先携带**：被测元素的字面 data-testid（如 `pm-web-agent-template-btn-ai-enhance` / `{prefix}-error-{field}`）；element_id 也可用**包裹前缀形式** `[data-testid^='stem-']`（动态 per-entity 家族，如 `[data-testid^='pm-web-agent-card-btn-edit-']`；执行引擎已支持，多匹配抛 AmbiguousElementError——绝不静默 .first）；**禁止把裸动态家族 stem 直接作 element_id**（如 `"pm-web-agent-card-link-name-"` —— runner 把裸 element_id 当精确字面量 `[data-testid="..."]` 解析，而动态家族永远带 `-${id}` 后缀渲染，精确字面量永远匹配不到；必须用包裹前缀形式，与 §6.3 的 target 负向规则对称）；多匹配歧义规则同 §6.3 target；`element_disabled`/`element_enabled`/`element_clickable` 必须携带，其余 element_* check 有 data-testid 就放进 element_id。携带 element_id 时 runner 按 data-testid 精确定位（语言无关）且豁免空值拦截 |
| `value` | **条件必填（text 类 check 必填）** | `text_exists` / `url_contains` 必须携带非空值；`element_*`（element_visible / element_hidden / element_disabled / element_enabled / element_clickable）只放人眼可见文本（按钮标签等），无文本目标则省略（携带 element_id 时可省略）— runner 取值链 `value`>`keyword`>`text`>`selector`>`content`（content 兼容但非规范，规范字段是 `value`）；缺值 = 空断言，运行时显式拒绝，生成层扫描器同步拦截。**禁止**把 data-testid、裸 testid token、或 `[data-testid='...']` 选择器字符串写进 `value`（运行时把 value 当文本处理，塞选择器导致畸形断言）。**验证/错误消息**（必填校验、内联错误 — 由 `{field}Error && ...` 错误态渲染或 `t('...Required')`/`t('...Error')` key）→ `element_visible` + `element_id:"{prefix}-error-{field}"`（enforce-locators 自动注入；**不做 locale 解析**，禁止 `text_exists` + locale 字符串）；**真实文本验证**（如持久化 VALUE 的显示文本）i18n-key 消息 → 按 `locales_dir/<default_locale>/<ns>.json` 解析后内联实际 locale 字符串（禁止猜语言 / 禁止静默 zh 兜底 — 解析失败 → 优先 `data-testid` 断言；无法避免可见文本断言时标 `_meta.validation_warnings:["locale_unknown"]`） |
| `expect_absent` | NO（仅 `check:"element_hidden"`） | 条件性不存在标记：值仅 `true` / `"true"`；语义 = 元素**本就不该渲染**（源码条件渲染不满足，如 `{!editAgentId && ...}` / 仅创建模式可用）。引擎读此标记（flag → count==0 → 直接 passed）。**禁止**用于「先出现后消失」（appear-then-disappear）或「step3 后 hidden + step4 后 visible」类时序断言 — 那是单一最终态无法表达的（见 §7.7#7 SINGLE-FINAL-STATE）；**禁止**携带于其他 check（引擎只在 `element_hidden` 上读取）。 |

---

## 7. 断言规范

### 7.1 断言来源优先级

**断言必须基于事实，不得基于文档猜测。**

优先级（高 → 低）：

1. **Dry-run 验证结果** — 实际 API 返回值是最终权威
2. **Source code 提取** — 从 router.py / Pydantic model 提取的真实行为
3. **KB 文档 测试断言表** — 有明确的断言 table
4. **KB 文档 请求/响应示例** — 推导断言
5. ~~文档描述性文字~~ — **禁止作为断言来源**

### 7.2 断言格式

| 断言类型 | JSON 格式 |
|---------|-----------|
| HTTP 状态码 | `{"type": "status", "expected": 200}` |
| 响应时间 | `{"type": "response_time", "max_ms": 3000}` |
| 字段非空 | `{"type": "not_empty", "path": "$.data.id"}` |
| 精确匹配 | `{"type": "jsonpath", "path": "$.status", "operator": "equals", "expected": "active"}` |
| 包含文本 | `{"type": "body_contains", "expected": "关键文本"}` |
| 正则匹配 | `{"type": "regex", "pattern": "...", "field": "body_text"}` |
| 数组检查 | `{"type": "array", "path": "$.items", "check": "length", "expected": 10}` |

### 7.3 默认断言（每个 API/E2E step 必须有）

```json
{"type": "status", "expected": <actual_status_code>}
{"type": "response_time", "max_ms": 3000}
```

### 7.4 推断断言的处理

当无法确定精确值时（源码不可达 + 无 dry-run）：
- 使用 `"operator": "in"` + 范围值
- 示例：`{"type": "status", "operator": "in", "expected": [400, 422]}`
- 在 `_meta` 中标注 `"assertion_source": "kb_doc_inferred"`

### 7.5 断言字段禁止 `{{var}}`

`assert[].expected`、`assert[].path`、`extract[].path` **禁止**出现任何 `{{...}}`（防御性策略）。执行引擎现已在 `assert[].expected` / `assert[].path` 内替换 `{{var}}`，但 **`extract[].path` 仍不替换**（内嵌 → 提取为空 → 下游变量链断裂）。统一禁止三类字段内嵌占位符，保证跨 runner 可跑、不依赖执行引擎行为版本。

需要回引前序 step 变量时，两步式修复：

1. **固定路径 extract**：在产生变量的 step 里用固定路径提取，如 `{"name": "agent_id", "source": "jsonpath", "path": "$.items[0].id"}`
2. **断言固定字段**：断言只比较固定路径/字面量；无法固定 → 删除该断言

✅ 合法：`{"type": "jsonpath", "path": "$.id", "operator": "==", "expected": "active"}`（expected 是字面量）
❌ 禁用：`{"type": "jsonpath", "path": "$.id", "operator": "==", "expected": "{{agent_id}}"}`（依赖执行引擎断言侧替换，跨 runner 不稳）
❌ 必挂：`{"name": "desc", "source": "jsonpath", "path": "$.items[?(@.id=='{{agent_id}}')].description"}`（extract.path 不替换）

### 7.6 禁止断言 `_unverified` 路径

`_meta.path_unverified` 中的路径 = **未被探针/实证来源确认的猜测路径**（探针失败、端点被跳过、或仅有模块级 blanket 约定）。**任何 `assert[].path` / `extract[].path` / `semantic_expect.path` / `prerequisites[].params.extract_field` / `verify_field` 不得引用 `path_unverified` 中的路径**（逐字比对）。

原因：在真实后端不返回该字段时，对未确认路径断言会以 `not_empty($.description) (actual=)` 稳定失败——**以当前接口探针实际返回为准**是生成/修复的唯一真值来源。

处理规则（无法确认路径时）：

1. **删除断言**：`assert.path` 命中 → 删该断言，保留 `status` 及其它已验证断言。
2. **删除提取或改写**：`extract.path` / `extract_field` 命中 → 若该轮已有探针确认的等价固定路径则改写；否则删除。删除破坏下游 `{{var}}` 链时同步改写/删除下游依赖。
3. **引用归零后清理**：`path_unverified` 中不再被任何路径引用的条目一并移除。
4. 修复记入 `_meta.validation_corrections[]`，`source` 为 `envelope-validation` 或 `unverified-assert-guard`。

✅ 合法：`{"type": "not_empty", "path": "$.items[0].id"}`（id 已被探针确认）
❌ 必挂：`{"type": "not_empty", "path": "$.description"}`（path_unverified 含 `$.description`）

### 7.7 UI 状态断言规则（编码为准）

UI 测试的**元素行为状态断言**（`element_disabled` / `element_enabled`）以前端源码为唯一真值（有需求以需求为准，没需求以编码为准，不和需求冲突）。文档文本（`pages/*.md`）只供补充，禁止用文档推断的 `disabled={isXxx...}` 表达式直接写断言。

**UI check 词汇枚举（合法值 = 本规范注册的 UI check 集合，执行引擎 runner 实际支持；超出即运行时 `unknown assertion type` 失败）：**

```
text_exists | element_visible | url_contains | element_hidden
element_disabled | element_enabled | element_clickable
```

> `element_visible` 已收敛为**纯可见性**（render/size/opacity/visibility/obscured 判定，不含 pointer-events/disabled）；`element_clickable` = 可见 **且** 可点击（未被禁用 / 未遮挡 / 可交互）。

**状态断言规则（任何一条违反 = 文件无效）：**

1. **词汇合法**：`expected_results[].check` 必须是上述枚举值之一。
2. **状态声明用状态 check**：`expected_result` 或 `step` 描述声称 disabled/enabled/可点击（如「处于禁用状态」「无法点击」「点击无任何效果」「可点击/可交互/可操作」）时，该 expected_result 的 `check` 必须是 `element_disabled` / `element_enabled` / `element_clickable`。**用 `element_visible` + 描述文本声称 disabled/enabled = 捏造断言；用 `element_visible` 声称「可点击/可交互/可操作」同样是捏造断言 — element_visible 已收敛为纯可见性，disabled/obscured 控件也会通过，可点击性断言必须用 `element_clickable`。**
3. **`element_id` 必填且真实存在（状态 check 仅字面 testid）**：状态 check 必须携带 `expected_results[].element_id`，且该 data-testid **必须存在于前端源码**（字面 `data-testid="..."`，动态家族名不算字面 id）。`element_disabled`/`element_enabled` 的 element_id **必须是字面 testid，不接受包裹前缀形式**（per-entity 状态无 id 无法钉死，语义歧义）。**非状态 element_* check 的 element_id 同样禁止裸动态家族 stem**（如 `pm-web-agent-card-link-name-`——runner 视为精确字面量，动态家族永远带 `-${id}` 后缀渲染，精确字面量永远匹配不到）；动态家族断言必须用包裹前缀形式 `[data-testid^='stem-']`。
4. **状态与源码一致**：
   - `element_disabled`：源码该节点必须存在 `disabled=` 属性（`<node> disabled={expr}</node>`）。
   - `element_enabled`：源码该节点不得**无条件禁用**（裸 `disabled` 或 `disabled={true}`）；条件禁用（如 `disabled={isSaving}`）合法——断言的是默认/条件外的可用态。
   - `element_clickable`：源码该节点不得**无条件禁用**，且未被遮挡 / 无 `pointer-events: none`（可见 **且** 可交互）；条件禁用（如 `disabled={isSaving}`）在默认态断言合法——断言的是默认/条件外的可点击态。
5. **源码证据留痕**：状态 check 的每条 `element_id` 必须在 `_meta.code_evidence["<element_id>"]` 记录 `"文件:行 实际disabled表达式（或无）"`（如 `"AgentTemplateDialog.tsx:1071 disabled={enhanceState.status === \"loading\"}"`），保证断言永远有源码依据可查。
6. **check 选择规则（visible vs clickable）**：断言「组件渲染/出现在页面」→ `element_visible`；断言「按钮可点/可交互/未被禁用」→ `element_clickable`。**不要用 `element_visible` 断言「可点击」**；也不要对被自己打开的弹窗遮挡的页面底层按钮断言 `element_visible`（会 covered 失败）。launcher 按钮的可见性用**步骤级 expect 动作**断言,放在点击打开弹窗的步骤之前;最终 expected_results 只断言终态可见的元素(弹窗自身内容);被本用例自己打开的弹窗覆盖的页面元素绝不能进 expected_results(会 covered 失败,且 element_clickable 也无法豁免——根因是断言位置)。`expect` 是合法步骤动作,用于在流程的特定时点断言元素可见性(如点击打开弹窗前的 pre-click 断言)。
7. **SINGLE-FINAL-STATE + ROUTE-CONSISTENCY（expected_results 只评估一次，属于 END-STATE 页面 = 流程最后一页）**：所有 `expected_results` 在整个流程**最后一个 step 执行完后**、对 **FINAL 页面状态** 评估**恰好一次** —— 框架**不**支持步骤绑定 / 时序断言（没有 step-bound `when`/`condition`，也不会在中间步骤评估）。**步骤绑定或时序断言（如「step3 后 hidden + step4 后 visible」「先出现后消失」）不可表示**，MUST 拆成各自最终态自洽的独立用例，或降级为**步骤级 expect / wait_for** 动作（在对应时点断言）。所有 `expected_results` 的 `element_id` 必须是 **END-STATE 页面**（流程的**最后一页**，expected_results 只在该页评估一次）上真实存在的 data-testid —— 对照该页 page-doc 元素清单（`页面元素清单`）/变更组件源码。多路由流程（如列表页 → 详情页 `detail?id=X&mode=edit`）中，只存在于**前序页面**的 testid（如列表页卡片 `pm-web-agent-card-link-name-*`）= WRONG-ROUTE 断言，运行时必挂 `'Element not found'`（end-state 在详情页，列表元素不在场）。处理方式：若想要的 testid 属于**流程的前序页面/其他路由** → 把它改在**步骤级** `wait_for`/`expect` 上断言（在它可见的那一页），或从 expected_results **删除**；**禁止**在某页面测试的 expected_results 中断言另一页面（含流程前序页面）的页面级元素。
8. **`expect_absent` 仅注册于 `element_hidden`（条件性不存在）**：`expected_results[].expect_absent` 只在 `check:"element_hidden"` 上合法，值仅 `true` / `"true"`，语义 = 元素**本就不该渲染**（源码条件渲染，如 `{!editAgentId && ...}` / 仅创建模式可用）。引擎读 `expect_absent`（flag → count==0 → 直接 passed），不读 `element_state`/`multi_action`。**禁止**用于「先出现后消失」（appear-then-disappear）或「step3 后 hidden + step4 后 visible」这类时序/步骤绑定断言 — 框架只支持单一最终态（见规则 7），此类断言 MUST 拆成各自最终态自洽的独立用例，或降级为步骤级 **expect / wait_for** 动作（在对应时点断言）。
9. **`element_state` / `multi_action` 不是支持字段（引擎零命中）**：禁止在 `expected_results` / step 中携带 `element_state`、`multi_action`（引擎不消费 —— 写入这些字段不产生任何效果，等于无效语义）。disabled 语义一律用 `element_disabled` / `element_enabled`（见规则 2-5）；多动作步骤用 §6.3 的一步一动作契约展开（一个 step = 一个工具动作，多字段 fill 展开为 N 个相邻 step，允许重复 `step` 号）。

**动态数据值禁止 text 断言（MANDATORY — 违反 = 文件无效）：**

预填/回填的字段内容、占位符（placeholder）文本、以及任何 data-dependent 的动态值 → **禁止**用 `text_exists` 断言其具体文本；正确断言 = `element_visible` + 该字段 data-testid 的 `element_id`（证明字段渲染/可见即可，不校验其内容）。`text_exists` 仅限静态文本（i18n-key 解析的运行时字符串、静态页面标签），不适用于动态预填值。示例错误：对编辑弹窗里预填的描述文本断言 `text_exists "Describe how to modify ..."`（占位符/数据依赖，必错）。

**与「编码为准」的典型映射**（文档说「空描述 → 校验拦截」≠「按钮 disabled」）：

| 源码事实 | 合法断言 |
|---------|---------|
| `disabled={enhanceState.status === "loading"}`（仅 loading 禁用） | 默认态断言 `element_enabled` + `element_id`；loading 态断言 `element_disabled` |
| 空描述点击 → handler `setDescError(true); return;`（按钮可点击） | `element_enabled` + `element_id` + `text_exists`（真实错误文案）——**禁止**断言「disabled」「无任何效果」 |
| `disabled={isSaving}`（提交保存中禁用） | 保存中 `element_disabled`；空闲 `element_enabled` |
| 交互意图（「按钮可点击」「点击后应触发动作」） | `element_clickable` + `element_id`；纯可见性 / 错误消息出现 → `element_visible` + `element_id` |

---

## 8. _meta 字段规范

## 8. _meta 字段规范

### 8.1 必填 _meta 字段

| 字段 | 说明 |
|------|------|
| `source_requirement` / `source_requirements` | 来源需求 ID |
| `test_point` / `test_points_covered` | 覆盖的测试点 |
| `priority` | P0 / P1 / P2 |
| `mcp_tool` | 执行工具名 |
| `generated_by` | 生成技能名 |
| `generated_at` | 生成日期 |
| `validated` | 验证状态：`true` / `"static_only"` / `"skipped:<reason>"` |

### 8.2 禁止事项

- `_meta` 中不得有 `{{...}}` 占位符残留
- `_meta` 中不得有未解析的模板变量
- 所有 `_meta` 字段必须有实际值（不得为空字符串）

---

## 9. 生成后自检 Checklist

**每个生成的测试文件必须通过以下全部检查，任何一条失败 = 文件无效，不得写入。**

### 9.1 通用检查（所有类型）

| # | 检查项 | 失败条件 |
|---|--------|----------|
| 1 | JSON 合法性 | 文件不是合法 JSON |
| 2 | type 分类正确 | type 值与实际步骤结构不匹配 |
| 3 | auth_system 存在 | 顶层缺少 auth_system 字段或为空 |
| 4 | auth_role 存在 | 顶层缺少 auth_role 字段或为空 |
| 5 | _meta 完整 | _meta 中有空字段或 `{{...}}` 残留 |
| 6 | validated 字段 | 缺少 `_meta.validated` 字段 |

### 9.2 API/E2E 专用检查

| # | 检查项 | 失败条件 |
|---|--------|----------|
| 7 | Auth headers | 任何 step 的 headers 缺少 `Authorization: Bearer {{token}}` |
| 8 | headers 格式 | headers 不是 JSON 字符串（是对象则失败） |
| 9 | body 格式 | body 不是 JSON 字符串且不是 null |
| 10 | URL 完整 | url 不以 `http://` 或 `https://` 开头 |
| 11 | 无非法变量 | 存在未声明的 `{{...}}` 变量（除 token 和 extract 产出） |
| 12 | assert 存在 | 任何 step 缺少 assert 数组或 assert 为空 |
| 13 | name 存在 | 任何 step 缺少 name 字段 |
| 18 | 断言字段无 {{var}} | assert[].expected / assert[].path / extract[].path 含 {{...}}（db_verify.conditions[].value 除外） |
| 19 | 无 unverified 断言 | 任何 assert[].path / extract[].path / extract_field / verify_field / semantic_expect.path 命中 `_meta.path_unverified` |

### 9.3 E2E 专用检查

| # | 检查项 | 失败条件 |
|---|--------|----------|
| 14 | 步骤数 | 业务步骤 < 2（auth_system 模式） |
| 15 | 变量传递 | step N 使用 `{{var}}` 但前序无 extract 定义 |
| 16 | Cleanup | 有 POST 创建但无对应 cleanup |
| 17 | 拓扑序 | 步骤顺序违反 depends_on 关系 |

### 9.4 UI 专用检查

| # | 检查项 | 失败条件 |
|---|--------|----------|
| 14 | 步骤数 | auth_system 模式 < 2；内联登录模式 < 4 |
| 15 | description 非空 | 任何 step 的 description 为空 |
| 16 | target 非空 | 任何 step 的 target 为空 |
| 17 | URL 完整 | url 不以 `http://` 开头或含占位符 |
| 18 | 无硬编码 ID | URL 中有 UUID/纯数字 ID 未用 `{{VAR}}` 包裹 |
| 19 | 语言一致 | target 文本语言与 DEFAULT_LOCALE 不一致；或验证/错误消息断言用了 `text_exists`+locale 字符串 而非 `element_visible`+`{prefix}-error-{field}` locator；或真实文本断言 i18n key 未按 `locales_dir/<default_locale>/<ns>.json` 解析（禁止猜语言 / 禁止静默 zh 兜底 — 解析失败 → 优先 `data-testid` 断言，无法避免可见文本断言时标 `_meta.validation_warnings:["locale_unknown"]`） |
| 20 | 业务闭环 | 写入操作缺少最终业务结果验证 |
| 21 | 状态断言用状态 check | 描述声称 disabled/enabled/可点击 的 expected_result 使用 `element_visible`/`text_exists` 等非状态 check |
| 22 | 状态 check 带 element_id | `element_disabled`/`element_enabled`/`element_clickable` 缺少 `expected_results[].element_id` |
| 23 | element_id 存在且与源码一致 | element_id 的 data-testid 不在前端源码，或状态与源码不符（无 disabled= 却断言 disabled / 无条件禁用却断言 enabled） |
| 24 | 源码证据留痕 | 状态 check 的 element_id 缺 `_meta.code_evidence[<element_id>]` 条目 |
| 25 | 无空值断言 | text 类 check（text_exists / url_contains）的 `value`/`keyword`/`text`/`selector`/`content` 全缺；或 element_* check（element_visible / element_hidden / element_disabled / element_enabled / element_clickable）未携带 `element_id` 且 value 类字段全缺（element_* 携带 `element_id` 时豁免 — 按 element_id 定位，value 可省略，仅放人眼可见文本） |
| 26 | ROUTE-CONSISTENCY | 任何 `expected_results` 的 `element_id` 不属于 **END-STATE 页面**（流程**最后一页**，expected_results 只在该页评估一次；多路由流程 ≠ `url` 入口页）上真实存在的 data-testid（对照该页 page-doc 元素清单 / 变更组件；只存在于流程前序页面或其他路由的 testid = WRONG-ROUTE 断言，必挂 'Element not found'） |
| 27 | 动态值禁止 text 断言 | 对预填/回填字段内容、placeholder 文本、data-dependent 动态值用 `text_exists` 断言具体文本（应为 `element_visible` + 该字段 data-testid 的 `element_id`，仅证明渲染/可见，不校验内容） |
| 28 | target 非 testid 形式未标记 no_testid | target 非 testid 形式且未标记 `no_testid` → REJECT（可见文本 target 只在元素无 testid + 已前置可见步骤 + 标记 no_testid 时合法） |
| 29 | 前缀 target 多匹配歧义 | 前缀 target 在页面上可能多匹配（同家族多个元素）而未收窄到唯一（无唯一容器/更长前缀/显式 `.first`）→ 生成时需收窄，否则 runner 抛歧义错 |
| 30 | 前缀 element_id 多匹配歧义 | 前缀 element_id 在页面上可能多匹配（同家族多个元素）而未收窄到唯一 → 生成时需收窄（仅上下文中唯一时可用前缀） |
| 31 | 裸动态家族 stem 禁作 element_id | 任何 element_* check 的 `element_id` 是**裸动态家族 stem**（如 `pm-web-agent-card-link-name-`，不带 `[data-testid^='...']` 包裹）→ REJECT（runner 视为精确字面量，动态家族永远带 `-${id}` 后缀渲染，精确字面量永远匹配不到；必须用包裹前缀形式 `[data-testid^='stem-']`） |
| 32 | 条件性不存在带 expect_absent | 任何 `element_hidden` 断言声称「不渲染 / 仅创建模式 / 条件性不存在」但**未**携带 `expect_absent:true` → REJECT（语义只塞 description = 引擎不消费，必判 failed） |
| 33 | 禁止不支持字段 | 任何 `expected_results` 条目携带 `element_state` / `multi_action` / `step` / `when` / `condition` → REJECT（引擎零命中这些字段；disabled 语义用 `element_disabled`/`element_enabled`，多动作用 §6.3 一步一动作展开） |
| 34 | expected_results 最终态自洽 | `expected_results` 集合在单一最终态下**逻辑互斥**（如「step3 后 hidden + step4 后 visible」「先出现后消失」→ 最终态自相矛盾）→ REJECT（框架只评估一次最终态；时序断言拆成自洽独立用例或降级为步骤级 expect/wait_for） |

> **流程覆盖检查（警告级，非 REJECT）** — 页面是流程参与者（页面文档 用户操作流"跳转目标"列非空 / FLOW-INDEX 标记 entry|intermediate|exit）时，该模块产物应至少 1 个 `_meta.flow:true` 的 full_flow 测试覆盖其参与的流程（按 `flow_id`）。缺失 → 生成器（gen-tests-ui Step 6b）标记 `_meta.validation_warnings: ["missing_flow_test::<page>"]`。**warning 级**：不使文件无效，与 `route_not_in_kb` 同级。数据驱动：仅当流程数据存在时检查，避免过渡期存量模块（无跳转目标列）误伤。

### 9.5 外部依赖 / LLM 步骤专用检查（所有类型）

测试步骤命中 **LLM 背书或外部 API 端点**（如 `enhance-description` → ChatOpenAI → 上游 LLM 网关）时，该步骤**必须有优雅逃生通道** —— 禁止把外部依赖当作应用回归的硬性前提；下游错误串（`Connection error.` / `AI 增强失败` / 上游超时）属于 **external dependency failure**（外部依赖失败），**不是** BUSINESS_BUG / 应用回归。

| # | 检查项 | 失败条件 |
|---|--------|----------|
| 1 | 外部依赖步骤必须有逃生通道 | LLM/外部 API 步骤未提供以下任一逃生通道：**(a)** soft/可选步骤 — 断言文档化的降级 UI（错误提示 + Retry，如 `{prefix}-error-{field}` / `btn-enhance-retry`，保留原文、不阻断后续编辑/提交）；**(b)** 步骤级有界重试/等待 — step 内轮询/重试配合 `options.max_retry`，而非 `fail_if_not_appear` 立即判死；**(c)** 外部依赖分类 — `_meta` 标注 flaky / 降级优先级，**不得**作为硬性 P0/P1 应用回归门禁 |
| 2 | 禁止硬门禁外部依赖 | 无上述逃生通道时，仍用 `fail_if_not_appear`（或 API/E2E 硬断言）把 LLM/外部 API 步骤硬门禁为 P0/P1 应用回归 → REJECT |
| 3 | 外部错误归类 | 把下游错误串（`Connection error.` / `AI 增强失败` / 上游超时）归为 BUSINESS_BUG / 应用回归 — 它们属于 **external dependency failure**（外部依赖失败），应按环境/外部依赖处理 |

---

## 10. 违规处理

1. **自检失败的文件不得写入磁盘** — 必须修复后重试
2. **自检通过但 dry-run 发现不匹配** — 以 dry-run 结果为准自动修正
3. **修正后再次自检** — 确保修正没有引入新违规
4. **3 次修正仍失败** — 标记为 `_validation: "failed:exceeded_retry"` 并报告

---

## Changelog

- 本规范正文为唯一事实来源；逐日变更历史不随公开发布物分发。
