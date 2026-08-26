# Sub-skill: Fill Single Requirement Document

## Purpose

Fill ONE requirement document by reading the template and replacing ALL placeholders with content derived from source code analysis. This is a focused, mechanical task — not creative writing.

## Input (provided by orchestrator)

You will receive:
1. **Template file path** — read it first
2. **Domain context** — router source, service layer, API docs, storage docs, i18n
3. **REQ-ID and REQ-NAME** — already determined by orchestrator
4. **File lists** — actual filenames in apis/, pages/, storage/ for cross-reference validation

## Execution

### Step 1: Read the template

Read `templates/REQ-TEMPLATE.md` from the skill directory. This is your **output contract** — every `{{PLACEHOLDER}}` must be replaced with real content.

### Step 2: Analyze source code

From the provided context, extract:

**A. Business Flow (🔒 必填 — 无条件输出，不可跳过):**

从 API 调用链 + 状态转换推导完整业务流程：
- Trace depends_on relationships between APIs
- Map status field transitions (draft → building → running → stopped)
- Identify preconditions (e.g. "must have running sandbox to chat")
- Include async/timer triggers (e.g. "heartbeat timeout → offline")

**🔒 兜底规则（即使状态机简单也必须输出）：**
- 每个子流程（如 save/publish/restore）= 流程图中的一条路径
- 至少包含：触发者 → 前置检查 → 核心操作 → 结果状态 → 后续可选操作
- 流程步骤数 MIN 4（简单 CRUD 也有：认证 → 校验 → 操作 → 返回）

**绝对禁止跳过此段。** 如果输出中没有 `### 业务流程` 或流程步骤 < 4 → 输出被拒绝。

**B. Domain Glossary (🔒 必填 — 无条件输出，不可跳过):**

来源优先级：i18n > UI text > code naming。按优先级依次尝试，至少输出 5 个术语：

1. i18n Chinese locale keys → 直接使用
2. i18n English → translate to Chinese
3. Frontend button labels / titles / toasts / placeholders → extract
4. **兜底（必定有内容）：** 代码中的 Enum 值、状态字段名、Model 类名、Service 方法动词 → 推导术语

**🔒 即使没有 i18n 文件，兜底规则也必然产出 5+ 术语：**
- 每个 Enum/Literal 的枚举值 = 一个术语（如 `status='running'` → 术语"运行中"）
- 每个核心 Model 类名 = 一个术语（如 `SandboxInstance` → 术语"沙箱实例"）
- 每个状态转换动词 = 一个术语（如 `publish` → 术语"发布"）
- 每个 API 路径名词 = 一个术语（如 `/sessions` → 术语"会话"）
- 每个错误消息中的业务概念 = 一个术语

**绝对禁止跳过此段。** 如果输出中没有 `### 领域术语` 表或少于 5 行 → 输出被拒绝。

**C. Business Rules (🔒 必填 — 无条件输出，不可跳过):**

从 validator + 状态检查 + 权限逻辑提取，至少输出 5 条规则：
- Idempotency: SELECT before INSERT patterns
- State preconditions: `if status != X: raise 409`
- Permission boundaries: `where created_by = current_user`
- Cascade effects: CASCADE DELETE or manual cleanup
- Concurrency: advisory locks, optimistic locking

**🔒 兜底规则（即使最简单的 CRUD 模块也必然产出 5+ 规则）：**
- 每个 `raise HTTPException` = 一条规则（如"非 owner 操作返回 403"）
- 每个 `if status != X` 检查 = 一条规则（如"发布要求沙箱运行中"）
- 每个唯一约束/索引 = 一条规则（如"(agent_id, version) 唯一"）
- 每个参数校验（Pydantic Field/validator）= 一条规则
- 每个事务/锁机制 = 一条规则（如"advisory lock 防并发保存"）

**为什么 MIN 5 对任何模块都合理（最简 CRUD 示例）：**
```
即使只有增删改查 4 个接口，也必然存在：
1. 创建校验 — 参数必填 + 格式校验 + 唯一约束（如"同名资源不可重复创建"）
2. 权限边界 — 只能操作自己创建的资源（如"非 owner 返回 403"）
3. 删除级联 — 删除 A 时关联的 B 如何处理（如"删除 Agent 同时清理 sessions"）
4. 更新冲突 — 并发修改同一资源的处理策略（如"乐观锁 version 字段"）
5. 查询约束 — 分页参数范围 / 默认排序 / 软删除过滤（如"只返回未删除的记录"）
```

**绝对禁止跳过此段。** 如果输出中没有 `### 业务规则与约束` 或少于 5 行 → 输出被拒绝。

**D. Test Points (🔒 必填 — 无条件输出，不可跳过):**

