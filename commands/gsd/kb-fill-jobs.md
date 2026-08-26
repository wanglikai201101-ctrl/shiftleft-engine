---
name: gsd-kb-fill-jobs
description: "Jobs auto-discovery: celery tasks, asyncio background tasks, timer-based cleanup logic"
argument-hint: "--module <name> --source <path> --output <path> [--force]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
---



<objective>
Discover and generate job/background-task documentation for a module.

Searches for both explicit task frameworks (celery, APScheduler) and implicit async
background logic (asyncio.create_task, timeout cleanup, keep-alive timers).

A module with keep-alive, autosave, timeout cleanup, or orphan detection logic
ALWAYS has background jobs — this skill must find and document them.
</objective>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name
- `--source <path>` (required): backend source code directory
- `--output <path>` (optional, default: `.planning/ontology`): documentation output directory
- `--force` (optional): re-generate ALL job docs, overwriting existing content. Without --force, only create new job docs for undocumented tasks and skip existing ones.

**🔒 --force 行为定义（强制执行，不可自行跳过）：**

当传入 `--force` 时：
- **必须**重新读取源代码并完整重写每个 job 文档
- **禁止**判断"现有文件已符合规范"而跳过重写
- **禁止**输出"文件保持现状"然后不做任何修改
- 唯一不覆盖的是 `<!-- manual -->` 标记的段落

Determine PROJECT_ROOT: walk up from `--source` until `pyproject.toml` / `package.json` / `setup.py` found.

## Step 2: Discover background tasks

Search the project using ALL of these patterns:

### Explicit task frameworks
```bash
grep -rn "@app\.task\|@celery\.task\|@celery_app\.task\|@shared_task\|@periodic_task\|crontab(\|@scheduler\.scheduled_job" "$PROJECT_ROOT" --include="*.py" | grep -v .venv | grep -v node_modules
```
Search scope: from `--source` upward, then in `tasks/`, `jobs/`, `workers/`, `celery_tasks/` directories.

### Implicit async background tasks
```bash
grep -rn "asyncio\.create_task(\|BackgroundTasks\.add_task(\|repeat_every(\|threading\.Timer(" "$SOURCE" --include="*.py"
```

### Timer/timeout-based logic
```bash
grep -rn "_TIMEOUT\|_INTERVAL\|_PERIOD\|_EXPIRE" "$SOURCE" --include="*.py"
```
Then check if these constants are used with periodic cleanup functions (loop, while True, scheduled check).

### Lifecycle hooks
```bash
grep -rn "@app\.on_event\|lifespan" "$SOURCE" --include="*.py"
```

## Step 3: Classify and generate job docs

For each discovered task:

### Explicit tasks (celery/scheduler)
Generate standard job skeleton with:
- `| 类型 | Celery Task |` or `| 类型 | 定时调度 |`
- Schedule/cron expression if found
- Source function reference

### Implicit background tasks (asyncio.create_task, timers, timeout cleanup)
Generate job skeleton with:
- `| 类型 | 内嵌异步任务（非独立进程） |`
- Trigger condition (e.g. "API调用触发", "心跳超时触发")
- Source location in the router/proxy file

Example patterns that MUST be recognized as jobs:
- `asyncio.create_task(_bg_save())` → autosave background job
- `_ONLINE_TIMEOUT = 120` + periodic cleanup in keep-alive → dead detection / online user cleanup job
- `_orphan_sids` cleanup logic → orphan sandbox cleanup job
- `_bg_append_history()` → chat history persistence job

### Job doc template
```markdown
# {job_name} — {description}

> 源函数: `{file_path}::{function_name}`

## 基本信息
| 字段 | 值 |
|------|-----|
| 模块 | {module} |
| 任务名 | {job_name} |
| 类型 | {Celery Task | 内嵌异步任务（非独立进程）} |
| 触发方式 | {cron表达式 | API调用 | 事件触发 | 超时触发} |
| 需求来源 | 待补充 |

## 触发条件
| 条件 | 来源 | 说明 |
|------|------|------|
| {trigger_condition} | {source} | {description} |

## 执行逻辑
{numbered steps describing what the task does}

## 错误处理
| 场景 | 处理方式 | 说明 |
|------|---------|------|
| {failure_scenario} | {handling} | {description} |

## 关联数据库
| 表 | 操作 | 字段 | 业务规则 | 说明 |
|-----|------|------|---------|------|

## 关联接口
| 接口 | 关系 | 说明 |
|------|------|------|

## 变更记录
| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 影响范围 |
|------|------|--------|--------|--------|--------|
| v1.0 | 待补充 | scaffold 自动生成 | 无（新建） | 从代码反推骨架 | 待补充 |
```

## Step 4: Handle "no jobs" case

**If genuinely no jobs exist** (no explicit tasks, no implicit background tasks, no timeout-based cleanup):
- Remove the empty `$OUTPUT/$MODULE/jobs/` directory (do not leave empty folders)
- Update MODULE.md "模块资产清单" table: `| 定时任务文档 | 0（该模块无定时任务） | jobs/ |`
- Do NOT leave a bare "0" — always annotate the reason

**IMPORTANT**: A module with `keep-alive`, `autosave`, `timeout cleanup`, or `orphan detection` logic ALWAYS has background jobs — do NOT report "0" for such modules.

## Step 5: Report

```
GSD > KB-FILL-JOBS Complete
────────────────────────────────────────────────────────────
Module:      {module}
Jobs found:  {N} (explicit: {n1}, implicit: {n2})
Job docs:    {generated}/{total}
────────────────────────────────────────────────────────────
```

</process>

<notes>
- Safe to re-run: skips existing job doc files (unless --force is passed)
- With --force: overwrites all job docs with fresh content from source code
- Recognizes both explicit (celery) and implicit (asyncio, timers) background tasks
- A module with keep-alive/autosave/timeout logic MUST report jobs
</notes>
