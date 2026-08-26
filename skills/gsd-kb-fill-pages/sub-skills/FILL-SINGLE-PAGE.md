# Sub-skill: Fill Single Page Document

## Purpose

Fill ONE page documentation by reading the template and replacing ALL placeholders with content extracted from frontend component source code.

## Input (provided by orchestrator)

1. **Template** — PAGE-TEMPLATE.md content
2. **Component source** — the actual TSX/Vue file
3. **Key imports** — imported sub-component sources (max 3)
4. **Route path** — derived from file structure
5. **Related API docs** — which APIs reference this page
6. **File lists** — actual filenames in apis/, pages/, storage/

## Execution

### Step 1: Analyze component source

From the frontend component, extract:

**Page structure** — from JSX/TSX return:
- Build ASCII tree with component names + CSS constraints
- Mark: fixed sizes (h-12/w-80), flex direction, z-index, conditional rendering
- Include Provider wrappers at the top

**Page elements** — from JSX attributes:
1. Has `data-testid` → use directly
2. Has `aria-label` or `role` → record as `aria:{label}` or `role:{role}`
3. Neither → suggest: `{module}-{page}-{type}-{function}`
- Element type MUST be concrete UI control (Button/Input/Select etc), NOT component name

**API call sequence** — from hooks, useEffect, event handlers:
- Page load: APIs called in useEffect/getServerSideProps/loader
- User actions: APIs called in onClick/onSubmit handlers
- SSR calls: mark with `[SSR]` prefix
- Format: `` `{METHOD} /api/v1/...` `` (backtick-wrapped for graph extraction)

**Data flow** — trace from source to display:
- URL params → state → rendered element
- API response → state → displayed component
- User input → state → API request body

**User operation flow** — from event handlers:
- Every onClick/onSubmit/onChange → one row
- Every Dialog/Modal → confirm + cancel rows
- Every try/catch → fill 异常处理 column
- Every loading/disabled state → fill 系统反应 column
- Error paths must be ≥30% of total rows
- One button = one row, never merge
- **Navigation target (跳转目标 column)** — from the same event handlers:
  - Every navigation side-effect → record the TARGET ROUTE in the 跳转目标 column, NOT prose. Sources (in priority order): `router.push('...')` / `router.replace('...')` → the string route; `<Link href="...">` → href; `window.location.href = '...'` → the path.
  - Keep dynamic segments as-is (e.g. `/orders/${id}` → `/orders/{order_id}`; route params from the page's own URL params).
  - No navigation on the row → fill `—`.
  - Do NOT write "跳管理页/跳回列表/跳转任务页" — the column must carry a concrete route so downstream flow enumeration can resolve the target page.

**Form validation pattern** — from form/dialog submit analysis:
For each form or dialog with a submit action, identify the validation mode by inspecting source:

1. **Check submit button's disabled prop:**
   - `disabled={!form.field}` / `disabled={!isValid}` → `DISABLE_UNTIL_VALID`
   - No disabled prop on submit button → likely `ERROR_ON_SUBMIT` or `ERROR_ON_BLUR`

2. **Check error state rendering:**
   - Error text rendered conditionally (`{error && <span>}`, `v-if="errors.x"`) + appears after submit click → `ERROR_ON_SUBMIT`
   - Error text rendered after `onBlur`/`focusout` → `ERROR_ON_BLUR`
   - Error text rendered inside `onChange` with immediate feedback → `INLINE_REALTIME`

3. **Check required markers:**
   - `<label>Name *</label>` or `required` HTML attribute → `REQUIRED_MARKER` (often combined with another mode)

4. **Record for each field/form:**
   - Field or form name
   - Validation mode (from classification above)
   - Source evidence: exact code snippet with line reference (e.g. `disabled={!form.description}` in L42)

If page has NO forms/dialogs → write "本页面无表单验证"
If page has forms but validation mode is unclear from source → mark as `[需确认]` with best guess

**State management** (if uses Context/Redux/useReducer):
- State fields: from type definitions
- Actions: from reducer/dispatch calls
- Provider scope: which children are wrapped

**Hooks** (if has custom hooks in _hooks/ or hooks/):
- For each: 职责, 输入, 输出, 副作用
- Skip generic hooks (useDebounce, useLocalStorage, etc.)

### Step 2: Fill template

Replace every `{{PLACEHOLDER}}`. Rules:
- No placeholder may remain
- Respect `<!-- MIN: N -->` constraints
- Route path MUST start with `/` (not bare path)
- Route path MUST NOT contain domain name
- 完整URL format: `{{FRONTEND_BASE_URL}}{route_path}`
- If component not found → infer from API docs + route structure, mark `[推断]`
- 状态管理/Hooks sections: if component is simple (no Context, <5 useState) → write "本页面使用简单 useState，无独立状态管理" and skip those sections

### Step 3: Self-validate

Before output, verify:
1. Zero `{{` remaining
2. 基本信息 has 路由路径 (starts with `/`) and 组件文件路径
3. 页面元素清单 has >= 5 rows
4. No row has ALL columns as "待补充"
5. 接口调用顺序 has >= 3 backtick-wrapped API calls
6. 数据流转 has >= 2 rows
7. 用户操作流 has >= 5 rows, >=30% are error/exception paths
8. All data-testid use proper prefix (not "代码中未明确")
9. 表单验证模式 section is filled: either "本页面无表单验证" or has >= 1 row with validation mode + source evidence
10. Every 用户操作流 row whose 系统反应 carries navigation semantics (跳转/跳回/跳转管理页/跳转任务页/跳转详情 etc) has a non-empty 跳转目标 column with a concrete route (starts with `/`), never prose like "管理页/列表"

If any fails → go back and fill.

## Output

Complete filled page markdown — ready to write to `pages/{page-name}.md`.

**🔒 UPDATE-FIRST 写入规则（更新优先，强制执行）：** 若目标文档 **已存在** 且符合模板规范（所有必需 `##` 节齐全、关键字段无 `待补充`）→ 调用方必须先 READ，再用 **Edit 工具** 只修改受影响的节（更新值、插入/更新行、追加 `变更记录` 行）；**逐字节保留**所有未修改内容，**包括**文件现有的行尾风格（CRLF/LF）。完整 `Write` 仅用于：全新文档、`--force`、或文档缺失必需模板节（schema 迁移）。
