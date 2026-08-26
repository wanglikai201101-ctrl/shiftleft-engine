---
name: gsd-kb-query
description: "Query knowledge graph for precise context — impact analysis, requirement tracing, doc lookup"
argument-hint: "<query-type> <target> [impact|coverage|trace|docs]"
allowed-tools:
  - Read
  - Bash
  - Grep
  - Glob
---


<objective>
Query the knowledge graph to get precise context for any task — coding, testing, debugging, or review.

Use cases:
- Before modifying code: "What does this change impact?"
- Before testing: "What are the exact params/fields/constraints for this requirement?"
- During debug: "Which requirement does this code implement?"
- During review: "Did this change update all related docs?"

This is the primary way to USE the graph — not just build it.
</objective>

<process>

## Step 1: Parse arguments

Parse `$ARGUMENTS` to determine query type and target:

| Pattern | Query type | Example |
|---------|-----------|---------|
| `impact <node-id>` | Impact analysis — what's affected | `/gsd-kb-query impact logistics-order:api:POST-orders` |
| `coverage <REQ-id>` | Requirement coverage | `/gsd-kb-query coverage logistics-order:REQ-LO-001` |
| `trace <file-path>` | Reverse trace — file → requirements | `/gsd-kb-query trace src/api/order.py` |
| `docs <module>` | List all docs for a module | `/gsd-kb-query docs billing-agent` |
| `context <REQ-id>` | Full context dump for testing/coding | `/gsd-kb-query context logistics-order:REQ-LO-001` |
| No args or `help` | Show usage | |

If no args, display usage:
```
Usage: /gsd-kb-query <type> <target>

Types:
  impact <node-id>     — What does changing this node affect?
  coverage <REQ-id>    — Is this requirement fully implemented?
  trace <file-path>    — Which requirements does this file serve?
  docs <module>        — List all documentation for a module
  context <REQ-id>     — Full precise context for a requirement (for testing/coding)
```

## Step 2: Locate knowledge-base and graph

```bash
KB_CLI=""
if [ -d "knowledge-base/packages/cli" ]; then
  KB_CLI="$(pwd)/knowledge-base"
elif [ -d "$HOME/.claude/knowledge-base/packages/cli" ]; then
  KB_CLI="$HOME/.claude/knowledge-base"
elif [ -d "$HOME/gsd-core/knowledge-base/packages/cli" ]; then
  KB_CLI="$HOME/gsd-core/knowledge-base"
fi
```

Check graph exists:
```bash
GRAPH_DIR="graph"
if [ ! -f "$GRAPH_DIR/graph.json" ]; then
  # Try module-relative paths
  for candidate in "knowledge-base/graph" "$KB_CLI/graph" "modules/../graph"; do
    if [ -f "$candidate/graph.json" ]; then
      GRAPH_DIR="$candidate"
      break
    fi
  done
fi
```

If graph not found: suggest running `/gsd-kb-init` first.

## Step 3: Execute query

### impact — "改了这个节点影响什么"

```bash
cd "$KB_CLI"
PYTHONIOENCODING=utf-8 python -m packages.cli graph impact --node "$TARGET" --output "$GRAPH_DIR"
```

Then **read the actual doc files** for each impacted node to provide precise context.
For each impacted node that has a `doc_path`, read that file and summarize key info (params, constraints, relations).

Output format:
```
Impact Analysis: <target>
────────────────────────────────────────
Direct impacts: N nodes
  [api] POST /orders — 参数: customer_id, origin, destination...
  [storage] t_order — 字段: id, order_no, status, total_amount
  [page] order-create — testid: btn-submit, input-origin...
  [requirement] REQ-LO-001 — 10 个测试点

Recommendation: Changing <target> requires updating:
  - [ ] API doc: modules/xxx/apis/xxx.md
  - [ ] Storage doc: modules/xxx/storage/xxx.md
  - [ ] Test cases covering: TP-xxx-01, TP-xxx-02
```

### coverage — "这个需求实现全了吗"

```bash
cd "$KB_CLI"
PYTHONIOENCODING=utf-8 python -m packages.cli graph coverage --node "$TARGET" --output "$GRAPH_DIR"
```

Then read requirement doc to list test points and their coverage status.

### trace — "这个文件为什么存在"

Search graph.json for nodes whose `source_path` or `doc_path` matches the target file.
Then trace edges backward to find requirements.

Output:
```
File: src/api/order.py
Serves requirements:
  - REQ-LO-001 (创建物流订单) via API POST /orders
  - REQ-LO-005 (订单状态流转) via API PUT /orders/{id}/status
```

### docs — "这个模块有什么文档"

List all doc files for the module from graph nodes.

### context — "给我这个需求的完整精确上下文"（最重要）

This is the **primary use case for testing and coding**. It:

1. Finds the requirement node
2. Traces ALL related nodes (apis, tables, pages, jobs)
3. **Reads each related doc file** and extracts:
   - API docs: path, method, params (name/type/required), response fields, error codes
   - Storage docs: table name, columns (name/type/constraints), indexes
   - Page docs: data-testid list, bound APIs
   - Job docs: trigger conditions, schedule
   - Requirement: test points with expected results
4. Outputs a **structured context block** ready to be consumed by AI testing/coding:

```
Context for REQ-LO-001 (创建物流订单)
════════════════════════════════════════════════════════════

## Test Points (10)
| ID | Description | Verification |
|....|.............|..............|

## APIs
### POST /api/v1/orders
- Params: customer_id(string,必填), origin(string,必填), ...
- Response: order_id, order_no(LO-YYYYMMDD-XXXX), status(draft), total_amount
- Error codes: 400(参数缺失), 404(客户不存在), 409(并发冲突)
- Depends on: GET /customers, GET /service-catalog

## Storage
### t_order
- Columns: id(PK), order_no(UNIQUE), customer_id(FK), status, total_amount, created_at
- Indexes: idx_order_no(UNIQUE), idx_customer_id

### t_service_item
- Columns: id(PK), order_id(FK→t_order), catalog_id, quantity, unit

## Pages
### order-create
- Elements: btn-submit, input-origin, input-destination, select-customer, table-services
- Calls: POST /orders, GET /customers, GET /service-catalog

════════════════════════════════════════════════════════════
```

This structured output is the **precise input** for AI-driven testing or coding.
</process>

<notes>
- `context` is the most important query type — it provides the "precise ammunition" for AI testing
- Graph must be built first (via /gsd-kb-init or `graph build`)
- After code changes, re-run `graph build` to update the graph
- Impact analysis helps decide: "do I need to update docs after this change?"
- Trace helps during debug: "why does this code exist, what requirement drives it?"
</notes>
