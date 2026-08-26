---
name: gsd-kb-gen-tests-e2e
description: "Generate MCP-Ready E2E test cases: orchestrator + template-driven generation"
argument-hint: "--module <name> --output <path> [--req <REQ-ID>] [--force] [--changed-routes \"GET /api/v1/x,POST /api/v1/y\"] [--min-variants happy] [--full-variants]"
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
- type 字段：E2E 场景 = `"e2e"`（多步 API + 可能含异步/DB/跨服务）
- 禁止出现 `{{BASE_URL}}`/`{{AUTH_USERNAME}}` 等模板占位符 — 只允许 `{{token}}` 和 extract 产出的变量
- 断言必须基于源码事实或 dry-run 验证，不得基于文档猜测
- 每个 step 必须有 name + request(url/method/headers/body) + assert
- 变量传递必须连贯：step N extract → step N+1 使用 `{{var}}`
- cleanup 必须覆盖所有创建操作

**自检时必须执行 TEST-OUTPUT-SPEC.md 第 9 节全部检查项。**
</output-spec>

<critical-rules>
🚫 HALT — 逐条阅读以下规则，违反任何一条 = 输出无效，必须删除重做

1. 🚫 NEVER skip ENV-CONFIG loading — 没有 ENV-CONFIG 就不能生成任何测试
2. 🚫 NEVER break dependency chain — steps 必须按 topological sort 顺序排列
3. 🚫 NEVER skip variable passing — step N extract 的变量必须在 step N+1 中使用 {{var}}
4. 🚫 NEVER omit cleanup steps — 所有创建操作必须有对应的清理步骤
5. 🚫 NEVER spawn agent without inlining template + sub-skill content
6. 🚫 NEVER output file without self-validation pass
7. 🚫 NEVER generate E2E with < 2 business steps (auth_system mode) or < 3 API steps including login (inline login mode) — E2E 必须是多步骤业务链路
8. 🚫 NEVER output headers/body as JSON object — 必须是 JSON 字符串格式（执行引擎强制）
9. 🚫 NEVER use inferred assertions without marking — 无源码验证的断言必须标注 [推断] 并用 operator: "in"
10. 🚫 NEVER end a run with zero test cases — 全量运行结束若 tests/e2e/ 下 0 个 E2E-*.json（或枚举了场景但填充 0 产出）→ FAIL LOUDLY（零产出门禁，Step 6c）
11. 🚫 NEVER emit a runnable e2e whose root flow needs pre-existing data without a SETUP seed step — 只有声明 `resource_exists` 前置在 pipeline 路径（执行引擎）不执行；数据前置必须发射幂等 SETUP 种子步骤到 steps[] 首位。**SETUP 端点/body schema 从 ENV-CONFIG 读取：`seed.endpoint` + `seed.payload_template`；未配置 `seed.endpoint` → 跳过 seed 步骤，只做通用测试生成（不强制生成任何项目的 sandbox 契约）。** 示例（来自 ENV-CONFIG 可配置，勿照抄）见 Step 2：POST /api/v1/sandbox/build，name=`qa-e2e-seed-<scenario_id>`，build-by-name 幂等复用
12. 🚫 NEVER emit a test for a route that doesn't exist — 链中任一 endpoint 路由缺失（ENVELOPE-INDEX 无 / KB apis/*.md 无 / 探针 404/405）→ 场景标 `_meta.status: "pending"` + `_meta.reason: "route_unavailable:<METHOD> <path>"`，不发射可运行用例，记录到 manifest（Step 2d / Step 6c Pending 计数）
13. 🚫 NEVER guess jsonpath from API docs — 变更作用域模式（`--changed-routes`）下，每个 step 的 assert/extract 的 jsonpath 必须来自 ENVELOPE-INDEX.json 中 `verified:true` 的条目（Step 2d.5 注入）、或 Step 2d 路由只读探测的真实响应、或 Step 5b dry-run 的真实响应；无 verified 来源 → 该 step 标 `_meta.path_unverified: true`（关键业务 step 无来源 → 场景标 pending，`reason: "jsonpath_unverified:<METHOD> <path>"`，不发射），禁止 LLM 从 API doc Response Schema 推测路径

每个 Step 完成后必须输出 checkpoint 标记，否则不得进入下一步。
</critical-rules>

<objective>
Orchestrate E2E test case generation by:
1. Building dependency chains from TP depends_on relationships
2. Chaining multiple API calls into complete business scenario flows
3. Spawning agents that fill E2E-TEST-TEMPLATE.json

Each agent reads `templates/E2E-TEST-TEMPLATE.json` and `sub-skills/GEN-SINGLE-E2E-TEST.md`.
Output: MCP-Ready JSON files for the executor's e2e dispatch tool.
</objective>

<process>

## Step 1: Parse arguments + load ENV-CONFIG

Extract from `$ARGUMENTS`:
- `--module <name>` (required)
- `--output <path>` (optional, default: `.planning/ontology`)
- `--req <REQ-ID>` (optional): specific requirement only
- `--force` (optional): ignore idempotent skip, force re-fill all scenarios (default: idempotent skip, Step 4b)
- `--changed-routes "GET /api/v1/x,POST /api/v1/y"` (optional): comma-separated `"METHOD path"` list identifying routes that changed in this run. When present, activates **change-scope mode**.
- `--min-variants happy` (optional): in change-scope mode, only generate happy_path variants (no edge/rollback). Default when `--changed-routes` is present is `--min-variants happy`.
- `--full-variants` (optional): in change-scope mode, re-enable edge/rollback variant enumeration. Default: off.

**Compatibility guarantee:** When `--changed-routes` is NOT provided, the entire process behaves exactly as before — all requirements are processed, all variants are enumerated, no change-scope filtering applies. This ensures backward compatibility with existing pipeline integrations.

