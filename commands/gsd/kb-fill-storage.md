---
name: gsd-kb-fill-storage
description: "Storage auto-discovery and fill: ORM + DDL + API reverse extraction"
argument-hint: "--module <name> --source <path> --output <path> [--models-dir <path>] [--force]"
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
Discover and generate storage documentation for a module.

Searches for table definitions via three strategies:
1. ORM models (`__tablename__`)
2. Raw DDL files (`CREATE TABLE`)
3. API doc reverse extraction (tables referenced in "关联数据库" sections)

Then fills each storage doc with field-level write/read traceability.
</objective>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name
- `--source <path>` (required): backend source code directory
- `--output <path>` (optional, default: `.planning/ontology`): documentation output directory
- `--models-dir <path>` (optional): override ORM models directory
- `--force` (optional): re-fill ALL sections and regenerate 关联需求. Without --force, only fill "待补充" sections and append new 关联需求 entries.

**🔒 --force 行为定义（强制执行，不可自行跳过）：**

当传入 `--force` 时：
- **必须**重新读取 ORM/DDL 源码并完整重写每个 storage 文档
- **禁止**判断"现有文件已符合规范"而跳过重写
- **禁止**输出"文件保持现状"然后不做任何修改
- 唯一不覆盖的是 `<!-- manual -->` 标记的段落

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name
- `--source <path>` (required): backend source code directory
- `--output <path>` (optional, default: `.planning/ontology`): documentation output directory
- `--models-dir <path>` (optional): ORM models directory, skip auto-discovery if provided

Determine PROJECT_ROOT: walk up from `--source` until `pyproject.toml` / `package.json` / `setup.py` found.

## Step 2: Discover all tables

### Strategy 1: ORM models
If `--models-dir` passed, use it directly. Otherwise:
- Search from PROJECT_ROOT for `*/domain/models/` or `*/models/` containing files with `__tablename__`
- Extract table names from `__tablename__ = '{name}'` patterns

### Strategy 2: Raw DDL files
Search for files containing `CREATE TABLE` statements:
```bash
grep -rl "CREATE TABLE" "$PROJECT_ROOT" --include="*.py" --include="*.sql" | grep -v .venv | grep -v node_modules
```
Extract table names from `CREATE TABLE IF NOT EXISTS {table_name}` patterns.

### Strategy 3: API doc reverse extraction
Scan all `$OUTPUT/$MODULE/apis/*.md` for "关联数据库" table sections. Extract unique table names referenced.

### Merge and deduplicate
Combine all three sources into a unique table list.

## Step 3: Scaffold missing storage docs

For each table that has no corresponding doc in `$OUTPUT/$MODULE/storage/`:

**If KB CLI available:**
```bash
KB_CLI=""
for candidate in \
  "$HOME/.claude/gsd-core/knowledge-base" \
  "$HOME/.claude/knowledge-base" \
  "$(pwd)/knowledge-base" \
  "$HOME/gsd-core/knowledge-base"; do
  if [ -f "$candidate/packages/cli/__main__.py" ]; then
    KB_CLI="$candidate"
    break
  fi
done

if [ -n "$KB_CLI" ]; then
  cd "$KB_CLI"
  PYTHONIOENCODING=utf-8 python -m packages.cli scaffold --source "$MODELS_DIR" --module "$MODULE" --output "$OUTPUT" --no-auto-detect
  PYTHONIOENCODING=utf-8 python -m packages.cli --kb-path "$OUTPUT" batch-fill --module "$MODULE" --source "$PROJECT_ROOT" --workers 8
fi
```

**If KB CLI NOT available:**
Generate a storage skeleton manually for each table:
```markdown
# {table_name} — 待补充

> 来源: `{source_file}` ({orm|ddl|api-reverse})

## 基本信息
| 字段 | 值 |
|------|-----|
| 存储类型 | 关系型数据库 (PostgreSQL) |
| 模块 | {module} |
| 表名 | {table_name} |
| 负责人 | 待补充 |
| 需求来源 | 待补充 |

## 字段定义
| 字段 | 类型 | 索引 | 写入来源 | 读取去向 | 业务规则 | 说明 |
|------|------|------|---------|---------|---------|------|
{columns from DDL/ORM, or "待补充" rows}
```

## Step 4: Fill storage docs (deep semantic)

For each `$OUTPUT/$MODULE/storage/*.md` that still contains "待补充" in 写入来源/读取去向:
1. Read the ORM model file or DDL definition (if available)
2. Read the API source code that references this table
3. Spawn an agent that traces which APIs read/write each field:
   - 写入来源: which API/task writes this field
   - 读取去向: which API/page reads this field
   - 业务规则: constraints, state machine rules, computed fields
   - 关联接口: all APIs that touch this table
   - 状态流转: if status field exists, document the state machine
   - **🆕 约束驱动断言: 从字段约束自动推导测试断言**

### 约束驱动断言（🔒 必填 — 供 gen-tests 直接消费生成异常测试）

每个 storage 文档必须包含 `## 约束驱动断言` 段，从字段定义的约束自动推导：

```markdown
## 约束驱动断言

| 约束类型 | 字段 | 违反时预期行为 | 触发接口 | 断言 |
|---------|------|--------------|---------|------|
| UNIQUE | order_no | 重复插入返回 409 或 422 | POST /orders | `{"type": "status", "operator": "in", "expected": [409, 422]}` |
| FK | customer_id → customers.id | 引用不存在的 customer 返回 404 或 422 | POST /orders | `{"type": "status", "operator": "in", "expected": [404, 422]}` |
| NOT NULL | name | 字段为空时返回 422 | POST /agents | `{"type": "status", "expected": 422}` |
| CHECK | amount >= 0 | 负数返回 422 | POST /items | `{"type": "status", "expected": 422}` |
| VARCHAR(N) | name(128) | 超长字符串返回 422 | POST /agents | `{"type": "status", "expected": 422}` |
| ENUM | status ∈ {draft,running,stopped} | 非法枚举值返回 422 | PATCH /agents/{id} | `{"type": "status", "expected": 422}` |
```

