---
name: gsd-kb-gen-tests-api
description: "Generate MCP-Ready API test cases: orchestrator + template-driven generation"
argument-hint: "--module <name> --output <path> [--req <REQ-ID>] [--force]"
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
- headers/body 必须是 **JSON 字符串**（不是 JSON 对象）— 执行引擎强制要求
- token 认证体系下，所有 API steps 必须带 `"Authorization": "Bearer {{token}}"`
- type 字段：API 测试统一为 `"api"`（无论单步还是多步 prerequisite + main）
- 禁止出现 `{{BASE_URL}}`/`{{AUTH_USERNAME}}` 等模板占位符 — 只允许 `{{token}}` 和 extract 产出的变量
- 断言必须基于源码事实或 dry-run 验证，不得基于文档猜测
- 每个 step 必须有 name + request(url/method/headers/body) + assert

**自检时必须执行 TEST-OUTPUT-SPEC.md 第 9 节全部检查项。**
</output-spec>

<critical-rules>
🚫 HALT — 逐条阅读以下规则，违反任何一条 = 输出无效，必须删除重做

1. 🚫 NEVER skip ENV-CONFIG loading — 没有 ENV-CONFIG 就不能生成任何测试
2. 🚫 NEVER generate test without 测试断言 source — 必须从 API doc 的断言表提取
3. 🚫 NEVER leave {{PLACEHOLDER}} in _meta fields — 所有 single-brace {ENV} 必须已解析
4. 🚫 NEVER skip boundary/error variants — 每个 API 至少 normal + top 3 error + 3 boundary
5. 🚫 NEVER spawn agent without inlining template + sub-skill content
6. 🚫 NEVER output file without self-validation pass
7. 🚫 NEVER hardcode auth tokens — 使用 auth_system/auth_role 声明，执行引擎自动注入认证
8. 🚫 NEVER output headers/body as JSON object — 必须是 JSON 字符串格式（执行引擎强制）
9. 🚫 NEVER use inferred assertions without marking — 无源码验证的断言必须标注 [推断] 并用 operator: "in"
10. 🚫 NEVER put {{var}} in assert.expected / assert.path / extract.path — 防御性策略（跨 runner 可移植 + 防执行引擎行为回退）：执行引擎现已在 assert.expected / assert.path 内替换 {{var}}，但 extract.path 仍不替换（内嵌 → 提取为空 → 下游变量链断裂）。统一禁止三类字段内嵌 {{var}}。需要回引前步变量的断言 → 先在前步用固定路径 extract（如 $.items[0].id），断言只比较固定字段；无法固定 → 删断言。
11. 🚫 NEVER end a run with zero test cases — 全量运行结束若 tests/api/ 下 0 个 API 测试文件（或枚举了场景但填充 0 产出）→ FAIL LOUDLY（零产出门禁，Step 6c）
12. 🚫 NEVER emit a runnable API test whose root flow needs pre-existing data without a SETUP seed step — 模板的 `{{PREREQUISITE_STEPS}}` 槽必须被幂等 SETUP 种子步骤填充（如 POST /api/v1/sandbox/build + name=qa-e2e-seed-<scenario_id>，build-by-name 幂等复用），禁止只声明 `resource_exists` 不造数
13. 🚫 NEVER emit a test for a route that doesn't exist — 路由缺失（ENVELOPE-INDEX 无 / KB apis/*.md 无 / 探针 404/405）→ 场景标 `_meta.status: "pending"` + `_meta.reason: "route_unavailable:<METHOD> <path>"`，不发射可运行用例，记录到 manifest（Step 2d / Step 6c Pending 计数）

每个 Step 完成后必须输出 checkpoint 标记，否则不得进入下一步。
</critical-rules>

<objective>
Orchestrate API test case generation by:
1. Collecting source docs (API docs 测试断言 + REQ test points + graph edges)
2. Resolving ENV-CONFIG for auth credentials
3. Spawning agents that fill API-TEST-TEMPLATE.json — not freeform generation
4. Generating error/boundary/idempotency variants

Each agent reads `templates/API-TEST-TEMPLATE.json` and `sub-skills/GEN-SINGLE-API-TEST.md`.
Output: MCP-Ready JSON files for the executor's api dispatch tool.
</objective>

<process>

## Step 1: Parse arguments + load ENV-CONFIG

Extract from `$ARGUMENTS`:
- `--module <name>` (required)
- `--output <path>` (optional, default: `.planning/ontology`)
- `--req <REQ-ID>` (optional): specific requirement only

Load `$OUTPUT/$MODULE/tests/ENV-CONFIG.json`:
- `AUTH_SYSTEM` — from `auth.system` (required — 执行引擎 handles auth injection)
- `AUTH_ROLE` — from `auth.role` (default: "admin")

Note: Tests use direct `http://localhost:3000` URLs instead of template variables. Containers auto-rewrite localhost to the actual service address at runtime.

Note: 执行引擎 handles authentication automatically based on `auth_system` and `auth_role` fields in the test case metadata. Generated tests do NOT include login steps.

```
✅ CHECKPOINT-1: ENV-CONFIG loaded
   MODULE: {name}
   AUTH_SYSTEM: {system_name}
   AUTH_ROLE: {role}
   如果 ENV-CONFIG.json 不存在 → STOP，报错退出
```

## Step 2: Collect source documents

### 2a: API docs with 测试断言
For each `$OUTPUT/$MODULE/apis/*.md`: extract:
- **Request Schema** (structured JSON schema — PRIMARY source for request body construction)
- 测试断言 tables (正常/异常/边界/变量提取)
- 请求/响应示例
- 基本信息 (method, path, description)
- 请求参数
- 错误码

**Request Schema extraction priority for body construction:**
1. `## Request Schema` section → parse JSON schema block + field table → use as authoritative body structure
2. If `_schema_unverified: true` or section missing → fall back to `## 请求参数` (filter body fields)
3. If neither available → fall back to source-code Pydantic model extraction (Step 4a-2)
4. All levels exhausted → HALT for that API

