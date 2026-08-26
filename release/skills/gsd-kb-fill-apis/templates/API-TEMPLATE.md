# {{METHOD}} {{PATH}} — {{TITLE}}

> 源函数: `{{SOURCE_FILE}}::{{FUNCTION_NAME}}` (line {{LINE_RANGE}})

## 基本信息
<!-- REQUIRED. Agent 必须验证并输出此表，从代码修正格式错误 -->
| 字段 | 值 |
|------|-----|
| 模块 | {{MODULE}} |
| 方法 | {{METHOD}} |
| 路径 | {{FULL_PATH}} |
| 认证 | {{AUTH_METHOD}} |
| 代码位置 | {{CODE_LOCATION}} |
| 负责人 | {{OWNER}} |
| 需求来源 | {{REQ_SOURCE}} |
| 版本 | v1.0 |

## 需求来源
<!-- REQUIRED. 从 requirements/ 目录 grep 反查 -->
| 需求 ID | 需求名称 |
|---------|---------|
{{REQ_SOURCE_ROWS}}

## Request Schema
<!-- REQUIRED. 从源码中的 Schema/DTO/Model 定义中提取的结构化 schema -->
<!-- 用于 gen-tests 构建准确的 request body，禁止从接口语义推断 -->

**Model:** `{{SCHEMA_CLASS_NAME}}` (from `{{SCHEMA_SOURCE_FILE}}:{{SCHEMA_SOURCE_LINE}}`)

```json
{{REQUEST_BODY_SCHEMA}}
```

| 字段 | 类型 | Required | 默认值 | 约束 | 说明 |
|------|------|----------|--------|------|------|
{{REQUEST_SCHEMA_ROWS}}

> - 从源码中的 Schema/DTO/Model 定义提取（Pydantic BaseModel / Serializer / DTO class / struct / Zod schema 等）
> - 如果无 request body（GET/DELETE 无 body）→ 写 `_no_request_body: true`
> - 如果无法从源码确定 → 写 `_schema_unverified: true` 并标注原因
> - `约束` 列: 框架特定的约束声明（如 Field(min_length=N)、@Size(min=N)、z.string().min(N)、binding:"min=N" 等）

## 请求参数
<!-- REQUIRED. MIN: 1 row. 来源列必填：追溯实际上游，不能写"body" -->
| 参数 | 类型 | 必填 | 来源 | 说明 |
|------|------|------|------|------|
{{REQUEST_PARAMS_ROWS}}

> "来源"选项: "用户输入", "URL 路径参数", "GET /xxx 返回", "JWT token", "系统生成", "{具体页面/接口}"

## Response Schema
<!-- REQUIRED. 从源码中的 response_model/返回类型定义中提取的结构化 schema -->
<!-- 用于 gen-tests 构建准确的 jsonpath 断言，禁止从接口语义推断 -->

**Model:** `{{RESPONSE_MODEL_NAME}}` (from `{{RESPONSE_SOURCE_FILE}}:{{RESPONSE_SOURCE_LINE}}`)

**Top-level structure:** {{RESPONSE_STRUCTURE_TYPE}}

> Top-level structure 取值:
> - `OBJECT` — 返回单个对象 `{...}` → jsonpath 前缀 `$`
> - `ARRAY` — 返回数组 `[...]` → jsonpath 前缀 `$[0]`
> - `PAGINATED` — 返回分页包裹 `{"data": [...], "total": N}` → jsonpath 前缀 `$.data[0]`
> - `WRAPPED` — 返回包裹对象 `{"data": {...}}` → jsonpath 前缀 `$.data`

```json
{{RESPONSE_BODY_SCHEMA}}
```

| 字段路径 | 类型 | 必返回 | Nullable | 说明 |
|---------|------|--------|----------|------|
{{RESPONSE_SCHEMA_ROWS}}

> - 从源码中的 response_model/返回类型定义提取（Pydantic BaseModel / Serializer / DTO class / struct 等）
> - 字段路径基于 Top-level structure 确定前缀后拼接（如 PAGINATED 下字段 id → `$.data[0].id`）
> - 如果无法从源码确定 → 写 `_schema_unverified: true` 并标注原因