Load `$OUTPUT/$MODULE/tests/ENV-CONFIG.json` for auth/base URL.
- `AUTH_SYSTEM` — from `auth.system` (optional — if present, use auth_system mode)
- `AUTH_ROLE` — from `auth.role` (optional, default: "admin")
- `SEED_ENDPOINT` — from `seed.endpoint` (optional — SETUP 种子步骤端点；未配置 → 跳过 seed 步骤，不做任何 sandbox 强约束)
- `SEED_PAYLOAD_TEMPLATE` — from `seed.payload_template` (optional — SETUP 种子 body 模板；缺省 `{"name": "qa-e2e-seed-<scenario_id>"}`，`{{SCENARIO_ID}}` 生成期替换)

```
✅ CHECKPOINT-1: ENV-CONFIG loaded
   MODULE: {name}
   BASE_URL: {url}
   LOGIN_PATH: {path}
   AUTH_MODE: {auth_system|inline_login}
   AUTH_SYSTEM: {system_name|N/A}
   AUTH_ROLE: {role|N/A}
   AUTH: {username} / ***
   如果 ENV-CONFIG.json 不存在 → STOP，报错退出
```

## Step 2: Collect source documents

### 2a: Build dependency chains
For each REQ doc in `$OUTPUT/$MODULE/requirements/*.md`:
1. Extract ALL test points from TP table
2. Parse `depends_on` → build DAG
3. Topological sort → order TPs
4. Group into E2E chains (connected components in DAG)
5. Extract 边缘场景 table for edge case variants

**🔒 变更作用域过滤（仅当传入 `--changed-routes` 时执行）：**
- 把 `--changed-routes` 解析为端点集合 `CHANGED_ROUTES = {"GET /api/v1/x", "POST /api/v1/y", ...}`（解析后归一化：trim 空白、`METHOD` 转大写、path 保持原始大小写但 trim 尾部斜杠）。
- 对每条已构建的依赖链，计算该链的 `ENDPOINT_SET`（链中所有 step 关联的 `"{METHOD} /path"` 端点集合）。
- 只保留 `ENDPOINT_SET ∩ CHANGED_ROUTES ≠ ∅` 的链（与变更接口有交集）。
- **零交集的链直接跳过**：不进入 Step 2d/4a/4b，不生成任何测试文件，记录到 checkpoint（`Skipped (no changed route): {N}`）。
- 若保留链 > 1 条 → 优先选**覆盖变更接口的那条链**（含变更端点数量最多的链；相同则选最长链）作为本轮唯一生成目标；其余保留链仅记录不生成（`--req` 存在时以该 REQ 的链为准）。
- **变更作用域模式产出收缩：** 最终只输出 **1 个 happy_path e2e 测试文件**（覆盖包含变更接口的那条链）。不产出 multi-file 展开。

### 2b: Load API docs per TP
For each TP in chain → resolve 关联接口 → read API doc (基本信息, 测试断言, 变量提取).

### 2c: Graph edges
Load `graph/graph.json` → `depends_on` (API→Job for async verification).

```
✅ CHECKPOINT-2: Source documents collected
   REQ docs found: {N}
   Total TPs: {N}
   Dependency chains built: {N} (list chain sizes)
   Longest chain: {N} steps
   Edge cases found: {N}
   APIs referenced: {N}
   Chains without depends_on (isolated TPs): {N} → these become single-API tests, not E2E
   MODE: {full|change-scope}
   Change-scope (if active):
     CHANGED_ROUTES: {N} routes
     Chains kept (∩ changed routes): {N} → 覆盖变更接口的链
     Chains skipped (no changed route): {N} → 不生成
     Selected chain: {REQ_ID} / {chain id} (覆盖 {M} 个变更端点)
     Output target: 1 happy_path E2E file
```

## Step 2d: Precondition route gate（路由门禁 — 前置校验）

**目的：** 生成前校验每条依赖链的每个 endpoint 路由是否存在（平台可能未实现该流程）。两步分开：**路由缺失 = 平台未实现 → SKIP/pending；数据缺失 = 平台已实现但空库 → SEED**（Step 4b 发射 SETUP 种子步骤）。

**路由存在性来源（按优先级）：**
1. `$OUTPUT/$MODULE/tests/ENVELOPE-INDEX.json` 的 `known_envelopes`（key 格式 `"{METHOD} /path"`，如 `"GET /api/v1/sandbox"`）
2. KB `$OUTPUT/$MODULE/apis/*.md`（文件命名 `{METHOD}-{path-stem}.md`，如 `POST-build.md`）
3. （可选）只读探针：`curl -s -o /dev/null -w "%{http_code}" "<url>"` → 404/405 = 路由缺失（探针只读，不产生数据；仅当 manifest/KB 冲突或均缺失时使用）

**判定：**
- 依赖链中所有 endpoint 都存在 → 进入 Step 3/4a 正常枚举填充。
- 任一 endpoint 缺失（ENVELOPE-INDEX 无记录 / KB 无 doc / 探针返回 404/405）→ **该链所有场景标 pending**：
  - 场景 `_meta.status: "pending"`，`_meta.reason: "route_unavailable:<METHOD> <path>"`
  - **不发射可运行测试**（filler 不得收到该场景，Step 4b 跳过）
  - 记录到 `_manifest-{REQ}.json` 的 `pending` 数组（Step 4a 清单 schema 已含）：`{"id": "{scenario_id}", "type": "{type}", "reason": "route_unavailable:<METHOD> <path>"}`
  - `total_scenarios` **只计非 pending 场景**（Step 6c 零产出门禁的 `S` 不含 pending）

```
✅ CHECKPOINT-2d: Route gate complete
   Chains checked: {N}
   Endpoints verified: {N} (ENVELOPE-INDEX: {a}, KB apis: {b}, probe: {c})
   Routes missing: {N} (list "<METHOD> <path>")
   Scenarios marked pending (route_unavailable): {N} → 不发射，记录到 manifest pending 数组
```

