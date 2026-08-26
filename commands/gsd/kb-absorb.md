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
   - APPEND new row to table, or CORRECT existing value
   - Add 变更记录 row: `| {date} | kb-absorb | {source_file} | {patch_description} |`
2. Write updated doc

## Step 7: Rebuild graph

```bash
# Trigger graph rebuild (edges may have changed)
# Uses same KB CLI as kb-fill-graph
cd "$KB_CLI"
PYTHONIOENCODING=utf-8 python -m packages.cli --kb-path "$OUTPUT" graph build --output "$OUTPUT/$MODULE/graph"
PYTHONIOENCODING=utf-8 python -m packages.cli --kb-path "$OUTPUT" graph repair-orphans --output "$OUTPUT/$MODULE/graph"
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
Graph:       rebuilt ({new_edges} edges)
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
