---
name: gsd-kb-fill
description: "Multi-agent AI fill for knowledge-base documentation — deep semantic extraction from source code"
argument-hint: "--module <module-name> --source <code-dir> --output <doc-dir> [--workers 4]"
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
Deep-fill knowledge-base documentation skeletons using AI agents that read and understand source code.

Unlike batch-fill (static regex/AST extraction), this skill uses multi-agent orchestration to:
- Trace function call chains to identify related tables and their operations (SELECT/INSERT/UPDATE/DELETE)
- Map API endpoints to frontend pages by following fetch/axios calls
- Extract error codes and HTTP status codes from exception handlers
- Infer business rules from conditional logic and validation code
- Identify upstream/downstream API dependencies

This is the "smart fill" step — it fills what regex cannot.

**CRITICAL**: This skill ALWAYS executes BOTH Phase 1 (CLI batch-fill) AND Phase 2 (AI semantic fill).
Phase 2 is NOT optional. The only way to skip Phase 2 is if the user explicitly passes `--no-semantic`.
If `--no-semantic` is NOT in the arguments, you MUST execute Phase 2 (requirement inference + AI deep fill).
</objective>

<process>

**⚠️ MANDATORY EXECUTION RULE — READ BEFORE ANYTHING ELSE:**
- This skill executes TWO phases in sequence. BOTH are mandatory. There is NO option to skip Phase 2.
- Phase 1: CLI batch-fill (fast static extraction)
- Phase 2: AI agent semantic fill (requirement inference + page fill + storage fill + API deep fill)
- After Phase 1 completes, you MUST IMMEDIATELY proceed to Phase 2. Do NOT stop. Do NOT report "Phase 2 跳过".
- `--semantic` parameter does not exist. `--no-semantic` is the only way to skip Phase 2.
- If you stop after Phase 1 without executing Phase 2, you have FAILED to execute this skill correctly.

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name in the docs output directory
- `--source <path>` (required): source code directory (backend). Accepts multiple comma-separated paths.
- `--output <path>` (optional, default: `.planning/ontology`): documentation output directory (where MODULE.md lives)
- `--frontend <path>` (optional): frontend source directory — auto-discovered if not specified
- `--models-dir <path>` (optional): ORM models directory — auto-discovered if not specified
- `--workers <n>` (optional, default: 4): number of parallel agents
- `--no-semantic` (optional): the ONLY way to skip Phase 2. If this flag is NOT present, Phase 2 MUST execute.

**🔒 Output 路径默认约定：**
- 不传 `--output` → 默认 `.planning/ontology`（项目根目录的 `.planning/ontology/` 下）
- 传了 `--output` → 使用用户指定路径（兼容旧行为）
- 最终文档位于 `$OUTPUT/$MODULE/`（如 `.planning/ontology/sandbox/`）
- 与 GSD 其他产物（phases/、quick/、debug/）同在 `.planning/ 下，保持一致性

**There is NO `--semantic` flag. Phase 2 always runs. Do not ask user to "add --semantic".**

If missing required args, prompt:
```
Usage: /gsd-kb-fill --module <module-name> --source <code-dir> [--output <doc-dir>]

Example:
  /gsd-kb-fill --module your-project --source C:/Code/your-project/backend --output docs/knows3
  /gsd-kb-fill --module sandbox --source C:/Code/your-project/backend/app/presentation/api/sandbox
  (不传 --output 时默认写入 .planning/ontology/)
```
  /gsd-kb-fill --module your-project --source C:/Code/your-project/backend --output docs/knows3
  /gsd-kb-fill --module sandbox --source C:/Code/your-project/backend/app/presentation/api/sandbox --output docs/test-sandbox
```

### Auto-discovery (runs by default):

1. **Frontend auto-discovery**: If `--frontend` not specified, look for a sibling or parent directory containing `package.json` with `next`/`vue`/`react` dependency. Common patterns:
   - `--source .../backend` → look for `../frontend`
   - `--source .../backend` → look for `../frontend` or `../web`
   - If found, use it to fill `pages/` docs with real component analysis

2. **Storage auto-discovery**: From the `--source` path, find the ORM models directory:
   - If `--models-dir` was passed, use it directly
   - Python: look for `*/models/` or `*/domain/models/` containing `__tablename__`
   - If ORM not found: fallback to extracting table names from generated API docs' "关联数据库" sections
   - Use it to fill `storage/` docs with field-level detail
   - NEVER silently produce 0 storage docs — always log why if no tables found

3. **Requirements are always generated** (default): requirement inference is part of the standard flow. Skip only with `--no-semantic`.

### Phase 1 CLI execution (exact commands):

Locate the KB CLI first:
```bash
KB_CLI="$HOME/.claude/knowledge-base"
# or: KB_CLI="$(find ~ -path "*/gsd-core/knowledge-base/packages/cli" -print -quit | sed 's|/packages/cli||')"
```

Then run batch-fill (**NOT `fill`** — `batch-fill` is the multi-file command):
```bash
cd "$KB_CLI"
PYTHONIOENCODING=utf-8 python -m packages.cli --kb-path "$OUTPUT" batch-fill --module "$MODULE" --source "$SOURCE_ROOT" --workers 8
```

**IMPORTANT**:
- The command is `batch-fill` (with hyphen), NOT `fill`
- `--kb-path` MUST be passed BEFORE the subcommand, pointing to `$OUTPUT`
- `--source` should point to project root (where skeleton path references resolve)

## Step 2: Execute Phase 2 — AI deep fill

After Phase 1 batch-fill completes, immediately invoke the AI orchestrator:

```
/gsd-kb-fill-ai --module "$MODULE" --source "$SOURCE_ROOT" --output "$OUTPUT" --frontend "$FRONTEND" --models-dir "$MODELS_DIR"
```

This orchestrator handles all AI fill steps in wave-based sequence:
- Wave 1: Storage discovery + Jobs discovery (parallel)
- Wave 2: Requirement inference (depends on storage/jobs)
- Wave 3: Page fill + API deep fill (parallel)
- Wave 4: Graph build
- Post-fill: Core data flows, git history, asset count validation

The orchestrator delegates to independent sub-skills (`kb-fill-storage`, `kb-fill-jobs`,
`kb-fill-requirements`, `kb-fill-pages`, `kb-fill-apis`, `kb-fill-graph`), each with
focused context for maximum quality.

**If `--no-semantic` was passed, skip this step entirely.**

## Step 3: Summary report

```
GSD > KB-FILL Complete
────────────────────────────────────────────────────────────
Module:     {module}
Source:     {source}
Phase 1:    batch-fill (static extraction)
Phase 2:    AI deep fill (orchestrated sub-skills)
────────────────────────────────────────────────────────────
```

</process>

<notes>
- This skill spawns multiple AI agents — expect it to take several minutes for large modules
- Each agent reads one source file + its skeleton, so context stays manageable
- Safe to re-run: only fills sections still containing "待补充"
- For very large modules (300+ APIs), consider running on a subset: --filter "apis/POST-*"
- Pair with /gsd-kb-init for end-to-end: scaffold → static fill → AI fill → graph
</notes>
