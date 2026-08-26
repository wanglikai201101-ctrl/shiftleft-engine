# Sub-skill: Generate Single E2E Test Case

> 🔒 **OUTPUT SPEC ENFORCEMENT:** 本 sub-skill 的所有输出必须符合 `skills/TEST-OUTPUT-SPEC.md`。
> 关键约束：headers/body 必须是 JSON 字符串（不是对象）；所有 step headers 必须含 Authorization；
> 变量传递必须连贯；cleanup 必须覆盖所有创建操作；断言必须基于事实来源。

## Purpose

Generate ONE E2E test case JSON by chaining multiple test points (from depends_on relationships) into a complete business scenario flow.

## Input (provided by orchestrator)

1. **Template** — E2E-TEST-TEMPLATE.json content
2. **TP chain** — topologically sorted test points with depends_on resolved
3. **API docs** — for each TP in chain, the corresponding API doc (基本信息, 测试断言, 变量提取)
4. **REQ doc** — edge cases table, fixtures
5. **ENV-CONFIG** — resolved auth credentials and base URL
6. **Graph edges** — depends_on (API→Job for async verification)
7. **Scenario** — scenario id / type / priority / description (SCENARIO_ID 必须写入 `_meta.scenario_id`，作为幂等续跑键)
8. **ENVELOPE_ENTRY** (optional) — injected by orchestrator Step 2d.5 from ENVELOPE-INDEX.json. Keyed map：key = `"{METHOD} /path"`，value = 该 endpoint 的 fresh verified envelope 条目（含 `list_path` / `item_id_path` / `item_fields` / `top_level_keys` / `conditional_fields` / `verified`）。某 endpoint 条目存在且 `verified:true`（fresh）→ 该 step 的断言/extract JSONPath 必须以它为准（见「jsonpath 断言精度规则」），覆盖 API doc Response Schema；key 缺失或非 fresh → 该 step 回退 API doc。链中无任何 fresh 条目 → `null`。
9. **MODE** (optional) — `"full"` 或 `"change-scope"`。change-scope 时触发 jsonpath 来源铁律（见下方「jsonpath 来源铁律（change-scope 模式）」）。

## Hard Rules

### Auth Header Enforcement

**When the test case declares `auth_system` at top level (i.e., auth_system mode is active), EVERY API step's `headers` object MUST include `"Authorization": "Bearer {{token}}"`.** No exceptions unless the step explicitly declares `"auth_required": false` (e.g., public health-check endpoints).

A step with `headers: "{}"` or `headers: {}` or missing the Authorization key is a generation FAILURE — the test will 401 at runtime.

This rule applies to:
- All business steps in the chain
- Prerequisite steps
- SETUP seed steps
- Verification steps
- ALL steps in the `steps` array without exception

### Precondition Route Gate（前置路由校验 — 路由缺失 → 不发射）

Before building the test, verify every endpoint in the chain actually exists（平台可能未实现该流程）:

1. Look up each endpoint in `tests/ENVELOPE-INDEX.json` → `known_envelopes`（key 格式 `"{METHOD} /path"`，如 `"GET /api/v1/sandbox"`）
2. If absent, look up the KB doc `$OUTPUT/$MODULE/apis/{METHOD}-{path-stem}.md`（如 `POST-build.md`）
3. If both are missing or conflict, run a read-only probe: `curl -s -o /dev/null -w "%{http_code}" "<url>"` → 404/405 = route missing

**If any required route is missing → DO NOT emit a runnable test.** Instead return:
- `_meta.status: "pending"`
- `_meta.reason: "route_unavailable:<METHOD> <path>"`
(The orchestrator records it in the manifest `pending` array → pipeline report shows `Pending (route unavailable): {N}`.)

**Two distinct cases (HYBRID strategy):**
- **route-missing** → SKIP/pending（above）— 平台未实现，不发射
- **data-missing** → SEED — 平台已实现但空库：发射幂等 SETUP 种子步骤（Step 2），使测试自足

## Execution

### Step 1: Build the chain

From topological sort of TPs:
- Each TP → one API step in the chain
- `depends_on` relationships define execution order
- Extract variables flow forward (step N extracts → step N+1 uses)
- **Route check per endpoint（见上方 Precondition Route Gate）：** 任一 endpoint 路由缺失 → 返回 `_meta.status: "pending"` + `_meta.reason: "route_unavailable:<METHOD> <path>"`，不发射测试。

