---
name: gsd-kb-gen-tests-e2e
description: "Generate MCP-Ready E2E test cases: orchestrator + template-driven generation"
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
Orchestrate E2E test case generation by:
1. Building dependency chains from TP depends_on relationships
2. Chaining multiple API calls into complete business scenario flows
3. Spawning agents that fill E2E-TEST-TEMPLATE.json

Each agent reads `templates/E2E-TEST-TEMPLATE.json` and `sub-skills/GEN-SINGLE-E2E-TEST.md`.
Output: MCP-Ready JSON files for the execution engine's E2E dispatch tool.
</objective>

<process>

## Step 1: Parse arguments + load ENV-CONFIG

Extract from `$ARGUMENTS`:
- `--module <name>` (required)
- `--output <path>` (optional, default: `.planning/ontology`)
- `--req <REQ-ID>` (optional): specific requirement only

Load `$OUTPUT/$MODULE/tests/ENV-CONFIG.json` for auth/base URL.

## Step 2: Collect source documents

### 2a: Build dependency chains
For each REQ doc:
1. Extract ALL test points from TP table
2. Parse `depends_on` → build DAG
3. Topological sort → order TPs
4. Group into E2E chains (connected components in DAG)
5. Extract 边缘场景 table for edge case variants

### 2b: Load API docs per TP
For each TP in chain → resolve 关联接口 → read API doc (基本信息, 测试断言, 变量提取).

### 2c: Graph edges
Load graph.json → `depends_on` (API→Job for async verification).

## Step 3: Load template and sub-skill

```bash
SKILL_DIR=""
for candidate in \
  "$HOME/.claude/skills/gsd-kb-gen-tests-e2e" \
  "$(pwd)/skills/gsd-kb-gen-tests-e2e" \
  "$HOME/gsd-core/skills/gsd-kb-gen-tests-e2e"; do
  if [ -f "$candidate/templates/E2E-TEST-TEMPLATE.json" ]; then
    SKILL_DIR="$candidate"
    break
  fi
done
```

## Step 4: Spawn agents (one per E2E chain)

For each dependency chain:

```
{SUB_SKILL: GEN-SINGLE-E2E-TEST.md content}

---
## Template (output contract):
{E2E-TEST-TEMPLATE.json content}

---
## Context:
REQ_ID: {requirement ID}
TP_CHAIN: {topologically sorted TPs with depends_on}
API_DOCS: {API doc content for each TP's 关联接口}
EDGE_CASES: {边缘场景 table rows}
FIXTURES: {测试 Fixture from REQ doc}
ENV_CONFIG: {resolved auth values}
GRAPH_EDGES: {relevant depends_on/writes_to}

🔒 Output must be valid JSON. Chain steps must maintain variable passing consistency.
Cleanup must cover all created resources.
```

**E2E types to generate per REQ:**
1. **Happy path** — from depends_on chain
2. **Edge cases** — from 边缘场景 table (independent files)
3. **Rollback/consistency** — for chain steps with 409/500/503 error codes

## Step 5: Write output files

Write to `$OUTPUT/$MODULE/tests/e2e/`:
- `E2E-{REQ}_{scenario-slug}.json` — happy path
- `E2E-{REQ}_EDGE-{scenario}.json` — edge case variants
- `E2E-{REQ}_ROLLBACK-step{N}-{reason}.json` — consistency tests
- `E2E-CROSS_{domain}.json` — cross-requirement flows

## Step 5b: Dry-run validation (post-generation assertion verification)

After writing test files, validate E2E chain assertions against real API behavior.

**Trigger:** For E2E test files where ALL steps are `type: "api"` (no UI steps).

**Skip condition:** If any step in the chain has `type: "ui"` or requires browser interaction → mark `"_validation": "skipped:has_ui_steps"` and skip.

**Process:**

1. **Check API reachability:**
   ```bash
   curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health" 2>/dev/null || echo "unreachable"
   ```
   - If unreachable → mark all tests `"_validation": "skipped:service_unreachable"` in `_meta` and skip.

2. **For each API-only E2E test file:**
   - Execute steps sequentially (respecting variable passing between steps)
   - For each step: capture actual `status_code` and `response_body`
   - Compare against generated assertions

3. **On mismatch — auto-correct:**
   - Update status code assertions to match actual response
   - Update JSONPath assertions to match actual response structure
   - Record corrections in `_meta.validation_corrections[]`:
     ```json
     {
       "_meta": {
         "validated": true,
         "validation_corrections": [
           {"step": 3, "field": "status", "expected": 400, "actual": 422, "source": "dry-run"}
         ]
       }
     }
     ```

4. **On match — mark validated:**
   ```json
   {"_meta": {"validated": true, "validation_corrections": []}}
   ```

5. **Chain dependency handling:**
   - If step N fails and step N+1 depends on its output → mark remaining steps `"_validation": "skipped:chain_broken_at_step_N"`
   - Still validate and correct step N's assertions based on actual response

**Key rule:** Dry-run results are AUTHORITATIVE. The real API behavior is the source of truth, not KB documentation.

## Step 6: Cross-requirement flows

From MODULE.md 功能域划分:
- Identify related REQs (shared entities/state machines)
- Build super-chain crossing requirement boundaries
- Generate `E2E-CROSS-{domain}.json`

## Step 7: Report

```
GSD > KB-GEN-TESTS-E2E Complete
────────────────────────────────────────────────────────────
Module:      {module}
E2E flows:   {total} (happy: {h}, edge: {e}, rollback: {r}, cross: {c})
TP coverage: {covered_tps}/{total_tps} test points in E2E chains
Requirements:{covered_reqs}/{total_reqs} with E2E tests
────────────────────────────────────────────────────────────
```

</process>

<notes>
- Template-driven: agents fill JSON template
- E2E chains built from depends_on DAG (topological sort)
- Variable passing: step N extract → step N+1 uses {{var}}
- Cleanup mandatory for all creation steps
- Edge cases from REQ doc → independent E2E files
- Async jobs (from graph) → wait + verify steps auto-inserted
- Dry-run validation (Step 5b): only for API-only chains (no UI steps)
- Validation auto-corrects assertions based on actual API responses
- Validation status tracked in _meta.validated and _meta.validation_corrections
</notes>
