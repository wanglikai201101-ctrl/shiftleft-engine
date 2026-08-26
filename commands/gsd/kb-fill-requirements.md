---
name: gsd-kb-fill-requirements
description: "Requirement inference from code: orchestrator + template-driven fill"
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
Orchestrate requirement document generation by:
1. Collecting source context (router, service, i18n, existing docs)
2. Grouping APIs by business capability
3. Spawning focused agents that fill a TEMPLATE — not freeform generation

Each agent reads `templates/REQ-TEMPLATE.md` and replaces ALL {{PLACEHOLDER}} markers.
This eliminates incomplete output — agents cannot skip sections because the structure is pre-defined.
</objective>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name
- `--source <path>` (required): backend source code directory
- `--output <path>` (optional, default: `.planning/ontology`): documentation output directory
- `--force` (optional): **完全重新生成所有 REQ 文档**

If `$OUTPUT/$MODULE/requirements/` already has files and `--force` is NOT passed, skip generation.

**🔒 --force 行为（强制执行，不可跳过）：**
- **必须**重新分析源代码并完整重写每个 REQ 文件
- **禁止**判断"现有文件已符合规范"而跳过
- 唯一不覆盖的是 `<!-- manual -->` 标记的段落

## Step 2: Discover domains and collect context

**2a. Determine domain scope:**
- If `--source` has `router.py` directly → single domain
- If `--source` has subdirs with routers → multi-domain

**2b. Service layer tracing (not limited to --source):**
```bash
ROUTER_FILE="$SOURCE/router.py"
grep -n "from\|import" "$ROUTER_FILE" | grep -i "service\|manager\|use_case"
```
Read imported service files (even if outside `--source`) — max 2 levels deep.

**2c. Collect all context per domain:**
- Router source (segmented if >100KB)
- Service/manager layer source
- State machine / Enum definitions
- i18n locale files (Chinese preferred)
- Existing API docs (关联数据库 + 错误码 sections)
- Existing storage/page/job doc filenames

**2d. Collect file lists for validation:**
```bash
API_FILES=$(ls "$OUTPUT/$MODULE/apis/"*.md 2>/dev/null | xargs -n1 basename)
PAGE_FILES=$(ls "$OUTPUT/$MODULE/pages/"*.md 2>/dev/null | xargs -n1 basename)
STORAGE_FILES=$(ls "$OUTPUT/$MODULE/storage/"*.md 2>/dev/null | xargs -n1 basename)
```

## Step 3: Group by business capability

Group APIs into business capabilities (NOT by HTTP method or path prefix):
- Shared state machine → same group
- Same user journey → same group
- Same core entity CRUD → same group

Each group → 1 REQ document → 1 agent.

## Step 4: Read template and sub-skill

```bash
TEMPLATE=$(cat "$SKILL_DIR/templates/REQ-TEMPLATE.md")
SUB_SKILL=$(cat "$SKILL_DIR/sub-skills/FILL-SINGLE-REQ.md")
```

`$SKILL_DIR` = the directory containing this SKILL.md file. Resolve it:
```bash
SKILL_DIR=""
for candidate in \
  "$HOME/.claude/skills/gsd-kb-fill-requirements" \
  "$(pwd)/skills/gsd-kb-fill-requirements" \
  "$HOME/gsd-core/skills/gsd-kb-fill-requirements"; do
  if [ -f "$candidate/templates/REQ-TEMPLATE.md" ]; then
    SKILL_DIR="$candidate"
    break
  fi
done
```

## Step 5: Spawn agents (one per REQ)

For each business capability group, spawn an agent with this prompt:

```
{SUB_SKILL content — the full FILL-SINGLE-REQ.md}

---

## Template (your output contract — fill ALL {{PLACEHOLDER}} markers):

{TEMPLATE content — the full REQ-TEMPLATE.md}

---

## Context for this requirement:

REQ-ID: {REQ_ID}
REQ-NAME: {REQ_NAME}
MODULE: {module}
MODULE_PREFIX: {prefix, e.g. SB}
TODAY: {today's date}

## Router source:
{router code for this group's APIs}

## Service layer source:
{service/manager code traced from router imports}

## State machine definitions:
{Enum/Literal/status field definitions}

## i18n / UI text:
{Chinese locale content, or English with translation}

## Existing API docs (关联数据库 + 错误码):
{Extracted sections from filled API docs}

## File lists for cross-reference:
API_FILES: {list}
PAGE_FILES: {list}
STORAGE_FILES: {list}

---

🔒 YOUR OUTPUT MUST:
1. Be the complete filled template — every {{...}} replaced
2. Have 0 remaining {{PLACEHOLDER}} markers
3. Be at least 250 lines for complex requirements (3+ sub-flows)
4. Contain ALL sections from the template (business flow, glossary, rules, TP, fixtures, edges, traceability)

If your output is missing any template section, it will be REJECTED.
```

## Step 6: Write files

For each agent result:
1. Verify no `{{` placeholders remain: `grep -c "{{" result` must be 0
2. If placeholders remain → log warning, ask agent to complete
3. Write to `$OUTPUT/$MODULE/requirements/REQ-{ID}.md`
4. With `--force`: overwrite (preserve `<!-- manual -->` sections)
5. Without `--force`: skip existing files

## Step 7: Update MODULE.md

After all REQs written:

**7a. Needs tracing table (全量刷新):**
- Scan all `requirements/REQ-*.md`
- Extract: REQ-ID, name, 关联接口, 关联表, 关联页面
- Rebuild MODULE.md 需求追溯表

**7b. Domain glossary (汇总):**
- Merge all REQ `### 领域术语` sections → MODULE.md `## 领域术语（模块级汇总）`

**7c. Business rules (汇总):**
- Top 10 rules from all REQ `### 业务规则与约束` → MODULE.md `## 核心业务规则`

**7d. Asset counts + timestamp:**
- Update file counts and 最后同步 date

## Step 8: Report

```
GSD > KB-FILL-REQUIREMENTS Complete
────────────────────────────────────────────────────────────
Module:       {module}
Domains:      {N} business capabilities
Requirements: {N} generated
Test points:  {total_TP} across all requirements
Avg lines:    {avg} per REQ (target: 250+)
────────────────────────────────────────────────────────────
```

</process>

<notes>
- Template-driven: agents fill a pre-defined structure, cannot skip sections
- Sub-skill contains analysis methodology (business flow/glossary/rules extraction)
- Self-validation: output rejected if any {{PLACEHOLDER}} remains
- Safe to re-run: skips existing files without --force
- Service layer tracing allowed beyond --source scope (2 levels max)
</notes>
