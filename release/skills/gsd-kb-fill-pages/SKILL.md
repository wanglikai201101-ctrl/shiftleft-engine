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

<critical-rules>
🚫 HALT — 逐条阅读以下规则，违反任何一条 = 输出无效，必须删除重做

1. 🚫 NEVER write files outside `$OUTPUT/$MODULE/pages/` — 禁止写入 apis/, storage/, tech/, graph/, tests/, requirements/, jobs/
2. 🚫 NEVER create files with non-standard names — only `{page-slug}.md` format (lowercase, hyphen-separated)
   - ✅ Allowed: `sandbox-management.md`, `sandbox-studio.md`, `agent-detail.md`
   - ❌ Forbidden: `SERVICE-*.md`, `_INDEX.md`, `SUMMARY.md`
3. 🚫 NEVER document non-page concerns — this skill documents FRONTEND PAGES only
   - ❌ Forbidden: API endpoint docs, table schemas, service class docs, job docs
   - ✅ Allowed: page route, components, user interactions, API calls from page
4. 🚫 NEVER skip frontend component reading — 必须读取实际组件源码，不可凭空推断
5. 🚫 NEVER leave {{PLACEHOLDER}} in output — 所有模板变量必须替换
6. 🚫 NEVER generate 页面元素清单 < 5 rows — 每个页面至少 5 个可交互元素
7. 🚫 NEVER generate 用户操作流 < 5 rows — 且 30%+ 必须是异常路径
8. 🚫 NEVER generate 接口调用顺序 < 3 entries — 页面至少调用 3 个 API
9. 🚫 NEVER skip route path resolution — 路由必须从文件结构或代码中提取
10. 🚫 NEVER spawn agent without inlining template + sub-skill content
11. 🚫 NEVER ignore --force flag — force 模式下必须重写，禁止判断"已符合规范"跳过

每个 Step 完成后必须输出 checkpoint 标记，否则不得进入下一步。
</critical-rules>

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
- `backend` → look for `../frontend`（example heuristic，可 per-project 用 `--frontend` 显式覆盖；非此命名项目走下方通用 fallback）
- `backend` → look for `../frontend` or `../web`（通用 fallback，主路径 — 换项目按实际目录自动发现）

```
✅ CHECKPOINT-1: Arguments parsed
   MODULE: {name}
   SOURCE: {path} (exists: yes/no)
   OUTPUT: {path}
   FRONTEND: {path} (exists: yes/no, framework: next/vue/react)
   FORCE: {yes/no}
   如果 frontend 不存在且无法自动发现 → STOP，报错退出
```

## Step 2: Inventory page docs

### 2a: Discover NEW pages from frontend (🔒 mandatory — prevents under-scan)

🚫 不能只 fill 已有文档。必须先从前端路由中发现所有应有页面，再对比已有文档。

**Next.js (App Router):**
```bash
# 找到所有 page.tsx / page.ts（每个都是一个路由页面）
find "$FRONTEND/app" -name "page.tsx" -o -name "page.ts" 2>/dev/null | grep -v node_modules | grep -v __tests__
```

**Next.js (Pages Router):**
```bash
find "$FRONTEND/pages" -name "*.tsx" -o -name "*.ts" 2>/dev/null | grep -v node_modules | grep -v _app | grep -v _document | grep -v __tests__
```

**Vue (file-based routing):**
```bash
find "$FRONTEND/src/views" -name "*.vue" 2>/dev/null
find "$FRONTEND/src/pages" -name "*.vue" 2>/dev/null
```

**Module scope filter (🔒 关键 — 只保留与 --module 相关的页面):**
```bash
# 从发现的路由文件中，只保留路径含 module 名相关关键词的页面
# 例如 --module sandbox → 保留含 sandbox/agent/studio 等关键词的路由
MODULE_KEYWORDS=$(derive_keywords_from_module "$MODULE")
# sandbox → "sandbox|agent|studio|session"（从已有 pages/*.md 文件名提取关键词）

for page_file in $DISCOVERED_PAGES; do
  route=$(extract_route_from_path "$page_file")
  if matches_module_scope "$route" "$MODULE_KEYWORDS"; then
    SCOPED_PAGES+=("$page_file")
  fi
done
```

