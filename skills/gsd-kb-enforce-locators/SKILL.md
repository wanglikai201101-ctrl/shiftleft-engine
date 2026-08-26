---
name: gsd-kb-enforce-locators
description: "Scan frontend components and inject standardized data-testid attributes (interactive + validation/error message elements) for Playwright automation"
argument-hint: "--module <name> --frontend <path> --output <path> [--dry-run] [--force]"
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

1. 🚫 NEVER inject data-testid on non-interactive elements — 只注入可交互元素（Button/Input/Select/Link/Textarea/Checkbox/Radio/Switch/Tab/Dialog trigger）
   EXCEPTION: form-validation error / feedback message elements (non-interactive text that asserts validation state — e.g. required-field errors, inline validation messages) ARE injectable with type `error`; they are assertion-relevant for UI tests.
2. 🚫 NEVER overwrite existing data-testid — 已有的保留不动
3. 🚫 NEVER generate naming that conflicts with existing testids in the module
4. 🚫 NEVER modify files in --dry-run mode — dry-run 只输出报告
5. 🚫 NEVER skip component analysis — 必须读取实际源码，不可凭空推断元素
6. 🚫 NEVER produce duplicate testid values — 每个 testid 在模块内必须唯一
7. 🚫 NEVER spawn agent without inlining naming convention rules
8. 🚫 NEVER silently skip dynamic/mapped per-entity elements — 每个动态/映射生成的 per-entity 可交互元素(per-card buttons、per-row actions、per-user controls、per-env inputs)必须按固定前缀约定注入 testid(见 Step 4 Dynamic per-entity elements),不得跳过
9. 🚫 NEVER mark a scope complete while gaps remain — 只要还有可交互元素缺少 data-testid,且无 `--force` 且无 LOCATOR-REPORT 中的书面 justification,即不得标记完成(COVERAGE GATE,见 Step 7)

每个 Step 完成后必须输出 checkpoint 标记，否则不得进入下一步。
</critical-rules>

<objective>
Scan frontend components and inject standardized `data-testid` attributes on all interactive elements
(plus validation/error/feedback message elements) that lack them, enabling deterministic Playwright
element selection.

This skill bridges the gap between "KB documents locators" and "code actually has locators":
- Scans TSX/Vue/JSX component files for interactive elements
- Checks each for existing `data-testid`, `aria-label`, or `role` attributes
- Injects missing `data-testid` following the naming convention: `{module}-{page}-{type}-{function}`
- Updates corresponding PAGE docs in KB (元素清单 column: "建议" → actual testid)
- Outputs LOCATOR-REPORT.md with coverage statistics

After this skill runs, `gsd-kb-gen-tests-ui` can generate tests with deterministic selectors
instead of relying on the execution engine's visual/semantic matching.
</objective>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name for testid prefix
- `--frontend <path>` (required): path to frontend source directory
- `--output <path>` (optional, default: `.planning/ontology`): KB documentation directory
- `--dry-run` (optional): report only, do not modify source files
- `--force` (optional): re-evaluate and re-inject even if testid exists (rename mode)

```
✅ CHECKPOINT-1: Arguments parsed
   MODULE: {name}
   FRONTEND: {path}
   OUTPUT: {path}
   MODE: {dry-run|inject|force}
```

## Step 2: Discover components

Scan `--frontend` path for component files:
```bash
find {frontend_path} -type f \( -name "*.tsx" -o -name "*.jsx" -o -name "*.vue" \) \
  | grep -v node_modules | grep -v __tests__ | grep -v .test. | grep -v .spec.
```

For each file, derive `page_name` from:
1. Nearest route definition (if resolvable)
2. Parent directory name
3. File name (strip extension, kebab-case)

```
✅ CHECKPOINT-2: Components discovered
   Total files: {N}
   Pages derived: {list of page_name → file mappings}
```

## Step 3: Analyze interactive elements

For each component file, identify interactive elements by matching JSX/template patterns:

**Interactive element patterns (TSX/JSX):**
- `<button` / `<Button` — type: Button
- `<input` / `<Input` — type: Input
- `<select` / `<Select` — type: Select
- `<textarea` / `<Textarea` — type: Textarea
- `<a href` / `<Link` — type: Link
- `<checkbox` / `<Checkbox` / `type="checkbox"` — type: Checkbox
- `<radio` / `<Radio` / `type="radio"` — type: Radio
- `<Switch` / `<Toggle` — type: Switch
- `<Tab` / `<TabsTrigger` — type: Tab
- Elements with `onClick` / `onSubmit` / `onChange` handlers — infer type from element
- `<Dialog` / `<Modal` trigger buttons — type: DialogTrigger

**Interactive element patterns (Vue):**
- `<el-button` / `<a-button` / `<van-button` — type: Button
- `<el-input` / `<a-input` — type: Input
- `<el-select` / `<a-select` — type: Select
- `@click` / `@submit` / `@change` handlers — infer type
- `<el-dialog` / `<a-modal` trigger — type: DialogTrigger

**Validation / error / feedback message patterns (TSX/JSX, type: error):**
Non-interactive text elements that assert validation state ARE injectable. Detect (match ANY):
- className contains a destructive/error token: `text-destructive`, `text-red-`, `text-error`, `text-danger`, `text-red`
- renders a validation i18n key: attribute or text using a `t('...Required')` / `t('...Error')` / `t('...Invalid')`-style key
- rendered from an error-state variable: `{nameError && (...)}`, `{error && (...)}`, `{errorMessage && (...)}`, or sibling message of an `aria-invalid` input
- semantic error/feedback class, or `role="alert"` / `aria-live` attribute

Concrete JSX matching patterns:
```jsx
{nameError && <p className="text-[11px] text-destructive mt-1">{t("create.nameRequired")}</p>}
// → {module}-{page}-error-name
{descError && <p className="text-xs text-red-500">{t("create.descRequired")}</p>}
// → {module}-{page}-error-desc
```

For each element found, check status:
- Has `data-testid="..."` → status: COVERED
- Has `aria-label="..."` → status: HAS_ARIA (still needs testid)
- Has `role="..."` → status: HAS_ROLE (still needs testid)
- None of the above → status: MISSING

```
✅ CHECKPOINT-3: Analysis complete
   Total interactive elements: {N}
   Validation/error message elements (type: error): {N}
   COVERED (has data-testid): {N} ({pct}%)
   HAS_ARIA (no testid): {N}
   HAS_ROLE (no testid): {N}
   MISSING (no locator at all): {N}
   Coverage: {covered}/{total} = {pct}%
```

## Step 4: Generate testid names

For each element with status != COVERED, generate a testid:

**Naming convention:** `{module}-{page}-{type}-{function}`

- `module`: from --module argument (kebab-case)
- `page`: derived page name (kebab-case)
- `type`: element type in lowercase (btn, input, select, link, textarea, checkbox, radio, switch, tab, dialog, error)
- `function`: inferred from:
  1. Nearest text content ("Submit" → "submit")
  2. Handler name (handleCreate → "create")
  3. Binding/model name (v-model="searchQuery" → "search-query")
  4. aria-label value if present
  5. Position context ("第一个按钮" → "primary")

**Type abbreviations:**
| Full type | Abbreviation |
|-----------|-------------|
| Button | btn |
| Input | input |
| Select | select |
| Link | link |
| Textarea | textarea |
| Checkbox | checkbox |
| Radio | radio |
| Switch | switch |
| Tab | tab |
| DialogTrigger | dialog |
| Error (validation/feedback message) | error |

**Error element naming:** `{module}-{page}-error-{field}` — `field` = the validated input's semantic field (derive from the sibling input/textarea binding name or the i18n key, e.g. `create.nameRequired` → `name`, `create.descRequired` → `desc`).

**Dedup rule:** If generated name conflicts, append `-{N}` suffix (e.g., `module-page-btn-submit-2`)

**Dynamic per-entity elements (MANDATORY prefix convention):**
Dynamic/mapped per-entity interactive elements — per-card buttons, per-row actions, per-user controls, per-env inputs, and any element rendered from `map()` / `.forEach()` / iteration over entities — MUST receive a stable-prefix testid so the whole family is targetable via a CSS prefix selector. Do NOT silently skip them.