### Step 2: Build prerequisites + SETUP seed step

From the chain's root TP (first in order):
- **数据前置 → 发射幂等 SETUP 种子步骤（不是只声明 `resource_exists`）——端点/契约可配置：** 若根流程需要已存在资源（path param 非前序创建步骤产出，如 `PATCH /api/v1/{resource}/{id}`），则**在 steps[] 首位 PREPEND 一个 SETUP 种子步骤**，使测试自足、空库可跑、顺序无关。执行引擎在 pipeline 路径**忽略** `prerequisites` 字段直接执行 `steps[]`，所以造数据必须作为真实 step 放进 `steps[]`。**SETUP 端点和 body schema 从 ENV-CONFIG 读取 `seed.endpoint` + `seed.payload_template`；ENV-CONFIG 未配置 `seed.endpoint` → 跳过 SETUP 步骤，只做通用测试生成，不生成任何项目的 sandbox/A2A 契约。**
- **自足链**（chain starts with creation，或链内已有创建步骤产出所需 ID）→ `prerequisites: []`，**无 SETUP 步骤**，保持原流程。
- 若 path param 需要但链内未产出：**`seed.endpoint` 已配置 → 必须发射 SETUP 步骤**（禁止仅声明 `resource_exists` 不造数）；**未配置 → 无 seed 可发，该场景标 `_meta.status: "pending"` + `_meta.reason: "seed_unavailable:<path param>"`，不发射可运行用例**（不得伪造任何项目 sandbox 契约）。

**SETUP 种子步骤模板（示例 — 参考 sandbox build-by-name 契约，来自 ENV-CONFIG 可配置；换项目必须用该项目实际 seed 端点/返回 envelope，禁止照抄 url/assert/extract）：**

```json
{
  "type": "api",
  "name": "SETUP: 幂等创建/复用种子资源（build-by-name 示例）",
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
    {"name": "seed_id", "source": "jsonpath", "path": "$.id"},
    {"name": "seed_name", "source": "jsonpath", "path": "$.name"}
  ]
}
```

- **实际生成铁律（示例非强制）：** `request.url` 必须取 ENV-CONFIG `seed.endpoint`（示例 URL 仅为参考，非真实端点），`body` 取 `seed.payload_template`；`assert`/`extract` 的 JSONPath 基于该项目 seed 返回的真实 envelope（探针/文档），`$.id`/`$.name` 仅为示例；`sandbox_id`/`a2a_endpoint` 是参考 sandbox 特有字段，目标项目无则不得引用。
- **幂等契约（示例约束，随项目 seed 语义调整）：** 种子名场景唯一（如 `qa-e2e-seed-<scenario_id>`）；后端按 (name + created_by + status) **build-by-name 幂等复用**——同名运行中资源直接返回，空库自动创建，重跑不重复造数、顺序无关。目标项目无 build-by-name 语义时，用其幂等造数方式替代。
- 后续步骤消费 SETUP extract 的 `{{seed_id}}` / `{{seed_name}}`；原"拉取列表取第一条"步骤**降级为验证步骤或删除**（禁止硬编码依赖已存在数据）。
- **cleanup 例外：** SETUP 造出的种子资源由幂等复用，**不 DELETE 种子**（删除会让后续重跑重新 build，违背幂等种子意图）。
- `prerequisites[].resource_exists` **补声明**（供交互式 LIST→CHECK→SATISFY→VERIFY 路径使用）——端点为**示例**，实际取 ENV-CONFIG `seed.endpoint` 与项目实际列表端点：
  ```json
  {
    "type": "resource_exists",
    "description": "由 steps[] 首位 SETUP 种子步骤满足（seed.endpoint 可配置）",
    "params": {
      "resource_type": "seed_resource",
      "list_endpoint": "http://localhost:8000/api/v1/sandbox?mine=true&limit=10",
      "list_filter": "$.items[?(@.status!='failed' && @.status!='deleted' && @.status!='terminated')]",
      "extract_field": "$.items[0].id",
      "satisfy_endpoint": "http://localhost:8000/api/v1/sandbox/build",
      "satisfy_body": "{\"name\": \"qa-e2e-seed-{{SCENARIO_ID}}\"}",
      "verify_field": "$.id"
    }
  }
  ```
  （`satisfy_endpoint` / `satisfy_body` / `verify_field` 均为可选字段，端点为参考示例；`{{SCENARIO_ID}}` 生成期替换，非运行时变量。）

