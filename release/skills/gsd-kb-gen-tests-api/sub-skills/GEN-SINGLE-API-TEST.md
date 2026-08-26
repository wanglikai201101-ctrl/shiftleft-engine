# Sub-skill: Generate Single API Test Case

> 🔒 **OUTPUT SPEC ENFORCEMENT:** 本 sub-skill 的所有输出必须符合 `skills/TEST-OUTPUT-SPEC.md`。
> 关键约束：headers/body 必须是 JSON 字符串（不是对象）；所有 step headers 必须含 Authorization；
> 断言必须基于事实来源；禁止未声明的 {{...}} 变量。

## Purpose

Generate ONE API test case JSON file by reading the template and replacing ALL placeholders with content derived from KB documentation (API docs + REQ docs + graph.json).

## Input (provided by orchestrator)

1. **Template** — API-TEST-TEMPLATE.json content
2. **API doc** — the target API's full documentation (测试断言, 请求参数, 响应结构, 错误码, 请求/响应示例)
3. **TP info** — test point ID, description, depends_on, DB断言
4. **ENV-CONFIG** — resolved auth credentials and base URL
5. **Graph edges** — writes_to/reads_from for DB enrichment
6. **SOURCE_FACTS** (optional) — extracted from source code by Step 4a-2, contains:
   - `validation_engine`: "pydantic" | "manual" | "mixed"
   - `error_responses[]`: actual status codes and detail structures from source code
   - `source_file`: path to the router/controller file
   - `confidence`: "high" (from source) | "low" (inferred)
   - When present, SOURCE_FACTS takes priority over KB doc for error assertions
7. **ENVELOPE_ENTRY** (optional) — injected by orchestrator Step 2d.5 from ENVELOPE-INDEX.json (fresh verified 或 pre_probe 候选). Contains `list_path` / `item_id_path` / `item_fields` / `top_level_keys` / `conditional_fields` / `verified` / `pre_probe`. When present, assertion/extract JSONPaths MUST come from it (见「jsonpath 断言精度规则」), overriding API doc Response Schema; `verified:true` (fresh) 直接用，`pre_probe:true` 用其 list_path/top_level_keys 但标 `_meta.path_unverified:true`. `null` → fall back to API doc.

## Hard Rules

### Auth Header Enforcement

**When the test case declares `auth_system` at top level (i.e., auth_system mode is active), EVERY API step's `headers` object MUST include `"Authorization": "Bearer {{token}}"`.** No exceptions unless the step explicitly declares `"auth_required": false` (e.g., public health-check endpoints).

A step with `headers: "{}"` or `headers: {}` or missing the Authorization key is a generation FAILURE — the test will 401 at runtime.

This rule applies to:
- Main test steps
- Prerequisite steps
- SETUP seed steps
- Error scenario steps
- Boundary value steps
- ALL steps in the `steps` array without exception

### Precondition Route Gate（前置路由校验 — 路由缺失 → 不发射）

Before building the test, verify the target endpoint actually exists（平台可能未实现该流程）:

1. Look up the endpoint in `tests/ENVELOPE-INDEX.json` → `known_envelopes`（key 格式 `"{METHOD} /path"`，如 `"POST /api/v1/sandbox/build"`）
2. If absent, look up the KB doc `$OUTPUT/$MODULE/apis/{METHOD}-{path-stem}.md`（如 `POST-build.md`）
3. If both are missing or conflict, run a read-only probe: `curl -s -o /dev/null -w "%{http_code}" "<url>"` → 404/405 = route missing

**If the target route is missing → DO NOT emit a runnable test.** Instead return:
- `_meta.status: "pending"`
- `_meta.reason: "route_unavailable:<METHOD> <path>"`
(The orchestrator records it in the manifest `pending` array → pipeline report shows `Pending (route unavailable): {N}`.)

**Two distinct cases (HYBRID strategy):**
- **route-missing** → SKIP/pending（above）— 平台未实现，不发射
- **data-missing** → SEED — 平台已实现但空库：在 `{{PREREQUISITE_STEPS}}` 槽发射幂等 SETUP 种子步骤（Step 2），使测试自足

## Execution

### Step 1: Determine assertion source level