Format (PREFIX + dynamic id):
```
{module}-{page}-{element}-{action}-${id}
```

- `module`: from --module argument (kebab-case)
- `page`: derived page name (kebab-case)
- `element`: static literal — entity/repeat element name (card, row, user, env, item, task, ...)
- `action`: static literal — the interaction (edit, delete, view, toggle, submit, ...)
- `${id}`: the ONLY dynamic segment — entity's unique id (agent.id, row.id, user.id, env.name, ...)

The whole family is then targetable in one selector:
```
[data-testid^='{module}-{page}-{element}-{action}-']
```

Rules:
- NEVER silently skip dynamic elements. If a mapped element is interactive, it gets a testid.
- Only `${id}` may be interpolated — `element` and `action` MUST be static literals so the prefix selector is stable.
- When the id is render-time-only, inject a template literal: `data-testid={`{module}-{page}-{element}-{action}-${agent.id}`}`.
- If id binding is impossible (third-party render, no id exposed), record it in LOCATOR-REPORT justification — never leave it silent.

Concrete examples:
```jsx
// per-card edit button → family targetable by [data-testid^='pm-web-agent-card-btn-edit-']
<button data-testid={`pm-web-agent-card-btn-edit-${agent.id}`} onClick={() => editAgent(agent)}>Edit</button>

// per-row delete menu item
<MenuItem data-testid={`pm-web-user-row-menu-delete-${user.id}`} ...>Delete</MenuItem>

// per-env input
<Input data-testid={`pm-web-env-input-name-${env.name}`} value={env.name} ... />
```

```
✅ CHECKPOINT-4: Names generated
   Names to inject: {N}
   Dynamic per-entity elements (prefix convention): {N}
   Sample: {first 5 testid → element mappings}
   Conflicts resolved: {N}
```

## Step 5: Inject data-testid (skip if --dry-run)

For each element needing injection, use Edit tool to add `data-testid` attribute:

**TSX/JSX injection rules:**
- Self-closing: `<Button />` → `<Button data-testid="{testid}" />`
- Opening tag: `<button onClick={...}>` → `<button data-testid="{testid}" onClick={...}>`
- Place `data-testid` as FIRST attribute after element name (easy to find)

**Vue injection rules:**
- `<el-button @click="...">` → `<el-button data-testid="{testid}" @click="...">`
- Place `data-testid` as FIRST attribute

**Shared-component testid propagation (MANDATORY):**
Shared components whose interactive parts would otherwise be unreachable (MultiSelect internals, DialogPrimitive.Close, shared Confirm buttons, dropdown triggers) MUST be made testid-addressable by prop-drilling a `dataTestId` / `data-testid` prop from the consumer — do not leave them as "Errors / Manual Review Needed".

- If the shared component already accepts `data-testid` / `dataTestId`, pass it at every call site: `<ConfirmButton data-testid="{module}-{page}-btn-confirm" ... />`
- If it does NOT accept one, add the prop to the shared component: accept `dataTestId?: string` and forward it to the internal interactive element:
  - `DialogPrimitive.Close` → `data-testid={`{dataTestId}-close`}`
  - MultiSelect internal checkboxes/options → `data-testid={`{dataTestId}-option-{value}`}`
  - Confirm button root → `data-testid={dataTestId}`
- Nested-internal convention: append a static suffix to the drilled prop (root `dataTestId` → `{dataTestId}-option-{value}` on option rows, `{dataTestId}-close` on DialogPrimitive.Close), so a prefix selector can target each internal family.
- Rationale: prop-drilling beats guessing/duplicating ids, keeps testids deterministic, and eliminates "Errors / Manual Review Needed" rows for shared internals.

**Spawn agents for parallel injection** (max 4 concurrent):
- Each agent handles one component file
- Agent receives: file path, list of (line_number, element, testid_to_inject)
- Agent uses Edit tool to inject, preserving formatting

```
✅ CHECKPOINT-5: Injection complete
   Files modified: {N}
   Elements injected: {N}
   Errors: {N} (list if any)
```