## 响应结构
<!-- REQUIRED. MIN: 1 row. JSONPath 层级必填，流向必填 -->
| 字段路径 | 类型 | 必返回 | 说明 | 流向 |
|---------|------|--------|------|------|
{{RESPONSE_FIELDS_ROWS}}

> 路径规则: 以 `$.` 开头, 数组用 `[]`, 如 `$.data.items[].name`
> 流向选项: "→ {page} 页面展示", "→ {API} 入参", "→ 仅本接口使用"

## 依赖接口（上游）
| 接口 | 传递的字段 | 关系 |
|------|----------|------|
{{UPSTREAM_DEPS_ROWS}}

## 被依赖接口（下游）
| 接口 | 消费的字段 | 关系 |
|------|----------|------|
{{DOWNSTREAM_DEPS_ROWS}}

## 关联数据库
<!-- REQUIRED. MIN: 1 row. 每行一个原子操作，禁止混合 SELECT/INSERT -->
| 表 | 操作 | 字段 | 业务规则 | 说明 |
|-----|------|------|---------|------|
{{DB_OPERATIONS_ROWS}}

> 业务规则列: 必须含 WHERE/SET 条件或计算公式
> 说明列: 格式 `①{触发条件}`, 带圈数字标明执行顺序
> 行序 = 执行顺序 = 测试断言顺序

## 关联定时任务
| 任务 | 关系 | 触发条件 |
|------|------|---------|
{{RELATED_JOBS_ROWS}}

## 关联前端页面
| 页面 | 触发元素 | 说明 |
|------|---------|------|
{{RELATED_PAGES_ROWS}}

## 错误码
<!-- REQUIRED. MIN: 3 rows. 必须从代码追溯，禁止靠 REST 惯例猜测 -->
| HTTP 状态码 | 触发条件 | 响应体 | 来源 |
|------------|---------|--------|------|
{{ERROR_CODES_ROWS}}

> 来源填写: Pydantic校验 / `file:line raise HTTPException(N)` / `exception_handler(Class)` / `dependency_func`
> 无法确认的标注 `[推断]`

## 请求/响应示例
<!-- REQUIRED. 至少 1 成功 + 1 错误场景 -->

### 成功场景
请求：
```json
{{SUCCESS_REQUEST_EXAMPLE}}
```

响应（{{SUCCESS_STATUS_CODE}}）：
```json
{{SUCCESS_RESPONSE_EXAMPLE}}
```

### 错误场景
请求：
```json
{{ERROR_REQUEST_EXAMPLE}}
```

响应（{{ERROR_STATUS_CODE}}）：
```json
{{ERROR_RESPONSE_EXAMPLE}}
```

## 测试断言
<!-- REQUIRED. 三个子表全部必填 -->

### 正常场景断言
| JSONPath | 断言类型 | 预期值 | 说明 |
|----------|---------|--------|------|
{{NORMAL_ASSERTIONS_ROWS}}

### 异常场景断言
<!-- MIN: 3 rows. 必须与错误码表对齐 -->
| 触发条件 | HTTP 状态码 | JSONPath | 预期值 | 来源 | 说明 |
|---------|-------------|----------|--------|------|------|
{{ERROR_ASSERTIONS_ROWS}}

### 边界值断言
<!-- MIN: 3 rows. 从请求参数类型机械推导 -->
| 参数 | 边界条件 | 输入值 | 预期 HTTP 状态码 | 预期行为 | 说明 |
|------|---------|--------|-----------------|---------|------|
{{BOUNDARY_ASSERTIONS_ROWS}}

### 变量提取（供链式测试使用）
| 变量名 | JSONPath | 用途 |
|--------|----------|------|
{{VARIABLE_EXTRACTIONS_ROWS}}

## 变更记录
| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 影响范围 |
|------|------|--------|--------|--------|--------|
| v1.0 | {{TODAY}} | auto-fill | 待补充 → 填充 | 从源码提取 | — |