## Step 2d.5: Envelope 条目注入（ENVELOPE-INDEX → Filler Context）

**目的：** 把 ENVELOPE-INDEX.json 里的 **verified envelope**（真实响应结构）注入到 Step 4b 每个 Filler agent 的 Context，使链中各 step 的断言/extract 的 JSONPath 以真实响应为准，而不是 API doc 的 Response Schema 猜测。

**读取来源（按优先级，找到即合并）：**
1. 模块索引：`$OUTPUT/$MODULE/tests/ENVELOPE-INDEX.json` → `known_envelopes`（key 格式 `"{METHOD} /path"`，如 `"GET /api/v1/sandbox"`）
2. 全局索引：ENV-CONFIG 或工作区配置声明的共享索引路径 → `known_envelopes`
（Step 1.5 前置探针已在生成前把真实 envelope 灌进索引，本步直接消费。）

**对每条依赖链涉及的所有 endpoint（每个 `known_envelopes` key 对应的端点）：**
1. 读取模块 + 全局 ENVELOPE-INDEX 的该端点条目（key = `"{METHOD} /path"`）。
2. **注入分级：**
   - **A. fresh verified 条目**：`verified:true` **且** `verified_at` 距今 <24h **且** `backend_fingerprint` 与当前后端一致。三者全满足 → 注入为 **verified**（`ENVELOPE_ENTRY` 含该条目，断言直接用，`_meta.path_unverified` 不设置）。
   - **B. pre_probe 条目**（`pre_probe:true`，`verified:false`，来自 Step 1.5 前置探针 route/KB 推导，list_path 非空）→ 注入为 **候选**；Filler 用其 list_path 作为 jsonpath 依据，但 `_meta` 记 `"envelope_source": "pre-probe"` + `"_meta.path_unverified": true`。
   - **C. 不注入**：无条目 / verified:false 且非 pre_probe / stale verified / fingerprint 不匹配 / pre_probe 但 list_path 空 → 该 step 回退 API doc。

**🔒 变更作用域模式的 jsonpath 来源铁律（`--changed-routes` 生效时强制执行）：**
- 测试的**每个 step** 的 assert/extract 的 jsonpath **必须**来自以下真实来源之一，**禁止 LLM 猜测 jsonpath / 禁止从 API doc 的 Response Schema 凭空推断**：
  1. `ENVELOPE-INDEX.json` 中 `verified:true` 的条目（由预探针真实解析写入；key = `"{METHOD} /path"`）—— Step 2d.5 注入为 verified 的条目；
  2. Step 2d 的路由只读探测的真实响应（探测返回 body 中真实存在的字段路径）；
  3. Step 5b 的 dry-run 真实响应（生成后校验阶段基于实际响应修正/重建路径）。
- 变更作用域模式下，某 step 的 endpoint **没有任何 verified 来源**（仅 pre_probe 候选或回退 API doc）→ 该 step 的断言路径**不得产出**；标记 `_meta.path_unverified: true`；若该 step 是关键业务步骤且无任何可用真实来源 → 该链场景标 pending（`reason: "jsonpath_unverified:<METHOD> <path>"`），不发射可运行用例（与 route_unavailable 同等处理，Step 6c 计 Pending）。
- 冲突铁律保持：真实响应（envelope/探测/dry-run）与 API doc 冲突 → **永远以真实响应为准**。
3. 每个 Filler 的 Context 注入格式（见 Step 4b `## Context:` 块）——链含多端点，注入 keyed map（key = `"{METHOD} /path"`，value = envelope 条目；只含 fresh 或 pre_probe 条目，链中无任何可注入条目 → `ENVELOPE_ENTRY: null`）：
   ```
   ENVELOPE_ENTRY: { "POST /api/v1/sandbox/build": {entry...}, "GET /api/v1/sandbox": {entry...} }
   ```
4. **冲突铁律：** envelope（真实探针回写）与 API doc 冲突 → **永远以 envelope 为准**。

```
✅ CHECKPOINT-2d.5: Envelope 条目注入完成
   Envelopes injected: {N}/{total_endpoints} (fresh verified entries fed to fillers)
   Stale/missing（回退 API doc）: {M} (list "<METHOD> <path>" + reason: verified:false / verified_at 过期 / fingerprint 不匹配 / 无条目)
   Change-scope jsonpath gate (if active): verified sources {N}/{M} steps · unverified (path_unverified) {U} · pending (jsonpath_unverified) {P}
```

## Step 3: Load template and sub-skill

```bash
SKILL_DIR=""
for candidate in \
  "$HOME/.claude/skills/gsd-kb-gen-tests-e2e" \
  "$(pwd)/skills/gsd-kb-gen-tests-e2e"; do
  if [ -f "$candidate/templates/E2E-TEST-TEMPLATE.json" ]; then
    SKILL_DIR="$candidate"
    break
  fi
done
```

Read `$SKILL_DIR/templates/E2E-TEST-TEMPLATE.json` → `$TEMPLATE`
Read `$SKILL_DIR/sub-skills/GEN-SINGLE-E2E-TEST.md` → `$SUB_SKILL`

```
✅ CHECKPOINT-3: Template + sub-skill loaded
   SKILL_DIR: {path}
   TEMPLATE: {first 50 chars}...
   SUB_SKILL: {first 50 chars}...
   如果任一为空 → STOP，报错退出
```

## Step 4a: Enumerate test scenarios (deterministic manifest)

**🔒 两阶段生成：先枚举清单，再逐个填充。AI 不能跳过清单中的任何场景。**