Assertion source levels:
- Level 1: has `## 测试断言` → use directly
- Level 2: has `## 请求/响应示例` → derive assertions
- Level 3: only `## 响应结构` → derive not_empty assertions (HALT — see gate below)
- Level 0: doc missing or empty → **fallback: read router.py Pydantic models (see below)**

**🔄 Level 0 Fallback — 从 router.py 提取真实字段名：**

当 API doc 完全缺失（Level 0）时，不得让 LLM 自由推断请求体字段名。必须执行以下 fallback 流程后再决定是否 HALT：

1. 在 `$SOURCE` 目录下查找与该 API endpoint 最匹配的 router 文件：
   ```bash
   grep -rl "@router\.(post|get|put|delete)" $SOURCE --include="*.py" | head -10
   ```
2. 在找到的 router 文件中，定位该 endpoint 的函数签名及其 Pydantic 模型参数：
   ```bash
   grep -A 30 "def <endpoint_function_name>" <router_file>
   ```
3. 追踪 Pydantic 模型定义，提取所有 `field_name: type` 声明（包括 Optional 字段）
4. 将提取到的字段名作为请求体字段名用于测试生成，并在 CHECKPOINT-2 中记录：
   `{api_name}: Level 0 (doc missing) → fallback from {router_file}:{ModelName} — fields: {field1, field2, ...}`
5. 如果 router 文件也找不到（grep 无结果），则执行 HALT：
   `缺少 API doc：{api_name}，无法生成可信测试，请先运行 kb-fill-apis`

**关键原则：fallback 只读 Pydantic 模型定义，不允许 LLM 凭经验推断字段名。提取结果必须来自源码。**

### 2b: Requirements (TP tables)
Load REQ docs → extract TPs with 验证方式 = "API", depends_on relationships.

### 2c: Graph edges
Load `graph/graph.json` → `writes_to` (for DB enrichment), `reads_from` (for regression pairs).

**🚫 HALT 条件（Level 0 或 Level 3 门控）：**

在输出 CHECKPOINT-2 之前，逐个检查每个 API doc 的文档级别：
- **Level 0**（文件不存在 / 文件为空 / 只有标题）：**立即 HALT**，输出错误：
  `缺少 API doc：{api_name}，无法生成可信测试，请先运行 kb-fill-apis`
- **Level 3**（只有 `## 响应结构` 但没有 `## 测试断言` 和 `## 请求/响应示例`）：**立即 HALT**，输出错误：
  `缺少 API doc：{api_name}（Level 3 — 文档质量不足），无法生成可信测试，请先运行 kb-fill-apis`

Level 3 文档没有断言来源，生成的测试用例全部依赖 LLM 推断，这会产生字段名错误、状态码错误的不可信测试。
**HALT 是硬性规则，不允许继续生成，不允许以 Level 3 为基础推导测试。**

如果所有 API doc 均为 Level 1 或 Level 2，继续输出 CHECKPOINT-2。

```
✅ CHECKPOINT-2: Source documents collected
   API docs found: {N} (list names)
   APIs with Level 1 assertions: {N}
   APIs with Level 2 (derived): {N}
   APIs with Level 3 (minimal): {N}  ← 若 N > 0 则已在上方 HALT
   API TPs found: {N} (list IDs)
   Graph edges loaded: {writes_to: N, reads_from: N}
```

## Step 1.5: 前置探针 — 从 route 文件 + KB doc 产出真实 envelope 索引

**目的：** 生成**之前**发现 API 端点并推导真实响应 envelope（list_path），让首遍断言就用 `$.items` / `$.data.items` 而非猜 `$.data`。这是生产端；Step 2d.5 是消费端。

**输入：**
- `$BACKEND`（后端源码树，含 route 定义；未显式提供时从 module/backend 探测）
- `$OUTPUT/$MODULE/apis/`（KB API doc 目录）
- `$OUTPUT/$MODULE/tests/`（输出目录）

**执行（内联探测规则，无外部脚本依赖——不调用任何 `scripts/...` 脚本，也不依赖本机路径）：**

1. **解析 ROUTES_DIR**：优先显式 `--backend`；否则从候选路径探测（`$MODULE_SRC`、`$OUTPUT/$MODULE`、`./backend`、`./server`、`./src` 中存在的第一个目录）；都没有 → 跳过探针。
2. **探测前置**：`$OUTPUT/$MODULE/apis`（KB API doc 目录）必须存在，才做 envelope 探测。
3. **内联探测规则（按以下规则直接执行，产出 envelope 索引）**：
   - 遍历 `ROUTES_DIR` 下 route 定义文件，提取端点清单：`grep -rEn "@router\.(get|post|put|delete|patch)" "$ROUTES_DIR" --include="*.py"`（其他框架等价：`@app.(get|post|...)`、`router.post(...)`、REST 注册表等），归一化为 `{METHOD} /path`；
   - 遍历 `$OUTPUT/$MODULE/apis/*.md`，从每个文档的响应结构 section 提取 `list_path`（如 `$.items` / `$.data.items`）与 `top_level_keys`；
   - 合并 route 端点与 KB 推导，写入 `$OUTPUT/$MODULE/tests/` 下的 envelope 索引：每个端点计 `pre_probe: true`、`verified: false`；
   - `log "Step 1.5: pre-probe wrote envelope index"`。
4. 任一前置缺失（无 ROUTES_DIR 或无 apis 目录）→ `log "warn: Step 1.5: no routes dir or no KB apis dir, envelope pre-probe skipped"`。

```
✅ CHECKPOINT-1.5: Pre-probe complete
   Routes dir: {path|none}
   Envelope index: {path|none (route/KB 缺失时跳过)}
   Endpoints discovered: {N|0}
   Envelope entries marked pre_probe (verified:false — 待 regression 实测复核)
```

> **契约（pre_probe）：** 探针从 route 文件 + KB doc 推导的 list_path / top_level_keys 是**未实测**的（`verified:false` + `pre_probe:true`）。Step 2d.5 会把这类条目注入为**候选**，断言 jsonpath 可用其 list_path（列表）或 top_level_keys（单对象）——比猜 `$.data` 准，但 `_meta.path_unverified:true`；regression 的 live envelope-validation 实测后翻转 `verified:true`。

