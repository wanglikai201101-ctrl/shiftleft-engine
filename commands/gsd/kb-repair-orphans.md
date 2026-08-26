---
name: gsd-kb-repair-orphans
description: "Diagnose and repair orphan nodes in knowledge graph — zero orphan target"
argument-hint: "--module <name> --output <path>"
allowed-tools:
  - Read
  - Write
  - Bash
  - Grep
  - Glob
---


<objective>
Detect, diagnose, and repair orphan nodes (nodes with zero edges) in the knowledge graph.

Goal: zero orphans. Every node must participate in at least one edge for full traceability.

Uses KB CLI `graph repair-orphans` command for deterministic Python-based repair.
</objective>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name
- `--output <path>` (required): KB documentation root (where MODULE.md lives)

## Step 2: Locate KB CLI

```bash
KB_CLI=""
for candidate in \
  "$HOME/.claude/gsd-core/knowledge-base" \
  "$HOME/.claude/knowledge-base" \
  "$(pwd)/knowledge-base" \
  "$HOME/gsd-core/knowledge-base"; do
  if [ -f "$candidate/packages/cli/__main__.py" ]; then
    KB_CLI="$candidate"
    break
  fi
done
```

If not found → STOP with error.

## Step 3: Run repair-orphans

```bash
cd "$KB_CLI"
PYTHONIOENCODING=utf-8 python -m packages.cli --kb-path "$OUTPUT" graph repair-orphans --output "$OUTPUT/$MODULE/graph"
```

## Step 4: Regenerate graph.html if orphans were repaired

```bash
cd "$KB_CLI"
PYTHONIOENCODING=utf-8 python -c "
import sys
sys.path.insert(0, '.')
from packages.core.graph.store import GraphStore
from packages.core.graph.visualize import generate_html

store = GraphStore(output_dir='$OUTPUT/$MODULE/graph')
graph = store.load()
if graph:
    generate_html(graph, output_path='$OUTPUT/$MODULE/graph/graph.html', title='$MODULE')
    print('graph.html regenerated')
"
```

## Step 5: Report

```
GSD > KB-REPAIR-ORPHANS Complete
────────────────────────────────────────────────────────────
Module:   {module}
Before:   {orphan_count} orphans
Repaired: {repaired_count} (edges added)
Remaining:{unresolved_count}
────────────────────────────────────────────────────────────
```

If unresolved orphans remain, list them with diagnosis:
```
[UNRESOLVED]
  [{type}] {node_id}
    reason: {diagnosis}
    doc:    {doc_path}
    action: fill the cross-reference sections in this doc
```

</process>

<notes>
- Safe to re-run: idempotent (skips already-connected nodes)
- Repaired edges marked confidence=INFERRED
- Run AFTER kb-fill-graph (requires graph.json to exist)
- If unresolved orphans remain, fix source docs then re-run kb-fill-graph + kb-repair-orphans
</notes>