**🔒 变体收口（变更作用域模式，`--changed-routes` 生效时）：**
- 默认 `--min-variants happy`：**只枚举 happy_path 场景 1 个**，不枚举 edge_case / rollback（边缘场景 table 行与链中 409/500/503 错误码**不产生**变体场景）。
- 显式 `--full-variants`：恢复现有 edge/rollback 枚举能力（边缘场景 table 每行 → 1 个 edge_case；链中错误码步骤 → rollback）。
- 非变更作用域模式（无 `--changed-routes`）→ 完全按下方全量枚举规则执行（与旧行为一致）。
- 变更作用域模式下，最低数量门控（见下方）**只要求 1 个 happy_path**；edge/rollback 门控跳过。

For each dependency chain (per REQ), spawn a **Scenario Enumerator** agent that ONLY outputs a structured scenario manifest (not test cases). This agent analyzes the KB docs and deterministically lists ALL required test scenarios:

```
你是一个 E2E 测试场景枚举器。分析以下 KB 文档，列出该 REQ 所有必须生成的 E2E 测试场景。

## MODE
MODE: {full|change-scope}
VARIANT_MODE: {min-variants|full-variants}
- change-scope + min-variants（默认）：只产出 1 个 happy_path 场景，忽略 edge_case / rollback 检查表。
- change-scope + full-variants：产出 1 个 happy_path + edge_case/rollback（按下方检查表）。
- full 模式：忽略本 MODE 块，按下方全量检查表执行。

## 🚫 硬性约束
- 每种适用的测试类型必须至少有对应数量的场景
- 输出是 JSON 对象，不是测试用例本身
- 不要生成测试步骤或断言，只列出场景元数据

## 场景类型检查表（逐条扫描，有证据就必须产生对应场景）：

| # | 类型 | 触发证据（KB 文档中的信号） | 最少数量 |
|---|------|---------------------------|---------|
| 1 | happy_path | depends_on chain exists | 1 |
| 2 | edge_case | 边缘场景 table rows | 1 per row |
| 3 | rollback | Chain steps with 409/500/503 codes | 1 per failing step |

## 枚举规则：
- 分析 depends_on chain → 至少 1 个 happy_path 场景（完整链路）
- 扫描 边缘场景 table → 每行产生 1 个 edge_case 场景
- 扫描 chain 中各步骤的 error codes → 有 409/500/503 的步骤各产生 1 个 rollback 场景
- rollback 场景必须标注 failing_step（链中第几步失败）和 error_code
- **Step 2d 已标记 route_unavailable 的链** → 场景**不放入 scenarios**，放入 `pending` 数组（`reason: "route_unavailable:<METHOD> <path>"`）；`total_scenarios` 只计非 pending 场景


---
## Context:
REQ_ID: {requirement ID}
TP_CHAIN: {topologically sorted TPs with depends_on}
API_DOCS: {API doc content for each TP's 关联接口}
EDGE_CASES: {边缘场景 table rows}
GRAPH_EDGES: {relevant depends_on/writes_to}
```

**Scenario Manifest Schema (强制):**
```json
{
  "type": "object",
  "properties": {
    "req_id": { "type": "string" },
    "chain_length": { "type": "integer" },
    "total_scenarios": { "type": "integer", "minimum": 0, "description": "只计非 pending 场景（route_unavailable 的链不计入）" },
    "scenarios": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "type": { "type": "string", "enum": ["happy_path", "edge_case", "rollback"] },
          "priority": { "type": "string", "enum": ["P0", "P1", "P2"] },
          "description": { "type": "string" },
          "failing_step": { "type": "integer" },
          "error_code": { "type": "integer" }
        },
        "required": ["id", "type", "priority", "description"]
      }
    },
    "pending": {
      "type": "array",
      "description": "不可发射的可运行用例：Step 2d 路由门禁 route_unavailable / Step 2d.5 jsonpath 来源铁律 jsonpath_unverified（不发射可运行用例；Step 6c 计为 Pending）",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "type": { "type": "string" },
          "reason": { "type": "string", "pattern": "^(route_unavailable|jsonpath_unverified):" }
        },
        "required": ["id", "type", "reason"]
      }
    },
    "evidence": {
      "type": "object",
      "properties": {
        "depends_on_edges": { "type": "integer" },
        "edge_case_rows": { "type": "integer" },
        "error_codes_in_chain": { "type": "integer" }
      }
    }
  },
  "required": ["req_id", "chain_length", "total_scenarios", "scenarios", "pending", "evidence"]
}
```

**🔒 中间产物写盘（与扫描目录隔离）：**
- Enumerator 清单显式落盘：`_manifest-{REQ}.json` 写入 `$OUTPUT/$MODULE/tests/_scenarios/.gen/`（`_scenarios` 非 api/e2e/ui 扫描子目录，test-inventory 不会把它当测试用例；`_manifest-*` 前缀已被 test-inventory skip 模式排除）。
- **绝不允许**写入 `tests/e2e/`、`tests/api/`、`tests/ui/` 等扫描目录。
- 中间产物保留供溯源/续跑，**不删除**。

**Priority assignment (写入 scenario.priority):**
| Test type | Priority | Rationale |
|-----------|----------|-----------|
| Happy path | `P0` | 核心链路验证，必须最先执行 |
| Edge cases | `P1` | 边缘场景验证 |
| Rollback/consistency | `P2` | 回滚一致性验证 |

**🔒 枚举归一化（CHECKPOINT-4a 验证第一步，先归一化再门控）：**

manifest 的 `scenario.type` 必须属于 3 个枚举值（happy_path / edge_case / rollback）。若枚举器输出非枚举值（LLM 漂移），**显式映射**而非裸 REJECT：