## Step 2d: Precondition route gate（路由门禁 — 前置校验）

**目的：** 生成前校验每个目标 endpoint 的路由是否存在（平台可能未实现该流程）。两步分开：**路由缺失 = 平台未实现 → SKIP/pending；数据缺失 = 平台已实现但空库 → SEED**（Step 4b 填充 `{{PREREQUISITE_STEPS}}` 发射幂等 SETUP 种子步骤）。

**路由存在性来源（按优先级）：**
1. `$OUTPUT/$MODULE/tests/ENVELOPE-INDEX.json` 的 `known_envelopes`（key 格式 `"{METHOD} /path"`，如 `"POST /api/v1/sandbox/build"`）
2. KB `$OUTPUT/$MODULE/apis/*.md`（文件命名 `{METHOD}-{path-stem}.md`，如 `POST-build.md`）
3. （可选）只读探针：`curl -s -o /dev/null -w "%{http_code}" "<url>"` → 404/405 = 路由缺失（探针只读，不产生数据；仅当 manifest/KB 冲突或均缺失时使用）

**判定：**
- 目标 endpoint 存在 → 进入 Step 3/4a 正常枚举填充。
- endpoint 缺失（ENVELOPE-INDEX 无记录 / KB 无 doc / 探针返回 404/405）→ **该 API 所有场景标 pending**：
  - 场景 `_meta.status: "pending"`，`_meta.reason: "route_unavailable:<METHOD> <path>"`
  - **不发射可运行测试**（filler 不得收到该场景，Step 4b 跳过）
  - 记录到 `_manifest-{ApiStem}.json` 的 `pending` 数组（Step 4a 清单 schema 已含）：`{"id": "{scenario_id}", "type": "{type}", "reason": "route_unavailable:<METHOD> <path>"}`
  - `total_scenarios` **只计非 pending 场景**（Step 6c 零产出门禁的 `S` 不含 pending）

```
✅ CHECKPOINT-2d: Route gate complete
   Endpoints verified: {N} (ENVELOPE-INDEX: {a}, KB apis: {b}, probe: {c})
   Routes missing: {N} (list "<METHOD> <path>")
   Scenarios marked pending (route_unavailable): {N} → 不发射，记录到 manifest pending 数组
```

## Step 2d.5: Envelope 条目注入（ENVELOPE-INDEX → Filler Context）

**目的：** 把 ENVELOPE-INDEX.json 里的 **verified envelope**（真实响应结构）注入到 Step 4b 每个 Filler agent 的 Context，使断言/extract 的 JSONPath 以真实响应为准，而不是 API doc 的 Response Schema 猜测。

**读取来源（按优先级，找到即合并）：**
1. 模块索引：`$OUTPUT/$MODULE/tests/ENVELOPE-INDEX.json` → `known_envelopes`（key 格式 `"{METHOD} /path"`，如 `"GET /api/v1/sandbox"`）
2. 全局索引：ENV-CONFIG 或工作区配置声明的共享索引路径 → `known_envelopes`
（Step 1.5 前置探针已在生成前把真实 envelope 灌进索引，本步直接消费。）

**对 manifest 里每个目标 endpoint（每个 `known_envelopes` key 对应的端点）：**
1. 读取模块 + 全局 ENVELOPE-INDEX 的该端点条目（key = `"{METHOD} /path"`）。
2. **注入分级：**
   - **A. fresh verified 条目**：`verified:true` **且** `verified_at` 距今 <24h **且** `backend_fingerprint` 与当前后端一致。三者全满足 → 注入为 **verified**（`ENVELOPE_ENTRY: {entry}`，断言直接用，`_meta.path_unverified` 不设置）。
   - **B. pre_probe 条目**：`pre_probe:true`（`verified:false`，来自 Step 1.5 前置探针 route/KB 推导）→ 注入为 **候选**（`ENVELOPE_ENTRY: {entry}` + 标注 `pre_probe:true`）；Filler 用其 list_path 或 top_level_keys 作为 jsonpath 依据，但 `_meta` 记 `"envelope_source": "pre-probe"` + `"_meta.path_unverified": true`（待 regression 实测复核）。判定细分（按此顺序）：
     - **pre_probe 且 list_path 非空** → **列表断言依据**：Filler 用 `$.{list_path}`（如 `$.items` / `$.data.items`）。
     - **pre_probe 且 list_path 空但有 top_level_keys**（单对象响应）→ **单对象断言依据**：Filler 用 `$.{top_level_keys[0]}` 等顶层字段（如 `$.id`、`$.status`），不猜 `$.data`。
     - **两者都没有**（无 list_path 且无 top_level_keys）→ 回退 API doc，`ENVELOPE_ENTRY: null`。
   - **C. 不注入**：无条目 / verified:false 且非 pre_probe / stale verified / fingerprint 不匹配 → 该 endpoint 回退 API doc，`ENVELOPE_ENTRY: null`。
3. 每个 Filler 的 Context 注入格式（见 Step 4b `## Context:` 块）：
   ```
   ENVELOPE_ENTRY: {该 endpoint 的 envelope 条目 JSON，含 list_path / item_id_path / item_fields / top_level_keys / conditional_fields / verified / pre_probe；无注入 → null}
   ```
4. **冲突铁律：** envelope（真实探针回写）与 API doc 冲突 → **永远以 envelope 为准**。

```
✅ CHECKPOINT-2d.5: Envelope 条目注入完成
   Verified envelopes injected: {N}/{total} (fresh verified entries fed to fillers)
   Pre-probe list envelopes injected (path_unverified): {M} (Step 1.5 推导，list_path 非空 → 列表断言依据)
   Pre-probe single-object envelopes injected (path_unverified): {P} (Step 1.5 推导，list_path 空但有 top_level_keys → 单对象断言依据)
   Stale/missing（回退 API doc）: {K} (list "<METHOD> <path>" + reason: verified:false / verified_at 过期 / fingerprint 不匹配 / 无条目 / pre_probe 但 list_path 与 top_level_keys 都空)
```

## Step 3: Load template and sub-skill

