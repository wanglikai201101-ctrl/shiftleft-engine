# Sub-skill: Fill Single API Document

## Purpose

Fill ONE API documentation by reading the template and replacing ALL placeholders with content derived from source code analysis.

## Input (provided by orchestrator)

1. **Template** — API-TEMPLATE.md content
2. **Source function** — the actual Python/JS function source code
3. **Doc skeleton** — existing API doc (if any, for preserving 基本信息)
4. **Related docs** — storage docs, requirement docs for cross-reference
5. **File lists** — actual filenames in apis/, pages/, storage/, requirements/

## Execution

### Step 1: Read source function

Trace the implementation:
- Router decorator → HTTP method + path
- Function signature → parameters (path, query, body, header)
- Function body → DB operations, service calls, error raises
- Return statement → response structure + model

### Step 2: Extract by section

**基本信息** — from router decorator:
- Method: `@router.post` → `POST`
- Path: full path from `/api/` prefix
- Function name: actual def name
- Auth: from `Depends(get_current_user...)` or similar

**Request Schema** — extract from source code's Schema/DTO/Model definition:

**Priority order:**
1. **OpenAPI spec** (if provided in context) → use requestBody.content.application/json.schema directly
2. **Framework-specific source extraction** (see below) → follow the matching framework path
3. **LLM inference** → if no schema class found, set `_schema_unverified: true` with reason

**Framework detection:** Identify which framework the project uses from the context provided (dependency files, import patterns, decorator/annotation style). Then follow the matching extraction path:

---

**[FastAPI / Flask+Pydantic] (Python — Pydantic BaseModel):**
1. Find body parameter in function signature (e.g., `body: EnhanceDescriptionRequest`)
2. Locate the Pydantic BaseModel class definition (follow import)
3. Extract fields: name, Python type annotation, `= Field(...)` constraints, Optional[] = not required
4. Required = no default value and not Optional[]; Constraints = Field(min_length, max_length, ge, le, regex, enum)

**[Django REST Framework] (Python — Serializer):**
1. Find the serializer class used in the view (e.g., `serializer_class = UserCreateSerializer`)
2. Locate the Serializer/ModelSerializer class definition
3. Extract fields: `field_name = serializers.CharField(...)` → type=str, required=(not `required=False`), constraints from kwargs
4. For ModelSerializer: also check `class Meta: model = X; fields = [...]` → trace to Django Model for types
5. Type mapping: CharField→str, IntegerField→int, BooleanField→bool, ListField→array, etc.

**[Flask + marshmallow] (Python — marshmallow Schema):**
1. Find the schema class used for request validation (e.g., `@use_args(UserSchema)` or manual `schema.load()`)
2. Locate the marshmallow.Schema subclass definition
3. Extract fields: `field_name = fields.String(required=True, ...)` → type from field class, required from kwarg
4. Constraints: validate=[Length(min=N, max=N), OneOf([...])], load_default=X (default value)

**[NestJS] (TypeScript — DTO class + class-validator decorators):**
1. Find the DTO class used in controller method (e.g., `@Body() dto: CreateUserDto`)
2. Locate the DTO class file (typically in `dto/` directory)
3. Extract fields: property name, TS type annotation, decorators for constraints
4. Required = no `@IsOptional()` decorator; Constraints: @MinLength(N), @MaxLength(N), @IsEmail(), @IsEnum(X), etc.
5. If `@ApiProperty()` from @nestjs/swagger exists, use its metadata too

**[Express + Zod] (TypeScript — z.object()):**
1. Find the Zod schema used for request validation (e.g., `const CreateUserSchema = z.object({...})`)
2. Locate the schema definition (may be inline in route or in schemas/ directory)
3. Extract fields: `field: z.string().min(3).max(50)` → type=string, constraints from chained methods
4. Required = not `.optional()`; Default = `.default(X)` ; Constraints: .min(), .max(), .email(), .regex(), .enum()

**[Express + Joi] (JavaScript/TypeScript — Joi.object()):**
1. Find the Joi schema used for validation (e.g., `const schema = Joi.object({...})`)
2. Locate the schema definition
3. Extract fields: `field: Joi.string().required().min(3)` → type=string, required from .required(), constraints from chain
4. Required = `.required()` present; Constraints: .min(), .max(), .email(), .pattern(), .valid()

