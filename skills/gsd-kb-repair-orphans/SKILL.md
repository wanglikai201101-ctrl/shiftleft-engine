---
name: gsd-kb-repair-orphans
description: "Run the KB repair-orphans CLI and report the result — report-only (no manual fixing)"
argument-hint: "--module <name> --output <path>"
allowed-tools:
  - Read
  - Write
  - Bash
  - Grep
  - Glob
---


<objective>
Run the repair CLI and REPORT the result. Do NOT fix orphan nodes by editing source docs or rebuilding the graph — report-only.

The KB CLI `graph repair-orphans` command performs deterministic Python-based repair. This skill runs that CLI once, captures its output, and reports it. Reporting IS the deliverable.

Goal: run the CLI once, print its output, and exit.
</objective>

**STOP — you are report-only.** Do NOT:
- edit any source doc (.md) in the KB
- run `graph build` or full graph rebuilds
- read builder.py / orphan_repair.py internals to hand-fix
- enter a fix-converge loop

Run the CLI once, print its output, and exit.

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name
- `--output <path>` (required): KB documentation root (where MODULE.md lives)

## Step 2: Locate KB CLI

```bash
# Canonical KB_CLI resolution — use directly, do NOT search $HOME
KB_CLI="${KB_CLI:-}"
if [ -z "$KB_CLI" ]; then
  for c in \
    "$HOME/.claude/gsd-core/knowledge-base" \
    "$HOME/.claude/knowledge-base" \
    "$(pwd)/knowledge-base"; do
    if [ -d "$c/packages/cli" ]; then KB_CLI="$c"; break; fi
  done
fi
if [ -z "$KB_CLI" ]; then
  for d in $(find "$HOME" -maxdepth 6 -type d -path "*knowledge-base/packages/cli" 2>/dev/null); do
    KB_CLI="$(dirname "$(dirname "$d")")"; break
  done
fi
```

If KB_CLI is still empty, return an error immediately — do NOT search further or reverse-engineer the CLI.

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

Reporting IS the deliverable. Run the CLI once (Step 3), relay its output verbatim, and exit — do not investigate further.

```
GSD > KB-REPAIR-ORPHANS Complete
────────────────────────────────────────────────────────────
Module:   {module}
Before:   {orphan_count} orphans
Repaired: {repaired_count} (edges added)
Remaining:{unresolved_count}
────────────────────────────────────────────────────────────
```

If unresolved orphans remain, report each one verbatim from the CLI output:
```
[UNRESOLVED]
  [{type}] {node_id}
    reason: {diagnosis}
    doc:    {doc_path}
```
If the diagnosis is opaque ("path mismatch"), do NOT investigate the internals — just relay the CLI output and exit.

</process>

<notes>
- Report-only: do NOT edit source docs or rebuild the graph to fix orphans
- The CLI `graph repair-orphans` command performs any repair deterministically — relay its output verbatim
- Safe to re-run: idempotent (skips already-connected nodes)
- Repaired edges marked confidence=INFERRED
- Run AFTER kb-fill-graph (requires graph.json to exist)
</notes>