```bash
SKILL_DIR=""
for candidate in \
  "$HOME/.claude/skills/gsd-kb-gen-tests-api" \
  "$(pwd)/skills/gsd-kb-gen-tests-api"; do
  if [ -f "$candidate/templates/API-TEST-TEMPLATE.json" ]; then
    SKILL_DIR="$candidate"
    break
  fi
done
```

Read `$SKILL_DIR/templates/API-TEST-TEMPLATE.json` → `$TEMPLATE`
Read `$SKILL_DIR/sub-skills/GEN-SINGLE-API-TEST.md` → `$SUB_SKILL`

```
✅ CHECKPOINT-3: Template + sub-skill loaded
   SKILL_DIR: {path}
   TEMPLATE: {first 50 chars}...
   SUB_SKILL: {first 50 chars}...
   如果任一为空 → STOP，报错退出
```

## Step 4a: Enumerate test scenarios (deterministic manifest)

**🔒 两阶段生成：先枚举清单，再逐个填充。AI 不能跳过清单中的任何场景。**

For each API doc, spawn a **Scenario Enumerator** agent that ONLY outputs a structured scenario manifest (not test cases). This agent analyzes the KB docs and deterministically lists ALL required test scenarios:

```
你是一个 API 测试场景枚举器。分析以下 KB 文档，列出该 API 所有必须生成的测试场景。

## 🚫 硬性约束
- 每种适用的测试类型必须至少有对应数量的场景
- 输出是 JSON 对象，不是测试用例本身
- 不要生成测试步骤或断言，只列出场景元数据

## 场景类型检查表（逐条扫描，有证据就必须产生对应场景）：

| # | 类型 | 触发证据（KB 文档中的信号） | 最少数量 |
|---|------|---------------------------|---------|
| 1 | normal | 正常场景断言 table rows | 1 |
| 2 | error | 异常场景断言 table — each error code | 1 per code (top 3) |
| 3 | boundary | 边界值断言 table — each param | 1 per param (min 3) |
| 4 | idempotency | POST endpoint without path param (creation) | 1 if applicable |

## 枚举规则：
- 扫描 正常场景断言 table → 至少 1 个 normal 场景
- 扫描 异常场景断言 table → 每个 error code 产生 1 个 error 场景（取 top 3）
- 扫描 边界值断言 table → 每个参数产生 1 个 boundary 场景（最少 3 个）
- 如果是 POST 且无 path param（创建接口）→ 产生 1 个 idempotency 场景
- **Step 2d 已标记 route_unavailable 的 API** → 场景**不放入 scenarios**，放入 `pending` 数组（`reason: "route_unavailable:<METHOD> <path>"`）；`total_scenarios` 只计非 pending 场景

---
## Context:
API_DOC: {full API doc content}
TP: {test point info}
GRAPH_EDGES: {relevant writes_to/reads_from}
```

**🔒 中间产物目录（所有枚举/清单中间产物统一写到此目录，禁止写入 `tests/api/` 等扫描目录）：**
- 目录：`$OUTPUT/$MODULE/tests/_scenarios/.gen/`（`_scenarios` 非 api/e2e/ui 扫描子目录，test-inventory 不会把它当测试用例）
- `_manifest-{ApiStem}.json` — 每 API 场景清单（本步骤产物；`_manifest-*` 前缀已由 test-inventory.sh skip 排除，天然不收录）
- 中间产物保留供溯源/重跑，**不删除**；但**绝不允许**写到 `tests/api/`、`tests/e2e/`、`tests/ui/` 下。

**Scenario Manifest Schema (强制):**
```json
{
  "type": "object",
  "properties": {
    "endpoint": { "type": "string" },
    "method": { "type": "string" },
    "total_scenarios": { "type": "integer", "minimum": 0, "description": "只计非 pending 场景（route_unavailable 的 API 不计入）" },
    "scenarios": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "type": { "type": "string", "enum": ["normal", "error", "boundary", "idempotency"] },
          "priority": { "type": "string", "enum": ["P0", "P1", "P2"] },
          "description": { "type": "string" },
          "error_code": { "type": "integer" },
          "boundary_param": { "type": "string" }
        },
        "required": ["id", "type", "priority", "description"]
      }
    },
    "pending": {
      "type": "array",
      "description": "Step 2d 路由门禁判定的不可用路由场景（不发射可运行用例；Step 6c 计为 Pending (route unavailable)）",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "type": { "type": "string" },
          "reason": { "type": "string", "pattern": "^route_unavailable:" }
        },
        "required": ["id", "type", "reason"]
      }
    },
    "evidence": {
      "type": "object",
      "properties": {
        "normal_assertions": { "type": "integer" },
        "error_codes": { "type": "integer" },
        "boundary_params": { "type": "integer" },
        "is_post_creation": { "type": "boolean" }
      }
    }
  },
  "required": ["endpoint", "method", "total_scenarios", "scenarios", "pending", "evidence"]
}
```

**Priority assignment (写入 scenario.priority):**
| Test type | Priority | Rationale |
|-----------|----------|-----------|
| Normal (happy path) | `P0` | 核心功能验证，必须最先执行 |
| Error (异常场景) | `P1` | 异常处理验证，happy path 通过后执行 |
| Boundary (边界值) | `P2` | 边界条件验证，最后执行 |
| Idempotency | `P2` | 幂等性验证，最后执行 |

**🔒 枚举归一化（CHECKPOINT-4a 验证第一步，先归一化再门控）：**

manifest 的 `scenario.type` 必须属于 4 个枚举值（normal / error / boundary / idempotency）。若枚举器输出非枚举值（LLM 漂移），**显式映射**而非裸 REJECT：

| 非枚举取值（枚举器输出） | 归一化到（枚举内） | 依据 |
|------------------------|-------------------|------|
| `validation_error` / `param_error` / `request_error` / `bad_request` / `schema_error` | `error` | 参数/校验/请求失败 → 异常路径 |
| `not_found` / `unauthorized` / `forbidden` / `conflict` | `error` | 业务错误码 → 异常路径 |
| `edge_case` / `boundary_value` / `limit_value` / `extreme` / `极端值` | `boundary` | 边界/极端输入 → 边界值场景 |
| `retry` / `duplicate` / `repeat` / `幂等` / `重复提交` | `idempotency` | 重试/重复/幂等语义 → 幂等性场景 |
| `success` / `happy_path` / `ok` / `成功路径` | `normal` | 成功路径 → 正常场景 |
| 其它未列出的非枚举值 | 按语义就近映射到 4 个枚举值之一 | 就近原则 |