**[Spring Boot] (Java — DTO class + Jakarta/Javax Validation):**
1. Find the DTO class in method signature (e.g., `@RequestBody CreateUserRequest request`)
2. Locate the class file (typically in dto/ or request/ package)
3. Extract fields: Java type + annotations → @NotNull=required, @Size(min=N,max=N), @Min(N), @Max(N), @Email, @Pattern(regexp=...)
4. Required = has @NotNull or @NotBlank; Type mapping: String→str, Integer/int→int, Boolean→bool, List<X>→array

**[Go gin/echo] (Go — struct with binding tags):**
1. Find the struct used for request binding (e.g., `var req CreateUserRequest; c.ShouldBindJSON(&req)`)
2. Locate the struct definition
3. Extract fields: struct field name, Go type, json tag (→ JSON field name), binding tag (→ constraints)
4. Required = `binding:"required"`; Constraints from validate/binding tag: min, max, oneof, email, etc.
5. JSON field name from `json:"field_name"` tag (not Go field name)

**[Rails] (Ruby — strong_params + ActiveModel validations):**
1. Find `params.require(:resource).permit(...)` in controller → gives field names
2. Check Model validations: `validates :field, presence: true, length: {min: N, max: N}`
3. Check db/schema.rb for column types
4. Required = `presence: true` validation; Type from DB column type; Constraints from validation DSL

**[Unknown framework / no clear schema class]:**
1. Look for any type annotation, interface, or schema definition associated with the request body
2. If found → extract and document with framework noted
3. If NOT found → set `_schema_unverified: true` with reason "No typed schema class found; framework: {name}"

---

**After framework-specific extraction, fill template sections:**
- `{{SCHEMA_CLASS_NAME}}`: exact class/struct/schema name (e.g., `CreateUserDto`, `UserSerializer`, `z.object(...)`)
- `{{SCHEMA_SOURCE_FILE}}`: file path where schema is defined
- `{{SCHEMA_SOURCE_LINE}}`: line number of definition
- `{{REQUEST_BODY_SCHEMA}}`: JSON example with all required fields using realistic values
- `{{REQUEST_SCHEMA_ROWS}}`: one row per field with type, required, default, constraints

**Special cases (all frameworks):**
- GET/DELETE with no body → set `_no_request_body: true` in schema block
- Untyped body (dict/any/object without schema) → set `_schema_unverified: true` with reason
- Nested models/objects → flatten with dot notation in field column (e.g., `config.timeout`)
- List/array body → document the item schema

**Hard rules:**
- NEVER guess field names from endpoint semantics or description text
- NEVER infer body structure from the API's name or purpose
- ONLY extract from actual schema/DTO/model/struct definitions in source code
- If OpenAPI spec is provided AND source code conflicts with spec → source code wins (spec may be stale)

**请求参数** — trace each parameter's real source:
- Path params: "URL 路径参数"
- Body fields: trace which page/form sends them → "{page名} 用户输入"
- Headers: "JWT token" / "系统生成"
- NEVER write just "body" as source

**Response Schema** — extract from response_model or return type:

**Priority order:**
1. **OpenAPI spec** (if provided in context) → use responses.200.content.application/json.schema directly
2. **Framework-specific response model extraction** (see below) → follow the matching framework path
3. **Return statement analysis** → trace actual returned object structure
4. **LLM inference** → if no response model found, set `_schema_unverified: true` with reason

**Framework-specific extraction paths:**

- **[FastAPI]** `response_model=ModelClass` in decorator OR function return type `-> ModelClass` → locate Pydantic class
- **[Django REST Framework]** View's `serializer_class` or `get_serializer()` → locate Serializer class for response
- **[NestJS]** `@ApiResponse({type: ResponseDto})` or method return type → locate DTO class
- **[Express + TypeScript]** Return type annotation or JSDoc `@returns` → locate interface/type
- **[Spring Boot]** `ResponseEntity<T>` generic parameter or `@ResponseBody` return type → locate class
- **[Go gin/echo]** Function return struct type or `c.JSON(200, responseStruct)` → locate struct definition

