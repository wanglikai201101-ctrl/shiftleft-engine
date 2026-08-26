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


<objective>
Orchestrate API test case generation by:
1. Collecting source docs (API docs 测试断言 + REQ test points + graph edges)
2. Resolving ENV-CONFIG for auth credentials
3. Spawning agents that fill API-TEST-TEMPLATE.json — not freeform generation
4. Generating error/boundary/idempotency variants

Each agent reads `templates/API-TEST-TEMPLATE.json` and `sub-skills/GEN-SINGLE-API-TEST.md`.
Output: MCP-Ready JSON files for the execution engine's API dispatch tool.
</objective>

<process>

## Step 1: Parse arguments + load ENV-CONFIG

Extract from `$ARGUMENTS`:
- `--module <name>` (required)
- `--output <path>` (optional, default: `.planning/ontology`)
- `--req <REQ-ID>` (optional): specific requirement only

Load `$OUTPUT/$MODULE/tests/ENV-CONFIG.json`:
- `BASE_URL`, `AUTH_USERNAME`, `AUTH_PASSWORD`, `LOGIN_PATH`, `TOKEN_PATH`
- If not exists, prompt user for values.

## Step 2: Collect source documents

### 2a: API docs with 测试断言
For each `apis/*.md`: extract **Request Schema** (structured JSON schema — PRIMARY source for body construction), 测试断言 tables (正常/异常/边界/变量提取), 请求/响应示例, 基本信息, 请求参数, 错误码.

**Request Schema extraction priority for body construction:**
1. `## Request Schema` section → parse JSON schema block + field table → use as authoritative body structure
2. If `_schema_unverified: true` or section missing → fall back to `## 请求参数` (filter body fields)
3. If neither available → fall back to source-code Pydantic model extraction (Step 4b)
4. All levels exhausted → HALT for that API

Assertion source levels:
- Level 1: has `## 测试断言` → use directly
- Level 2: has `## 请求/响应示例` → derive assertions
- Level 3: only `## 响应结构` → derive not_empty assertions

### 2b: Requirements (TP tables)
Load REQ docs → extract TPs with 验证方式 = "API", depends_on relationships.

### 2c: Graph edges
Load `graph/graph.json` → `writes_to` (for DB enrichment), `reads_from` (for regression pairs).

## Step 3: Load template and sub-skill

```bash
SKILL_DIR=""
for candidate in \
  "$HOME/.claude/skills/gsd-kb-gen-tests-api" \
  "$(pwd)/skills/gsd-kb-gen-tests-api" \
  "$HOME/gsd-core/skills/gsd-kb-gen-tests-api"; do
  if [ -f "$candidate/templates/API-TEST-TEMPLATE.json" ]; then
    SKILL_DIR="$candidate"
    break
  fi
done
```

## Step 4: Spawn agents

For each API doc (or group of simple APIs):

```
{SUB_SKILL: GEN-SINGLE-API-TEST.md content}

---
## Template (output contract):
{API-TEST-TEMPLATE.json content}

---
## Context:
API_DOC: {full API doc content}
TP: {test point info}
ENV_CONFIG: {resolved values — BASE_URL, credentials, paths}
GRAPH_EDGES: {relevant writes_to/reads_from}
FILE_LISTS: {existing test files for dedup}

🔒 Output must be valid JSON. All single-brace {ENV} resolved. Zero {{PLACEHOLDER}} in _meta.
```

**Test types to generate per API:**
1. **Normal** — happy path from 正常场景断言
2. **Error** (top 3) — from 异常场景断言 table
3. **Boundary** (min 3) — from 边界值断言 table
4. **Idempotency** — for POST creation endpoints (no path param)

## Step 4b: Source-code extraction for error scenarios (pre-generation enrichment)

Before agents generate error/boundary assertions, attempt to extract ground-truth from source code:

**Trigger:** For each API that has 异常场景断言 or 边界值断言 to generate.

**Process:**
1. Locate API source file (from KB doc `## 基本信息` → 源码路径, or grep route decorator pattern)
2. Extract exception handling facts:
   - `HTTPException(status_code=N, detail=...)` → exact status + message
   - Pydantic model fields with `Field(..., min_length=, max_length=)` → validation rules
   - FastAPI/Pydantic auto-validation → always returns 422 with `{"detail": [{"loc":[], "msg":"...", "type":"..."}]}`
   - Custom exception handlers registered in app
