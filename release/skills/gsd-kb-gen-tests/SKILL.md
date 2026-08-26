---
name: gsd-kb-gen-tests
description: "Generate structured test cases from KB docs — API contract, E2E flows, DB assertions. Output to tests/ for MCP-based execution."
argument-hint: "--module <name> --output <path> [--req <REQ-ID>] [--type api|e2e|ui|all] [--force]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Grep
  - Glob
  - Skill
---



<objective>
Router entry point for test case generation. Handles environment setup, type selection,
and dispatches to specialized sub-skills:

- `/gsd-kb-gen-tests-api` → api 测试用例格式（executor:api）
- `/gsd-kb-gen-tests-e2e` → e2e 测试用例格式（executor:e2e）
- `/gsd-kb-gen-tests-ui` → ui 测试用例格式（executor:ui）

Also handles cross-type concerns: graph-driven chain tests, risk matrix, and TEST-INDEX generation.
</objective>

<process>

## Step 1: Parse arguments and collect environment config

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name
- `--output <path>` (optional, default: `.planning/ontology`): KB documentation directory (where MODULE.md lives)
- `--req <REQ-ID>` (optional): generate tests for a specific requirement only
- `--type <api|e2e|ui|all>` (optional): which test types to generate. If not specified, ask user.
- `--force` (optional): overwrite existing test files. Without --force, skip files that already exist.

### Idempotency rules:
- Without `--force`: if `$OUTPUT/$MODULE/tests/api/TP-SB-005-01.json` already exists, skip it
- With `--force`: always overwrite (safe because tests are derived, not hand-authored)
- ENV-CONFIG.json is always updated (merge, not overwrite — preserve user edits to password field)
- TEST-INDEX.json is always regenerated (reflects current state)

Output directory: `$OUTPUT/$MODULE/tests/`

### 1.1: Collect test environment configuration (🔒 mandatory)

If `$OUTPUT/$MODULE/tests/ENV-CONFIG.json` exists, read it.
Otherwise, prompt user for:

| Parameter | Source | Example |
|-----------|--------|---------|
| `FRONTEND_BASE_URL` | `--frontend-url` or .env | `http://localhost:3000` |
| `API_BASE_URL` | `--api-url` or .env | `http://localhost:3000` |
| `AUTH_USERNAME` | `--username` or prompt | `admin@example.com` |
| `AUTH_PASSWORD` | `--password` or prompt | `***` |

Note: Tests use direct `http://localhost:3000` URLs instead of template variables. These parameters are stored in ENV-CONFIG.json for reference but are NOT injected as `{{...}}` placeholders into test files.

### 1.2: Generate/update ENV-CONFIG.json

Write `$OUTPUT/$MODULE/tests/ENV-CONFIG.json`:

```json
{
  "module": "sandbox",
  "environment": {
    "frontend_base_url": "http://localhost:3000",
    "api_base_url": "http://localhost:3000"
  },
  "auth": {
    "system_name": "your-project",
    "login_path": "/api/v1/auth/login",
    "token_path": "$.data.access_token",
    "login_body_field": "email",
    "username": "{{AUTH_USERNAME}}",
    "password": "{{AUTH_PASSWORD}}"
  },
  "executor_setup_commands": [
    {
      "tool": "session_setup",
      "args": {
        "variables": {}
      }
    }
  ],
  "notes": "执行引擎 handles login internally. Tests use direct http://localhost:3000 URLs — containers auto-rewrite to actual service address."
}
```

## Step 2: Type selection (if --type not specified)

Ask user via AskUserQuestion:

```
Which test types to generate?
- api: API contract tests (executor:api) — fast, no browser
- e2e: E2E scenario tests (executor:e2e) — multi-step flows
- ui: UI automation tests (executor:ui) — browser-based, agent-driven
- all: Generate all basic types (api + e2e + ui)
- perf: Performance baseline tests (executor:perf) — 专项，需显式指定
- concurrency: Cross-REQ concurrency tests — 专项，需显式指定
```

## Step 3: Dispatch to sub-skills

Based on selected type(s), read and execute the corresponding skill inline:

```
if type == "api" or type == "all":
    Read commands/gsd/kb-gen-tests-api.md and execute its <process> with args: --module {module} --output {output} [--req {req}]

if type == "e2e" or type == "all":
    Read commands/gsd/kb-gen-tests-e2e.md and execute its <process> with args: --module {module} --output {output} [--req {req}]

if type == "ui" or type == "all":
    Read commands/gsd/kb-gen-tests-ui.md and execute its <process> with args: --module {module} --output {output} [--req {req}]

if type == "perf":
    Execute Step 4c (Performance baseline tests) — 专项测试，不包含在 "all" 中

if type == "concurrency":
    Execute gen-tests-e2e Step 7b (Cross-REQ Concurrency Tests) — 专项测试，不包含在 "all" 中
```

Note: Sub-skills are executed inline (read their process and follow it), not via Skill tool nesting.
If context is too large, use Agent tool to spawn a subagent with the sub-skill's content as prompt.

## Step 4: Cross-type graph enrichment (only when type == "all")

### 4a: UI→API→DB chain tests

From graph edges, trace full chains: Page → (calls) → API → (writes_to) → Storage

For each complete chain:
```json
{
  "_meta": {"type": "chain", "mcp_tool": "executor:e2e"},
  "name": "CHAIN-{page}-{api}-{table}: 全链路验证",
  "steps": [
    {"type": "api", "name": "Login", ...},
    {"type": "api", "name": "Call {api} (simulating UI trigger)", ...},
    {"type": "api", "name": "Verify via read API", ...}
  ]
}
```