- Level 1: API doc has `## 测试断言` → use directly
- Level 2: API doc has `## 请求/响应示例` → derive assertions
- Level 3: Only `## 响应结构` exists → derive not_empty assertions
- Level 0 (no API doc provided): **按顺序尝试以下 fallback，找到即停止**：
  1. 从 router.py / controller 文件里的 Pydantic/Schema 模型提取字段名 → 继续生成，标注 `"doc_source": "router_fallback"` 到 `_meta`
  2. router.py 也找不到 → **HALT**，报错："缺少 API doc 且无法从源码提取字段名，无法生成测试用例"

### Step 2: Build prerequisites + SETUP seed step

From TP's 前置条件 + API path params:
- **数据前置 → 发射幂等 SETUP 种子步骤到 `{{PREREQUISITE_STEPS}}`（不是只声明 `resource_exists`）：** 若主测试的 path 含 `{id}` 且该 ID 非前序创建步骤产出（如 `PATCH /api/v1/sandbox/{agent_id}`），必须在模板 `steps` 的 `{{PREREQUISITE_STEPS}}` 槽填充幂等 SETUP 种子步骤（见下方固定模板），使测试自足、空库可跑、顺序无关。执行引擎在 pipeline 路径**忽略** `prerequisites` 字段直接执行 `steps[]`，所以造数据必须作为真实 step 放进 `steps[]`。
- Path has `{id}` not from prior step → `resource_exists` prerequisite **且** 发射 SETUP 步骤
- TP requires specific state → `state_reached` prerequisite
- Pure creation/list API → `prerequisites: []`，`{{PREREQUISITE_STEPS}}` 留空（自足，无 SETUP）

**SETUP 种子步骤固定模板（幂等 build-by-name — POST /api/v1/sandbox/build）：**

```json
{
  "type": "api",
  "name": "SETUP: 幂等创建/复用种子 Agent（build-by-name）",
  "request": {
    "url": "http://localhost:8000/api/v1/sandbox/build",
    "method": "POST",
    "headers": "{\"Authorization\": \"Bearer {{token}}\", \"Content-Type\": \"application/json\"}",
    "body": "{\"name\": \"qa-e2e-seed-{{SCENARIO_ID}}\"}"
  },
  "assert": [
    {"type": "status", "expected": 200},
    {"type": "not_empty", "path": "$.id"}
  ],
  "extract": [
    {"name": "agent_id", "source": "jsonpath", "path": "$.id"},
    {"name": "agent_name", "source": "jsonpath", "path": "$.name"}
  ]
}
```

- **幂等契约：** 种子名 `qa-e2e-seed-<scenario_id>` 场景唯一；后端按 (name + created_by + status running/ready) **build-by-name 幂等复用**——同名 running/ready agent 直接返回，空库自动创建，重跑不重复造数、顺序无关。
- **后端契约：** `POST /api/v1/sandbox/build`，body `{"name": "..."}`，200 返回 `{id, name, status, version, sandbox_id, a2a_endpoint}`（`AgentResponse`）。
- 主测试步骤消费 SETUP extract 的 `{{agent_id}}` / `{{agent_name}}`。
- `prerequisites[].resource_exists` **补声明**（供交互式 LIST→CHECK→SATISFY→VERIFY 路径使用）：`satisfy_endpoint`（= build 端点）、`satisfy_body`（= 种子 body）、`verify_field`（= "$.id"）——均为可选字段，`{{SCENARIO_ID}}` 生成期替换，非运行时变量。

### Step 3: Build steps

**认证方式（二选一，由 ENV-CONFIG 决定）：**

- **auth_system 模式（推荐）**：如果 ENV-CONFIG 中有 `auth.system` 字段：
  - 模板顶层填充 `"auth_system": "{system_name}"` 和 `"auth_role": "{role}"`
  - steps 数组**不生成登录步骤**
  - Auth Agent 自动注入 token 到请求 headers
  - 业务步骤 headers 中仍使用 `"Authorization": "Bearer {{token}}"` — token 由运行时注入

- **内联登录模式（兼容旧流程）**：如果 ENV-CONFIG 没有 `auth.system`：
  - step 0 为登录步骤（POST login 获取 token）
  - 登录 body 的凭证字段名从 `LOGIN_BODY_FIELD`（ENV-CONFIG `auth.login_body_field`）读取，默认 "email"
  - 后续步骤通过 `{{token}}` 引用

