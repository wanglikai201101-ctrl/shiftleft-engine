---
name: gsd-kb-init
description: "Initialize knowledge-base documentation and graph for a project module from source code"
argument-hint: "--source <code-dir> --module <module-name> [--output <doc-dir>] [--no-auto-detect]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
---



<objective>
Initialize knowledge-base documentation scaffolding and knowledge graph for a project module.

Scans source code directory, generates doc skeletons (MODULE.md + apis/ + storage/ + pages/ + jobs/),
builds the knowledge graph, and reports coverage.

Supports automatic subproject detection: when --source points to a root directory containing multiple
subprojects (identified by package.json, pyproject.toml, pom.xml, etc.), each subproject is scaffolded
as a separate module automatically.

This is the one-command entry point for bringing a module into the documentation system.
</objective>

<install>

**一键部署 / 首次安装：**

本 skill 与配套的 gsd-kb-* skills（如 gsd-kb-fill、gsd-kb-query、gsd-kb-gen-tests 等）、9 个 gsd-core 研发技能，以及 gsd-core 引擎，可通过一键脚本部署到 `~/.claude/`：

```bash
bash scripts/install-kb.sh
```

脚本安装内容：
- gsd-kb-* skills → `~/.claude/skills/`
- 9 个 gsd-core 研发技能 → `~/.claude/skills/`
- gsd-core 引擎 → `~/.claude/gsd-core/`

> 此部署属于**首次使用/安装**流程，用于安装整套 gsd-kb 工具链；
> 与 kb-init 本身的**文档初始化**职责（扫描源码、生成 doc skeleton、构建知识图谱）相互独立；
> 安装完成后，日常使用本 skill 无需重复执行此脚本。

</install>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--source <path>` (required): source code directory to scan. Accepts MULTIPLE paths separated by commas (e.g. `--source backend,frontend,models`)
- `--module <name>` (required): module name for the generated docs
- `--output <path>` (optional, default: `.planning/ontology`): documentation output directory
- `--no-auto-detect` (optional): disable subproject auto-detection, treat entire source as one module
- `--no-fill` (optional): skip auto-fill phase, only generate skeletons

**🔒 Output 路径默认约定：**
- 不传 `--output` → 默认 `.planning/ontology`（与 GSD 其他产物 phases/quick/debug 同级）
- 传了 `--output` → 使用用户指定路径（兼容旧行为）
- 最终文档位于 `$OUTPUT/$MODULE/`（如 `.planning/ontology/sandbox/`）

If `--source` or `--module` is missing, prompt:
```
Usage: /gsd-kb-init --source <code-dir>[,<code-dir2>,...] --module <module-name> [--output <doc-dir>]

Example:
  /gsd-kb-init --source src/billing --module billing
  /gsd-kb-init --source C:/Code/your-project --module your-project --output docs/kb
  /gsd-kb-init --source C:/Code/your-project/backend,C:/Code/your-project/frontend --module your-project
  (不传 --output 时默认写入 .planning/ontology/)
```

When multiple sources are provided:
- Each source is scaffolded into the SAME module output directory
- Backend sources contribute apis/, storage/, jobs/
- Frontend sources contribute pages/
- This produces a unified module with full-stack coverage

## Step 2: Locate knowledge-base CLI

```bash
# Check multiple possible locations
KB_CLI=""
if [ -d "knowledge-base/packages/cli" ]; then
  KB_CLI="$(pwd)/knowledge-base"
elif [ -d "$HOME/gsd-core/knowledge-base/packages/cli" ]; then
  KB_CLI="$HOME/gsd-core/knowledge-base"
elif [ -d "$HOME/.claude/gsd-core/../knowledge-base/packages/cli" ]; then
  KB_CLI="$HOME/.claude/gsd-core/../knowledge-base"
fi

if [ -z "$KB_CLI" ]; then
  echo "ERROR: knowledge-base not found. Expected at ./knowledge-base/ or ~/gsd-core/knowledge-base/"
  exit 1