**关键词推导规则：**
1. 从 `$OUTPUT/$MODULE/pages/*.md` 已有文件名提取关键词（去掉 .md 后缀，按 `-` 分割）
2. 从 `$OUTPUT/$MODULE/MODULE.md` 的描述中提取实体名
3. 模块名本身（如 `sandbox`）
4. 如果是子模块路径（如 `--source` 含 `services/sandbox`），取最后一段

**对比已有文档，发现缺失：**
```bash
EXISTING_PAGES=$(ls "$OUTPUT/$MODULE/pages/"*.md 2>/dev/null | xargs -I {} basename {} .md)

for page_file in ${SCOPED_PAGES[@]}; do
  page_slug=$(route_to_slug "$page_file")
  if ! echo "$EXISTING_PAGES" | grep -q "^${page_slug}$"; then
    MISSING_PAGES+=("$page_file → $page_slug")
  fi
done
```

**自动 scaffold 缺失页面：**
```bash
for missing in ${MISSING_PAGES[@]}; do
  # 创建骨架文件
  cat > "$OUTPUT/$MODULE/pages/${page_slug}.md" << EOF
# ${page_slug} — 待补充

> 自动发现于: ${page_file}
> 路由: ${route}

## 基本信息
| 字段 | 值 |
|------|-----|
| 页面名称 | 待补充 |
| 路由路径 | ${route} |
| 组件文件路径 | ${page_file} |
| 所属模块 | ${MODULE} |
EOF
done
```

```
✅ CHECKPOINT-2a: Page discovery
   Frontend pages found (total): {N}
   Module-scoped pages: {N}
   Already documented: {N}
   NEW pages discovered: {N} — {list slugs}
   Auto-scaffolded: {N}
```

### 2b: Scan existing docs (including newly scaffolded)

List all `$OUTPUT/$MODULE/pages/*.md`. For each:
- **Without --force:** check if key sections contain "待补充". Skip filled ones.
- **With --force:** treat all as unfilled.

### 2c: Match to frontend components
For each page doc, find the corresponding frontend component:
- Read 基本信息 for 组件文件路径 hint
- Search frontend directory by page name pattern
- Next.js: `app/{path}/page.tsx` or `{path}Client.tsx`
- Vue: `src/views/{path}.vue` or `src/pages/{path}.vue`

```
✅ CHECKPOINT-2: Inventory complete
   Page docs found: {N} (list names)
   Need fill: {N} (list names)
   Skipped (already filled): {N}
   Component matches:
     {page_name} → {component_path} ✅
     {page_name} → NOT FOUND ❌
   如果所有 page 都 matched → proceed
   如果有 NOT FOUND → log warning, proceed with API-only inference for those
```

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
```

Read `$SKILL_DIR/templates/PAGE-TEMPLATE.md` → `$TEMPLATE`
Read `$SKILL_DIR/sub-skills/FILL-SINGLE-PAGE.md` → `$SUB_SKILL`

```
✅ CHECKPOINT-3: Template + sub-skill loaded
   SKILL_DIR: {path}
   TEMPLATE: {first 50 chars}...
   SUB_SKILL: {first 50 chars}...
   如果任一为空 → STOP，报错退出
```

## Step 4: Spawn agents (one per page)

For each page doc needing fill, spawn an Agent with ALL content inlined:

```
你是一个前端页面文档生成器。严格按照以下 SUB-SKILL 指令填充模板。

## 🚫 硬性约束
- 页面元素清单 >= 5 rows
- 用户操作流 >= 5 rows（30%+ error paths）
- **用户操作流必须填"跳转目标"列**: 有跳转副作用的行填具体目标路由(如 `/dashboard/agent`、`/orders/{order_id}`),无跳转填 `—`;禁止写"跳管理页/跳回列表"这类无路由描述。此列是跨页流程测试的结构化数据源
- 接口调用顺序 >= 3 API calls（backtick-wrapped）
- 路由路径必须从文件结构提取，以 / 开头
- 所有 {{PLACEHOLDER}} 必须替换，不得残留
- 复杂页面（Studio etc）必须包含 状态管理架构 + Hooks sections
- 表单验证模式: 有表单/dialog 的页面必须填写验证模式 section（从源码 submit button disabled prop 和 error state 渲染方式提取证据）

