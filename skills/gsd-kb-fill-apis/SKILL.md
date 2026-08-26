---
name: gsd-kb-fill-apis
description: "API deep semantic fill: orchestrator + template-driven fill"
argument-hint: "--module <name> --source <path> --output <path> [--force] [--only <paths>] [--api-blacklist <paths>]"
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

<critical-rules>
🚫 HALT — 逐条阅读以下规则，违反任何一条 = 输出无效，必须删除重做

1. 🚫 NEVER create files with non-standard names — only `{METHOD}-{path-slug}.md` format is allowed
   - ✅ Allowed: `GET-my-agents.md`, `POST-{agent_id}-run.md`, `DELETE-{agent_id}.md`
   - ❌ Forbidden: `SERVICE-*.md`, `_INDEX.md`, `SUMMARY.md`, `README.md`, any freeform name
2. 🚫 NEVER write files outside `$OUTPUT/$MODULE/apis/` — no writes to storage/, pages/, tech/, graph/, tests/
3. 🚫 NEVER generate documentation for internal service classes — this skill documents HTTP API endpoints ONLY
   - ❌ Forbidden: SandboxClient docs, AgentManager docs, LifecycleManager docs
   - ✅ Allowed: route handler endpoint documentation (FastAPI/Flask/Express routes)
4. 🚫 NEVER create new API doc files from scratch — only fill EXISTING skeleton files or files matching discovered routes
5. 🚫 If apis/ directory is empty or contains no route-based .md files → report "No API skeletons found" and STOP
   - Do NOT invent alternative documentation formats
   - Do NOT fall back to documenting services/classes/modules

违反以上任何一条 = 立即停止，输出 "BOUNDARY VIOLATION: {which rule}" 并退出。
</critical-rules>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required)
- `--source <path>` (required): backend source code directory
- `--output <path>` (optional, default: `.planning/ontology`)
- `--force` (optional): re-fill EVERY API doc IN SCOPE. Without `--only`, scope = all discovered routes (minus `--api-blacklist`) → full sweep.
- `--only <paths>` (optional): STRICT scope — comma-separated API doc paths (relative to module, e.g. `apis/enhance-description.md`) that are the ONLY docs to fill. Overrides route discovery; do NOT fill anything outside this list. If omitted, fill all discovered routes (minus --api-blacklist).
- `--api-blacklist <paths>` (optional): comma-separated API paths to EXCLUDE — do NOT create/fill docs for these (hidden/unexposed interfaces). New interfaces are unaffected.

**🔒 --only × --force 优先级（强制执行，不可跳过）：**
- `--only` 定义 in-scope 集合（**最高优先级**）：提供时，只有列出的文档会被考虑（不按路由发现扩展）；未提供时，in-scope = 全部已发现路由（再排除 `--api-blacklist`）。
- `--force` 只改变 in-scope 内文档的处理方式：把 in-scope 内所有文档视为 unfilled。
- `--only` + `--force` = 只完整重写列出的文档（绝不 sweep 列表外的文档）。
- `--force` 无 `--only` = 全量 sweep（重写所有已发现路由的文档）。
- 无 `--force` = 只填 in-scope 内含 "待补充" 的文档。

**🔒 --force 行为（强制执行，不可跳过，仅作用于 in-scope 文档）：**
- **必须**重新读取源代码并完整重写每个 in-scope API 文档
- **禁止**判断"现有文件已符合规范"而跳过（in-scope 内）
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

## Step 1.7: Detect framework and OpenAPI spec

**框架探测:** 从 `--source` 目录向上查找依赖文件，确定 REST 框架类型。