| 非枚举取值（枚举器输出） | 归一化到（枚举内） | 依据 |
|------------------------|-------------------|------|
| `error_handler` / `error_path` | `rollback` | 异常处理器 → 链中失败/回滚一致性 |
| `network_error` / `timeout` / `concurrency` | `rollback` | 网络/超时/并发失败 → 回滚一致性 |
| `boundary_value` / `edge` | `edge_case` | 边界/极端输入 → 边缘场景 |
| `empty_state` / `loading_state` | `happy_path` | 空态/加载态在链路中 = 正常前置条件 |
| `conditional` / `decision` / `decision_branch` | `happy_path` | 条件/决策分支在 E2E 链路 = 主路径的一种走向 |
| `success` / `main_flow` / `end_to_end` | `happy_path` | 主路径/成功链路 → happy_path |
| `consistency` / `rollback_consistency` | `rollback` | 一致性验证 → 回滚类 |
| 其它未列出的非枚举值 | 按语义就近映射到 3 个枚举值之一 | 就近原则 |

**规则：**
- 先执行归一化映射 → 再跑下方最低数量门控。归一化后若场景仍无法归类到任何枚举值 → 才是 REJECT，重新枚举。
- **禁止裸 REJECT**（枚举器输出任何非枚举值直接拒绝会触发重枚举死循环）。
- **堵住 off-enum 静默穿透：** 非枚举值必须先归一化，未归一化的 type **不得**流入填充器（Step 4b SCENARIO_TYPE）或文件命名（Step 5）；写盘到 `_manifest-{REQ}.json` 时 `scenario.type` 恒为枚举值。

**🔒 最低数量门控（CHECKPOINT-4a 验证，第二步 — 枚举归一化之后执行）：**
- 必须至少有 1 个 `happy_path` 场景
- `evidence.edge_case_rows > 0` 但没有 `edge_case` 类型场景 → REJECT，重新枚举
- `evidence.error_codes_in_chain > 0` 但没有 `rollback` 类型场景 → REJECT，重新枚举
- **门控只针对非 pending 场景**（`pending` 数组 = route_unavailable，不参与门控）。某 REQ 全部场景 pending → `scenarios` 可为空、`pending` 非空，跳过门控（Step 6c 按 Pending 计数，不 FAIL）。
- **变更作用域模式（`--min-variants happy`）门控覆盖：** 只要求 ≥1 个 `happy_path` 场景；edge_case / rollback 门控**跳过**（无论 evidence 中 edge_case_rows / error_codes_in_chain 是否 > 0，均不 REJECT）。场景枚举数 = 1（happy_path），外加 pending（route_unavailable / jsonpath_unverified）。

```
✅ CHECKPOINT-4a: Scenario manifests generated
   REQs processed: {N}
   Total scenarios enumerated: {N}
   Pending (route unavailable): {P} — 不发射可运行用例，记录到 manifest pending 数组
   Enum normalization: {N} off-enum types mapped (details: type_a→type_b ×N)
   Per-REQ breakdown:
     {REQ_ID}: {N} scenarios (happy:{h}, edge:{e}, rollback:{r}) + pending:{p}
   Evidence: {depends_on_edges} edges, {edge_case_rows} edge cases, {error_codes_in_chain} error codes
   Gate check: ALL passed / REJECTED {N} (re-enumerated)
   MODE: {full|change-scope} · VARIANT_MODE: {min-variants|full-variants}
   Change-scope contraction: {N} chains → 1 happy_path scenario only (edge/rollback contracted) / full-variants restore
```

## Step 4b: Fill test cases from manifest (one agent per scenario)

For each scenario in the manifest, spawn an independent **Test Filler** agent that fills the template:

**🔒 幂等/可续跑（重复运行不重复生成）：**
- 填充前先扫描 `$OUTPUT/$MODULE/tests/e2e/` 下已有 `E2E-*.json` / `E2E-CROSS-*.json`，提取每个文件的 `_meta.scenario_id`（Step 5 写盘时强制打上）。
- 已存在对应 `E2E-*.json` 的场景 ID → **跳过**，不重复 spawn filler。
- **pending 场景（Step 2d route_unavailable）→ 不 spawn filler、不写盘**（已在 manifest pending 数组记录；Step 6c 计为 Pending）。
- 只填充缺失的场景 → 支持中断后续跑、重复运行不产生重复用例、也不覆盖已有产物。
- 幂等键 = `_meta.scenario_id`（对应 manifest 场景 id）；无此字段的旧文件不参与跳过判断。
- **`--force` 指定时忽略幂等跳过**：所有场景强制重填（覆盖已有产物）。默认不带 `--force` → 幂等跳过生效。

**🔒 批量上限（Batch cap）：**
- 单批最多 spawn `MAX_PARALLEL_FILLERS`（建议 **8**）个 Filler agent 并行（场景间彼此独立，见下"并行执行"）。
- 场景总数超过上限 → 分多批顺序执行；每批完成后校验该批产出（合法 JSON 数）再进下一批。
- 每批进度记录到 CHECKPOINT-4b 汇总，供续跑判断哪些场景已填、哪些缺失。