3. Build a `source_facts` object per API:
   ```json
   {
     "validation_engine": "pydantic|manual|mixed",
     "error_responses": [
       {"trigger": "missing required field", "status": 422, "detail_structure": "array_of_objects"},
       {"trigger": "not found", "status": 404, "detail_structure": "string"}
     ]
   }
   ```
4. Pass `source_facts` into agent context — agents MUST prefer source_facts over KB doc when conflicting.

**If source code not found:** Mark assertions as `[推断]` and use `operator: "in"` with range values (e.g., `[400, 422]`).

## Step 5: Write output files

Write to `$OUTPUT/$MODULE/tests/api/`:
- `{METHOD}-{api-stem}_{TP-ID}.json` — normal test
- `{METHOD}-{api-stem}_ERR-{code}.json` — error variant
- `{METHOD}-{api-stem}_BOUNDARY-{param}.json` — boundary variant
- `POST-{api-stem}_IDEMPOTENT.json` — idempotency test

## Step 5b: Dry-run validation (post-generation assertion verification)

After writing test files, validate assertions against real API behavior.

**Trigger:** For ALL generated API test files (normal + error + boundary).

**Process:**

1. **Check API reachability:**
   ```bash
   curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health" 2>/dev/null || echo "unreachable"
   ```
   - If unreachable → mark all tests `"_validation": "skipped:service_unreachable"` in `_meta` and skip to Step 6.

2. **For each generated test file:**
   - Read the `steps` array
   - Execute each step's request (url, method, headers, body) using curl or equivalent
   - Capture actual `status_code` and `response_body`
   - Compare against generated assertions:
     - `status_code` assertion vs actual status
     - JSONPath assertions vs actual response structure

3. **On mismatch — auto-correct:**
   - If expected `status: 400` but actual `status: 422` → update assertion to `422`
   - If expected `$.detail == "string"` but actual `$.detail` is array → update JSONPath to `$.detail[0].msg`
   - If expected response structure differs → rebuild assertions from actual response
   - Record original vs corrected in `_meta.validation_corrections[]`:
     ```json
     {
       "_meta": {
         "validated": true,
         "validation_corrections": [
           {"field": "status", "expected": 400, "actual": 422, "source": "dry-run"},
           {"field": "assertion.path", "expected": "$.detail", "actual": "$.detail[0].msg", "source": "dry-run"}
         ]
       }
     }
     ```

4. **On match — mark validated:**
   ```json
   {"_meta": {"validated": true, "validation_corrections": []}}
   ```

5. **Error handling during dry-run:**
   - Auth failure (401/403) → attempt login first using ENV-CONFIG credentials, retry
   - Connection timeout → mark `"_validation": "skipped:timeout"`
   - 500 server error → mark `"_validation": "skipped:server_error"`, keep original assertions
   - Test requires precondition data (e.g., existing entity) → mark `"_validation": "skipped:missing_precondition"`

**Key rule:** Dry-run results are AUTHORITATIVE. If the actual API returns 422, the test asserts 422 — regardless of what KB documentation says. The real API behavior is the source of truth.

## Step 6: Graph-driven regression pairs

From `writes_to`/`reads_from` edges:
- API-A writes table-T, API-B reads table-T → generate write→read consistency test
- Write to `tests/api/REGRESSION-{api-a}-{api-b}.json`

## Step 7: Report

```
GSD > KB-GEN-TESTS-API Complete
────────────────────────────────────────────────────────────
Module:      {module}
APIs:        {N} with test cases generated
Test files:  {total} (normal: {n}, error: {e}, boundary: {b}, idempotent: {i}, regression: {r})
Coverage:    {covered_apis}/{total_apis} APIs have tests
────────────────────────────────────────────────────────────
```

</process>

<notes>
- Template-driven: agents fill JSON template structure
- ENV-CONFIG values resolved at generation time (single-brace)
- Only {{variable}} double-brace remains for runtime inter-step passing
- Assertion conversion: doc format → 执行引擎 format handled by sub-skill
- [推断] assertions use operator "in" with range for flexibility
- Source-code extraction (Step 4b): prefer source facts over KB doc for error scenarios
- Dry-run validation (Step 5b): actual API response is authoritative over documentation
- Validation status tracked in _meta.validated and _meta.validation_corrections
</notes>
