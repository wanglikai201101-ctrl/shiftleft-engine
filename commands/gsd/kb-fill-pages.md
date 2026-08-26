---
name: gsd-kb-fill-pages
description: "Page docs fill: orchestrator + template-driven extraction from frontend components"
argument-hint: "--module <name> --source <path> --output <path> --frontend <path> [--force]"
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
Orchestrate page documentation fill by:
1. Discovering frontend components matching page docs
2. Spawning agents that fill PAGE-TEMPLATE.md — not freeform generation
3. Post-fill: split oversized pages into sub-page docs

Each agent reads `templates/PAGE-TEMPLATE.md` and `sub-skills/FILL-SINGLE-PAGE.md`, replaces ALL {{PLACEHOLDER}} markers.
</objective>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required)
- `--source <path>` (required): backend source directory (for PROJECT_ROOT)
- `--output <path>` (optional, default: `.planning/ontology`)
- `--frontend <path>` (optional): frontend source directory
- `--force` (optional): re-fill ALL sections

**🔒 --force 行为（强制执行，不可跳过）：**
- **必须**重新读取前端组件源码并完整重写每个 page 文件
- **禁止**判断"现有文件已符合规范"而跳过
- 唯一不覆盖的是 `<!-- manual -->` 标记的段落

### Frontend auto-discovery (if --frontend not specified):
Walk up from `--source` to project root, look for sibling with `package.json` containing next/vue/react:
- `backend` → look for `../frontend`
- `backend` → look for `../frontend` or `../web`

If not found: log warning and STOP.

## Step 2: Inventory page docs

### 2a: Scan existing docs
List all `$OUTPUT/$MODULE/pages/*.md`. For each:
- **Without --force:** check if key sections contain "待补充". Skip filled ones.
- **With --force:** treat all as unfilled.

### 2b: Match to frontend components
For each page doc, find the corresponding frontend component:
- Read 基本信息 for 组件文件路径 hint
- Search frontend directory by page name pattern
- Next.js: `app/{path}/page.tsx`
- Vue: `src/views/{path}.vue` or `src/pages/{path}.vue`

## Step 3: Load template and sub-skill

```bash
SKILL_DIR=""
for candidate in \
  "$HOME/.claude/skills/gsd-kb-fill-pages" \
  "$(pwd)/skills/gsd-kb-fill-pages" \
  "$HOME/gsd-core/skills/gsd-kb-fill-pages"; do
  if [ -f "$candidate/templates/PAGE-TEMPLATE.md" ]; then
    SKILL_DIR="$candidate"
    break
  fi
done

TEMPLATE=$(cat "$SKILL_DIR/templates/PAGE-TEMPLATE.md")
SUB_SKILL=$(cat "$SKILL_DIR/sub-skills/FILL-SINGLE-PAGE.md")
```

## Step 4: Spawn agents (one per page)

For each page doc needing fill:

```
{SUB_SKILL content}

---
## Template (fill ALL {{PLACEHOLDER}} markers):
{TEMPLATE content}

---
## Context:

PAGE_NAME: {page-name}
MODULE: {module}
TODAY: {today}

## Frontend component source:
{component source code — or "NOT FOUND, infer from API docs below"}

## Component file path:
{relative path, e.g. "app/dashboard/sandbox/studio/StudioPageClient.tsx"}

## Extracted route path:
{route from file structure, e.g. "/dashboard/sandbox/studio"}

## Key imports (max 3 sub-components):
{imported component sources}

## Related API docs that reference this page:
{grep results from apis/*.md "关联前端页面" sections}

## File lists:
API_FILES: {list}
PAGE_FILES: {list}
STORAGE_FILES: {list}

---
🔒 YOUR OUTPUT MUST:
1. Be the complete filled template — every {{...}} replaced
2. Have 0 remaining {{PLACEHOLDER}} markers
3. 页面元素清单 >= 5 rows
4. 接口调用顺序 >= 3 API calls (backtick-wrapped)
5. 用户操作流 >= 5 rows (30%+ error paths)
6. Complex pages: include 状态管理架构 + Hooks sections

If output is missing template sections, it will be REJECTED.
```

## Step 5: Merge results

For each agent result:
1. Verify no `{{` placeholders remain
2. Write to `$OUTPUT/$MODULE/pages/{page-name}.md`
3. Preserve `<!-- manual -->` sections
4. Update 基本信息 (路由路径, 完整URL, 组件文件路径)

## Step 6: Post-fill split (oversized pages)

After all pages filled, check element counts:
1. Count rows in `## 页面元素清单` per page
2. If > 15 rows AND no child docs exist (`{page-name}-*.md`):
   - Identify sub-components (Panel/Drawer/Dialog/Tab)
   - Create sub-page docs with skeleton
   - Spawn fill agents for each sub-page
3. Skip if: <= 15 elements, child docs exist, or `<!-- no-split -->` present

## Step 7: Report

```
GSD > KB-FILL-PAGES Complete
────────────────────────────────────────────────────────────
Module:       {module}
Pages total:  {total}
Filled:       {filled}
Skipped:      {skipped}
Split:        {split_count} pages split into sub-pages
────────────────────────────────────────────────────────────
```

</process>

<notes>
- Template-driven: agents fill pre-defined structure, cannot skip sections
- Complex pages (Studio etc) get 状态管理/Hooks/布局 sections automatically
- Post-fill split: pages with >15 elements are split into sub-page docs
- Self-validation: output rejected if {{PLACEHOLDER}} remains
- Route path must start with / and not contain domain
</notes>