## SUB-SKILL 指令:
{$SUB_SKILL content}

---
## Template (fill ALL {{PLACEHOLDER}} markers):
{$TEMPLATE content}

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
7. 表单验证模式: 有表单/dialog → 必须填写验证模式表 (DISABLE_UNTIL_VALID/ERROR_ON_SUBMIT/etc) + 源码证据; 无表单 → 写 "本页面无表单验证"

If output is missing template sections, it will be REJECTED.
```

```
✅ CHECKPOINT-4: Agents completed
   Total agents spawned: {N}
   Results received: {N}
   Placeholder-free: {N} / Still has {{...}}: {N}
   Per-page quality:
     {page_name}: elements={N}, flows={N}, APIs={N} ✅/❌
```

## Step 5: Merge results + self-validate

For each agent result:

**🔒 Self-validation (MUST pass before write):**
1. ✅ No `{{` placeholders remain (`grep -c "{{" result` == 0)
2. ✅ 页面元素清单 table has >= 5 data rows
3. ✅ 用户操作流 table has >= 5 data rows (count error paths >= 30%)
4. ✅ 接口调用顺序 has >= 3 backtick-wrapped API entries
5. ✅ 路由路径 starts with `/` and contains no domain
6. ✅ All template sections present (基本信息, 元素清单, 操作流, 接口调用, 数据流转)

If validation fails → log error, retry agent once, then skip and report.

Write to `$OUTPUT/$MODULE/pages/{page-name}.md`:
- **🔒 UPDATE-FIRST 写入规则（更新优先，强制执行）：** 目标文档 **已存在** 且符合模板规范（所有必需 `##` 节齐全、关键字段无 `待补充`）→ **先 READ** 该文件，再用 **Edit 工具** 只修改受影响的节（更新值、插入/更新行、追加 `变更记录` 行）；**逐字节保留**所有未修改内容，**包括**文件现有的行尾风格（CRLF/LF）。完整 `Write` 仅用于：全新文档、`--force`、或文档缺失必需模板节（schema 迁移）
- Preserve `<!-- manual -->` sections
- Update 基本信息 (路由路径, 完整URL, 组件文件路径)

```
✅ CHECKPOINT-5: Files written + validated
   Files written: {N}
   Validation passed: {N}
   Validation failed: {N} (details: ...)
   Retried: {N}
```

## Step 6: Post-fill split (oversized pages)

After all pages filled, check element counts:
1. Count rows in `## 页面元素清单` per page
2. If > 15 rows AND no child docs exist (`{page-name}-*.md`):
   - Identify sub-components (Panel/Drawer/Dialog/Tab)
   - Create sub-page docs with skeleton
   - Spawn fill agents for each sub-page
3. Skip if: <= 15 elements, child docs exist, or `<!-- no-split -->` present

```
✅ CHECKPOINT-6: Post-fill split
   Pages checked: {N}
   Oversized (>15 elements): {N}
   Split into sub-pages: {N} → {list new files}
   Skipped (already has children): {N}
```

## Step 7: Final report

```
GSD > KB-FILL-PAGES Complete
────────────────────────────────────────────────────────────
Module:       {module}
Pages total:  {total}
Filled:       {filled}
Skipped:      {skipped}
Split:        {split_count} pages split into sub-pages
Validation:   {passed}/{total} files passed self-check
────────────────────────────────────────────────────────────
```

</process>

<validation>
执行结束后，对照以下清单做最终检查。任何 FAIL 项必须修复后重新输出：

| # | Check | FAIL condition |
|---|-------|----------------|
| 1 | Placeholder残留 | 任何文件中仍有 `{{` 模板变量 |
| 2 | 元素清单不足 | 任何页面 < 5 rows |
| 3 | 操作流不足 | 任何页面 < 5 rows 或 error paths < 30% |
| 4 | 接口不足 | 任何页面 < 3 API calls |
| 5 | 路由无效 | 路由路径不以 `/` 开头或包含域名 |
| 6 | 模板缺节 | 输出缺少模板中定义的任何一级标题 |
| 7 | --force 未执行 | --force 模式下有页面被跳过（非 manual 标记） |
| 8 | 表单验证模式缺失 | 页面有表单/dialog 提交但没有 `## 表单验证模式` section 或 section 为空 |
</validation>