**auth_system 模式下的 steps 构建：**
1. **Prerequisite steps** (if depends_on) — extract IDs from depended APIs; 数据前置场景在此槽填充 SETUP 种子步骤（Step 2 固定模板）
2. **Main test step**:
   - `url`: 从 ENV-CONFIG 读取 `environment.backend_url` + `environment.api_prefix` + path，直接拼接为完整 URL（如 `http://localhost:8000/api/v1/agents`）。**禁止使用 `{{BASE_URL}}` 等占位符**。path params 用 `{{variable}}` 格式仅限 extract 提取的运行时变量
   - `method`: from API doc 基本信息
   - `headers`: `{"Authorization": "Bearer {{token}}", "Content-Type": "application/json"}`
   - `body`：按以下优先级提取请求体字段名，**禁止**凭接口语义或经验推断：
     1. API doc 的 `## Request Schema` 章节（结构化 JSON schema + 字段表）— **首选，最准确**
     2. API doc 的 `## 请求参数` 章节（筛选 来源 含 "用户输入" 的 body 字段）
     3. `TECH-*.md` 里该接口的调用描述（格式如 `POST /path { field1, field2 }`）
     4. router.py / controller 文件里的 Pydantic/Schema 模型定义
     以上四级都找不到 → HALT，不生成该用例
     
     **Request Schema 使用规则：**
     - 如果 `## Request Schema` 存在且非 `_no_request_body: true` 且非 `_schema_unverified: true`：
       - 从 JSON schema block 中提取完整字段结构
       - Required 字段全部填充有意义的测试值
       - Optional 字段按测试场景需要选择性填充
       - 字段名必须与 schema 中定义的完全一致（区分大小写）
     - 如果 `_schema_unverified: true`：降级到优先级 2（请求参数表）
     - 如果 `_no_request_body: true`：body 为 null/空（GET/DELETE 无 body）
   - `extract`: from 变量提取表
   - `assert`: convert from 测试断言 table

**内联登录模式下的 steps 构建：**
1. **Login step** (always first) — resolve from ENV-CONFIG
2. **Prerequisite steps** (if depends_on) — extract IDs from depended APIs; 数据前置场景在此槽填充 SETUP 种子步骤（Step 2 固定模板）
3. **Main test step**:
   - `url`: 从 ENV-CONFIG 读取 `environment.backend_url` + `environment.api_prefix` + path，直接拼接为完整 URL（如 `http://localhost:8000/api/v1/auth/login`）。**禁止使用 `{{BASE_URL}}` 等占位符**。path params 用 `{{variable}}` 格式仅限 extract 提取的运行时变量
   - `method`: from API doc 基本信息
   - `headers`: `{"Authorization": "Bearer {{token}}", "Content-Type": "application/json"}`
   - `body`：按以下优先级提取请求体字段名，**禁止**凭接口语义或经验推断：
     1. API doc 的 `## Request Schema` 章节（结构化 JSON schema + 字段表）— **首选，最准确**
     2. API doc 的 `## 请求参数` 章节（筛选 来源 含 "用户输入" 的 body 字段）
     3. `TECH-*.md` 里该接口的调用描述（格式如 `POST /path { field1, field2 }`）
     4. router.py / controller 文件里的 Pydantic/Schema 模型定义
     以上四级都找不到 → HALT，不生成该用例
     
     **Request Schema 使用规则：**
     - 如果 `## Request Schema` 存在且非 `_no_request_body: true` 且非 `_schema_unverified: true`：
       - 从 JSON schema block 中提取完整字段结构
       - Required 字段全部填充有意义的测试值
       - Optional 字段按测试场景需要选择性填充
       - 字段名必须与 schema 中定义的完全一致（区分大小写）
     - 如果 `_schema_unverified: true`：降级到优先级 2（请求参数表）
     - 如果 `_no_request_body: true`：body 为 null/空（GET/DELETE 无 body）
   - `extract`: from 变量提取表
   - `assert`: convert from 测试断言 table

### jsonpath 断言精度规则

**ENVELOPE 优先（覆盖下面 Top-level structure 表）：**
1. 若 orchestrator 注入了 `ENVELOPE_ENTRY` 且 `verified:true`（fresh）→ 断言/extract 路径**必须**从 envelope 取，不用 API doc 的 Response Schema：
   - 列表接口（entry.list_path 非空，如 `$.items`）→ `not_empty($.<list_path>)` + 字段用 `item_fields`（如 `$.items[0].id`）；`item_id_path` 若给出则用它的精确形式。
   - 单对象接口（无 list_path）→ 直接用 `top_level_keys`（如 `$.id`、`$.status`）。
   - `conditional_fields`（数据依赖字段，如 description）只能在探针确认过该数据存在时才断言；否则不产出断言，标注 `_unverified`。