```bash
SOURCE_DIR="$SOURCE"

# Python detection
if [ -f "$SOURCE_DIR/requirements.txt" ] || [ -f "$SOURCE_DIR/pyproject.toml" ] || [ -f "$SOURCE_DIR/Pipfile" ]; then
  DEP_CONTENT=$(cat "$SOURCE_DIR/requirements.txt" "$SOURCE_DIR/pyproject.toml" "$SOURCE_DIR/Pipfile" 2>/dev/null)
  if echo "$DEP_CONTENT" | grep -qi "fastapi"; then
    FRAMEWORK="fastapi"
  elif echo "$DEP_CONTENT" | grep -qi "djangorestframework"; then
    FRAMEWORK="django-rest"
  elif echo "$DEP_CONTENT" | grep -qi "flask" && echo "$DEP_CONTENT" | grep -qi "marshmallow"; then
    FRAMEWORK="flask-marshmallow"
  elif echo "$DEP_CONTENT" | grep -qi "flask" && echo "$DEP_CONTENT" | grep -qi "pydantic"; then
    FRAMEWORK="fastapi"  # Flask+Pydantic follows same pattern
  fi
fi

# Node/TS detection
if [ -f "$SOURCE_DIR/package.json" ]; then
  PKG=$(cat "$SOURCE_DIR/package.json")
  if echo "$PKG" | grep -q "@nestjs/common"; then
    FRAMEWORK="nestjs"
  elif echo "$PKG" | grep -q "\"zod\""; then
    FRAMEWORK="express-zod"
  elif echo "$PKG" | grep -q "\"joi\"" || echo "$PKG" | grep -q "@hapi/joi"; then
    FRAMEWORK="express-joi"
  elif echo "$PKG" | grep -q "\"express\""; then
    FRAMEWORK="express-unknown"
  fi
fi

# Java detection
if find "$SOURCE_DIR" -maxdepth 2 -name "pom.xml" -o -name "build.gradle" 2>/dev/null | head -1 | grep -q .; then
  BUILD_CONTENT=$(cat $(find "$SOURCE_DIR" -maxdepth 2 \( -name "pom.xml" -o -name "build.gradle" \) 2>/dev/null | head -1))
  if echo "$BUILD_CONTENT" | grep -qi "spring-boot"; then
    FRAMEWORK="spring-boot"
  fi
fi

# Go detection
if [ -f "$SOURCE_DIR/go.mod" ]; then
  if grep -q "gin-gonic/gin" "$SOURCE_DIR/go.mod"; then
    FRAMEWORK="go-gin"
  elif grep -q "labstack/echo" "$SOURCE_DIR/go.mod"; then
    FRAMEWORK="go-echo"
  fi
fi

# Ruby detection
if [ -f "$SOURCE_DIR/Gemfile" ]; then
  if grep -q "rails" "$SOURCE_DIR/Gemfile"; then
    FRAMEWORK="rails"
  fi
fi

FRAMEWORK="${FRAMEWORK:-unknown}"
echo "Detected framework: $FRAMEWORK"
```

**OpenAPI spec 查找:**

```bash
OPENAPI_SPEC=""
for spec_file in \
  "$SOURCE_DIR/openapi.json" \
  "$SOURCE_DIR/openapi.yaml" \
  "$SOURCE_DIR/openapi.yml" \
  "$SOURCE_DIR/swagger.json" \
  "$SOURCE_DIR/swagger.yaml" \
  "$SOURCE_DIR/docs/openapi.json" \
  "$SOURCE_DIR/docs/openapi.yaml" \
  "$SOURCE_DIR/static/openapi.json" \
  "$SOURCE_DIR/api-docs/openapi.json"; do
  if [ -f "$spec_file" ]; then
    OPENAPI_SPEC="$spec_file"
    break
  fi
done

# Also check for generated spec locations
if [ -z "$OPENAPI_SPEC" ]; then
  OPENAPI_SPEC=$(find "$SOURCE_DIR" -maxdepth 3 -name "openapi.json" -o -name "openapi.yaml" -o -name "swagger.json" 2>/dev/null | head -1)
fi

if [ -n "$OPENAPI_SPEC" ]; then
  echo "Found OpenAPI spec: $OPENAPI_SPEC"
  HAS_OPENAPI=true
else
  echo "No OpenAPI spec found — will use source code extraction only"
  HAS_OPENAPI=false
fi
```

**将 FRAMEWORK 和 OPENAPI_SPEC 传递到 Step 4 的 Agent prompt 中。**

