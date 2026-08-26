---
name: gsd-kb-fill-graph-links
description: "Backfill bidirectional traceability links across KB docs using graph.json"
argument-hint: "--module <name> --output <path>"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
---



<objective>
Establish bidirectional traceability links across all KB documents using graph.json edges.

This is a standalone post-processing skill — it does NOT fill content. It ONLY adds/updates
cross-reference links between documents. Run after any kb-fill-* skill to wire up the graph.

Jobs:
1. API docs: add `## 需求来源` section (API → REQ reverse link)
2. Requirement docs: replace `[待创建]` with actual file links (REQ → API/DB/Page)
3. Storage docs: add `## 关联需求` section (Storage → REQ reverse link)
4. Page docs: add `## 关联需求` section (Page → REQ reverse link)
</objective>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name
- `--output <path>` (optional, default: `.planning/ontology`): KB documentation root (where MODULE.md lives)

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

## Step 3: Execute backfill-links via CLI (🔒 确定性代码执行)

**必须使用 CLI 命令，禁止手动解析 graph.json + 编辑 markdown：**

```bash
cd "$KB_CLI"
PYTHONIOENCODING=utf-8 python -m packages.cli --kb-path "$OUTPUT" graph backfill-links --output "$OUTPUT/$MODULE/graph"
```

**如果 KB CLI 不可用：**
```
❌ 追溯链接回填需要 KB CLI (graph backfill-links 命令)。
   请确保 gsd-core/knowledge-base/packages/cli/__main__.py 存在。
```
**STOP — 不要手动解析 JSON 和编辑文档。**

## Step 4: Report

显示 CLI 输出的统计结果。

</process>

<notes>
- This skill calls `graph backfill-links` CLI command — deterministic Python code, not AI parsing
- Safe to re-run: idempotent (checks existing sections before adding)
- Depends on graph.json being up to date — run kb-fill-graph first if graph is stale
- Run after ANY kb-fill-* skill to ensure links are current
- Principle: critical logic lives in code (packages/cli/__main__.py), skill only orchestrates CLI calls
</notes>