```
你是一个 E2E 测试用例填充器。根据以下场景描述，填充 JSON 模板产出一个完整的测试用例。

## 🚫 硬性约束
- E2E 必须包含 >= 3 个 API 步骤（不含 login/cleanup；SETUP 种子步骤计入业务步骤）
- 变量传递必须连贯：step N extract → step N+1 使用 {{var}}
- 所有创建操作必须有 cleanup 步骤（SETUP 造出的种子 Agent 由 build-by-name 幂等复用，不需要也不应 DELETE 种子）
- 步骤顺序必须遵循 topological sort
- **所有 steps 的 headers 必须包含 "Authorization": "Bearer {{token}}" — 无论该 step 是业务步骤、前置步骤、SETUP 种子步骤还是验证步骤。headers 为空("{}" 或 {})= 生成失败**
- 输出必须是合法 JSON
- 严格按场景描述生成，不要自行增减场景范围
- **数据前置 → 发射 SETUP 种子步骤（不是只声明 resource_exists）——端点/契约可配置（不强制 sandbox）**：链的根流程需要已存在资源（path param 非前序创建步骤产出）时，在 steps[] 首位 PREPEND 幂等 SETUP 步骤。**SETUP 端点与 body schema 从 ENV-CONFIG 读取：`seed.endpoint`（配置了才发射 seed 步骤）+ `seed.payload_template`（可选，缺省 `{"name": "qa-e2e-seed-<SCENARIO_ID>"}`）。`seed.endpoint` 未配置 → 跳过 seed 步骤，只做通用测试生成，不强制生成任何项目的 sandbox/A2A 契约。** 下方 JSON 仅为**示例**（参考 sandbox 的 build-by-name 契约，来自 ENV-CONFIG 可配置）；换项目必须用该项目实际 seed 端点与返回 envelope，禁止照抄 url / assert / extract：

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
> ⚠️ **示例契约（ENV-CONFIG 可配置）**：`request.url` 实际生成时必须取 ENV-CONFIG `seed.endpoint`（示例 URL 仅为参考，非真实端点），`body` 取 `seed.payload_template`；`assert`/`extract` 的 JSONPath 必须基于该项目 seed 返回的真实 envelope（探针/文档），`$.id`/`$.name` 仅为示例；`sandbox_id`/`a2a_endpoint` 是参考 sandbox 特有字段，目标项目无则不得引用。

  - 后续步骤消费 SETUP extract 的 `{{seed_id}}` / `{{seed_name}}`（原"拉取列表取第一条"步骤降级为验证步骤或删除，禁止硬编码依赖已存在数据）
  - `prerequisites[].resource_exists` 补 `satisfy_endpoint`（= 从 ENV-CONFIG 读取的 seed 端点）、`satisfy_body`（= seed body）、`verify_field`（= seed 返回的 id 路径，示例 "$.id"）——交互式 LIST→CHECK→SATISFY→VERIFY 路径的声明元数据，均为示例/可配置
  - **自足测试**（链内已有创建步骤产出所需 ID）→ **无 SETUP 步骤**，保持原流程不变
  - **无 seed 可发**（需要已存在资源但 ENV-CONFIG 未配置 `seed.endpoint`）→ 不得伪造任何 sandbox 契约；该链标 `_meta.status: "pending"` + `_meta.reason: "seed_unavailable:<path param>"`（或补充 seed 配置后重跑），不发射可运行用例


## 场景信息:
SCENARIO_ID: {scenario.id}
SCENARIO_TYPE: {scenario.type} — 恒为枚举值（happy_path / edge_case / rollback，CHECKPOINT-4a 已归一化）
SCENARIO_PRIORITY: {scenario.priority}
SCENARIO_DESCRIPTION: {scenario.description}
FAILING_STEP: {scenario.failing_step, if applicable}
ERROR_CODE: {scenario.error_code, if applicable}
MODE: {full|change-scope} — change-scope 时强制满足 jsonpath 来源铁律（见 Context 的 ENVELOPE_ENTRY 说明）
VARIANT_MODE: {min-variants|full-variants}

## SUB-SKILL 指令:
{$SUB_SKILL full content}

---
## Template (输出必须符合此结构):
{$TEMPLATE full content}

---
## Context:
REQ_ID: {requirement ID}
TP_CHAIN: {topologically sorted TPs with depends_on}
API_DOCS: {API doc content for each TP's 关联接口}
EDGE_CASES: {边缘场景 table rows}
FIXTURES: {测试 Fixture from REQ doc}
ENV_CONFIG: {resolved auth values}
GRAPH_EDGES: {relevant depends_on/writes_to}
ENVELOPE_ENTRY: {链中各 endpoint 的 fresh envelope 条目 keyed map，key=`"{METHOD} /path"`，无 fresh 条目 → null}
   — ENVELOPE_ENTRY 存在且 fresh 时，对应 step 的断言/extract 的 JSONPath 必须以它为准（见 GEN-SINGLE-E2E-TEST.md「jsonpath 断言精度规则」），而不是 API doc 的 Response Schema。
   — **🔒 变更作用域模式（MODE=change-scope）jsonpath 来源铁律：** 本测试每个 step 的 assert/extract 的 jsonpath 必须来自 (1) ENVELOPE-INDEX 中 verified:true 条目、或 (2) Step 2d 路由只读探测的真实响应、或 (3) Step 5b dry-run 的真实响应。**禁止 LLM 猜测 jsonpath，禁止用 API doc Response Schema 凭空推断路径。** 某 step 无任何 verified 来源 → 不产出断言路径、标记 `_meta.path_unverified: true`；关键业务 step 无 verified 来源 → 场景不发射（标 pending，reason=jsonpath_unverified）。

🔒 Output must be valid JSON. Chain steps must maintain variable passing consistency.
Cleanup must cover all created resources.
```

**🔒 并行执行：** 同一 REQ 的所有 scenarios 可以 parallel 生成（彼此独立）。

```
✅ CHECKPOINT-4b: E2E test cases generated (from manifest)
   Total scenarios: {N} (from manifests, 不含 pending)
   Pending skipped (route_unavailable): {P} — 不 spawn filler，计入 Step 6c Pending
   Skipped (已有 E2E-*.json, 幂等): {N}
   Agents spawned this run: {N} (batches: {B}, 每批 ≤ {MAX_PARALLEL_FILLERS})
   Results received: {N}
   Valid JSON: {N} / Failed: {N}
   Per-REQ breakdown:
     {REQ_ID}: happy:{h}, edge:{e}, rollback:{r} (+pending:{p})
   Manifest coverage: {generated}/{total_scenarios} scenarios filled (100% = no gaps)
   Variable passing verified: {N}/{N} chains consistent
   SETUP seed steps emitted: {N} (数据前置场景已自足化)
```

