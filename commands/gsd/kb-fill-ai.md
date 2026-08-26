---
name: gsd-kb-fill-ai
description: "AI multi-agent deep fill orchestrator: coordinates storage, jobs, requirements, pages, APIs, and graph sub-skills"
argument-hint: "--module <module-name> --source <code-dir> --output <doc-dir> [--frontend <path>] [--models-dir <path>]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
  - Agent
---



<objective>
Orchestrate the AI deep-fill pipeline by coordinating 6 independent sub-skills in sequence.

This skill does NOT contain fill logic itself — it parses arguments, discovers paths,
then delegates to focused sub-skills that each handle one doc type with minimal context.

Sub-skills (executed in dependency order):
1. `/gsd-kb-fill-storage` — Storage discovery + fill
2. `/gsd-kb-fill-jobs` — Background task discovery
3. `/gsd-kb-fill-requirements` — Requirement inference (depends on storage/jobs existing)
4. `/gsd-kb-fill-pages` — Page docs fill (independent of requirements)
5. `/gsd-kb-fill-apis` — API deep fill (depends on requirements + storage existing)
6. `/gsd-kb-fill-graph` — Knowledge graph build (last, scans all docs)

Run `/gsd-kb-fill-tech` first for fast static extraction, then this for deep fill.
</objective>

<process>

## Step 1: Parse arguments and discover paths

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name
- `--source <path>` (required): backend source code directory
- `--output <path>` (optional, default: `.planning/ontology`): documentation output directory
- `--frontend <path>` (optional): frontend source, auto-discovered if not specified
- `--models-dir <path>` (optional): ORM models directory, auto-discovered if not specified
- `--only <step>` (optional): run only a specific sub-skill (storage|jobs|requirements|pages|apis|graph)

### Auto-discovery:

**Frontend**: Walk up from `--source` to project root, look for sibling with `package.json` containing next/vue/react:
- `backend` → look for `../frontend`
- `backend` → look for `../frontend` or `../web`

**Storage models**: From project root, find `*/domain/models/` or `*/models/` containing `__tablename__`

**PROJECT_ROOT**: Walk up from `--source` until `pyproject.toml` / `package.json` / `setup.py` found.

Store discovered paths for passing to sub-skills:
```
MODULE="{module}"
SOURCE="{source}"
OUTPUT="{output}"
FRONTEND="{discovered or passed frontend path}"
MODELS_DIR="{discovered or passed models path}"
PROJECT_ROOT="{resolved project root}"
```

## Step 2: Execute sub-skills

### If `--only` is specified, run only that sub-skill and skip to Step 4.

### Otherwise, execute in dependency order:

**Wave 1 (parallel — no dependencies between them):**
```
/gsd-kb-fill-storage --module $MODULE --source $SOURCE --output $OUTPUT --models-dir $MODELS_DIR
/gsd-kb-fill-jobs --module $MODULE --source $SOURCE --output $OUTPUT
```

**Wave 2 (depends on Wave 1 — storage and jobs must exist):**
```
/gsd-kb-fill-requirements --module $MODULE --source $SOURCE --output $OUTPUT
```

**Wave 3 (parallel — pages independent of requirements, APIs depend on requirements+storage):**
```
/gsd-kb-fill-pages --module $MODULE --source $SOURCE --output $OUTPUT --frontend $FRONTEND
/gsd-kb-fill-apis --module $MODULE --source $SOURCE --output $OUTPUT
```

**Wave 4 (last — needs all docs to exist for complete graph):**
```
/gsd-kb-fill-graph --module $MODULE --output $OUTPUT
```

Note: If running sub-skills as Agent calls (not literal /slash commands), pass the full
argument string to each agent and let it parse. Each sub-skill is self-contained.

## Step 3: Post-fill tasks

### 3.1: Generate core data flows in MODULE.md

After requirements and APIs are filled, generate a "核心数据流" section:
1. Select 2-3 highest priority requirements (P0/P1) that represent end-to-end user journeys
2. For each, trace: 前端操作 → API 调用 → DB 写入/读取 → 事件/响应
3. Insert after "业务概述" in MODULE.md:

```markdown
## 核心数据流

### {链路名称}（来自 REQ-xxx）

```
1. 用户在 {page} 页面 {操作}
   → 前端调用: {API endpoint}
2. 后端处理: {关键逻辑}
   → 写入: {table}（{关键字段}）
3. {后续动作}
```
```

### 3.2: Fill 负责人 and 创建时间 from git history

Check if `--source` is inside a git repository:
```bash
cd "$PROJECT_ROOT" && git rev-parse --is-inside-work-tree 2>/dev/null
```
If not a git repo, skip.

**MODULE.md:**
```bash
MODULE_OWNER=$(cd "$PROJECT_ROOT" && git shortlog -sn -- "$SOURCE_RELATIVE_PATH" | head -1 | sed 's/^[[:space:]]*[0-9]*[[:space:]]*//')
MODULE_CREATED=$(cd "$PROJECT_ROOT" && git log --follow --diff-filter=A --format='%ai' -- "$SOURCE_RELATIVE_PATH" | tail -1 | cut -d' ' -f1)
```
Update MODULE.md: replace `负责人：代码中未明确` → `负责人：{MODULE_OWNER}`, update 创建时间.

**API docs:**
For each `apis/*.md`, extract source file from `> 源函数:`, then:
```bash
API_OWNER=$(cd "$PROJECT_ROOT" && git log -1 --format='%aN' -- "$SOURCE_FILE")
```

**Page docs:**
For each `pages/*.md`, extract component from `> 组件:`, then:
```bash
PAGE_OWNER=$(cd "$PROJECT_ROOT" && git log -1 --format='%aN' -- "$COMPONENT_FILE")
```

Rules:
- Only overwrite "待补充" or "代码中未明确" — never overwrite human-entered names
- If git command fails or returns empty, leave as "代码中未明确"

### 3.3: Update MODULE.md asset counts

Re-count actual files in each directory and update "模块资产清单" table:
- Count files in `apis/`, `storage/`, `pages/`, `jobs/`, `requirements/`
- If a directory has 0 docs AND genuinely no assets, annotate: `0（该模块无{类型}）`
- If 0 docs but SHOULD have assets (referenced in other docs), annotate: `0（⚠️ 待补充）`

## Step 4: Summary report

```
GSD > KB-FILL-AI Complete
────────────────────────────────────────────────────────────
Module:       {module}
Requirements: {N} generated (with TP test points)
Pages filled: {N}/{total}
Storage filled: {N}/{total}
APIs filled:  {N}/{total}
Jobs:         {N} (or "0 — 该模块无定时任务")
Graph:        {nodes} nodes, {edges} edges
负责人:       {owner}
创建时间:     {date}
────────────────────────────────────────────────────────────
```

</process>

<notes>
- This is an ORCHESTRATOR — it delegates to sub-skills, does not contain fill logic
- Each sub-skill runs in its own context with minimal prompt size
- Use `--only <step>` to re-run a specific sub-skill independently
- Wave-based execution: storage+jobs → requirements → pages+apis → graph
- Post-fill tasks (data flow, git history, asset counts) run after all sub-skills complete
- Safe to re-run: each sub-skill is idempotent (fills only "待补充" placeholders)
- Total time: ~5-15 minutes for a full module (sub-skills run in waves)
</notes>