Output to `$OUTPUT/$MODULE/tests/chain/`

### 4b: Risk matrix

If graph shows multiple REQs share an API node:
```json
{
  "shared_apis": [
    {"api": "POST /build", "requirements": ["REQ-SB-001", "REQ-SB-003"], "risk": "high"},
    {"api": "GET /{id}", "requirements": ["REQ-SB-001", "REQ-SB-002", "REQ-SB-007"], "risk": "critical"}
  ]
}
```

Output to `$OUTPUT/$MODULE/tests/RISK-MATRIX.json`

### 4c: Performance baseline tests（专项测试 — 仅 `--type perf` 时执行，不包含在 `all` 中）

From graph.json, identify **高扇入 API**（被 5+ 页面/需求引用的节点）：

```
high_fan_in_apis = []
for each api_node in graph.nodes where type == "api":
    incoming_edges = edges where target == api_node.id
    if len(incoming_edges) >= 5:
        high_fan_in_apis.append(api_node)
```

For each high-fan-in API, generate a performance baseline test:

```json
{
  "_meta": {
    "type": "perf",
    "mcp_tool": "executor:perf",
    "generated_by": "gsd-kb-gen-tests",
    "source_api": "{api_node.id}",
    "fan_in_count": N
  },
  "name": "PERF-{METHOD}-{api-name}: 并发压测基线",
  "url": "http://localhost:3000{api_path}",
  "method": "{METHOD}",
  "headers": "{\"Authorization\": \"Bearer {{token}}\", \"Content-Type\": \"application/json\"}",
  "concurrency": 10,
  "timeout": 30,
  "assertions": {
    "max_p95_ms": 3000,
    "max_error_rate": 0.05,
    "expected_status": 200
  }
}
```

**并发数选择规则：**
| 扇入数 | 并发数 | 说明 |
|--------|--------|------|
| 5~10 | 10 | 基础压测 |
| 11~20 | 20 | 中等压测 |
| > 20 | 50 | 高频核心接口 |

**Prerequisites（perf 测试特殊）：**
- 性能测试需要稳定的测试环境（非本地开发环境）
- 每个 perf 测试 JSON 标注 `"env_requirement": "staging_or_above"`
- 本地执行时降低 concurrency 为 3（仅验证无 500 错误）

Output to `$OUTPUT/$MODULE/tests/perf/`

## Step 5: Generate TEST-INDEX.json

Scan all generated test files and produce `$OUTPUT/$MODULE/tests/TEST-INDEX.json`:

```json
{
  "module": "sandbox",
  "generated_at": "2026-06-24",
  "graph_enriched": true,
  "summary": {
    "api_tests": 13,
    "e2e_tests": 3,
    "ui_tests": 5,
    "chain_tests": 6,
    "total_assertions": 78
  },
  "coverage": {
    "requirements_covered": ["REQ-SB-001", "REQ-SB-002"],
    "test_points_covered": 25,
    "test_points_total": 70,
    "coverage_percentage": 35.7,
    "uncovered_test_points": ["TP-SB-003-04", "TP-SB-005-07", "TP-SB-005-08"]
  },
  "risk_matrix": {
    "critical_shared_apis": 2,
    "high_shared_apis": 5
  },
  "execution_guide": {
    "api_regression": {
      "tool": "executor:api",
      "directory": "tests/api/",
      "estimated_time": "2-5 minutes"
    },
    "e2e_flows": {
      "tool": "executor:e2e",
      "directory": "tests/e2e/",
      "estimated_time": "5-10 minutes"
    },
    "ui_tests": {
      "tool": "executor:ui",
      "directory": "tests/ui/",
      "estimated_time": "2-10 minutes per test"
    }
  }
}
```

**🔒 uncovered_test_points 推导逻辑（强制）：**

```
all_tps = 扫描所有 $OUTPUT/$MODULE/requirements/REQ-*.md 的 TP 表，提取全部 TP-ID
covered_tps = 扫描所有 tests/**/*.json 的 _meta.test_point 或文件名中的 TP-ID
uncovered_test_points = all_tps - covered_tps
```

此列表让用户明确知道哪些测试点还没有自动化测试覆盖，可针对性补充。

## Step 6: Report

```
GSD > KB-GEN-TESTS Complete
────────────────────────────────────────────────────────────
Module:       {module}
Type:         {selected_type}
Generated:
  API tests:       {api_count} cases
  E2E flows:       {e2e_count} chains
  UI tests:        {ui_count} cases
  Perf tests:      {perf_count} cases (高扇入 API 并发基线)
  Chain tests:     {chain_count} (graph-derived)
  Risk matrix:     {critical} critical, {high} high shared APIs
Coverage:
  Test points:     {covered}/{total} ({pct}%)
  Uncovered TPs:   {uncovered_count} (详见 TEST-INDEX.json)
Output:       $OUTPUT/$MODULE/tests/
────────────────────────────────────────────────────────────

Execute:
  API:  executor:api(steps=<file>.steps)
  E2E:  executor:e2e(name=<file>.name, steps=<file>.steps)
  UI:   executor:ui(name, url, steps, expected_results, options)
  Perf: executor:perf(url, method, headers, concurrency, timeout)
```

</process>

<notes>
- This is a ROUTER — actual generation logic lives in sub-skills
- ENV-CONFIG.json is shared across all sub-skills
- Graph enrichment (chain tests + risk matrix) only runs when --type all
- Sub-skills output MCP-Ready format — no conversion needed
- Safe to re-run: overwrites test files (tests are derived, not hand-authored)
- Use --req to regenerate tests for a single requirement after doc updates
- Use --type api for fastest iteration (no browser needed)
</notes>
