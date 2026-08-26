---
name: gsd-kb-gen-tests-ui
description: "Generate MCP-Ready UI test cases: orchestrator + template-driven generation"
argument-hint: "--module <name> --output <path> [--req <REQ-ID>] [--force]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Grep
  - Glob
  - Agent
---


<objective>
Orchestrate UI test case generation by:
1. Mapping page docs (元素清单 + 用户操作流) to the execution engine's UI dispatch format
2. Resolving prerequisites for dynamic data
3. Spawning agents that fill UI-TEST-TEMPLATE.json

Each agent reads `templates/UI-TEST-TEMPLATE.json` and `sub-skills/GEN-SINGLE-UI-TEST.md`.
Output: MCP-Ready JSON files for the execution engine's UI dispatch tool.
</objective>

<process>

## Step 1: Parse arguments + load ENV-CONFIG

Extract from `$ARGUMENTS`:
- `--module <name>` (required)
- `--output <path>` (optional, default: `.planning/ontology`)
- `--req <REQ-ID>` (optional): specific requirement only

Load `$OUTPUT/$MODULE/tests/ENV-CONFIG.json`:
- `FRONTEND_BASE_URL` — from `environment.frontend_url`
- `FRONTEND_LOGIN_PATH` — from `environment.frontend_login_path` (fallback: from login page doc's 路由路径, or `/login` as last resort)
- `AUTH_USERNAME` — from `auth.username`
- `AUTH_PASSWORD` — from `auth.password`
- `DEFAULT_LOCALE` — from `i18n.default_locale` (fallback: detection strategy below)

**🔒 默认语言解析（DEFAULT_LOCALE）：**

Resolution priority:
1. ENV-CONFIG `i18n.default_locale` 字段（如果存在）→ 直接使用
2. **自动检测**（如果 `i18n.default_locale` 不存在）：
   - 检查前端源码中的 i18n 配置文件（grep `defaultLocale`, `fallbackLng`, `default_language`）
   - 检查 `next-i18next.config`, `i18n.ts`, `locale/index.ts` 等常见配置
   - 检查 `package.json` 中的 i18n 相关配置
3. 如果无法检测 → 默认 `"zh"`（向后兼容，中文 target）

`DEFAULT_LOCALE` 值传递给每个 agent spawn 的 context 中，影响 target 字段的文本语言。

**🔒 登录路由解析优先级：**
1. ENV-CONFIG.json `environment.frontend_login_path` 字段（如果存在）
2. KB page docs 中名为 `login.md` 的文档的 `## 基本信息` → `路由路径` 字段
3. 代码中的实际路由定义（grep frontend 源码中的 login route）
4. 兜底 `/login`（标注 `[推断]`）

**禁止** 不做任何查找就使用 `/login` — 很多项目登录页是 `/auth/login`、`/sign-in`、`/account/login` 等。

## Step 2: Collect source documents

### 2a: Load page docs
For each `pages/*.md`:
1. 页面元素清单 (data-testid, 元素类型, 功能, 触发接口)
2. 用户操作流 (操作, 触发方式, 系统反应, 异常处理, 关联接口) — **primary source**
3. 接口调用顺序 (page lifecycle)
4. 数据流转 (data sources and display)
5. 基本信息 → 路由路径 (must start with `/`)

**UI test priority:**
1. **首选:** 用户操作流 table → each row = one test step
2. **次选:** 页面元素清单 + 接口调用顺序 → derive steps
3. **兜底:** TP 操作步骤 column → derive steps

### 2b: Load requirements
Extract TPs with 验证方式 containing "UI" → map to pages via 关联前端页面.

### 2c: Route resolution
- Read `路由路径` from page 基本信息
- Must start with `/` (prepend if missing)
- Must NOT contain domain (strip if present)
- Preserve ALL query params (?id=, ?mode=, ?tab=)
- Dynamic params → `{{VARIABLE}}` from prerequisites

**🔒 ID 语义验证:**
- Trace what ID the page URL expects (from 接口调用顺序)
- Verify list_endpoint returns correct entity type
- If mismatch → add transform or correct extract_field

### 2d: Transient state analysis
For UI elements with conditional disabled state:
- Loading/async → test AFTER load completes (瞬态)
- Backend state dependent → two test cases (met/unmet)
- Permission-based → single disabled assertion (永久)

## Step 3: Load template and sub-skill

```bash
SKILL_DIR=""
for candidate in \
  "$HOME/.claude/skills/gsd-kb-gen-tests-ui" \
  "$(pwd)/skills/gsd-kb-gen-tests-ui" \
  "$HOME/gsd-core/skills/gsd-kb-gen-tests-ui"; do
  if [ -f "$candidate/templates/UI-TEST-TEMPLATE.json" ]; then
    SKILL_DIR="$candidate"
    break
  fi
done
```

## Step 4: Spawn agents (one per page × TP combination)

For each TP mapped to a page:

```
{SUB_SKILL: GEN-SINGLE-UI-TEST.md content}

---
## Template (output contract):
{UI-TEST-TEMPLATE.json content}

---
## Context:
PAGE_DOC: {full page doc content}
TP: {test point — 操作步骤, 预期结果, 前置条件}
PAGE_NAME: {page display name}
PAGE_URL: {resolved full URL with params}
ENV_CONFIG: {FRONTEND_BASE_URL, auth credentials — resolved}
ELEMENTS: {页面元素清单 relevant rows}
USER_FLOWS: {用户操作流 relevant rows}
DEFAULT_LOCALE: {resolved locale, e.g. "en" or "zh"}

🔒 Output must be valid JSON.
Steps >= 4 (2 login + 1 nav + 1 business minimum).
No hardcoded IDs. Prerequisites declared if URL has dynamic params.
🔒 Target text MUST use DEFAULT_LOCALE language (e.g. "Create" for en, "创建" for zh).
```

**Test types to generate per page:**
1. **Happy path** — from 用户操作流 normal rows
2. **Error path** — from 用户操作流 rows with 异常处理 filled
3. **Network error** — from rows mentioning 网络/离线/超时
4. **Conditional state** — met/unmet variants for disabled elements

## Step 5: Generate agent-prompts (chat format)

For each REQ, generate a comprehensive exploratory prompt at `tests/agent-prompts/REQ-{ID}.json`:
- One prompt covering all UI TPs for that requirement
- Natural language instructions for the recording agent
- Includes login info, page URLs, expected behaviors

## Step 6: Write output files

Write to `$OUTPUT/$MODULE/tests/ui/`:
- `UI-{REQ}-{TP}_{scenario}.json` — normal test
- `UI-{REQ}-{TP}_ERROR-{slug}.json` — error variant
- `UI-{REQ}-{TP}_NETWORK-{slug}.json` — network error test

Write to `$OUTPUT/$MODULE/tests/agent-prompts/`:
- `REQ-{ID}.json` — exploratory chat prompt

## Step 6b: Static validation (post-generation sanity check)

UI tests cannot be dry-run validated (require browser environment), but apply static checks:

**Process:**

1. **URL format validation:**
   - All `url` fields start with `/` (relative) or `{{FRONTEND_BASE_URL}}` (templated)
   - No hardcoded domains (e.g., `http://localhost:3000/page`)
   - Dynamic params use `{{VARIABLE}}` syntax

2. **Route existence verification:**
   - For each test's target URL path, verify it matches a known page doc route (from `pages/*.md` 基本信息 → 路由路径)
   - If URL not found in any page doc → mark `"_validation": "warning:route_not_in_kb"`

3. **Target text language verification:**
   - All `target` fields (button text, labels) must use `DEFAULT_LOCALE` language
   - If mixed languages detected → flag as `"_validation": "warning:mixed_locale"`

4. **Prerequisites completeness:**
   - If URL contains `{{VAR}}`, verify a `prerequisites` section defines how to obtain `VAR`
   - Missing prerequisite → mark `"_validation": "warning:missing_prerequisite"`

5. **Write validation status to _meta:**
   ```json
   {
     "_meta": {
       "validated": "static_only",
       "validation_warnings": ["route_not_in_kb::/settings/advanced"]
     }
   }
   ```
   Or if all checks pass: `{"_meta": {"validated": "static_only", "validation_warnings": []}}`

**Note:** Full runtime validation for UI tests happens at execution time via the execution engine's UI dispatch. This static check catches structural errors early.

## Step 7: Report

```
GSD > KB-GEN-TESTS-UI Complete
────────────────────────────────────────────────────────────
Module:       {module}
Pages:        {N} with UI tests
Test files:   {total} (happy: {h}, error: {e}, network: {n})
Agent prompts:{p} generated
TP coverage:  {covered}/{total} UI test points
────────────────────────────────────────────────────────────
```

</process>

<notes>
- Template-driven: agents fill JSON template structure
- 用户操作流 is PRIMARY source for step generation (not elements alone)
- Prerequisites: mandatory for pages with dynamic URL params
- ID semantic verification: trace what the page URL actually expects
- Transient states: don't test disabled during loading — test after ready
- Agent-prompts: for exploratory testing via execution engine chat mode
- Static validation (Step 6b): URL format, route existence, locale, prerequisites
- Full runtime validation deferred to execution engine's UI dispatch
- Validation status tracked in _meta.validated and _meta.validation_warnings
</notes>
