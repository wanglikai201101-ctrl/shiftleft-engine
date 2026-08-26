# REQ-{{REQ_ID}} — {{REQ_NAME}}

## 需求概述
| 字段 | 值 |
|------|-----|
| 编号 | REQ-{{REQ_ID}} |
| 名称 | {{REQ_NAME}} |
| 来源 | 从代码反推 |
| 优先级 | {{PRIORITY}} |
| 模块 | {{MODULE}} |
| 版本 | v1.0 |

## 业务描述

{{BUSINESS_DESCRIPTION}}
<!-- MIN: 5 sentences. 回答"用户为什么需要这个功能"，描述完整业务场景，不是技术实现 -->

### 业务流程
<!-- REQUIRED. Format: ASCII numbered flowchart with status transitions. MIN: 4 steps per sub-flow -->
```
{{BUSINESS_FLOW_ASCII}}
```

### 状态转换矩阵
<!-- REQUIRED. MIN: 5 rows. 如果无状态流转，写"该需求无状态流转，跳过矩阵" -->
| 当前状态 | 触发动作 | 目标状态 | 守卫条件 | 拒绝时行为 |
|---------|---------|---------|---------|-----------|
{{STATE_MATRIX_ROWS}}

### 领域术语
<!-- REQUIRED. MIN: 5 terms. 来源优先级：i18n > UI文本 > 代码命名 -->
| 术语 | i18n key / UI 文本 | 代码表现 | 业务含义 | 区分于 |
|------|-------------------|---------|---------|--------|
{{GLOSSARY_ROWS}}

### 业务规则与约束
<!-- REQUIRED. MIN: 5 rules. 从 validator + 状态检查 + 权限逻辑提取 -->
| 规则 ID | 规则描述 | 代码来源 | 违反时行为 |
|---------|---------|---------|-----------|
{{BUSINESS_RULES_ROWS}}

## 最小可测单元拆解
<!-- REQUIRED. MIN: 5 rows. 复杂需求（含 3+ 子流程）: 15~25 rows -->
| 测试点 ID | 测试点描述 | 类型 | 前置条件 | 操作步骤 | 预期结果 | 验证方式 | depends_on | DB断言 |
|-----------|-----------|------|---------|---------|---------|---------|------------|--------|
{{TEST_POINTS_ROWS}}

## 测试 Fixture
<!-- REQUIRED. 表格 + JSON blocks -->
| Fixture ID | 数据描述 | 关联表 | 初始状态 | 使用的测试点 |
|------------|---------|--------|---------|-------------|
{{FIXTURE_TABLE_ROWS}}

<!-- MIN: 2 JSON fixture blocks. 必须是可直接用于测试 seed 的具体值 -->

{{FIXTURE_JSON_BLOCKS}}

## 边缘场景
<!-- REQUIRED. MIN: 5 scenarios. 从状态机 + 错误码 + 业务规则交叉推导 -->
| 场景 ID | 场景描述 | 触发条件 | 预期行为 | 来源 |
|---------|---------|---------|---------|------|
{{EDGE_CASES_ROWS}}

## 关联实现（追溯链）

### 关联接口
<!-- REQUIRED. kb-fill-graph 消费此表构建 implemented_by 边 -->
| 测试点 ID | 接口 | 接口文档 |
|-----------|------|---------|
{{API_LINKS_ROWS}}

### 关联数据库
<!-- REQUIRED. kb-fill-graph 消费此表构建 REQ→Storage 路径 -->
| 测试点 ID | 表 | 数据库文档 |
|-----------|-----|---------|
{{DB_LINKS_ROWS}}

### 关联前端页面
<!-- REQUIRED. kb-gen-tests-ui 消费此表 -->
| 测试点 ID | 页面 | 关键元素(data-testid) | 页面文档 |
|-----------|------|---------------------|---------|
{{PAGE_LINKS_ROWS}}

### 关联源码
| 测试点 ID | 源文件 | 行号范围 | 关键函数 |
|-----------|--------|---------|---------|
{{SOURCE_LINKS_ROWS}}

## 变更记录
| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 影响范围 |
|------|------|--------|--------|--------|--------|
| v1.0 | {{TODAY}} | scaffold 自动生成 | 无（新建） | 从代码反推 | — |
