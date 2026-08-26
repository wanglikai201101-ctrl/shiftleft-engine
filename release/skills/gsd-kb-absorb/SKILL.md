---
name: gsd-kb-absorb
description: "Absorb .planning/ artifacts into KB docs — incremental patch, not rewrite"
argument-hint: "--module <name> --output <path> [--since <date|commit>] [--files <paths>] [--dir <path>] [--dry-run]"
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
Absorb knowledge from .planning/ artifacts (debug, quick, research, verification, deviation)
into KB documentation as incremental patches.

NOT a rewrite — only appends new rows / corrects existing values.
Preserves <!-- manual --> sections. Outputs ABSORB-REPORT.md for review before commit.

Sub-skills handle each source type independently:
- ABSORB-DEBUG.md → edge cases + business rules + error codes
- ABSORB-QUICK.md → API changes + state transitions
- ABSORB-RESEARCH.md → glossary + architecture
- ABSORB-VERIFICATION.md → TP result corrections
</objective>

<process>

## CLI resolution

Resolve the KB CLI path ONCE at the start. Use the resolved `$KB_CLI` directly — do NOT search `$HOME` or reverse-engineer the CLI from source:

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

If KB_CLI is still empty, return an error immediately — do NOT search $HOME or reverse-engineer the CLI from source.

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required)
- `--output <path>` (optional, default: `.planning/ontology`)
- `--since <date|commit>` (optional): only absorb files modified after this point. Default: read `.planning/ontology/.last-absorb` timestamp
- `--files <path1,path2,...>` (optional): absorb specific files only (comma-separated)
- `--dir <path>` (optional): absorb all .md files in a specific directory
- `--dry-run` (optional): output ABSORB-REPORT.md only, don't patch docs

## Step 2: Scan changed .planning/ files

**Three modes (mutually exclusive, priority: --files > --dir > --since):**

### Mode A: Specific files (`--files`)
```bash
# Directly use the provided file list, no time-based filtering
FILES="file1.md,file2.md,..."
# Split by comma, verify each exists
```

### Mode B: Specific directory (`--dir`)
```bash
# Scan all .md files in the given directory (recursive)
find "$DIR" -name "*.md" -type f
```

### Mode C: Time-based scan (default, uses `--since` or `.last-absorb`)
```bash
ABSORB_FILE="$OUTPUT/$MODULE/.last-absorb"

if [ ! -f "$ABSORB_FILE" ]; then
  # 首次执行：不扫描历史文件，只初始化时间戳
  echo "First run: initializing .last-absorb timestamp. No files to absorb."
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$ABSORB_FILE"
  exit 0  # STOP — 旧文件对应旧代码逻辑，KB 已从当前代码生成，历史积累无意义
fi

# 非首次执行：只扫描上次 absorb 之后的增量
find .planning/debug/ -name "*.md" -newer "$ABSORB_FILE" 2>/dev/null
find .planning/quick/ -name "SUMMARY.md" -newer "$ABSORB_FILE" 2>/dev/null
find .planning/quick/ -name "PLAN.md" -newer "$ABSORB_FILE" 2>/dev/null
find .planning/research/ -name "*.md" -newer "$ABSORB_FILE" 2>/dev/null
find .planning/phases/ -name "VERIFICATION.md" -newer "$ABSORB_FILE" 2>/dev/null
find .planning/phases/ -name "DEVIATION.md" -newer "$ABSORB_FILE" 2>/dev/null
```

**首次执行行为（🔒 强制）：**
- `.last-absorb` 不存在 → 创建时间戳 → STOP（不扫描任何文件）
- 理由：KB 已从当前代码生成，旧的 debug/quick/research 记录对应旧逻辑，反哺会引入过时信息
- 如果确实需要吸收旧文件 → 用 `--files` 或 `--dir` 显式指定

If no files found → print "No new .planning/ artifacts since last absorb." and STOP.

## Step 3: Classify and dispatch

Group files by source type, then spawn sub-skill agents in parallel:

| Source | Sub-skill | Target KB docs |
|--------|-----------|---------------|
| `debug/*.md` | ABSORB-DEBUG | REQ (边缘场景 + 业务规则), API (错误码) |
| `quick/*/SUMMARY.md` | ABSORB-QUICK | API (参数/响应), Storage (字段), REQ (状态矩阵) |
| `research/*.md` | ABSORB-RESEARCH | REQ (领域术语), MODULE.md (架构) |
| `phases/*/VERIFICATION.md` | ABSORB-VERIFICATION | REQ (TP 预期结果修正) |
| `phases/*/DEVIATION.md` | ABSORB-VERIFICATION | REQ (业务规则修正 + 范围调整) |

## Step 4: Load sub-skills and spawn agents

```bash
SKILL_DIR=""
for candidate in \
  "$HOME/.claude/skills/gsd-kb-absorb" \
  "$(pwd)/skills/gsd-kb-absorb" \
  "$HOME/gsd-core/skills/gsd-kb-absorb"; do
  if [ -d "$candidate/sub-skills" ]; then
    SKILL_DIR="$candidate"
    break
  fi
done
```