## Step 5: Write output files + self-validate

Write to `$OUTPUT/$MODULE/tests/e2e/`:
- `E2E-{REQ}_{scenario-slug}.json` — happy path
- `E2E-{REQ}_EDGE-{scenario}.json` — edge case variants
- `E2E-{REQ}_ROLLBACK-step{N}-{reason}.json` — consistency tests

**🔒 变更作用域模式输出（`--changed-routes` + `--min-variants happy`）：** 只写 **1 个** `E2E-{REQ}_{scenario-slug}.json`（happy_path，覆盖含变更接口的链）；不产生 EDGE / ROLLBACK 文件。`--full-variants` 时恢复上方三态命名。非变更作用域模式不受影响。

**🔒 写入位置（与中间产物隔离）：**
- 最终测试用例**只写** `$OUTPUT/$MODULE/tests/e2e/`（扫描目录，test-inventory 会收录）。
- 中间产物（`_manifest-*`）在 `tests/_scenarios/.gen/`，**禁止**写回 `tests/e2e/` 等扫描目录。
- 文件命名基于**归一化后**的枚举 type（`scenario.type` 恒为枚举值；off-enum 值不得出现在文件名 slug 中）。
- 每个测试用例的 `_meta.scenario_id` 必填（= 对应 manifest 场景 id），写盘时强制写入，作为幂等续跑键（Step 4b 跳过判断依赖它）。

**🔒 Self-validation (per file, MUST pass before write):**
1. ✅ Valid JSON (parseable)
2. ✅ `steps` array has >= 3 API calls (not counting login/cleanup; SETUP 种子步骤计入业务步骤)
3. ✅ Variable passing: every `{{var}}` in step N has a matching `extract` in step < N
4. ✅ Cleanup steps present for all POST/creation steps（种子 Agent 由 build-by-name 幂等复用，不 DELETE 种子）
5. ✅ Steps follow topological order (no step uses data from a later step)
6. ✅ ENV values resolved (no `{BASE_URL}` remaining)
7. ✅ Each step has `assert` with >= 1 assertion
8. ✅ **Auth header enforcement:** If top-level `auth_system` is present, every step's `headers` MUST contain `"Authorization": "Bearer {{token}}"`. A step with empty headers (`"{}"`, `{}`) or missing `Authorization` key → REJECT
9. ✅ **SETUP seed check:** 需要已存在资源的场景（path param 非前序创建步骤产出）且 ENV-CONFIG 配置了 `seed.endpoint` → steps[0] 必须是 SETUP 种子步骤（url=`seed.endpoint`，body 遵循 `seed.payload_template`，name 示例 `qa-e2e-seed-<scenario_id>`），且其 extract 供应下游使用的 path param；缺失 → REJECT（禁止只声明 resource_exists 不发射 SETUP）。ENV-CONFIG 未配置 `seed.endpoint` → 跳过 seed 检查，不强制 sandbox 契约

Any file failing validation → log error, do NOT write, report in summary.

```
✅ CHECKPOINT-5: Files written + validated
   Files written: {N}
   Validation passed: {N}
   Validation failed: {N} (details: ...)
```

## Step 5b: Dry-run validation (post-generation assertion verification)

**目的：** 对 API-only 的 E2E 链路执行实际调用，校验断言准确度。

**触发条件：** 仅对所有 steps 都是 `type: "api"` 的 E2E 测试文件。

**跳过条件：**
- 任何 step 含 `type: "ui"` 或需要浏览器交互 → 标记 `"_validation": "skipped:has_ui_steps"`
- 链路中有 step 依赖异步 Job 完成 → 标记 `"_validation": "skipped:has_async_steps"`

**Process:**

1. **检测 API 服务可达性：**
   ```bash
   HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health" 2>/dev/null || echo "000")
   ```
   - 不可达 → 所有文件标记 `"_validation": "skipped:service_unreachable"`，跳到 Step 6

2. **逐文件顺序执行 dry-run（保持链路依赖）：**
   - 按 steps 顺序执行每个 API 调用
   - 维护 variable context（step N extract 的值传给 step N+1）
   - 对每个 step 的 assertions 与实际响应对比

3. **对比与修正（同 API 测试规则）：**
   - Status code 不匹配 → 修正为实际值
   - JSONPath 结构不匹配 → 基于实际响应重建路径
   - 记录修正到 `_meta.validation_corrections[]`

4. **链路断裂处理：**
   - 如果 step N 失败（非断言失败，而是请求本身出错）且 step N+1 依赖其 extract → 标记后续 steps `"_validation": "skipped:chain_broken_at_step_N"`
   - 仍然修正已执行 steps 的断言

5. **标记验证结果：**
   ```json
   {
     "_meta": {
       "validated": true,
       "validated_at": "2026-07-28T10:30:00Z",
       "validation_corrections": [],
       "chain_execution": {"steps_executed": 5, "steps_total": 5, "broken_at": null}
     }
   }
   ```

**🔒 核心原则：** Dry-run 结果是权威的。实际 API 行为 > KB 文档 > LLM 推断。

```
✅ CHECKPOINT-5b: Dry-run validation complete
   API-only E2E files: {N}/{total}
   Files validated (dry-run): {N}
   Assertions corrected: {N}
   Skipped (has UI/async steps): {N}
   Skipped (service unreachable): {N}
   Chain execution success rate: {N}/{N} chains completed fully
```

## Step 6: Cross-requirement flows

From MODULE.md 功能域划分:
- Identify related REQs (shared entities/state machines)
- Build super-chain crossing requirement boundaries
- Generate `E2E-CROSS-{domain}.json`

