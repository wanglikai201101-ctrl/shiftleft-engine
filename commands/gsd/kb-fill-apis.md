---
name: gsd-kb-fill-apis
description: "API deep semantic fill: orchestrator + template-driven fill"
argument-hint: "--module <name> --source <path> --output <path> [--force]"
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
Orchestrate API documentation fill by:
1. Classifying APIs (simple vs complex)
2. Reading source functions
3. Spawning agents that fill API-TEMPLATE.md — not freeform generation
4. Backfilling reverse traceability (需求来源 section)

Each agent reads `templates/API-TEMPLATE.md` and `sub-skills/FILL-SINGLE-API.md`, replaces ALL {{PLACEHOLDER}} markers.
</objective>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required)
- `--source <path>` (required): backend source code directory
- `--output <path>` (optional, default: `.planning/ontology`)
- `--force` (optional): re-fill ALL sections

**🔒 --force 行为（强制执行，不可跳过）：**
- **必须**重新读取源代码并完整重写每个 API 文档
- **禁止**判断"现有文件已符合规范"而跳过
- 唯一不覆盖的是 `<!-- manual -->` 标记的段落

## Step 1.5: Check traceability state

```bash
# How many API docs have ## 需求来源 section?
TRACED=$(grep -rl "## 需求来源" "$OUTPUT/$MODULE/apis/"*.md 2>/dev/null | wc -l)
TOTAL=$(ls "$OUTPUT/$MODULE/apis/"*.md 2>/dev/null | wc -l)
# Any REQ docs with [待创建]?
PENDING=$(grep -rl "\[待创建\]" "$OUTPUT/$MODULE/requirements/"*.md 2>/dev/null | wc -l)
```

Set `TRACEABILITY_NEEDED=true` if TRACED < TOTAL or PENDING > 0.
**Step 6 ALWAYS runs if TRACEABILITY_NEEDED=true, even when content is already filled.**

## Step 2: Inventory and classify

**Without --force:** scan for docs with "待补充" in key sections. Skip already-filled files.
**With --force:** treat ALL API docs as unfilled.

Classify by reading source function:
- **Simple** (batch, max 5 per agent): single-entity CRUD, <30 lines, simple repo calls
- **Complex** (1 per agent): multi-step flows, state machines, 3+ service calls, >30 lines

## Step 3: Load template and sub-skill

```bash
SKILL_DIR=""
for candidate in \
  "$HOME/.claude/skills/gsd-kb-fill-apis" \
  "$(pwd)/skills/gsd-kb-fill-apis" \
  "$HOME/gsd-core/skills/gsd-kb-fill-apis"; do
  if [ -f "$candidate/templates/API-TEMPLATE.md" ]; then
    SKILL_DIR="$candidate"
    break
  fi
done

TEMPLATE=$(cat "$SKILL_DIR/templates/API-TEMPLATE.md")
SUB_SKILL=$(cat "$SKILL_DIR/sub-skills/FILL-SINGLE-API.md")
```

## Step 4: Spawn agents (max 15 APIs per round)

**🔒 Rate limiting:** max 15 APIs per round. Multiple rounds if needed.

**Batch mode (simple APIs, max 5 per agent):**
```
{SUB_SKILL content}

---
## Template (fill ALL {{PLACEHOLDER}} markers):
{TEMPLATE content}

---
## APIs to fill (output each with ===FILE: {filename}=== separator):
{for each: METHOD, PATH, function name, source code}

## Related storage docs:
{table summaries}

## File lists:
API_FILES: {list}
PAGE_FILES: {list}
STORAGE_FILES: {list}
REQ_FILES: {list}

🔒 Output ALL template sections for EACH API. Zero {{PLACEHOLDER}} allowed.
```

**Dedicated mode (complex APIs, 1 per agent):**
Same prompt structure but with single API + full function source + imported service code.

## Step 5: Merge results

For each agent result:
1. Verify no `{{` placeholders remain
2. Parse `===FILE:` separators (batch mode)
3. Write/overwrite API docs
4. Preserve `<!-- manual -->` sections
5. Post-merge validation: `grep -l "待补充" "$OUTPUT/$MODULE/apis/"*.md | wc -l`

If all APIs in a round still contain "待补充" → retry with batch size 3.

## Step 5.5: Update MODULE.md

1. Update asset counts
2. Backfill `[待创建]` links in requirement docs
3. Rebuild 需求追溯 table
4. Update 最后同步时间戳

## Step 6: Backfill reverse traceability (🔒 ALWAYS runs if TRACEABILITY_NEEDED)

**6a: Fill "需求来源" in each API doc:**
```bash
for api_file in "$API_DIR"/*.md; do
  api_basename=$(basename "$api_file")
  matched_reqs=$(grep -l "$api_basename" "$REQ_DIR"/*.md 2>/dev/null)
  # Build ## 需求来源 section from matches
  # Insert/replace in API doc
done
```

**6b: Backfill "关联接口" links in REQ docs** — replace `[待创建]` with actual file links
**6c: Backfill "关联数据库" links in REQ docs**
**6d: Backfill "关联前端页面" links in REQ docs**

## Step 7: Report

```
GSD > KB-FILL-APIS Complete
────────────────────────────────────────────────────────────
Module:      {module}
APIs total:  {total}
Batch mode:  {batch_count} simple APIs
Dedicated:   {dedicated_count} complex APIs
Skipped:     {skipped}
Traceability: {traced}/{total} APIs linked to REQ
────────────────────────────────────────────────────────────
```

</process>

<notes>
- Template-driven: agents fill pre-defined structure, cannot skip sections
- Max 15 APIs per round prevents context overflow
- Batch (5/agent) for simple, dedicated (1/agent) for complex
- Step 6 runs unconditionally for traceability — even if content is filled
- Self-validation: output rejected if {{PLACEHOLDER}} remains
</notes>
