---
name: gsd-kb-fill-error-handling
description: "Error handling auto-discovery: error inbox, retry mechanisms, dead letter queues, error classification"
argument-hint: "--module <name> --source <path> --output <path> [--force]"
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

1. 🚫 NEVER write files outside `$OUTPUT/$MODULE/error-handling/` — 禁止写入 apis/, pages/, tech/, graph/, tests/, requirements/, storage/, jobs/, config/, integration/
2. 🚫 NEVER create files with non-standard names — only `{error-type}.md` format (lowercase, hyphen-separated)
   - ✅ Allowed: `billing-recognition-errors.md`, `etl-validation-errors.md`, `integration-timeout-errors.md`
   - ❌ Forbidden: `SERVICE-*.md`, `_INDEX.md`, `SUMMARY.md`, `README.md`
3. 🚫 NEVER document non-error-handling concerns — this skill documents ERROR MECHANISMS only
   - ❌ Forbidden: API endpoints, page docs, table schemas, job docs, config docs
   - ✅ Allowed: error types, error inbox tables, retry logic, dead letter queues, error state machines, error recovery flows
4. 🚫 NEVER ignore --force flag — force 模式下必须重写，禁止判断"已符合规范"跳过

违反以上任何一条 = 立即停止，输出 "BOUNDARY VIOLATION: {which rule}" 并退出。
</critical-rules>

<objective>
Discover and generate error handling documentation for a module.

Searches for error management mechanisms:
1. Error inbox/queue tables (error_inbox, failed_*, dead_letter_*)
2. Retry mechanisms (retry decorators, retry loops, exponential backoff)
3. Error classification enums (ErrorType, FailureReason, error_code)
4. Error recovery flows (status machines: pending → retrying → fixed/ignored)
5. Dead letter queues (DLQ, unprocessable messages)
6. Error notification/alerting (error → notification → human review)

A module with retry logic, error tables, or error classification
ALWAYS has error handling — this skill must find and document them.
</objective>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name
- `--source <path>` (required): backend source code directory
- `--output <path>` (optional, default: `.planning/ontology`): documentation output directory
- `--force` (optional): re-generate ALL error handling docs, overwriting existing content. Without --force, only create new docs for undocumented error mechanisms and skip existing ones.

**🔒 --force 行为定义（强制执行，不可自行跳过）：**

当传入 `--force` 时：
- **必须**重新读取源代码并完整重写每个 error-handling 文档
- **禁止**判断"现有文件已符合规范"而跳过重写
- **禁止**输出"文件保持现状"然后不做任何修改
- 唯一不覆盖的是 `<!-- manual -->` 标记的段落

Determine PROJECT_ROOT: walk up from `--source` until `pyproject.toml` / `package.json` / `setup.py` found.

## Step 2: Discover error handling mechanisms

🚫 扫描范围必须限定在 `--source` 路径内，不得向上扩展到 PROJECT_ROOT 全局扫描。
只有当 `--source` 内没有找到任何错误机制时，才 fallback 到 PROJECT_ROOT，但 fallback 时必须用 module 名做路径过滤。

### Strategy 1: Error inbox/queue tables
```bash
grep -rn "error_inbox\|error_queue\|failed_\|dead_letter\|dlq\|error_log\|error_record" "$SOURCE" --include="*.py" --include="*.sql" | grep -v .venv | grep -v __pycache__
```

### Strategy 2: Retry mechanisms
```bash
grep -rn "@retry\|tenacity\|retry_count\|max_retries\|exponential_backoff\|backoff\.\|RetryPolicy\|retry_after" "$SOURCE" --include="*.py" | grep -v .venv | grep -v __pycache__
```

### Strategy 3: Error classification (enums, constants)
```bash
grep -rn "class.*Error.*Enum\|ErrorType\|FailureReason\|ERROR_CODE\|error_type\s*=\|ErrorCategory" "$SOURCE" --include="*.py" | grep -v .venv | grep -v __pycache__
```

### Strategy 4: Error state machines (status transitions)
```bash
grep -rn "pending.*retrying\|retrying.*fixed\|status.*ignored\|error_status\|ErrorStatus\|mark_as_failed\|mark_as_fixed" "$SOURCE" --include="*.py" | grep -v .venv | grep -v __pycache__
```

### Strategy 5: Error notification/alerting
```bash
grep -rn "notify_error\|alert_on_failure\|send_error_notification\|error.*webhook\|on_failure\|failure_callback" "$SOURCE" --include="*.py" | grep -v .venv | grep -v __pycache__
```

### Strategy 6: Exception handlers with persistence
```bash
grep -rn "except.*:\s*$" "$SOURCE" --include="*.py" -A 3 | grep -i "save\|persist\|insert\|create.*error\|log.*error.*db\|write.*error" | grep -v .venv | grep -v __pycache__
```

