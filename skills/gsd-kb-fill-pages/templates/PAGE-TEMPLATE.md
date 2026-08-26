# {{PAGE_NAME}} — {{PAGE_TITLE}}

> 组件: `{{COMPONENT_PATH}}`

## 基本信息
<!-- REQUIRED -->
| 字段 | 值 |
|------|-----|
| 模块 | {{MODULE}} |
| 页面名 | {{PAGE_NAME}} |
| 路由路径 | {{ROUTE_PATH}} |
| 完整URL | {{FRONTEND_BASE_URL}}{{ROUTE_PATH}} |
| 组件文件路径 | {{COMPONENT_FILE_PATH}} |
| 负责人 | {{OWNER}} |
| 需求来源 | {{REQ_SOURCE}} |

## URL 参数
<!-- 如果有 query params，填写此表；无则写"无 URL 参数" -->
| 参数 | 必须 | 说明 |
|------|------|------|
{{URL_PARAMS_ROWS}}

## 页面结构
<!-- REQUIRED. ASCII tree 含组件名 + CSS 约束 -->
```
{{PAGE_STRUCTURE_TREE}}
```

## 页面元素清单
<!-- REQUIRED. MIN: 5 rows -->
| data-testid | 元素类型 | 功能 | 触发接口 | 绑定字段 | 数据来源 |
|---|---|---|---|---|---|
{{PAGE_ELEMENTS_ROWS}}

> data-testid 优先级: 代码中有 → 直接用; 有 aria-label → "aria:{label}"; 无 → "建议: {module}-{page}-{type}-{function}"
> 元素类型: Button/Input/Select/Table/Dialog/Textarea/Checkbox/Tab/Link/Form/Badge/Panel

## 接口调用顺序
<!-- REQUIRED. MIN: 3 API calls. 反引号包裹完整路径 -->

{{API_CALL_SEQUENCE}}

> 格式: `{METHOD} /api/v1/...` — 反引号内, kb-fill-graph 提取此模式构建 calls 边
> SSR 接口标注 `[SSR]` 前缀

## 数据流转
<!-- REQUIRED. MIN: 2 rows -->
| 数据 | 来源 | 展示元素 | 流向 |
|------|------|----------|------|
{{DATA_FLOW_ROWS}}

## 用户操作流
<!-- REQUIRED. MIN: 5 rows. 异常路径至少占 30% -->
| 操作 | 触发方式 | 系统反应 | 异常处理 | 关联接口 | 跳转目标 |
|------|----------|----------|----------|----------|----------|
{{USER_FLOW_ROWS}}

> 推导: onClick/onSubmit → 一行; Dialog/confirm → 确认+取消两行; try/catch → 异常处理列
> 一个按钮 = 一行, 不合并
> **跳转目标列** = 该操作引起的页面跳转目标路由(如 `/dashboard/agent`、`/orders/{order_id}`);无页面跳转填 `—`;从源码 `router.push/replace`、`<Link href>`、`window.location` 提取。此列是跨页流程测试的结构化数据源,必须填具体路由,不要写"跳管理页/跳回列表"这类无路由描述。

## 表单验证模式
<!-- CONDITIONAL: 仅当页面包含表单/dialog 提交时填写 -->
<!-- 如果页面没有表单输入 → 写 "本页面无表单验证" -->
<!-- 从源码中 submit button 的 disabled prop、error state 变量的使用方式、validation 触发时机推导 -->

| 字段/表单 | 验证模式 | 源码证据 |
|-----------|----------|----------|
{{FORM_VALIDATION_ROWS}}

> 验证模式分类:
> - `DISABLE_UNTIL_VALID` — 按钮/提交禁用直到表单有效 (React: `disabled={!form.x}`, Vue: `:disabled="!valid"`, Angular: `[disabled]="form.invalid"`)
> - `ERROR_ON_SUBMIT` — 提交后显示错误文本 (`{error && <ErrorMsg>}`, `v-if="errors.field"`, `*ngIf="field.invalid"`)
> - `ERROR_ON_BLUR` — 失焦时显示错误 (`onBlur` handler + error state toggle)
> - `INLINE_REALTIME` — 实时验证反馈 (`onChange` + immediate error display)
> - `REQUIRED_MARKER` — 星号/颜色标记必填 (`*`, `required` attribute)
> - 组合模式: `DISABLE_UNTIL_VALID + REQUIRED_MARKER` (多种模式同时使用时用 + 连接)

## 状态管理架构
<!-- CONDITIONAL: 仅当组件使用 Context/Redux/useReducer 管理复杂状态时填写 -->
<!-- 如果只用简单 useState (<5个), 写 "本页面使用简单 useState，无独立状态管理" -->

### State 字段
| 分组 | 字段 | 类型 | 说明 |
|------|------|------|------|
{{STATE_FIELDS_ROWS}}

### 核心 Actions
| Action | 触发场景 | 状态变化 |
|--------|---------|---------|
{{ACTIONS_ROWS}}

### Provider 作用域
{{PROVIDER_SCOPE}}

## 关键 Hooks
<!-- CONDITIONAL: 仅当有自定义 hooks 时填写 -->
<!-- 跳过通用 hooks (useDebounce/useLocalStorage 等) -->

{{HOOKS_DESCRIPTIONS}}

> 格式:
> ### hookName
> - 职责: 一句话
> - 输入: `{ params }`
> - 输出: `{ returns }`
> - 副作用: API 调用/事件监听/定时器

## 关联需求
| 需求 | 触发接口 | 说明 |
|------|---------|------|
{{RELATED_REQS_ROWS}}

## 变更记录
| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 影响范围 |
|------|------|--------|--------|--------|--------|
| v1.0 | {{TODAY}} | auto-fill | 待补充 → 填充 | 从源码提取 | — |