## Step 6: Update PAGE docs in KB

For each injected testid, find the corresponding PAGE doc in `{output}/{module}/pages/`:
- Match by page_name
- In `## 页面元素清单` table, update the `data-testid` column:
  - "建议: {old-suggestion}" → `{actual-testid}`
  - Add new row if element not yet documented

```
✅ CHECKPOINT-6: KB docs updated
   Page docs updated: {N}
   Elements synced: {N}
   New rows added: {N}
```

## Step 7: Generate LOCATOR-REPORT.md

Write to `{output}/{module}/LOCATOR-REPORT.md`:

```markdown
# Locator Report — {MODULE}

> Generated: {TODAY}
> Frontend: {frontend_path}
> Mode: {dry-run|inject|force}

## Coverage Summary

| Metric | Value |
|--------|-------|
| Total elements (interactive + validation/error messages) | {N} |
| Interactive elements | {N} |
| Validation/error message elements (type: error) | {N} |
| Already covered (data-testid) | {N} ({pct}%) |
| Injected this run | {N} |
| Final coverage | {N}/{N} = {pct}% |
| Gate | {PASS\|WAIVED\|FAILED} |

## Injected Elements

| File | Element | testid | Source |
|------|---------|--------|--------|
| {relative_path} | {type} | {testid} | {text/handler/model} |
...

## Dynamic Per-Entity Families

| File | Prefix selector | Element | Actions |
|------|----------------|---------|---------|
| {relative_path} | `[data-testid^='{module}-{page}-{element}-']` | {card/row/user/env} | {edit/delete/toggle/...} |
...

## Skipped (already covered)

| File | Element | Existing testid |
|------|---------|-----------------|
...

## Errors / Manual Review Needed (gate waivers)

| File | Line | Issue | Justification |
|------|------|-------|--------------|
...
```

**COVERAGE GATE (MANDATORY):**
The skill MUST refuse to mark the scope complete while any interactive element lacks a data-testid. "Every interactive element" = buttons, menu items, dropdown triggers, inputs, toggles, links with handlers, dialog closes.

The scope is complete ONLY when:
1. Coverage of interactive elements is 100% (every interactive element has a data-testid), AND
2. Every dynamic per-entity element follows the prefix convention from Step 4 (family targetable via `[data-testid^='...']`), AND
3. Shared-component interactive parts are testid-addressable via prop drilling from Step 5 (no unreachable internals), AND
4. Any remaining gap is explicitly listed in "Errors / Manual Review Needed" with a written justification, OR the run was executed with `--force`.

Gate outcomes:
- **PASS** — no gaps; every interactive element has a data-testid.
- **WAIVED** — gaps exist but each is either covered by `--force` or has a documented justification in the report. State the waiver reason per element.
- **FAILED** — gaps exist WITHOUT `--force` and WITHOUT documented justification. The scope is NOT complete; emit the report, surface the failed gate, and do not present the work as done.

```
✅ CHECKPOINT-7: Report generated
   Location: {output}/{module}/LOCATOR-REPORT.md
   Final coverage: {pct}%
   Gate: {PASS|WAIVED|FAILED}
```

</process>

<notes>
- Safe to re-run: only injects where missing, never overwrites existing testids
- --dry-run is recommended first to review what would be injected
- Works with React (TSX/JSX), Vue (SFC), and mixed projects
- After injection, run `gsd-kb-fill-pages --force` to refresh page docs with new testids
- Naming convention matches what gsd-kb-fill-pages FILL-SINGLE-PAGE.md already suggests
- For projects using component libraries (Ant Design, Element Plus, MUI), recognizes their interactive components
- Dynamic per-entity elements MUST follow the prefix convention `{module}-{page}-{element}-{action}-${id}`; target the family with `[data-testid^='{module}-{page}-{element}-{action}-']`
- Coverage gate: scope is complete only when every interactive element has a data-testid — or each gap carries `--force` / a documented justification in LOCATOR-REPORT
- Does NOT inject on: pure display components, layout wrappers, SVG elements, non-interactive divs
  — EXCEPT validation/error/feedback message elements (type `error`), which ARE injectable
</notes>