### Strategy 7: Custom exception hierarchies
```bash
grep -rn "class.*Exception\|class.*Error.*Exception\|raise.*Error(" "$SOURCE" --include="*.py" | grep -v .venv | grep -v __pycache__ | grep -v "ImportError\|ValueError\|TypeError\|KeyError\|RuntimeError"
```

## Step 3: Classify and generate error handling docs

For each discovered mechanism, group by error domain:

| Discovery pattern | Error domain |
|---|---|
| Error inbox/queue table | 错误收件箱 |
| Retry decorator/loop | 重试机制 |
| Error enum/classification | 错误分类 |
| Status state machine | 错误状态流转 |
| DLQ/dead letter | 死信队列 |
| Error notification | 错误通知 |
| Custom exception hierarchy | 异常层次结构 |

Group related mechanisms into a single doc per error domain (e.g., billing errors: classification + retry + inbox = one doc).

### Error handling doc template

```markdown
# {error_domain} — {description}

> 源文件: `{file_path}`

## 基本信息

| 字段 | 值 |
|------|-----|
| 错误域 | {billing/integration/etl/validation/...} |
| 机制类型 | {错误收件箱/重试机制/死信队列/错误分类} |
| 模块 | {module} |
| 负责人 | 待补充 |
| 需求来源 | 待补充 |
| 版本 | v1.0 |

## 错误类型定义

| 错误类型 | 说明 | 典型场景 | 修复方式 |
|---------|------|---------|---------|
| {error_type} | {description} | {scenario} | {fix_method} |

## 错误状态流转

```
pending ──(重试)──→ retrying ──(成功)──→ fixed
   │                    │
   │                    └──(失败)──→ pending（retry_count+1）
   │
   └──(忽略)──→ ignored
```

{如果有自定义状态流转，描述实际的状态机}

## 重试策略

| 错误类型 | 是否重试 | 重试次数 | 重试间隔 | 退避策略 |
|---------|---------|---------|---------|---------|
| {type} | {是/否} | {max_retries} | {interval} | {fixed/exponential/linear} |

## 错误记录结构

| 字段 | 类型 | 说明 |
|------|------|------|
| error_id | string | 错误唯一标识 |
| error_type | enum | 错误类型 |
| source_id | string | 错误来源（原始数据ID） |
| error_message | text | 错误详细信息 |
| status | enum | 处理状态 |
| retry_count | integer | 已重试次数 |
| created_at | datetime | 错误发生时间 |

{根据实际代码中的错误表/模型填写}

## 错误恢复流程

1. **错误发生**：{描述错误如何被捕获}
2. **错误记录**：{描述错误如何被持久化}
3. **错误通知**：{描述是否通知相关人员}
4. **错误修复**：{描述修复后如何重试}

## 关联需求

| 需求编号 | 说明 |
|---------|------|
| 待补充 | 待补充 |

## 关联接口

| 接口 | 操作 | 说明 |
|------|------|------|

## 关联数据库

| 表 | 操作 | 说明 |
|-----|------|------|

## 关联任务

| 任务 | 关系 | 说明 |
|------|------|------|

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 影响范围 |
|------|------|--------|--------|--------|--------|
| v1.0 | 待补充 | scaffold 自动生成 | 无（新建） | 从代码反推骨架 | 待补充 |
```

## Step 4: Handle "no error handling" case

**If genuinely no error handling mechanisms exist** (no error tables, no retry logic, no error classification):
- Remove the empty `$OUTPUT/$MODULE/error-handling/` directory (do not leave empty folders)
- Update MODULE.md "模块资产清单" table: `| 错误处理文档 | 0（该模块无独立错误处理机制） | error-handling/ |`
- Do NOT leave a bare "0" — always annotate the reason

**IMPORTANT**: A module with retry decorators, error tables, or error classification enums ALWAYS has error handling — do NOT report "0" for such modules.

## Step 5: Report

```
GSD > KB-FILL-ERROR-HANDLING Complete
────────────────────────────────────────────────────────────
Module:              {module}
Error domains found: {N} (inbox: {n1}, retry: {n2}, DLQ: {n3}, classification: {n4})
Error handling docs: {generated}/{total}
────────────────────────────────────────────────────────────
```

</process>

<notes>
- Safe to re-run: skips existing error handling doc files (unless --force is passed)
- With --force: overwrites all error handling docs with fresh content from source code
- Groups related mechanisms (classification + retry + inbox) into a single domain doc
- Recognizes error inboxes, retry patterns, DLQs, status state machines, and custom exceptions
- A module with retry decorators or error tables MUST report error handling
- Error handling docs feed into the knowledge graph as "error-handling" type nodes
</notes>