**API 黑名单过滤(若提供 `--api-blacklist`):**
`--api-blacklist` 的路径(逗号分隔)是**要排除**的接口——发现路由时,凡 PATH 匹配黑名单任一路径(或黑名单路径是该 PATH 的前缀),一律跳过,**不生成、不填充**其文档。
- 例:黑名单 `/api/v1/hidden` → 跳过 `/api/v1/hidden-a`、`/api/v1/hidden-b`;黑名单 `/api/v1/legacy/x` → 只跳过该精确路径
- 新增/未列入黑名单的接口正常 fill,不受影响
- 黑名单路径从 `--api-blacklist` 参数读取(逗号分隔),在处理"APIs to fill"列表前先过滤

**--only 严格范围(若提供,最高优先):**
`--only` 列出的 API 文档路径是**唯一**要 fill 的——只处理这些文档,不要通过路由发现去 fill 其它接口。
1. `--only` 路径相对模块根(如 `apis/enhance-description.md`)
2. 只 fill `--only` 列出的文档;列表外的接口(即使 `--source` 里有路由)一律不 fill
3. `--only` 未提供时,才按路由发现 fill(再排除 `--api-blacklist`)
4. `--only` 同时定义 `--force` 的 in-scope:带 `--only` 的 `--force` 只重写列表内文档;不带 `--only` 的 `--force` 才是全量 sweep

## Step 2: Inventory and classify

**Without --force:** scan for docs with "待补充" in key sections. Skip already-filled files.
**With --force:** treat every API doc IN SCOPE as unfilled (the `--only` list if provided; otherwise all discovered routes minus `--api-blacklist`).

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
## Framework context:
Detected framework: {FRAMEWORK}
{if HAS_OPENAPI: "OpenAPI spec available — use as primary schema source, validate against source code"}
{if HAS_OPENAPI: include relevant requestBody schemas extracted from spec for each API in this batch}

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

Same prompt structure but with single API + **deep context extraction** (see below).

### Deep Context Extraction (🔒 mandatory for ALL APIs — prevents "待补充" flood)

Before spawning any fill agent, for each API's route handler function, extract the full call chain:

```bash
# 1. Route handler source (direct)
HANDLER_SOURCE=$(read route handler function)

# 2. Service layer — follow imports from handler
#    e.g., handler imports `from app.services.sandbox import SandboxService`
#    → read SandboxService.{method} that the handler calls
SERVICE_IMPORTS=$(grep -E "^(from|import)" "$HANDLER_FILE" | grep -i "service")
for svc_import in $SERVICE_IMPORTS; do
  SVC_FILE=$(resolve_import_to_file "$svc_import")
  SVC_METHODS=$(extract_called_methods "$HANDLER_SOURCE" "$SVC_FILE")
  SERVICE_SOURCES+=("$SVC_FILE:$SVC_METHODS")
done

# 3. Repository/DAL layer — follow imports from service
#    e.g., service imports `from app.repositories.agent_repo import AgentRepository`
for svc_file in ${SERVICE_FILES[@]}; do
  REPO_IMPORTS=$(grep -E "^(from|import)" "$svc_file" | grep -iE "repo|dal|crud|database")
  for repo_import in $REPO_IMPORTS; do
    REPO_FILE=$(resolve_import_to_file "$repo_import")
    REPO_SOURCES+=("$REPO_FILE")
  done
done

# 4. External SDK/client calls — identify 3rd party integrations
#    e.g., `from langfuse import Langfuse` or `import httpx`
EXTERNAL_IMPORTS=$(grep -E "^(from|import)" "$HANDLER_FILE" "$SVC_FILES" \
  | grep -vE "(app\.|\.\.)" \
  | grep -vE "^(typing|os|json|datetime|uuid|enum|dataclass)")
```

**Agent prompt 中必须包含的上下文层次：**