**规则：** 先执行归一化映射 → 再跑下方最低数量门控。归一化后若场景仍无法归类到任何枚举值 → 才是 REJECT，重新枚举。**禁止裸 REJECT（会触发重枚举死循环）。**

**🔒 最低数量门控（CHECKPOINT-4a 验证，第二步，在归一化之后运行）：**
- `evidence.error_codes > 0` 但没有 `error` 类型场景 → REJECT，重新枚举
- `evidence.boundary_params > 0` 但没有 `boundary` 类型场景 → REJECT，重新枚举
- `evidence.is_post_creation == true` 但没有 `idempotency` 类型场景 → REJECT，重新枚举
- 必须至少有 1 个 `normal` 场景
- **门控只针对非 pending 场景**（`pending` 数组 = route_unavailable，不参与门控）。某 API 全部场景 pending → `scenarios` 可为空、`pending` 非空，跳过门控（Step 6c 按 Pending 计数，不 FAIL）。

```
✅ CHECKPOINT-4a: Scenario manifests generated
   APIs processed: {N}
   Total scenarios enumerated: {N}
   Pending (route unavailable): {P} — 不发射可运行用例，记录到 manifest pending 数组
   Per-API breakdown:
     {api_name}: {N} scenarios (normal:{n}, error:{e}, boundary:{b}, idempotent:{i}) + pending:{p}
   Evidence: {error_codes} error codes, {boundary_params} boundary params across all APIs
   Normalized: {N} off-enum types mapped (CHECKPOINT-4a 归一化表)
   Gate check: ALL passed / REJECTED {N} (re-enumerated)
```

## Step 4a-2: Source-code extraction for error scenarios (pre-generation enrichment)

**目的：** 从源码中提取异常场景的真实行为，避免断言完全依赖 KB 文档的推断。

**触发条件：** 对每个有 异常场景断言 或 边界值断言 的 API，在 manifest 生成之后、test case 填充之前执行。

**Process:**

1. **定位 API 源码文件：**
   - 从 KB doc `## 基本信息` 中的 `源码路径` 字段获取（如果有）
   - 或 grep route decorator：`grep -rl "@router\.(post|get|put|delete).*{endpoint_path}" $SOURCE --include="*.py"`
   - 或从项目结构推断（`app/routers/`, `src/api/`, `backend/routes/`）

2. **提取异常处理事实：**
   - `HTTPException(status_code=N, detail=...)` → 精确 status + message 格式
   - Pydantic model 的 field 定义 → `Field(..., min_length=, max_length=, regex=)` 对应的校验规则
   - FastAPI/Pydantic 自动校验行为：缺失必填字段 → 422 + `{"detail": [{"loc":[], "msg":"Field required", "type":"missing"}]}`
   - 自定义 exception handler（如果有注册在 app 上的）

3. **构建 `source_facts` 对象：**
   ```json
   {
     "api_endpoint": "POST /api/v1/builds",
     "validation_engine": "pydantic|manual|mixed",
     "error_responses": [
       {
         "trigger": "missing required field",
         "status": 422,
         "detail_structure": "array_of_objects",
         "detail_example": [{"loc": ["body", "name"], "msg": "Field required", "type": "missing"}]
       },
       {
         "trigger": "entity not found",
         "status": 404,
         "detail_structure": "string",
         "detail_example": "Build not found"
       }
     ],
     "source_file": "app/routers/builds.py",
     "confidence": "high"
   }
   ```

4. **传递给 Step 4b 的 agent context：**
   - 将 `source_facts` 作为额外 context 传入 Test Filler agent
   - Agent 指令中明确：**当 source_facts 与 KB doc 断言表冲突时，以 source_facts 为准**
   - 例：KB 写 `status: 400`，source_facts 写 `status: 422` → 生成 `422`

5. **如果源码不可达（找不到源文件）：**
   - 标记该 API 的异常断言为 `[推断]`
   - 使用 `operator: "in"` + 范围值（如 `"expected": [400, 422]`）
   - 在 `_meta` 中记录 `"assertion_source": "kb_doc_inferred"`

**如果源码找到：**
   - 在 `_meta` 中记录 `"assertion_source": "source_code_extracted"`

```
✅ CHECKPOINT-4a-2: Source facts extracted
   APIs with source code found: {N}/{total}
   Validation engines: pydantic:{N}, manual:{N}, mixed:{N}, unknown:{N}
   Error responses extracted: {N} total
   APIs using inferred assertions (no source): {N} (list names)
```

## Step 4b: Fill test cases from manifest (one agent per scenario)

For each scenario in the manifest, spawn an independent **Test Filler** agent that fills the template:

**🔒 幂等/可续跑（重复运行不重复生成）：**
- 填充前先扫描 `$OUTPUT/$MODULE/tests/api/` 下已有测试文件（`{METHOD}-{api-stem}_*.json` + `REGRESSION-*.json`），提取每个文件的 `_meta.scenario_id`（Step 5 写盘时强制打上）。
- 已存在对应测试文件的场景 ID → **跳过**，不重复 spawn filler。
- 只填充缺失的场景 → 支持中断后续跑、重复运行不产生重复用例、也不覆盖已有产物。
- 幂等键 = `_meta.scenario_id`（对应 manifest 场景 id）；无此字段的旧文件不参与跳过判断。
- **pending 场景（Step 2d route_unavailable）→ 不 spawn filler、不写盘**（已在 manifest pending 数组记录；Step 6c 计为 Pending）。

**🔒 批量上限（Batch cap）：**
- 单批最多 spawn `MAX_PARALLEL_FILLERS`（建议 **8**）个 Filler agent 并行（场景间彼此独立，见下"并行执行"）。
- 场景总数超过上限 → 分多批顺序执行；每批完成后校验该批产出（合法 JSON 数）再进下一批。
- 每批进度记录到 CHECKPOINT-4b 汇总，供续跑判断哪些场景已填、哪些缺失。