**提取要素：**
- `{{RESPONSE_MODEL_NAME}}`: Response model 类名（如 `AgentListResponse`, `Page[AgentDTO]`）
- `{{RESPONSE_SOURCE_FILE}}`: 源文件路径
- `{{RESPONSE_SOURCE_LINE}}`: 定义行号
- `{{RESPONSE_STRUCTURE_TYPE}}`: 顶层结构类型，取值规则：
  - 直接返回 model → `OBJECT`（jsonpath 前缀 `$`）
  - 返回 `List[Model]` / 数组 → `ARRAY`（jsonpath 前缀 `$[0]`）
  - 返回 `Page[Model]` / 有 data+total 分页结构 → `PAGINATED`（jsonpath 前缀 `$.data[0]`）
  - 返回 `{"data": Model}` wrapper → `WRAPPED`（jsonpath 前缀 `$.data`）
- `{{RESPONSE_BODY_SCHEMA}}`: JSON schema block（带真实结构，区分列表和对象）
- `{{RESPONSE_SCHEMA_ROWS}}`: 每个字段一行：字段路径、类型、是否必返回、是否 nullable、说明

**通用框架适配（无法识别具体框架时）：**
- 查找 route handler 的 `response_model` 参数或返回类型注解
- 追踪到对应的 Model/DTO/Schema class
- 提取字段名、类型、描述
- 确定顶层结构类型

**Hard rules:**
- NEVER guess response structure from endpoint semantics or API name
- ONLY extract from actual response model/DTO/Schema definitions in source code
- If source code has both `response_model` decorator param AND return type annotation → prefer `response_model`（it's the actual serialization schema）

**响应结构** — from return statement or response_model:
- Full JSONPath from root ($.data.field, not just "field")
- Check if wrapped in `{data: ...}` or `{items: [...]}` 
- Arrays must have `[]` marker
- Trace downstream: which page displays this? which API consumes it?

**关联数据库** — one row per atomic DB operation:
- Each SELECT/INSERT/UPDATE/DELETE = separate row
- 业务规则列: actual WHERE/SET clause
- 说明列: ①②③ numbered execution order
- NEVER combine operations in one row

**错误码** — trace from code, NEVER guess from REST conventions:
1. Pydantic validator → 422 (NOT 400)
2. `raise HTTPException(code)` → exact code from source
3. Global exception handlers → mapped codes
4. Dependency injection failures → codes from the dep function
- Mark `[推断]` if cannot confirm from code

**测试断言** — derive from response structure + error codes:
- Normal: every required response field → one assertion row
- Error: top 3 error codes from 错误码 table → assertion rows (MUST align)
- Boundary: from parameter types (string→empty/long/special, int→negative/zero/huge, UUID→invalid)
- Variable extraction: fields consumed by downstream APIs

**请求/响应示例** — concrete mock data:
- Success: realistic values matching response structure
- Error: most common error case from 错误码 table

### Step 3: Fill template

Replace every `{{PLACEHOLDER}}`. Rules:
- No placeholder may remain
- Respect `<!-- MIN: N -->` constraints
- If cannot determine → write `[需人工补充: 原因]` (NOT "待补充")
- File references: ONLY use filenames from provided file lists

### Step 4: Self-validate

Before output, verify:
1. Zero `{{` remaining
2. Request Schema has either: a valid JSON schema block with field definitions, OR `_no_request_body: true` (for GET/DELETE), OR `_schema_unverified: true` with reason
3. Request Schema `Model:` line references an actual class/struct/schema name from source (not generic like "RequestBody" or "Object")
4. 请求参数 has >= 1 real row (not 待补充)
5. 响应结构 has >= 1 row with JSONPath starting with `$.`
6. 关联数据库 has >= 1 row with WHERE/SET in 业务规则
7. 错误码 has >= 3 rows with 来源 filled
8. 测试断言 has all 3 sub-tables non-empty
9. 请求/响应示例 has success + error scenarios
10. Request Schema fields are consistent with 请求参数 body fields (same names, same types)

If any fails → go back and fill.

## Output

Complete filled API markdown — ready to write to `apis/{METHOD}-{slug}.md`.

For batch mode: output multiple docs separated by `===FILE: {filename}===` headers.

**🔒 UPDATE-FIRST 写入规则（更新优先，强制执行）：** 若目标文档 **已存在** 且符合模板规范（所有必需 `##` 节齐全、关键字段无 `待补充`）→ 调用方必须先 READ，再用 **Edit 工具** 只修改受影响的节（更新值、插入/更新行、追加 `变更记录` 行）；**逐字节保留**所有未修改内容，**包括**文件现有的行尾风格（CRLF/LF）。完整 `Write` 仅用于：全新文档、`--force`、或文档缺失必需模板节（schema 迁移）。