```
## Source code context (layered):

### Layer 1: Route handler
{handler function source — the direct endpoint}

### Layer 2: Service layer (called by handler)
{each service method source that handler invokes}

### Layer 3: Repository/DAL layer (called by service)
{each repo method source — SQL queries, ORM operations}

### Layer 4: External integrations (SDKs, HTTP clients)
{for each external import: package name + which methods are called}
{if source available (e.g., local SDK wrapper): include wrapper source}
{if 3rd party (langfuse/stripe/etc.): note "external SDK — document input/output contract from usage"}

### Layer 5: Related models/schemas
{Request/Response schema definitions — framework-specific:
  - Python/FastAPI: Pydantic BaseModel, dataclass, TypedDict
  - Python/DRF: Serializer class
  - Python/Flask: marshmallow Schema class
  - Node/NestJS: DTO class with class-validator decorators
  - Node/Express+Zod: z.object() schema definitions
  - Node/Express+Joi: Joi.object() schema definitions
  - Java/Spring: DTO class with Jakarta Validation annotations
  - Go: struct with json/binding/validate tags
  - Ruby/Rails: Model with validations + db/schema.rb}
{🔒 CRITICAL for Request Schema section: must include the EXACT schema/DTO/model class used as request body}
{For each route handler body parameter:
  - Follow the import/reference to the schema definition file
  - Include the FULL class/struct/schema definition with all fields and constraints
  - Include any parent classes or composed schemas
  - Framework examples:
    - FastAPI: `async def create(body: CreateUserRequest)` → find `class CreateUserRequest(BaseModel):` → include ALL fields
    - NestJS: `@Body() dto: CreateUserDto` → find `export class CreateUserDto` → include ALL properties + decorators
    - Spring: `@RequestBody CreateUserRequest req` → find `public class CreateUserRequest` → include ALL fields + annotations
    - Go: `var req CreateUserRequest; c.ShouldBindJSON(&req)` → find `type CreateUserRequest struct` → include ALL fields + tags
    - Zod: validated with `CreateUserSchema.parse(req.body)` → find `const CreateUserSchema = z.object({...})` → include full definition}
```

**🔒 上下文完整性检查 (pre-spawn gate):**

Before spawning the fill agent, verify the context is sufficient:
1. Layer 1 (handler) must be non-empty — 如果找不到 handler source → STOP, report
2. If handler has service imports → Layer 2 must be non-empty
3. If Layer 4 identifies external SDKs → include usage context (至少列出哪些方法被调用)

如果上下文不足（例如源码不在 --source 路径内），在 agent prompt 中明确标注：
```
⚠️ CONTEXT GAP: {service/repo/SDK} source not found at expected path.
Fill with "需进一步调查: {what's missing}" rather than "待补充".
Use whatever is available (function signatures, type hints, API response schemas) to infer.
```

This prevents the agent from producing empty "待补充" fields — it either fills from context or explicitly states what's missing and why.

## Step 5: Merge results

For each agent result:
1. Verify no `{{` placeholders remain
2. Parse `===FILE:` separators (batch mode)
3. Write/overwrite API docs
   **🔒 UPDATE-FIRST 写入规则（更新优先，强制执行）：** 目标文档 **已存在** 且符合模板规范（所有必需 `##` 节齐全、关键字段无 `待补充`）→ **先 READ** 该文件，再用 **Edit 工具** 只修改受影响的节（更新值、插入/更新行、追加 `变更记录` 行）；**逐字节保留**所有未修改内容，**包括**文件现有的行尾风格（CRLF/LF）。完整 `Write` 仅用于：全新文档、`--force`、或文档缺失必需模板节（schema 迁移）
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
Framework:   {FRAMEWORK}
OpenAPI:     {HAS_OPENAPI ? spec_path : "not found"}
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
- Multi-framework support: Step 1.7 detects framework from dependency files, passes to agents
- Schema extraction priority: OpenAPI spec > framework-specific source extraction > LLM inference
- Request Schema section: MUST be extracted from source code schema/DTO/model definitions
  - gen-tests uses this section as the PRIMARY source for request body construction
  - If schema cannot be extracted, mark `_schema_unverified: true` — never guess field names
- Supported frameworks: FastAPI, Django REST, Flask+marshmallow, NestJS, Express+Zod, Express+Joi, Spring Boot, Go gin/echo, Rails
- Backward compatible: existing FastAPI projects use the same flow (framework auto-detected as "fastapi")
</notes>
