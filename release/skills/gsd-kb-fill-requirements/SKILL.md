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

<critical-rules>
🚫 HALT — 逐条阅读以下规则，违反任何一条 = 输出无效，必须删除重做

1. 🚫 NEVER write files outside `$OUTPUT/$MODULE/requirements/` — 禁止写入 apis/, pages/, tech/, graph/, tests/, storage/, jobs/
2. 🚫 NEVER create files with non-standard names — only `REQ-{MODULE}-{NNN}.md` format
   - ✅ Allowed: `REQ-SB-001.md`, `REQ-SB-002.md`
   - ❌ Forbidden: `SERVICE-*.md`, `_INDEX.md`, `SUMMARY.md`
3. 🚫 NEVER document non-requirement concerns — this skill documents BUSINESS REQUIREMENTS only
4. 🚫 NEVER leave {{PLACEHOLDER}} in output — 所有模板变量必须替换
5. 🚫 NEVER generate REQ < 250 lines — 复杂需求（3+ 子流程）至少 250 行
6. 🚫 NEVER skip template sections — 输出必须包含模板中所有节（business flow, glossary, rules, TP, fixtures, edges, traceability）
7. 🚫 NEVER skip service layer tracing — 必须从 router imports 追踪 service/manager 层
8. 🚫 NEVER group by HTTP method — 必须按业务能力（shared state machine / user journey）分组
9. 🚫 NEVER spawn agent without inlining template + sub-skill content
10. 🚫 NEVER ignore --force flag — force 模式下必须重写，禁止判断"已存在"跳过
11. 🚫 NEVER write TP without 验证方式 — 每个 TP 必须指定 API/UI/DB 验证方式

每个 Step 完成后必须输出 checkpoint 标记，否则不得进入下一步。
</critical-rules>

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

If `$OUTPUT/$MODULE/requirements/` already has files and `--force` is NOT passed, do NOT regenerate from scratch — existing template-compliant docs are updated incrementally via UPDATE-FIRST Edits (see Step 6).

**🔒 --force 行为（强制执行，不可跳过）：**
- **必须**重新分析源代码并完整重写每个 REQ 文件
- **禁止**判断"现有文件已符合规范"而跳过
- 唯一不覆盖的是 `<!-- manual -->` 标记的段落

```
✅ CHECKPOINT-1: Arguments parsed
   MODULE: {name}
   SOURCE: {path} (exists: yes/no)
   OUTPUT: {path}
   FORCE: {yes/no}
   Existing REQ files: {N}
   Action: {generate all / update-first incremental (files exist, no --force) / force regenerate}
   如果 --source 不存在 → STOP，报错退出
```

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

```
✅ CHECKPOINT-2: Context collected
   Domain scope: {single/multi}
   Routers found: {N} (list paths)
   Service files traced: {N} (list paths)
   State machines found: {N} (list enum names)
   i18n files: {N}
   Existing API docs: {N}
   Existing page docs: {N}
   Existing storage docs: {N}
```

## Step 3: Group by business capability

Group APIs into business capabilities (NOT by HTTP method or path prefix):
- Shared state machine → same group
- Same user journey → same group
- Same core entity CRUD → same group

Each group → 1 REQ document → 1 agent.

```
✅ CHECKPOINT-3: Business capability groups
   Groups identified: {N}
   Per-group breakdown:
     {group_name}: {N} APIs, state_machine: {yes/no}, entity: {name}
   Grouping rationale: {brief explanation per group}
```

## Step 4: Read template and sub-skill

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

Read `$SKILL_DIR/templates/REQ-TEMPLATE.md` → `$TEMPLATE`
Read `$SKILL_DIR/sub-skills/FILL-SINGLE-REQ.md` → `$SUB_SKILL`

```
✅ CHECKPOINT-4: Template + sub-skill loaded
   SKILL_DIR: {path}
   TEMPLATE: {first 50 chars}...
   SUB_SKILL: {first 50 chars}...
   如果任一为空 → STOP，报错退出
```

## Step 5: Spawn agents (one per REQ)

For each business capability group, spawn an agent with ALL content inlined:

```
你是一个需求文档生成器。严格按照以下 SUB-SKILL 指令填充模板。

## 🚫 硬性约束
- 所有 {{PLACEHOLDER}} 必须替换，0 残留
- 复杂需求（3+ 子流程）至少 250 行
- 必须包含所有模板节：business flow, glossary, rules, TP, fixtures, edges, traceability
- 每个 TP 必须有明确的 验证方式（API/UI/DB）
- 按业务能力分组，不按 HTTP method 分组
- TP 的 depends_on 必须反映实际数据依赖

## SUB-SKILL 指令:
{$SUB_SKILL content — the full FILL-SINGLE-REQ.md}

---
## Template (your output contract — fill ALL {{PLACEHOLDER}} markers):
{$TEMPLATE content — the full REQ-TEMPLATE.md}

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
4. Contain ALL sections from the template
5. Every TP has 验证方式 filled (API/UI/DB)

If your output is missing any template section, it will be REJECTED.
```

```
✅ CHECKPOINT-5: Agents completed
   Total agents spawned: {N}
   Results received: {N}
   Placeholder-free: {N} / Still has {{...}}: {N}
   Per-REQ quality:
     {REQ_ID}: lines={N}, TPs={N}, sections_complete={yes/no}
```

## Step 6: Write files + self-validate

For each agent result:

**🔒 Self-validation (MUST pass before write):**
1. ✅ No `{{` placeholders remain (`grep -c "{{" result` == 0)
2. ✅ Line count >= 250 for complex REQs (3+ sub-flows)
3. ✅ All template sections present (count H2/H3 headers)
4. ✅ Every TP has 验证方式 filled
5. ✅ TP depends_on references valid TP IDs (within same REQ)
6. ✅ 关联接口 references match actual API doc filenames
7. ✅ 关联前端页面 references match actual page doc filenames

If validation fails → log error, retry agent once, then skip and report.

Write to `$OUTPUT/$MODULE/requirements/REQ-{ID}.md`:
- **🔒 UPDATE-FIRST 写入规则（更新优先，强制执行）：** 目标文档 **已存在** 且符合模板规范（所有必需 `##` 节齐全、关键字段无 `待补充`）→ **先 READ** 该文件，再用 **Edit 工具** 只修改受影响的节（更新值、插入/更新行、追加 `变更记录` 行）；**逐字节保留**所有未修改内容，**包括**文件现有的行尾风格（CRLF/LF）。完整 `Write` 仅用于：全新文档、`--force`、或文档缺失必需模板节（schema 迁移）
- With `--force`: full overwrite (preserve `<!-- manual -->` sections)
- Without `--force`: existing template-compliant docs → UPDATE-FIRST incremental Edit (above); skip docs that are already complete

```
✅ CHECKPOINT-6: Files written + validated
   Files written: {N}
   Validation passed: {N}
   Validation failed: {N} (details: ...)
   Retried: {N}
```

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

```
✅ CHECKPOINT-7: MODULE.md updated
   Tracing table entries: {N}
   Glossary terms merged: {N}
   Business rules summarized: {N}
```

## Step 8: Final report

```
GSD > KB-FILL-REQUIREMENTS Complete
────────────────────────────────────────────────────────────
Module:       {module}
Domains:      {N} business capabilities
Requirements: {N} generated
Test points:  {total_TP} across all requirements
Avg lines:    {avg} per REQ (target: 250+)
Validation:   {passed}/{total} files passed self-check
────────────────────────────────────────────────────────────
```

</process>

<validation>
执行结束后，对照以下清单做最终检查。任何 FAIL 项必须修复后重新输出：

| # | Check | FAIL condition |
|---|-------|----------------|
| 1 | Placeholder残留 | 任何文件中仍有 `{{` 模板变量 |
| 2 | 行数不足 | 复杂 REQ（3+ 子流程）< 250 行 |
| 3 | 模板缺节 | 输出缺少模板中定义的任何一级/二级标题 |
| 4 | TP 无验证方式 | 任何 TP 的 验证方式 列为空 |
| 5 | depends_on 无效 | TP 引用了不存在的 TP ID |
| 6 | 按 method 分组 | REQ 是按 GET/POST 分组而非业务能力 |
| 7 | --force 未执行 | --force 模式下有文件被跳过（非 manual 标记） |
| 8 | 关联引用无效 | 关联接口/页面/表 引用了不存在的文件 |
</validation>