2. 若 `ENVELOPE_ENTRY` 为 `pre_probe:true`（`verified:false`，来自 Step 1.5 前置探针 route/KB 推导，尚未实测）→ **可**用其 list_path 或 top_level_keys 作为断言 jsonpath 依据（比 API doc 猜 `$.data` 更准），但**必须**：
   - 在 `_meta` 记录 `"envelope_source": "pre-probe"` + `"_meta.path_unverified": true`（直到 regression 实测复核翻转 verified）。
   - **list_path 非空** → 列表断言用 `$.{list_path}`（如 `$.items` / `$.data.items`），字段取 `item_fields` 或 `$.<list_path>[0].<key>`。
   - **list_path 空但有 top_level_keys**（单对象响应）→ 单对象断言用 `$.{top_level_keys[0]}` 等顶层字段（如 `$.id`、`$.status`），不猜 `$.data`；`_meta.envelope_source: "pre-probe"` 语义保持不变。
   - **两者都没有**（list_path 空且 top_level_keys 空/不存在）→ 回退 API doc（`_meta.envelope_source: "api-doc"`）。
   - 不产出基于 conditional_fields 的断言（未实测，禁止猜）。
3. 无 ENVELOPE_ENTRY 或非 fresh → 回退下方 API doc `## Response Schema` 的 Top-level structure 表。
4. 每次生成在 `_meta` 记录 `"envelope_source": "envelope-index"`（用了 envelope）/ `"pre-probe"`（用了前置探针）/ `"api-doc"`（回退）。
5. 冲突铁律：envelope（真实探针回写）与 API doc 冲突 → **永远以 envelope 为准**。

**断言的 `path` 必须基于 API doc 中 `## Response Schema` 的 Top-level structure：**

| Top-level structure | path 前缀 | 示例 |
|--------------------|-----------| -----|
| OBJECT | `$` | `$.id`, `$.name`, `$.enhanced_description` |
| ARRAY | `$[0]` | `$[0].id`, `$[0].name` |
| PAGINATED | `$.data[0]` | `$.data[0].id`, `$.data[0].name` |
| WRAPPED | `$.data` | `$.data.id`, `$.data.name` |

**规则：**
1. 先查 `## Response Schema` 的 Top-level structure 字段
2. 根据结构类型确定前缀
3. 拼接具体字段路径（从 schema 的字段表中选取关键字段）
4. `not_empty` 断言用最精确的路径：
   - ARRAY → `not_empty($)` 检查数组非空，再 `not_empty($[0].id)` 检查有内容
   - OBJECT → `not_empty($.key_field)` 检查关键字段
   - PAGINATED → `not_empty($.data[0].id)` 检查分页数据有内容
   - WRAPPED → `not_empty($.data.key_field)` 检查包裹内容
5. 禁止使用 `not_empty($)` 对 OBJECT 类型（对象永远非空，该断言无意义）
6. 禁止在列表响应上用 `$.field`（列表根级没有字段，必须用 `$[0].field` 或 `$.data[0].field`）

**如果 API doc 没有 Response Schema section：** 从源码 grep response_model 获取顶层结构信息，标记为 unverified。如果完全无法确定，降级为 `## 响应结构` 表中的 JSONPath（但需验证其前缀是否正确）。

### Step 4: Convert assertions

| Doc format | 执行引擎 format |
|------------|-----------------|
| `not_empty` | `{"type": "not_empty", "path": "$.xxx"}` |
| `jsonpath` + operator | `{"type": "jsonpath", "path": "$.xxx", "operator": ">=", "expected": 10}` |
| `status` | `{"type": "status", "expected": N}` |
| `response_time` | `{"type": "response_time", "max_ms": N}` |
| `regex` | `{"type": "regex", "pattern": "...", "field": "body_text"}` |
| `array` | `{"type": "array", "path": "$.items", "check": "length", "expected": N}` |
| `body_contains` | `{"type": "body_contains", "expected": "关键文本"}` |

**`body_contains` parameter rule:** Always use `expected` as the parameter name. Do NOT use `text` or `value` — the dispatcher accepts all three but generation MUST use `expected` for consistency with other assertion types.

### SSE / Streaming Endpoint Assertion Rules

For SSE (Server-Sent Events) or streaming endpoints, the HTTPClient parses SSE frames and returns concatenated pure content (not raw SSE frames like `data: ...`).

**How to detect SSE endpoints:**
- Endpoint path contains "stream" (e.g. `/api/v1/chat/stream`)
- Response Content-Type is `text/event-stream`
- API doc mentions SSE, streaming, or EventSource