```
你是一个 API 测试用例填充器。根据以下场景描述，填充 JSON 模板产出一个完整的测试用例。

## 🚫 硬性约束
- _meta 中不得有 {{PLACEHOLDER}} 残留
- 所有 ENV 变量必须已解析为实际值
- 不要生成登录步骤 — 执行引擎通过 auth_system/auth_role 自动注入认证
- 测试用例顶层必须包含 "auth_system" 和 "auth_role" 字段
- **所有 steps 的 headers 必须包含 "Authorization": "Bearer {{token}}" — 无论该 step 是主测试、前置步骤、SETUP 种子步骤还是错误/边界场景。headers 为空("{}" 或 {})= 生成失败**
- 输出必须是合法 JSON
- 严格按场景描述生成，不要自行增减场景范围
- **数据前置 → 必须发射幂等 SETUP 种子步骤到 `{{PREREQUISITE_STEPS}}`（不是只声明 resource_exists）**：主测试需要已存在资源（path param 非前序创建步骤产出，如 `PATCH /api/v1/sandbox/{agent_id}`）时，在 steps[] 的 `{{PREREQUISITE_STEPS}}` 槽填充如下幂等 SETUP 步骤（POST /api/v1/sandbox/build，build-by-name 幂等：同名 running/ready 直接复用，空库自动创建，重跑不重复、顺序无关）：

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

  - 主测试步骤消费 SETUP extract 的 `{{agent_id}}` / `{{agent_name}}`；`{{PREREQUISITE_STEPS}}` 槽不再留空
  - `prerequisites[].resource_exists` 补 `satisfy_endpoint`（= build 端点）、`satisfy_body`（= 种子 body）、`verify_field`（= "$.id"）——交互式 LIST→CHECK→SATISFY→VERIFY 路径的声明元数据
  - 自足测试（主步骤无需已存在资源）→ `{{PREREQUISITE_STEPS}}` 留空，保持原流程不变


## 场景信息:
SCENARIO_ID: {scenario.id}
SCENARIO_TYPE: {scenario.type}
SCENARIO_PRIORITY: {scenario.priority}
SCENARIO_DESCRIPTION: {scenario.description}
ERROR_CODE: {scenario.error_code, if applicable}
BOUNDARY_PARAM: {scenario.boundary_param, if applicable}

## SUB-SKILL 指令:
{$SUB_SKILL full content}

---
## Template (输出必须符合此结构):
{$TEMPLATE full content}

---
## Context:
API_DOC: {full API doc content}
TP: {test point info}
ENV_CONFIG: {resolved values — BASE_URL, credentials, paths}
GRAPH_EDGES: {relevant writes_to/reads_from}
SCENARIO_ID: {scenario.id} — 必须写入 _meta.scenario_id（幂等续跑键）
ENVELOPE_ENTRY: {该 endpoint 的 fresh envelope 条目 JSON，无则 null}
   — ENVELOPE_ENTRY 存在且 fresh 时，断言/extract 的 JSONPath 必须以它为准（见 GEN-SINGLE-API-TEST.md「jsonpath 断言精度规则」），而不是 API doc 的 Response Schema。

🔒 Output must be valid JSON. All single-brace {ENV} resolved. Zero {{PLACEHOLDER}} in _meta.
```

**🔒 并行执行：** 同一 API 的所有 scenarios 可以 parallel 生成（彼此独立）。

```
✅ CHECKPOINT-4b: Test cases generated (from manifest)
   Total scenarios: {N} (from manifests, 不含 pending)
   Pending skipped (route_unavailable): {P} — 不 spawn filler，计入 Step 6c Pending
   Skipped (已有 API 测试文件, 幂等): {N}
   Agents spawned this run: {N} (batches: {B}, 每批 ≤ {MAX_PARALLEL_FILLERS})
   Results received: {N}
   Valid JSON: {N} / Failed: {N}
   Per-API breakdown:
     {api_name}: normal:{n}, error:{e}, boundary:{b}, idempotent:{i} (+pending:{p})
   Manifest coverage: {generated}/{total_scenarios} scenarios filled (100% = no gaps)
   APIs missing variants: {list} → must fix before proceeding
   SETUP seed steps emitted: {N} (数据前置测试已自足化)
```

## Step 5: Write output files + self-validate

Write to `$OUTPUT/$MODULE/tests/api/`:
- `{METHOD}-{api-stem}_{TP-ID}.json` — normal test
- `{METHOD}-{api-stem}_ERR-{code}.json` — error variant
- `{METHOD}-{api-stem}_BOUNDARY-{param}.json` — boundary variant
- `POST-{api-stem}_IDEMPOTENT.json` — idempotency test

**🔒 写入位置（与中间产物隔离）：**
- 最终测试用例**只写** `$OUTPUT/$MODULE/tests/api/`（扫描目录，test-inventory 会收录）。
- 中间产物（`_manifest-*` / `_api-manifest-*`）在 `tests/_scenarios/.gen/`，**禁止**写回 `tests/api/` 等扫描目录。
- 每个测试用例的 `_meta.scenario_id` 必填（= 对应 manifest 场景 id），作为幂等续跑键（Step 4b 跳过判断依赖它）。

**🔒 Self-validation (per file, MUST pass before write):**
1. ✅ Valid JSON (parseable)
2. ✅ `steps` array has business API call steps (NO login steps)
3. ✅ `assert` array has >= 1 assertion per step
4. ✅ No `{{PLACEHOLDER}}` in _meta fields
5. ✅ BASE_URL resolved (starts with `http`)
6. ✅ Top-level `auth_system` and `auth_role` fields present
7. ✅ Error tests use correct HTTP status codes from doc
8. ✅ No unresolved `{{...}}` variables in `steps[].request.url`, `steps[].request.headers`, or `steps[].request.body` — EXCEPT approved runtime variables: any variable name declared in a prior step's `extract[].name` (e.g. `{{token}}`, `{{session_id}}`, `{{agent_id}}`)
9. ✅ **Auth header enforcement:** If top-level `auth_system` is present, every step's `headers` MUST contain `"Authorization": "Bearer {{token}}"`. A step with empty headers (`"{}"`, `{}`) or missing `Authorization` key → REJECT
10. ✅ **SETUP seed check:** 需要已存在资源的测试（path param 非前序创建步骤产出）→ `{{PREREQUISITE_STEPS}}` 槽必须含幂等 SETUP 种子步骤（`POST {base}/api/v1/sandbox/build`，body name=`qa-e2e-seed-<scenario_id>`），且其 extract 供应下游 path param；缺失 → REJECT（禁止只声明 resource_exists 不发射 SETUP）