🔒 MUST use the Agent tool to spawn one sub-agent per source type, in PARALLEL (single message, multiple Agent calls). Do NOT process sources inline sequentially. If you cannot spawn sub-agents, stop and report.

For each source type with files, spawn an agent:

```
{SUB_SKILL content}

---
## Source files to absorb:
{file contents}

## Target KB docs directory:
$OUTPUT/$MODULE/

## Existing KB docs (for context):
{relevant sections from target docs — only the sections that might be patched}

---
🔒 Rules:
- APPEND only — never delete existing rows
- Skip <!-- manual --> sections entirely
- Output format: structured patch list (see sub-skill for format)
```

## Step 5: Merge patches + generate ABSORB-REPORT.md

Collect all agent outputs (structured patch lists). Write `$OUTPUT/$MODULE/ABSORB-REPORT.md`:

```markdown
# KB Absorb Report — {date}

## Summary
- Sources scanned: {N} files
- Patches proposed: {N}
- Target docs affected: {N}

## Patches

### From debug/
| Target Doc | Section | Action | Content | Source |
|-----------|---------|--------|---------|--------|
| REQ-SB-003.md | 边缘场景 | APPEND row | EDGE-SB-003-09: S3 presigned 过期... | debug/fix-publish-timeout.md |
| POST-{agent_id}-publish.md | 错误码 | APPEND row | 504: S3 上传超时... | debug/fix-publish-timeout.md |

### From quick/
...

### From verification/
| Target Doc | Section | Action | Content | Source |
|-----------|---------|--------|---------|--------|
| REQ-SB-003.md | TP-SB-003-04 预期结果 | CORRECT | "200" → "201" | phases/p3/VERIFICATION.md |
```

## Step 6: Apply patches (unless --dry-run)

If NOT `--dry-run`:
1. For each patch in ABSORB-REPORT.md:
   - Read target doc
   - Find target section (by `##` heading match)
   - Skip if section has `<!-- manual -->`
   - **防重复（幂等检查）**：APPEND 前先 grep 目标 section 是否已含该行内容（或该行 ID，如 EDGE-xxx-NN / BR-xxx-NN / 错误码行）。已存在 → 跳过（说明上次已写入，禁止重复追加）。CORRECT 同理：先查旧值是否已是目标值，是则跳过。
   - APPEND new row to table, or CORRECT existing value
   - Add 变更记录 row: `| {date} | kb-absorb | {source_file} | {patch_description} |`
2. Write updated doc
3. **断点前移（防重复）**：全部 patch 写盘成功后，立即更新 `.last-absorb`（`date -u +"%Y-%m-%dT%H:%M:%SZ" > "$OUTPUT/$MODULE/.last-absorb"`），再执行 graph rebuild（Step 7）
4. If ANY KB doc was written, set `PATCHED_KB_DOCS=1` (used by the Step 7 guard); otherwise leave it unset.

> 🔒 **`.last-absorb` 断点时机**：`.last-absorb` 不再是"最后一步收尾动作"，而是"Step 6 patch 全部写盘成功后立刻写入"的断点。中途死亡后重试重扫时，用新时间戳过滤增量，配合上面逐条查重，可避免对同批内容重复 APPEND / 换新 ID / 重复 changelog。graph rebuild（Step 7）在断点之后执行，即使 rebuild 失败也可安全重试。

## Step 7: Rebuild graph (CONDITIONAL)

🔒 Guard: Only run this step if the absorbed patches modified KB docs or module structure (docs under `$OUTPUT/$MODULE/` were patched, or edges may have changed). If the absorb only touched planning artifacts (PLAN.md / REPORT.md / debug notes) with NO KB doc changes, SKIP the rebuild entirely and note it in the report.

```bash
# PATCHED_KB_DOCS=1 is set in Step 6 when any KB doc was written
if [ -n "${PATCHED_KB_DOCS:-}" ]; then
  # Trigger graph rebuild (edges may have changed)
  # Uses same KB CLI as kb-fill-graph
  cd "$KB_CLI"
  PYTHONIOENCODING=utf-8 python -m packages.cli --kb-path "$OUTPUT" graph build --output "$OUTPUT/$MODULE/graph"
  PYTHONIOENCODING=utf-8 python -m packages.cli --kb-path "$OUTPUT" graph repair-orphans --output "$OUTPUT/$MODULE/graph"
fi
```

## Step 8: Update timestamp + report

```bash
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$OUTPUT/$MODULE/.last-absorb"
```

```
GSD > KB-ABSORB Complete
────────────────────────────────────────────────────────────
Module:      {module}
Scanned:     {N} source files
Patches:     {applied}/{proposed} applied
Docs patched:{N} files updated
Graph:       rebuilt ({new_edges} edges) | skipped (no KB doc changes)
Report:      ABSORB-REPORT.md (review before commit)
────────────────────────────────────────────────────────────
```

</process>

<notes>
- Incremental: only appends/corrects, never deletes or rewrites
- Auditable: ABSORB-REPORT.md lists every patch for review
- Idempotent: .last-absorb timestamp prevents re-processing
- --dry-run: preview patches without applying
- Respects <!-- manual --> protection
- Rebuilds graph after patching (new edges may emerge)
- Trigger suggestion: after /gsd:ship or /gsd:complete-milestone
</notes>