### Step 3: Build steps array

**认证方式（二选一，由 ENV-CONFIG 决定）：**

- **auth_system 模式（推荐）**：如果 ENV-CONFIG 中有 `auth.system` 字段：
  - 模板顶层填充 `"auth_system": "{system_name}"` 和 `"auth_role": "{role}"`
  - steps 数组**不生成登录步骤**
  - Auth Agent 自动注入 token，业务步骤 headers 使用 `"Authorization": "Bearer {{token}}"`

- **内联登录模式（兼容旧流程）**：如果 ENV-CONFIG 没有 `auth.system`：
  - step 1 为登录步骤（POST login 获取 token）
  - 后续步骤通过 `{{token}}` 引用

**步骤构建（两种模式共用）：**

For each TP in chain order:
1. Read corresponding API doc
2. Build step:
   - `type`: "api" (or "db_verify" for DB assertion steps)
   - `name`: `"{N}. {TP描述}"`
   - `request`: 
     - `url`: 从 ENV-CONFIG 读取 `environment.backend_url` + `environment.api_prefix` + path，直接拼接为完整 URL（如 `http://localhost:8000/api/v1/agents`）。**禁止使用 `{{BASE_URL}}` 等占位符**。path params 用 `{{variable}}` 格式仅限 extract 提取的运行时变量
     - `method`: from API doc
     - `headers`: `{"Authorization": "Bearer {{token}}", "Content-Type": "application/json"}`
     - `body`: from 请求参数
   - `extract`: from 变量提取表 (pass to next steps) — **change-scope 模式：jsonpath 必须来自 verified 来源**（见「jsonpath 来源铁律（change-scope 模式）」），不得用 API doc 变量提取表推测路径
   - `assert`: from 正常场景断言表 — **change-scope 模式：断言路径同上，必须来自 verified 来源**

3. If TP mentions "等待" → insert `{"type": "wait", "seconds": 3}` between steps
4. If graph shows API triggers async job → add wait + verification step

### jsonpath 断言精度规则（ENVELOPE 优先）

**ENVELOPE 优先（覆盖 API doc `## Response Schema` / 断言表的路径猜测）：**

1. 若 orchestrator 注入了 `ENVELOPE_ENTRY`（keyed map，key = `"{METHOD} /path"`）：链中每个 step 的 endpoint，按 key 查找它的 envelope 条目；若条目存在且 `verified:true`（fresh）→ 该 step 的断言/extract 路径**必须**从 envelope 取，不用 API doc 的 Response Schema：
   - 列表接口（entry.list_path 非空，如 `$.items`）→ `not_empty($.<list_path>)` + 字段用 `item_fields`（如 `$.items[0].id`）；`item_id_path` 若给出则用它的精确形式。
   - 单对象接口（无 list_path）→ 直接用 `top_level_keys`（如 `$.id`、`$.status`）。
   - `conditional_fields`（数据依赖字段，如 description）只能在探针确认过该数据存在时才断言；否则不产出断言，标注 `_unverified`。
2. key 不存在（无 fresh 条目）→ 该 step 回退 API doc `## Response Schema` / 断言表的路径。
3. 每次生成在 `_meta` 记录 `"envelope_source": "envelope-index"`（链中任一 step 用了 envelope）或 `"envelope_source": "api-doc"`（全部回退）。
4. 冲突铁律：envelope（真实探针回写）与 API doc 冲突 → **永远以 envelope 为准**。

### 🔒 jsonpath 来源铁律（change-scope 模式）

**当 MODE=change-scope 时强制执行，违反 = 生成失败：**