```
✅ CHECKPOINT-6: Cross-requirement flows
   Related REQ groups: {N}
   Cross-REQ files generated: {N}
```

## Step 6c: Zero-output hard gate (零产出门禁 — 独立运行的最后防线)

**🔒 全量运行收尾时强制执行。不满足 = 运行失败，必须 FAIL LOUDLY（报错退出 / 返回 failed），不得静默结束。**

统计四项：
- `F` = `$OUTPUT/$MODULE/tests/e2e/` 下测试用例文件（`E2E-{REQ}_*.json` / `E2E-CROSS-*.json`）总数
- `S` = 本轮全部 `_manifest-*.json` 的 `total_scenarios` 之和（从 `tests/_scenarios/.gen/` 读取；**不含 pending**）
- `W` = 本轮实际新写出的测试用例数（Step 4b/5/6 累计写盘数）
- `P` = 本轮全部 `_manifest-*.json` 的 `pending` 数组长度之和（Step 2d route_unavailable 场景 + Step 2d.5 jsonpath_unverified 场景）

**门禁判定：**
1. 若 `F == 0` 且 `P == 0` → **FAIL LOUDLY**：`tests/e2e/` 下 0 个测试用例，报 `ZERO-OUTPUT-GATE: FAILED`，以非零状态退出。
2. 若 `S > 0` 且 `W == 0` 且 `P == 0` → **FAIL LOUDLY**：枚举了 `{S}` 个场景但填充未产出任何用例（典型停在 Step 4a/4b），报 `ZERO-OUTPUT-GATE: FAILED`，提示按 Step 4b 幂等续跑。
3. 若 `F == 0` 且 `P > 0` → **门禁通过**（全部场景因路由不可用而 pending）：报告显示 `Pending (route unavailable): {P}`，不写任何可运行用例，进入 Step 7。
4. 其余情况 → 门禁通过，进入 Step 7 正常收尾。

**FAIL 输出格式：**
```
❌ ZERO-OUTPUT-GATE: FAILED
   enumerated_scenarios: {S}
   written_this_run: {W}
   total_e2e_test_files: {F}
   reason: Step 4b 填充未执行或未完成 / tests/e2e/ 无测试用例
   action: 按此提示续跑（Step 4b 幂等，跳过已有场景）或排查枚举/填充
```

## Step 7: Final report

**🔒 仅当 Step 6c 零产出门禁通过后才能输出 Complete 报告；FAIL 则输出失败报告并以非零状态退出。**

```
GSD > KB-GEN-TESTS-E2E Complete
────────────────────────────────────────────────────────────
Module:      {module}
E2E flows:   {total} (happy: {h}, edge: {e}, rollback: {r}, cross: {c})
TP coverage: {covered_tps}/{total_tps} test points in E2E chains
Requirements:{covered_reqs}/{total_reqs} with E2E tests
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
| 1 | Chain length | 任何 E2E 文件 API steps < 3（不含 login/cleanup） |
| 2 | Variable passing | step N 使用 {{var}} 但之前没有 extract 定义 |
| 3 | Cleanup missing | 有 POST 创建步骤但没有对应 cleanup/teardown |
| 4 | Topological order | 步骤顺序违反 depends_on 关系 |
| 5 | ENV resolved | 文件中仍有 `{BASE_URL}` 未解析 |
| 6 | JSON valid | 任何输出文件不是合法 JSON |
| 7 | Isolated TPs | 没有 depends_on 的 TP 被错误地生成为 E2E（应该是 API test） |
| 8 | Dry-run status | 所有文件必须有 `_meta.validated` 字段（true/skipped:reason） |
| 9 | Correction applied | dry-run 发现的不匹配必须已修正到文件中 |
| 10 | Auth headers present | token 认证体系下，所有 steps 的 headers 必须包含认证头 — headers 为 `"{}"` 或 `{}` 或缺少认证键 = FAIL |
| 11 | headers 是 JSON 字符串 | headers 字段是 JSON 对象而非字符串 = FAIL（执行引擎强制要求 JSON 字符串格式） |
| 12 | body 是 JSON 字符串 | body 字段是 JSON 对象而非字符串或 null = FAIL（执行引擎强制要求 JSON 字符串格式） |
| 13 | type 分类正确 | E2E 场景必须为 `"e2e"`，不得标记为 "api" 或 "ui" |
| 14 | 断言来源标注 | 无源码验证的推断断言未标注 `[推断]` 或未使用 `operator: "in"` |
| 15 | Zero-output gate | Step 6c 未通过（tests/e2e/ 下 0 用例且无 pending，或枚举场景但填充 0 产出）却报告了 success |
| 16 | SETUP seed step | 需要已存在资源的 E2E 且 ENV-CONFIG 配置了 `seed.endpoint`，却没有 SETUP 种子步骤（url=seed.endpoint，body=seed.payload_template，name 示例 qa-e2e-seed-<scenario_id>）而只声明 resource_exists |
| 17 | Route gate | 路由缺失（ENVELOPE-INDEX 无 / KB apis 无 / 探针 404/405）的链仍发射了可运行测试（应 pending/route_unavailable，不发射） |
| 18 | Envelope priority | ENVELOPE_ENTRY 注入且某 endpoint 的条目 fresh 时，该 step 断言路径没有用 API doc 猜测（应来自 envelope item_fields/list_path） |
| 19 | Change-scope jsonpath | 变更作用域模式下，某 step 的 assert/extract jsonpath 无 verified 来源（ENVELOPE-INDEX verified:true / 探测 / dry-run）却产出了路径（应为 `_meta.path_unverified: true` 或 pending `jsonpath_unverified`） |
| 20 | Change-scope output count | 变更作用域模式（`--min-variants happy`）下，产出 >1 个 E2E 文件，或产出了 EDGE/ROLLBACK 文件（应为 1 个 happy_path 文件） |
</validation>