**Correct assertions for SSE endpoints:**
- `{"type": "not_empty", "path": "$"}` — verify response has content
- `{"type": "body_contains", "expected": "关键业务词"}` — verify content contains expected business text

**WRONG (do NOT use):**
- `{"type": "body_contains", "expected": "data:"}` — raw SSE frame prefix is stripped by HTTPClient
- `{"type": "regex", "pattern": "^data:", "field": "body_text"}` — same reason, body is pure content

**Default assertions (every test must have):**
1. `{"type": "status", "expected": 200}`
2. `{"type": "response_time", "max_ms": 3000}`

**[推断] handling:** Use `"operator": "in"` with range (e.g. `[400, 422]`)

### Step 5: Generate error scenario variant

For each error in 异常场景断言 table (top 3):
- Construct request that triggers the error
- Assert the expected status code + error message

**🔒 Source-facts priority rule (when SOURCE_FACTS provided in context):**

When the orchestrator provides `SOURCE_FACTS` in the agent context, error scenario assertions MUST follow source-code facts over KB documentation:

| Conflict | Resolution |
|----------|-----------|
| KB says `status: 400`, source_facts says `status: 422` | Use `422` |
| KB says `$.detail == "error message"`, source says detail is array | Use `$.detail[0].msg` |
| KB says "required field missing → 400", source shows Pydantic auto-validation | Use `422` + Pydantic error structure |
| Source_facts not available (no source code found) | Use KB doc value but mark `[推断]` → use `"operator": "in", "expected": [400, 422]` |

**Error response structure patterns (from source_facts.validation_engine):**

| validation_engine | Status | detail structure | JSONPath pattern |
|-------------------|--------|-----------------|-----------------|
| `pydantic` | 422 | `[{"loc":[], "msg":"...", "type":"..."}]` | `$.detail[0].msg` |
| `manual` | varies (from HTTPException) | string or custom object | `$.detail` or `$.detail.message` |
| `mixed` | 422 for validation, custom for business logic | depends on trigger | check source_facts.error_responses per trigger |

**示例 — KB 文档写 400 但源码是 Pydantic 校验：**
```json
// KB doc 异常场景断言: "必填字段缺失 → 400"
// source_facts: {"validation_engine": "pydantic", "error_responses": [{"trigger": "missing required field", "status": 422, ...}]}
// 生成的断言（以 source_facts 为准）:
{"type": "status", "expected": 422}
{"type": "jsonpath", "path": "$.detail[0].msg", "operator": "equals", "expected": "Field required"}
```

### Step 6: Generate boundary value variant

From 边界值断言 table (at least 3):
- Each boundary condition → separate test or step

### Step 7: Self-validate

1. Output is valid JSON (parseable)
2. All `{{ENV}}` single-brace resolved to actual values
3. Only `{{variable}}` double-brace remain (runtime inter-step passing)
4. `steps` array has >= 1 entry (auth_system mode: main step only) or >= 2 entries (inline login mode: login + main)
5. Main step has >= 2 assertions
6. `_meta` fields all populated
7. If `auth_system` is set → no login step in `steps`; if not set → login step present as step 0
8. **Auth header check:** If top-level `auth_system` is declared, EVERY step in `steps` array MUST have `headers` containing `"Authorization": "Bearer {{token}}"`. Any step missing this header → REJECT output, fix and regenerate.
9. **`_meta.scenario_id` 必填非空** — 等于场景 id（SCENARIO_ID），作为幂等续跑键（Step 4b 跳过判断依赖它；重复运行跳过已生成场景，不覆盖已有产物）。缺失 = 生成失败，必须补写后重验。
10. **SETUP seed check:** 需要已存在资源的测试（path param 非前序创建步骤产出）→ `{{PREREQUISITE_STEPS}}` 槽必须含幂等 SETUP 种子步骤（`POST .../api/v1/sandbox/build`，body name=`qa-e2e-seed-<scenario_id>`），且其 extract 供应下游 path param；缺失 → REJECT（禁止只声明 resource_exists 不发射 SETUP）。
11. **Route gate:** 目标 endpoint 路由缺失（ENVELOPE-INDEX/KB/探针）→ 不发射，返回 `_meta.status: "pending"` + `_meta.reason: "route_unavailable:<METHOD> <path>"`。

## Output

Valid JSON file content — ready to write to `tests/api/{filename}.json`.