分解为最小可测单元，复杂需求（3+ 子流程）必须 15+ 行：
- Every API endpoint: happy path + main error paths
- Every state transition: valid + invalid
- Permission: owner vs non-owner
- Concurrency: parallel requests
- Each TP must have: depends_on (or —) and DB断言 (or —)

**🔒 兜底规则：**
- 每个 API 至少 2 个 TP（正常 + 主要异常）
- 每个状态转换至少 1 个 TP
- 权限相关至少 1 个 TP
- 如果总计 < 5 → 从边缘场景补充

**绝对禁止跳过此段。** 如果输出中 TP 行数 < 5 → 输出被拒绝。

**E. Fixtures (🔒 必填 — 无条件输出，不可跳过):**

具体 JSON 测试数据，至少 2 个 fixture block：
- Real UUID values (fixed, for assertion matching)
- All table fields from storage docs
- Multiple fixtures for different scenarios (正常态 + 异常态)

**🔒 兜底规则：**
- 至少 1 个"正常初始状态" fixture（如 running agent）
- 至少 1 个"异常/边界状态" fixture（如 stopped agent、无权限用户）
- 每个 fixture 必须是完整 JSON（可直接 seed 到 DB）

**绝对禁止跳过此段。** 如果输出中没有 JSON fixture block → 输出被拒绝。

**F. Edge Cases (🔒 必填 — 无条件输出，不可跳过):**

从状态机 × 错误码 × 业务规则交叉推导，至少 5 个场景：
- Illegal state transitions
- Concurrent conflicts
- Resource deleted mid-operation
- Timeout / network failure
- Data boundary (empty, oversized)

**🔒 兜底规则（机械推导，不需要猜）：**
- 状态矩阵中每个 ❌ 行 = 一个边缘场景
- 每对并发写入的 API = 一个边缘场景
- 每个外部依赖（S3/Redis/第三方）= 一个超时/失败场景
- 每个 DELETE 操作 = 一个"资源已被删除后再操作"场景

**为什么 MIN 5 对任何模块都合理（最简 CRUD 示例）：**
```
即使只有增删改查 4 个接口，也必然存在：
1. 创建重复 — 同名资源已存在时再创建（幂等 or 报错？）
2. 删除不存在 — 对已删除/不存在的资源执行删除
3. 修改已删除 — 删除后立即修改（并发竞态）
4. 并发写入 — 两个用户同时修改同一资源
5. 空列表查询 — 无数据时查询返回格式是否正确
```

**绝对禁止跳过此段。** 如果输出中边缘场景 < 5 → 输出被拒绝。

### Step 3: Fill template

Replace every `{{PLACEHOLDER}}` with the extracted content. Rules:
- **No placeholder may remain** — if you cannot determine content, write `[需人工补充: 原因]`
- Respect `<!-- MIN: N -->` constraints in the template
- TP-ID format: `TP-{MODULE_PREFIX}-{REQ_NUMBER}-{NN}` (e.g. TP-SB-003-01)
- BR-ID format: `BR-{MODULE_PREFIX}-{REQ_NUMBER}-{NN}` (e.g. BR-SB-003-01)
- EDGE-ID format: `EDGE-{MODULE_PREFIX}-{REQ_NUMBER}-{NN}`
- FX-ID format: `FX-{MODULE_PREFIX}-{REQ_NUMBER}-{NN}`
- File references: ONLY use filenames from the provided file lists. If not found → `[待创建]`

### Step 4: Self-validate

Before outputting, check:
1. `grep -c "{{" output` must be 0 (no remaining placeholders)
2. Line count >= 250 (complex requirements with 3+ sub-flows)
3. TP rows >= 5 (complex: 15+)
4. Business rules >= 5
5. Edge cases >= 5
6. Glossary >= 5 terms
7. At least 2 JSON fixture blocks
8. All 4 traceability tables (关联接口/数据库/页面/源码) are non-empty

If any check fails, go back and fill the missing content. Do NOT output an incomplete document.

## Output

The complete filled REQ markdown document — ready to write directly to `requirements/REQ-{ID}.md`.

**🔒 UPDATE-FIRST 写入规则（更新优先，强制执行）：** 若目标文档 **已存在** 且符合模板规范（所有必需 `##` 节齐全、关键字段无 `待补充`）→ 调用方必须先 READ，再用 **Edit 工具** 只修改受影响的节（更新值、插入/更新行、追加 `变更记录` 行）；**逐字节保留**所有未修改内容，**包括**文件现有的行尾风格（CRLF/LF）。完整 `Write` 仅用于：全新文档、`--force`、或文档缺失必需模板节（schema 迁移）。
