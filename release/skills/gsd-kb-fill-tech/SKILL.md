---
name: gsd-kb-fill-tech
description: "Phase 1 only: CLI batch-fill for knowledge-base docs — fast static extraction (params, types, fields) from AST"
argument-hint: "--module <module-name> --source <code-dir> --output <doc-dir> [--force]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Grep
  - Glob
---



<objective>
Fast static extraction of technical details from source code into documentation skeletons.

Uses CLI `batch-fill` command to extract via AST/regex:
- Request parameters (names, types, required)
- ORM field definitions (column types, constraints)
- Route metadata (HTTP method, path)

This is the FAST phase (~seconds). It only fills what regex/AST can determine.
For deep semantic fill (business rules, requirements, page elements), use `/gsd-kb-fill-ai`.
</objective>

<critical-rules>
🚫 HALT — 逐条阅读以下规则，违反任何一条 = 输出无效，必须删除重做

1. 🚫 NEVER write files to apis/, pages/, storage/, requirements/, jobs/, graph/, tests/ directories
   - fill-tech ONLY writes to: `$OUTPUT/$MODULE/tech.md` (single file)
   - 其他目录由各自专属 skill 管理（fill-apis, fill-pages, fill-storage 等）
2. 🚫 NEVER create SERVICE-*.md, _INDEX.md, or any freeform file names in other KB subdirectories
3. 🚫 NEVER write more than 1 file — output is ALWAYS a single `tech.md` at `$OUTPUT/$MODULE/tech.md`
4. 🚫 If CLI tool is not found → STOP and return error ("KB CLI not found — cannot batch-fill tech.md"). NEVER fall back to manual source code scanning.

违反以上任何一条 = 立即停止，输出 "BOUNDARY VIOLATION: {which rule}" 并退出。
</critical-rules>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name in the docs output directory
- `--source <path>` (required): source code directory
- `--output <path>` (optional, default: `.planning/ontology`): documentation output directory
- `--force` (optional): re-run batch-fill with `--overwrite` flag, overwriting existing filled content. Without --force, only fills "待补充" placeholders.

## Step 2: Locate CLI and determine SOURCE_ROOT

🔒 CLI 路径检测（使用规范 KB_CLI 解析块）：

```bash
# Canonical KB_CLI resolution — use directly, do NOT search $HOME
KB_CLI="${KB_CLI:-}"
if [ -z "$KB_CLI" ]; then
  for c in \
    "$HOME/.claude/gsd-core/knowledge-base" \
    "$HOME/.claude/knowledge-base" \
    "$(pwd)/knowledge-base"; do
    if [ -d "$c/packages/cli" ]; then KB_CLI="$c"; break; fi
  done
fi
if [ -z "$KB_CLI" ]; then
  for d in $(find "$HOME" -maxdepth 6 -type d -path "*knowledge-base/packages/cli" 2>/dev/null); do
    KB_CLI="$(dirname "$(dirname "$d")")"; break
  done
fi
```

If KB_CLI is still empty, return an error immediately — do NOT search further or reverse-engineer the CLI from source.

```bash
# Determine SOURCE_ROOT (project root where skeleton path refs resolve)
SOURCE_ROOT="$SOURCE"
while [ ! -f "$SOURCE_ROOT/pyproject.toml" ] && [ ! -f "$SOURCE_ROOT/package.json" ] && [ ! -f "$SOURCE_ROOT/setup.py" ] && [ "$SOURCE_ROOT" != "/" ]; do
  SOURCE_ROOT=$(dirname "$SOURCE_ROOT")
done
```

## Step 3a: Execute batch-fill (PRIMARY — when CLI found)

```bash
cd "$KB_CLI"
PYTHONIOENCODING=utf-8 python -m packages.cli --kb-path "$OUTPUT/$MODULE" batch-fill --module "$MODULE" --source "$SOURCE_ROOT" --workers 8
```

**IMPORTANT**:
- Command is `batch-fill` (with hyphen), NOT `fill`
- `--kb-path` MUST come BEFORE the subcommand
- `--kb-path` points to `$OUTPUT/$MODULE` (the module's KB directory where MODULE.md lives)
- `--source` points to project root (NOT the subdirectory)
- If the command succeeds → DONE. Skip Step 3b.

## Step 3b: CLI not found → HARD ERROR (no manual fallback)

🔒 If KB_CLI is still empty after Step 2's canonical resolution:
- **STOP** and return an error: **"KB CLI not found — cannot batch-fill tech.md; run /gsd-kb-fill-tech after the KB CLI is available"**
- Do **NOT** scan source code manually to generate tech.md.
- Do **NOT** reverse-engineer the CLI from source.
- The CLI `batch-fill` command is the **only sanctioned fast path** for fill-tech.

**UPDATE-FIRST 增量更新优先（🔒 默认写路径）：**

如果 `tech.md` **已存在且符合模板规范**（所有必需 `##` 段齐全，关键字段无 `待补充`）：
1. **先 READ** 目标 `tech.md`
2. 使用 **Edit 工具** 只修改受影响的段落（更新字段值、插入/更新表格行、追加 `变更记录` 行）
3. **逐字节保留所有未修改内容**，包括文件现有的行尾风格（CRLF vs LF）

**只有以下情况才使用完整 Write（整体重写）：**
- 文档是新建的（brand-new doc，尚不存在）
- 传入了 `--force`
- 文档缺少必需模板段（schema 迁移）

## Step 4: Report

Display filled/skipped/failed counts (from CLI) or the hard-error message (if KB CLI was not found).

</process>

<notes>
- This is Phase 1 only. For AI semantic fill, run `/gsd-kb-fill-ai` after this.
- Safe to re-run: only fills "待补充" placeholders, preserves existing content (unless --force is passed).
- With --force: overwrites all filled content with fresh extraction from source code.
- Typical time: 5-30 seconds for 50-100 docs (CLI path).
- CLI batch-fill fills ALL doc types (apis/, storage/, etc.) — not just tech.md.
  When CLI is available, it does the heavy lifting; fill-tech just orchestrates the call.
</notes>