fi
```

## Step 3: Run scaffold

`--source` supports multiple paths (space-separated via `nargs="+"`).

If the user provided multiple sources (comma or space separated), pass them all:
```bash
cd "$KB_CLI"
# Multiple sources: pass each as separate argument after --source
PYTHONIOENCODING=utf-8 python -m packages.cli scaffold --source $SOURCES --module "$MODULE" --output "$OUTPUT" --no-auto-detect
```

If single source with auto-detect:
```bash
cd "$KB_CLI"
PYTHONIOENCODING=utf-8 python -m packages.cli scaffold --source "$SOURCE" --module "$MODULE" --output "$OUTPUT"
```

Split user's `--source` value on commas into space-separated paths for the CLI call.
Example: user passes `--source a,b,c` → CLI gets `--source a b c`.

Display results: how many files generated, skipped, errors.

## Step 3.5: Auto-fill documentation (two-phase)

**Phase 1 — Static extraction (fast, seconds):**

Determine the SOURCE_ROOT for batch-fill: `--source` may point to a subdirectory
(e.g. `backend/app/presentation/api/sandbox`), but skeleton path references are relative
to the project root (e.g. `app\presentation\api\sandbox\router.py`). Walk up from `$SOURCE`
until you find `pyproject.toml` / `package.json` / `setup.py` — that's the SOURCE_ROOT.

```bash
cd "$KB_CLI"
# Determine SOURCE_ROOT (project root that skeleton paths are relative to)
SOURCE_ROOT="$SOURCE"
while [ ! -f "$SOURCE_ROOT/pyproject.toml" ] && [ ! -f "$SOURCE_ROOT/package.json" ] && [ ! -f "$SOURCE_ROOT/setup.py" ] && [ "$SOURCE_ROOT" != "/" ]; do
  SOURCE_ROOT=$(dirname "$SOURCE_ROOT")
done

PYTHONIOENCODING=utf-8 python -m packages.cli --kb-path "$OUTPUT" batch-fill --module "$MODULE" --source "$SOURCE_ROOT" --workers 8
```

This fills basic fields that AST/regex can extract (params, types, routes).
If auto-detect found multiple subprojects, run for each subproject.

**Phase 2 — AI deep fill (smart, minutes):**

Invoke `/gsd-kb-fill` to spawn agents that read code and fill semantic sections.
This is now the DEFAULT behavior — requirements, pages, and storage are all auto-discovered.

```
/gsd-kb-fill --module "$MODULE" --source "$SOURCE_ROOT" --output "$OUTPUT"
```

This automatically:
- Discovers frontend sibling directory and fills pages/ docs
- Discovers ORM models and fills storage/ docs with field-level detail
- Generates requirements/ with TP test points from functional domain analysis
- Fills API docs: 响应结构, 关联数据库, 错误码, 依赖接口, 关联前端页面

If running in `--quick` mode or user specifies `--no-fill`, skip Phase 2.

## Step 4: Build knowledge graph

```bash
cd "$KB_CLI"
PYTHONIOENCODING=utf-8 python -m packages.cli --kb-path "$OUTPUT" graph build --output "$OUTPUT/graph"
```

Note: `--kb-path` must point to the directory CONTAINING module subdirectories (e.g. `docs/knows3/`),
not the module directory itself. The graph builder iterates `{kb-path}/{module-name}/apis/*.md` etc.

Display: node count, edge count, module count.

## Step 5: Run coverage and orphan check

```bash
cd "$KB_CLI"
PYTHONIOENCODING=utf-8 python -m packages.cli --kb-path "$OUTPUT" graph orphans --output "$OUTPUT/graph"
```

Report orphan nodes if any.

## Step 6: Summary

Display final report:
```
GSD > KB-INIT Complete
────────────────────────────────────────
Module:     <module-name>
Source:     <source-dir>
Output:     <output-dir>

Generated:  X doc skeletons
Graph:      Y nodes, Z edges
Orphans:    N (or "none")
────────────────────────────────────────
Next steps:
  - Run `python -m packages.cli fill --doc <骨架> --code <代码>` to fill technical details
  - Review MODULE.md and add business descriptions
  - Run `python -m packages.cli check --module <module>` to verify consistency
```

</process>

<notes>
- This skill runs inline (no subagent spawn needed)
- Safe to run multiple times — scaffold skips existing files
- Graph build is idempotent — rebuilds from all module docs
- Works with any project that has Python/SQL/Vue/JS/TS source code
- Auto-detects subprojects by marker files: package.json, pyproject.toml, pom.xml, build.gradle, go.mod, Cargo.toml
- Recognizes frameworks: Next.js (App Router pages), Vue, React, Express, FastAPI, Django, Flask, NestJS
- Use --no-auto-detect to force single-module mode for a directory that contains marker files
</notes>