**Check 8 — Unresolved variable scan (MANDATORY):**
For each output file, scan the ENTIRE JSON (not just `_meta`) for `{{...}}` patterns.
Any match that is NOT in the approved list below is a validation FAILURE:
- Approved extracted variables: any `name` from a preceding step's `extract[]` array (e.g. `session_id`, `agent_id`, `token`)
- Everything else (e.g. `{{BASE_URL}}`, `{{API_BASE_URL}}`, `{{PLACEHOLDER}}`, `{{LOGIN_URL}}`, `{{AUTH_USERNAME}}`, `{{AUTH_PASSWORD}}`, `{{AUTH_TOKEN}}`) → REJECT the file

Regex for detection: `\{\{([^}]+)\}\}` — extract all matches, filter against approved list.

Any file failing validation → log error, do NOT write, report in summary.

**Check 8b — Assertion-field {{var}} ban (MANDATORY, defensive policy):**
`assert[].expected` / `assert[].path` / `extract[].path` MUST NOT contain any `{{...}}` — even if the variable name is in the approved extract whitelist. 执行引擎 substitutes `{{var}}` in `request.url/headers/body` and (since 2026-08-06) in `assert.expected` / `assert.path`; `extract.path` still does NOT substitute (a var inside it → empty extraction → downstream variable chain breaks). We ban `{{var}}` in all three fields for cross-runner portability / not depending on the execution engine's behavior version.
Regex for detection: `\{\{([^}]+)\}\}` applied to `steps[].assert[].expected`, `steps[].assert[].path`, `steps[].extract[].path` (skip `db_verify.conditions[].value` — 执行引擎 substitutes there).
Repair (two-step): the producing step extracts via a fixed path (e.g. `$.items[0].id` → `{{agent_id}}`), then the assertion compares a fixed field / literal; if no fixed path exists → DELETE the assertion (keep `status` + `not_empty`). A file that can't be fixed → REJECT it.

```
✅ CHECKPOINT-5: Files written + validated
   Files written: {N}
   Validation passed: {N}
   Validation failed: {N} (details: ...)
```

## Step 5b: Dry-run validation (post-generation assertion verification)

**目的：** 调用真实 API，用实际响应校验生成的断言，自动修正不匹配项。这是确保断言准确度的最终防线。

**触发条件：** 对所有已写入的 API 测试文件（normal + error + boundary）。

**Process:**

1. **检测 API 服务可达性：**
   ```bash
   HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health" 2>/dev/null || echo "000")
   if [ "$HTTP_CODE" = "000" ]; then
     echo "API service unreachable — skip dry-run"
   fi
   ```
   - 如果不可达（返回 000 或连接超时）→ 所有文件标记 `"_validation": "skipped:service_unreachable"`，跳到 Step 6
   - 如果可达（返回任何 HTTP 状态码）→ 继续验证

2. **逐文件执行 dry-run：**
   对每个生成的测试 JSON 文件：
   - 读取 `steps` 数组
   - 对每个 step 的 request（url, method, headers, body）执行实际 HTTP 调用
   - 捕获实际 `status_code` 和 `response_body`
   - 与生成的 assertions 对比

3. **对比规则：**
   | 断言类型 | 对比方式 |
   |---------|---------|
   | `status` | 精确匹配 actual HTTP status code |
   | `jsonpath` (equals) | 提取实际响应对应路径的值，精确匹配 |
   | `jsonpath` (not_empty) | 验证路径存在且非空 |
   | `jsonpath` (contains) | 验证实际值包含期望子串 |

4. **不匹配时 — 自动修正：**
   - `status: 400` 实际 `422` → 更新为 `422`
   - `$.detail == "string"` 实际 `$.detail` 是 array → 更新 JSONPath 为 `$.detail[0].msg`
   - 响应结构不同 → 基于实际响应重建断言路径
   - 记录修正：
     ```json
     {
       "_meta": {
         "validated": true,
         "validated_at": "2026-07-28T10:30:00Z",
         "validation_corrections": [
           {"step": 1, "field": "status", "original": 400, "corrected": 422, "source": "dry-run"},
           {"step": 1, "field": "assertion.path", "original": "$.detail", "corrected": "$.detail[0].msg", "source": "dry-run"}
         ]
       }
     }
     ```

5. **匹配时 — 标记已验证：**
   ```json
   {"_meta": {"validated": true, "validated_at": "2026-07-28T10:30:00Z", "validation_corrections": []}}
   ```

6. **Dry-run 异常处理：**
   | 情况 | 处理 |
   |-----|------|
   | Auth failure (401/403) | 先用 ENV-CONFIG credentials 登录获取 token，重试 |
   | Connection timeout | 标记 `"_validation": "skipped:timeout"` |
   | 500 server error | 标记 `"_validation": "skipped:server_error"`，保留原始断言 |
   | 需要前置数据（如 entity 不存在） | 标记 `"_validation": "skipped:missing_precondition"` |
   | 请求包含 runtime 变量 `{{var}}` | 标记 `"_validation": "skipped:has_runtime_variables"` |

7. **🔒 核心原则：Dry-run 结果是权威的。**
   - 如果实际 API 返回 422，测试断言就写 422 — 无论 KB 文档怎么记录
   - 实际 API 行为是 source of truth，高于文档、高于 LLM 推断
   - 修正后的文件立即覆写（测试文件是派生产物，safe to overwrite）

```
✅ CHECKPOINT-5b: Dry-run validation complete
   Files validated: {N}/{total}
   Assertions correct (no correction needed): {N}
   Assertions corrected: {N} (list: file → correction summary)
   Skipped (service unreachable): {N}
   Skipped (other reasons): {N}
   Validation coverage: {validated}/{total} ({pct}%)
```

