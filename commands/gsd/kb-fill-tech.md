---
name: gsd-kb-fill-tech
description: "Phase 1 only: CLI batch-fill for knowledge-base docs — fast static extraction (params, types, fields) from AST"
argument-hint: "--module <module-name> --source <code-dir> --output <doc-dir> [--force]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Grep
  - Glob
---



<objective>
Fast static extraction of technical details from source code into documentation skeletons.

Uses CLI `batch-fill` command to extract via AST/regex:
- Request parameters (names, types, required)
- ORM field definitions (column types, constraints)
- Route metadata (HTTP method, path)

This is the FAST phase (~seconds). It only fills what regex/AST can determine.
For deep semantic fill (business rules, requirements, page elements), use `/gsd-kb-fill-ai`.
</objective>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name in the docs output directory
- `--source <path>` (required): source code directory
- `--output <path>` (optional, default: `.planning/ontology`): documentation output directory
- `--force` (optional): re-run batch-fill with `--overwrite` flag, overwriting existing filled content. Without --force, only fills "待补充" placeholders.

## Step 2: Locate CLI and determine SOURCE_ROOT

```bash
KB_CLI="$HOME/.claude/knowledge-base"
# If not found there:
# KB_CLI="$(pwd)/knowledge-base"

# Determine SOURCE_ROOT (project root where skeleton path refs resolve)
SOURCE_ROOT="$SOURCE"
while [ ! -f "$SOURCE_ROOT/pyproject.toml" ] && [ ! -f "$SOURCE_ROOT/package.json" ] && [ ! -f "$SOURCE_ROOT/setup.py" ] && [ "$SOURCE_ROOT" != "/" ]; do
  SOURCE_ROOT=$(dirname "$SOURCE_ROOT")
done
```

## Step 3: Execute batch-fill

```bash
cd "$KB_CLI"
PYTHONIOENCODING=utf-8 python -m packages.cli --kb-path "$OUTPUT" batch-fill --module "$MODULE" --source "$SOURCE_ROOT" --workers 8
```

**IMPORTANT**:
- Command is `batch-fill` (with hyphen), NOT `fill`
- `--kb-path` MUST come BEFORE the subcommand
- `--kb-path` points to `$OUTPUT` (where MODULE.md lives)
- `--source` points to project root (NOT the subdirectory)

## Step 4: Report

Display filled/skipped/failed counts. Done.

</process>

<notes>
- This is Phase 1 only. For AI semantic fill, run `/gsd-kb-fill-ai` after this.
- Safe to re-run: only fills "待补充" placeholders, preserves existing content (unless --force is passed).
- With --force: overwrites all filled content with fresh extraction from source code.
- Typical time: 5-30 seconds for 50-100 docs.
</notes>