1. 本测试的**每个 step** 的 assert/extract 的 jsonpath **必须**来自以下真实来源之一，**禁止 LLM 猜测 jsonpath / 禁止从 API doc 的 Response Schema 凭空推断路径**：
   - **(A) ENVELOPE-INDEX.json 中 verified:true 的条目**（由预探针真实解析写入；key = `"{METHOD} /path"`）—— orchestrator Step 2d.5 注入为 verified 的条目，直接使用其 `list_path` / `item_id_path` / `top_level_keys` / `item_fields`。
   - **(B) Step 2d 路由只读探测的真实响应**（探测返回 body 中真实存在的字段路径）—— 仅当 A 不可用时回退，且必须在探测时解析了真实响应 body。
   - **(C) Step 5b dry-run 的真实响应**（生成后校验阶段基于实际响应修正/重建路径）—— 仅用于 Step 5b 修正阶段，非初始生成来源。

2. **无 verified 来源处理：** 某 step 的 endpoint 没有任何 (A) 或 (B) 来源 → 该 step 的断言路径**不得产出**；标记 `_meta.path_unverified: true`。若该 step 是关键业务步骤且无任何可用真实来源 → **不发射可运行测试**，返回 `_meta.status: "pending"` + `_meta.reason: "jsonpath_unverified:<METHOD> <path>"`（与 route_unavailable 同等处理）。

3. **冲突铁律保持：** 真实响应（envelope/探测/dry-run）与 API doc 冲突 → **永远以真实响应为准**。

### Step 4: Build cleanup

For each POST step that creates a resource (extracts an ID):
- Add corresponding DELETE to cleanup array
- Use the extracted variable as ID
- If chain's last step IS the delete → cleanup = []

### Step 5: Generate rollback/consistency variant

If chain has a step whose API doc 错误码 includes 409/500/503:
- Generate variant: steps 1~N-1 normal → step N force-fail → verify consistency

### Step 6: Generate edge case variants

From REQ doc 边缘场景 table:
- Each edge case → independent E2E with steps constructing the failure condition
- Name: `E2E-{REQ}_EDGE-{scenario-slug}.json`

### Step 7: Self-validate

1. Output is valid JSON
2. Steps array has >= 2 entries (auth_system mode: at least 2 business steps, SETUP 计入) or >= 3 entries (inline login mode: login + at least 2 business steps)
3. Variable passing is consistent (extract in step N → use `{{var}}` in step N+1)
4. cleanup covers all created resources（SETUP 种子 Agent 幂等复用，不 DELETE 种子）
5. `_meta.test_points_covered` lists all TPs in chain
6. All single-brace `{ENV}` resolved; only double-brace `{{var}}` remain
7. If `auth_system` is set → no login step in `steps`; if not set → login step present as step 1
8. **Auth header check:** If top-level `auth_system` is declared, EVERY step in `steps` array MUST have `headers` containing `"Authorization": "Bearer {{token}}"`. Any step missing this header → REJECT output, fix and regenerate.
9. **`_meta.scenario_id` equals the provided SCENARIO_ID** — 幂等续跑键，orchestrator Step 4b 跳过判断依赖它。
10. **SETUP seed check:** 需要已存在资源的场景且 ENV-CONFIG 配置了 `seed.endpoint` → steps[0] 必须是 SETUP 种子步骤（url=`seed.endpoint`，body 遵循 `seed.payload_template`，name 示例 `qa-e2e-seed-<scenario_id>`），且其 extract 供应下游 path param；缺失 → REJECT（禁止只声明 resource_exists 不发射 SETUP）。ENV-CONFIG 未配置 `seed.endpoint` → 跳过 seed 检查（不强制 sandbox 契约；该场景按 Step 2「无 seed 可发」处理）。
11. **Route gate:** 若链中任一 endpoint 路由缺失（ENVELOPE-INDEX/KB/探针）→ 不发射，返回 `_meta.status: "pending"` + `_meta.reason: "route_unavailable:<METHOD> <path>"`。
12. **Change-scope jsonpath gate (MODE=change-scope):** 每个 step 的 assert/extract 路径必须来自 verified 来源（ENVELOPE-INDEX verified:true 条目 / Step 2d 探测真实响应 / Step 5b dry-run）。任何 step 的路径无 verified 来源却产出 → REJECT，删除断言路径并标 `_meta.path_unverified: true`；关键业务 step 无来源 → 整链 pending（`jsonpath_unverified:<METHOD> <path>`），不发射。

## Output

Valid JSON file content — ready to write to `tests/e2e/E2E-{REQ}_{scenario}.json`.
For edge cases: additional JSON files named `E2E-{REQ}_EDGE-{slug}.json`.