## Step 6: Graph-driven regression pairs

From `writes_to`/`reads_from` edges:
- API-A writes table-T, API-B reads table-T → generate write→read consistency test
- Write to `tests/api/REGRESSION-{api-a}-{api-b}.json`

```
✅ CHECKPOINT-6: Regression pairs generated
   Pairs found: {N}
   Files written: {N}
```

## Step 6c: Zero-output hard gate (零产出门禁 — 独立运行的最后防线)

**🔒 全量运行收尾时强制执行。不满足 = 运行失败，必须 FAIL LOUDLY（报错退出 / 返回 failed），不得静默结束。**

统计四项：
- `F` = `$OUTPUT/$MODULE/tests/api/` 下 API 测试用例文件（`{METHOD}-{api-stem}_*.json` + `REGRESSION-*.json`）总数
- `S` = 本轮全部 `_manifest-*.json` 的 `total_scenarios` 之和（从 `tests/_scenarios/.gen/` 读取；**不含 pending**）
- `W` = 本轮实际新写出的测试用例数（Step 4b/5 累计写盘数）
- `P` = 本轮全部 `_manifest-*.json` 的 `pending` 数组长度之和（Step 2d route_unavailable 场景）

**门禁判定：**
1. 若 `F == 0` 且 `P == 0` → **FAIL LOUDLY**：`tests/api/` 下 0 个 API 测试用例，报 `ZERO-OUTPUT-GATE: FAILED`，以非零状态退出。
2. 若 `S > 0` 且 `W == 0` 且 `P == 0` → **FAIL LOUDLY**：枚举了 `{S}` 个场景但填充未产出任何用例（典型停在 Step 4a/4a-2），报 `ZERO-OUTPUT-GATE: FAILED`，提示按 Step 4b 幂等续跑。
3. 若 `F == 0` 且 `P > 0` → **门禁通过**（全部场景因路由不可用而 pending）：报告显示 `Pending (route unavailable): {P}`，不写任何可运行用例，进入 Step 7。
4. 其余情况 → 门禁通过，进入 Step 7 正常收尾。

**FAIL 输出格式：**
```
❌ ZERO-OUTPUT-GATE: FAILED
   enumerated_scenarios: {S}
   written_this_run: {W}
   total_api_test_files: {F}
   reason: Step 4b 填充未执行或未完成 / tests/api/ 无 API 测试用例
   action: 按此提示续跑（Step 4b 幂等，跳过已有场景）或排查枚举/填充
```

## Step 7: Final report

**🔒 仅当 Step 6c 零产出门禁通过后才能输出 Complete 报告；FAIL 则输出失败报告并以非零状态退出。**

```
GSD > KB-GEN-TESTS-API Complete
────────────────────────────────────────────────────────────
Module:      {module}
APIs:        {N} with test cases generated
Test files:  {total} (normal: {n}, error: {e}, boundary: {b}, idempotent: {i}, regression: {r})
Coverage:    {covered_apis}/{total_apis} APIs have tests
Validation:  {passed}/{total} files passed self-check
Pending:     {P} (route unavailable) — pipeline 报告显示 "Pending (route unavailable): {P}"
Zero-output gate: PASSED (F: {F}, S: {S}, W: {W}, P: {P})
────────────────────────────────────────────────────────────
```

</process>

<validation>
执行结束后，对照以下清单做最终检查。任何 FAIL 项必须修复后重新输出：

| # | Check | FAIL condition |
|---|-------|----------------|
| 1 | ENV resolved | 任何文件中仍有 `{{BASE_URL}}` 或其他未解析模板变量 |
| 2 | Variant coverage | 任何 API 只有 normal 没有 error/boundary variants |
| 3 | Auth declaration | 任何文件缺少顶层 auth_system/auth_role 字段 |
| 4 | Assertion source | test assertions 与 API doc 的断言表不匹配（除非 dry-run 已修正） |
| 5 | _meta clean | _meta 中存在 `{{` 模板变量 |
| 6 | JSON valid | 任何输出文件不是合法 JSON |
| 7 | Dedup | 同一个 API+场景 生成了重复文件 |
| 8 | No login steps | 任何文件包含登录/获取 Token 步骤 |
| 9 | Dry-run status | 所有文件必须有 `_meta.validated` 字段（true/static_only/skipped:reason） |
| 10 | Source facts applied | 有 source_facts 的 API，其 error assertions 必须与 source_facts 一致 |
| 11 | Auth headers present | token 认证体系下，所有 steps 的 headers 必须包含认证头 — headers 为 `"{}"` 或 `{}` 或缺少认证键 = FAIL |
| 12 | headers 是 JSON 字符串 | headers 字段是 JSON 对象而非字符串 = FAIL（执行引擎强制要求 JSON 字符串格式） |
| 13 | body 是 JSON 字符串 | body 字段是 JSON 对象而非字符串或 null = FAIL（执行引擎强制要求 JSON 字符串格式） |
| 14 | type 分类正确 | API 测试统一为 `"api"`（无论单步还是含 prerequisite 的多步） |
| 15 | 断言来源标注 | 无源码验证的推断断言未标注 `[推断]` 或未使用 `operator: "in"` |
| 16 | Zero-output gate | Step 6c 未通过（tests/api/ 下 0 用例且无 pending，或枚举场景但填充 0 产出）却报告了 success |
| 17 | SETUP seed step | 需要已存在资源的测试（path param 非前序创建步骤产出）没有 SETUP 种子步骤（POST /api/v1/sandbox/build，name=qa-e2e-seed-<scenario_id>）而只声明 resource_exists，`{{PREREQUISITE_STEPS}}` 槽留空 |
| 18 | Route gate | 路由缺失（ENVELOPE-INDEX 无 / KB apis 无 / 探针 404/405）仍发射了可运行测试（应 pending/route_unavailable，不发射） |
| 19 | Envelope priority | ENVELOPE_ENTRY 注入且 fresh 时，断言路径没有用 API doc 猜测（应来自 envelope item_fields/list_path） |
</validation>
