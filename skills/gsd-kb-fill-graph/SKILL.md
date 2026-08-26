---
name: gsd-kb-fill-graph
description: "Build knowledge graph: graph.json + interactive D3 visualization (graph.html)"
argument-hint: "--module <name> --output <path>"
allowed-tools:
  - Read
  - Write
  - Bash
  - Grep
  - Glob
---



<objective>
Build the knowledge graph for a module by scanning all generated documentation.

Produces:
- `graph.json` — structured node/edge data
- `graph.html` — interactive D3.js force-directed visualization (offline-capable)
- Copies `d3.v7.min.js` for local file:// access
</objective>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name
- `--output <path>` (optional, default: `.planning/ontology`): documentation output directory (where MODULE.md lives)

## Step 2: Locate KB CLI

**优先使用 pipeline 传入的路径（在 prompt 中以 `KB_CLI="..."` 形式提供）。**
如果 pipeline 未提供路径，执行以下搜索：

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
```

**验证（必须执行）：**
```bash
if [ ! -f "$KB_CLI/packages/cli/__main__.py" ]; then
  echo "❌ KB CLI NOT FOUND at: $KB_CLI"
  echo "   Also checked: $HOME/.claude/gsd-core/knowledge-base, $(pwd)/knowledge-base"
  echo "   STOPPING — inline graph construction is PROHIBITED."
  exit 1
fi
```

## Step 3: Build graph

**🔒 必须使用 CLI 代码构建图谱（禁止 inline 手动解析）：**

图谱构建的边解析逻辑（REQ→API, Page→API, API→Storage）已实现在 Python 代码中
（`packages/core/graph/builder.py`），具有确定性和可测试性。
禁止使用自然语言 inline 规则替代代码执行 — AI 执行自然语言规则不可靠（历史教训：sandbox7 孤岛率 23%）。

**判断构建模式：**
- 如果 pipeline 传入模式为 `patch`（增量更新），使用 `--merge` 标志：
  ```bash
  cd "$KB_CLI"
  PYTHONIOENCODING=utf-8 python -m packages.cli --kb-path "$OUTPUT" graph build --output "$OUTPUT/$MODULE/graph" --merge
  ```
- 如果 pipeline 传入模式为 `rebuild`（完全重建）或未指定模式，不加 `--merge`：
  ```bash
  cd "$KB_CLI"
  PYTHONIOENCODING=utf-8 python -m packages.cli --kb-path "$OUTPUT" graph build --output "$OUTPUT/$MODULE/graph"
  ```

**merge 模式说明：**
- 新扫描产出的节点/边覆盖旧图中同 ID 的节点/边（新数据优先）
- 旧图中存在但新扫描没有产出的节点/边保留（防止正则解析失败丢节点）
- 完全新的节点/边直接新增
- 结果 = old_graph ∪ new_graph（new 覆盖 old 中的重复项）

**如果 KB CLI 不可用（Step 2 未找到）：**

🔒 **CIRCUIT BREAKER — HARD STOP:**
```
❌ KB CLI NOT FOUND.
   图谱构建需要 KB CLI (packages/core/graph/builder.py)。
   请确保 gsd-core/knowledge-base/packages/cli/__main__.py 存在。
   已检查路径: [列出所有尝试过的路径]
   运行位置: cd <gsd-core>/knowledge-base && python -m packages.cli graph build
```

**🚫 ABSOLUTE PROHIBITION: 如果 CLI 不可用，你必须立即停止并返回上述错误信息。**
**🚫 禁止尝试 inline 手动构建 graph.json 或 graph.html。**
**🚫 禁止读取文档来"推断"图谱结构。**
**🚫 禁止写入任何 graph 相关文件。**
**🚫 违反此规则 = 上下文耗尽 + pipeline 卡死（已发生过，117次 Write 调用后死亡）。**

Return this exact error text as your response and STOP. Do not proceed to any further steps.

## Step 4: Verify and cleanup

**Verify ALL three files exist (🔒 mandatory):**
```bash
ls "$OUTPUT/$MODULE/graph/graph.json" "$OUTPUT/$MODULE/graph/graph.html" "$OUTPUT/$MODULE/graph/d3.v7.min.js"
```
If ANY file is missing, the step has FAILED — do not proceed.

**Verify graph.html content (🔒 mandatory):**
```bash
# Must contain inline data, not fetch
grep -q "const graph = {" "$OUTPUT/$MODULE/graph/graph.html" || grep -q "var GRAPH_DATA = {" "$OUTPUT/$MODULE/graph/graph.html" || echo "FAIL: no inline graph data"
grep -q "fetch(" "$OUTPUT/$MODULE/graph/graph.html" && echo "FAIL: contains fetch() — PROHIBITED"
grep -q 'src="d3.v7.min.js"' "$OUTPUT/$MODULE/graph/graph.html" || echo "FAIL: no local d3 reference"
```

If any verification fails, REGENERATE via the CLI. Do not attempt manual construction.

**Cleanup stale top-level graph:**
```bash
rm -rf "$OUTPUT/graph" 2>/dev/null || true
```

**Rules:**
- Graph ONLY lives at `$OUTPUT/$MODULE/graph/` (module-level)
- Do NOT generate a separate top-level `$OUTPUT/graph/` directory
- The `graph.html` references local `d3.v7.min.js` — both must be in the same directory

## Step 5: Report and open

```
GSD > KB-FILL-GRAPH Complete
────────────────────────────────────────────────────────────
Module:  {module}
Graph:   {nodes} nodes, {edges} edges
Files:   graph.json + graph.html + d3.v7.min.js
Path:    $OUTPUT/$MODULE/graph/
────────────────────────────────────────────────────────────
```

**🔒 生成完毕后自动在浏览器中打开 graph.html：**
```bash
# Windows
start "" "$OUTPUT/$MODULE/graph/graph.html"
# macOS
# open "$OUTPUT/$MODULE/graph/graph.html"
# Linux
# xdg-open "$OUTPUT/$MODULE/graph/graph.html"
```

</process>

<notes>
- Safe to re-run: rebuilds graph from current doc state
- CLI ONLY — never falls back to inline generation (circuit breaker enforced)
- graph.html is fully self-contained (inline data, local d3.js)
- Edge filter prevents D3 crash on dangling references
- Auto fit-to-screen ensures all nodes visible on load
</notes>