**推导规则（机械化，从字段定义直接映射）：**

| 字段约束 | 自动生成的测试场景 | 预期 HTTP 码 |
|---------|-----------------|-------------|
| `UNIQUE` | 先 INSERT 一条，再 INSERT 相同值 | 409 或 422（取决于框架处理方式） |
| `FK(other_table.id)` | INSERT 时 FK 字段传一个不存在的 UUID | 404 或 422 |
| `NOT NULL` (非默认值字段) | INSERT 时不传该字段 / 传 null | 422 |
| `CHECK(field >= N)` | INSERT 时传 N-1 | 422 |
| `VARCHAR(N)` / `String(N)` | INSERT 时传 N+1 长度的字符串 | 422 |
| `ENUM(values)` | INSERT 时传不在枚举列表中的值 | 422 |

**触发接口确定规则：**
- 从"关联接口"表中找到对该字段有 INSERT/UPDATE 操作的接口
- 如果多个接口都写入该字段，每个都生成一行

**🔒 下游消费（gen-tests-api / gen-tests-e2e）：**
- gen-tests-api 从此表直接生成 `_ERR` 和 `_BOUNDARY` 测试文件
- gen-tests-e2e 的异常路径测试引用此表确定预期状态码
- 如果约束类型为 UNIQUE，额外生成幂等性测试（第二次调用的预期行为）

**🔒 关联接口段填写规范（强制 — 用于图谱边提取）：**

"关联接口" 表中必须引用具体的 API 文件名，禁止模糊描述。

✅ 正确：
| 接口 | 操作 | 涉及字段 |
|------|------|---------|
| start-instance.md | SELECT | key, value |
| run-agent.md | SELECT | key='persistent_sandbox_enabled' |

❌ 错误（禁止）：
| 接口 | 操作 | 涉及字段 |
|------|------|---------|
| 服务内部（lifecycle, start-instance） | SELECT | key, value |
| Agent 创建/编辑流程（内部） | INSERT / DELETE | 全部字段 |

规则：
- "接口"列的值必须是 `$OUTPUT/$MODULE/apis/` 目录下实际存在的文件名（不含路径前缀）
- 如果是被 job 访问的表，"接口"列写 job 文件名：`lifecycle-heartbeat.md`
- 如果是纯内部服务调用（无对应 API 或 job 文档），写 `[内部: {service_name}]` 并补充说明
- 禁止写 "服务内部"、"Agent 创建/编辑流程" 这样的模糊描述
- Agent prompt 中传入实际 API 文件列表和 job 文件列表供参考：
  ```
  API files: {list of filenames in $OUTPUT/$MODULE/apis/}
  Job files: {list of filenames in $OUTPUT/$MODULE/jobs/}
  ```

**🔒 格式校验规则（Agent 输出 + merge 后验证）：**
- 文件名格式：纯文件名，不含路径前缀（`build-agent.md`，不是 `apis/build-agent.md` 或 `../apis/build-agent.md`）
- 文件名必须含 `.md` 后缀
- 文件名匹配策略（同 fill-requirements）：先精确匹配 API_FILES 列表，未命中则尝试新旧命名规范变体
- **Post-merge 校验（🔒 mandatory）：** merge 完成后，扫描所有 storage 文档的"关联接口"列值，检查每个值是否存在于 `$OUTPUT/$MODULE/apis/` 或 `$OUTPUT/$MODULE/jobs/` 中。不存在的标记 WARNING 输出到报告：
  ```
  ⚠️  storage/{table}.md 关联接口引用了不存在的文件: {filename}
      请检查文件名拼写或确认该 API 文档是否已生成
  ```

## Step 5: Report

```
GSD > KB-FILL-STORAGE Complete
────────────────────────────────────────────────────────────
Module:      {module}
Tables discovered: {N} (ORM: {n1}, DDL: {n2}, API-reverse: {n3})
Storage docs: {filled}/{total} filled
────────────────────────────────────────────────────────────
```

**If 0 tables discovered from ALL sources:**
```
ℹ️  No storage references found — this module may not own any tables directly.
```

## Step 6: Backfill reverse traceability — "关联需求" (🔒 mandatory post-fill)

After all storage docs are filled, add reverse links to requirements:

For each storage doc in `$OUTPUT/$MODULE/storage/*.md`:
1. Read graph.json → find edges where `target == "sandbox:storage:{table-name}"` and `relation == "writes_to"`
2. For each `source` API node, follow reverse `implemented_by` edges to find the requirement
3. If the storage doc does NOT have a `## 关联需求` section, append:

```markdown
## 关联需求

| 需求 | 关系 | 说明 |
|------|------|------|
| REQ-SB-005 | 通过 create-agent-session, delete-agent-session 写入 | 会话管理与历史记录 |
| REQ-SB-003 | 通过 delete-agent 级联删除 | Agent 停止与删除 |
```

4. If the section already exists, merge new entries (avoid duplicates)

Derivation logic:
- Storage ←(writes_to)← API ←(implemented_by)← Requirement
- Group by requirement, list the intermediate APIs in "关系" column

</process>

<notes>
- Safe to re-run: only fills "待补充" placeholders, preserves existing content
- Discovers tables from 3 sources (ORM + DDL + API reverse) for maximum coverage
- Step 6 adds bidirectional traceability: Storage → Requirement (via graph reverse edges)
- NEVER silently produces 0 docs — always logs why
</notes>
