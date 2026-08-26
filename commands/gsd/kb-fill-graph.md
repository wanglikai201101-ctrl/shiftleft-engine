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

## Step 3: Build graph

**🔒 必须使用 CLI 代码构建图谱（禁止 inline 手动解析）：**

图谱构建的边解析逻辑（REQ→API, Page→API, API→Storage）已实现在 Python 代码中
（`packages/core/graph/builder.py`），具有确定性和可测试性。
禁止使用自然语言 inline 规则替代代码执行 — AI 执行自然语言规则不可靠（历史教训：sandbox7 孤岛率 23%）。

```bash
cd "$KB_CLI"
PYTHONIOENCODING=utf-8 python -m packages.cli --kb-path "$OUTPUT" graph build --output "$OUTPUT/$MODULE/graph"
```

**如果 KB CLI 不可用（Step 2 未找到）：**
```
❌ 图谱构建需要 KB CLI (packages/core/graph/builder.py)。
   请确保 gsd-core/knowledge-base/packages/cli/__main__.py 存在。
   运行位置: cd <gsd-core>/knowledge-base && python -m packages.cli graph build
```
**STOP — 不要尝试 inline 构建。**

<!--
==============================================================================
以下内容为 builder.py 的设计参考文档，不是执行指令。
实际逻辑已实现在 knowledge-base/packages/core/graph/builder.py 中。
仅在修改 builder.py 时参考此段了解设计意图。
==============================================================================
-->

**3a. Generate graph.json** by scanning all docs in `$OUTPUT/$MODULE/`:

- Parse `requirements/*.md` → requirement nodes (from `# REQ-xxx` title)
- Parse `apis/*.md` → api nodes (extract 需求来源 for edges)
- Parse `storage/*.md` → storage nodes
- Parse `pages/*.md` → page nodes
- Parse `jobs/*.md` → job nodes
- Build edges from:
  - **REQ docs "### 关联接口" table** → `implemented_by` edges (requirement → api)
  - MODULE.md 需求追溯表 → `implemented_by` edges (requirement → api) [备选来源]
  - API docs "关联数据库" → `writes_to` / `reads_from` edges (api → storage)
  - API docs "关联前端页面" → `calls` edges (page → api)
  - API docs "依赖接口" → `depends_on` edges (api → api)
  - API docs "关联定时任务" → `depends_on` edges (api → job)
  - **Page docs "接口调用顺序"** → `calls` edges (page → api) — 提取反引号内的 `{METHOD} /api/v1/...` 模式
  - **Job docs "关联数据库"** → `writes_to` / `reads_from` edges (job → storage)
  - **Job docs "关联接口"** → `affects` edges (job → api)，表示 job 的执行会影响 API 返回的数据
  - **Job docs "需求来源"** → `implemented_by` edges (requirement → job)

**🔒 边构建的数据源优先级和匹配策略：**

### REQ → API 边 (`implemented_by`)

按优先级依次尝试，命中即停：
1. **REQ doc "### 关联接口" 表的"接口文档"列** — 提取 markdown 链接中的文件名 → 匹配 api node
2. **REQ doc "### 关联接口" 表的"接口"列** — 提取 HTTP 方法+路径 → 匹配 api node 的 path
3. **REQ doc 正文中出现的 API 文档文件引用** — `POST-build-agent.md` 或 `build-agent.md` → 匹配 api node
4. **MODULE.md "需求追溯"表** — REQ 行的"关联接口"列
5. **函数名反向匹配** — REQ doc "关联源码"表的函数名 → 匹配 api doc 的"函数名"字段

### Page → API 边 (`calls`)

按优先级依次尝试：
1. **Page doc "接口调用顺序"段** — 提取反引号内 `{METHOD} /api/v1/{module}/...` 模式
2. **Page doc "用户操作流"表的"关联接口"列** — 提取接口路径
3. **Page doc "页面元素清单"的"触发接口"列** — 提取非空接口引用

匹配规则（路径 → api node ID）：
- `POST /api/v1/sandbox/build` → 在 apis/*.md 中找 `方法=POST, 路径含 /build` 的文档 → node ID
- 如果匹配到多个，取路径最精确匹配的那个
- 路径参数 `{agent_id}` 视为通配

**🔒 多匹配精度规则（防止误边）：**

当 `{METHOD} {path}` 匹配到 **多个 API 节点** 时，必须按以下策略消歧：

1. **精确度排序：** 按路径段数排序（段数多 = 更精确），取最长匹配
   - `POST /api/v1/sandbox/build` 只能匹配 `POST-build.md`，不能匹配 `POST-build-version.md`
   - 匹配分数 = 路径重叠段数 / 候选路径总段数（取分数最高的）

2. **方法+路径联合匹配（🔒 强制）：**
   - 必须同时匹配 HTTP 方法和路径，不能只匹配路径
   - `POST /build` 和 `GET /build` 是不同节点，不能混淆
   - 如果路径中 `[SSR]` 前缀存在，提取时忽略该前缀

3. **多匹配 WARNING（强制输出）：**
   - 如果消歧后仍有 2+ 候选 → 选择第一个但输出 WARNING：
   ```
   ⚠️ 路径 POST /api/v1/sandbox/build 匹配到多个节点: [sandbox:api:POST-build, sandbox:api:build-agent]
      选择: sandbox:api:POST-build (精确度更高)
      请检查是否存在重复 API 文档
   ```
   - WARNING 写入 graph build 报告的 `warnings` 数组
   - graph.json 中该边标记 `confidence: "AMBIGUOUS"`

4. **零匹配处理：**
   - 路径在所有 API 节点中无匹配 → 不创建边，输出：
   ```
   ⚠️ 路径 POST /api/v1/sandbox/unknown 无匹配 API 节点 — 跳过边创建
   ```

### 孤岛检测与补救

图谱构建完成后，检测孤立节点。对每种类型的孤岛执行补救：

| 孤岛类型 | 补救策略 |
|---------|---------|
| requirement 孤岛 | 读 REQ doc 全文，搜索任何 API 路径/文件名引用，推断 implemented_by 边 (confidence=INFERRED) |
| page 孤岛 | 读 Page doc 全文，搜索 `/api/v1/` 模式，推断 calls 边 (confidence=INFERRED) |
| api 孤岛 | 读 API doc "关联数据库" + "关联前端页面"，如果有内容但未产生边 → 解析格式问题，报告 warning |
| job 孤岛 | 走现有 ZERO ORPHAN JOBS RULE |

补救产生的边标记 `confidence: "INFERRED"`，区别于正常解析产生的 `EXTRACTED`。

**🔒 ZERO ORPHAN REQUIREMENTS/PAGES RULE（新增）：**
- 每个 requirement 节点必须至少有一条 `implemented_by` 边
- 每个 page 节点必须至少有一条 `calls` 边
- 如果补救后仍为孤岛 → 输出 WARNING 到报告，标注需要人工检查

**🔒 ZERO ORPHAN JOBS RULE:**
Every job node MUST have at least one edge. If a job doc has "关联数据库" or "关联接口" sections filled, those MUST produce edges. If after scanning all docs a job node still has zero edges:
1. Read the job doc's "关联数据库" and "关联接口" sections
2. If they contain table/API references, create the corresponding edges
3. If the job doc has NO "关联数据库" and NO "关联接口" (all "待补充"), connect it to the requirement via "需求来源" field
4. As last resort: if the job clearly operates on a table (e.g. "lifecycle-heartbeat" operates on sandbox_instances), infer the `writes_to` edge from the job name + execution logic description

Write `$OUTPUT/$MODULE/graph/graph.json`:
```json
{
  "nodes": [
    {"id": "{module}:{type}:{stem}", "type": "requirement|api|storage|page|job", "label": "{title}", "module": "{module}"}
  ],
  "edges": [
    {"source": "{node_id}", "target": "{node_id}", "relation": "implemented_by|calls|writes_to|reads_from|depends_on|affects|tested_by"}
  ]
}
```

**🔒 BIDIRECTIONAL GRAPH RULE — every edge implies a reverse traversal path:**

After building all forward edges, generate **reverse index edges** to enable single-hop bidirectional queries:

| Forward Edge | Reverse Edge (auto-generated) | Use Case |
|-------------|-------------------------------|----------|
| REQ →(implemented_by)→ API | API →(implements)→ REQ | "这个 API 属于哪个需求？" |
| API →(writes_to)→ Storage | Storage →(written_by)→ API | "这张表被哪些 API 写入？" |
| API →(reads_from)→ Storage | Storage →(read_by)→ API | "这张表被哪些 API 读取？" |
| Page →(calls)→ API | API →(called_by)→ Page | "这个 API 被哪些页面调用？" |
| API →(depends_on)→ Job | Job →(depended_by)→ API | "这个 Job 影响哪些 API？" |
| REQ →(implemented_by)→ Job | Job →(implements)→ REQ | "这个 Job 属于哪个需求？" |

**🔒 CONFIDENCE TIER — every edge must have a confidence field:**

Each edge carries a `confidence` field indicating how it was derived:

| Tier | Value | Meaning | Example |
|------|-------|---------|---------|
| EXTRACTED | 1.0 | Directly stated in document | API doc "关联数据库" table explicitly names the table |
| INFERRED | 0.7 | Derived from document cross-reference | Graph edge derived from MODULE.md 需求追溯表 |
| AMBIGUOUS | 0.4 | Heuristic/name-based guess | Job name contains table name → inferred writes_to |

Edge format with confidence:
```json
{"source": "{node_id}", "target": "{node_id}", "relation": "...", "confidence": "EXTRACTED|INFERRED|AMBIGUOUS"}
```

Reverse edges inherit the confidence of their forward edge.

Assignment rules:
- Edges from API doc "关联数据库" section → EXTRACTED
- Edges from API doc "依赖接口" section → EXTRACTED
- Edges from MODULE.md "需求追溯" table → INFERRED
- Edges from page doc "接口调用顺序" → EXTRACTED
- Edges from job doc "关联数据库" → EXTRACTED
- Edges from job name heuristic (zero-orphan fallback) → AMBIGUOUS

Implementation:
```
for each edge in forward_edges:
    reverse_edges.append({
        "source": edge.target,
        "target": edge.source,
        "relation": REVERSE_MAP[edge.relation]
    })

REVERSE_MAP = {
    "implemented_by": "implements",
    "writes_to": "written_by",
    "reads_from": "read_by",
    "calls": "called_by",
    "depends_on": "depended_by",
    "affects": "affected_by"
}
```

Final edges = forward_edges + reverse_edges (deduplicated — if a reverse edge already exists as forward, skip).

This ensures: from ANY node in the graph, you can reach ALL related nodes in ONE hop, regardless of direction.

**Edge count expectation:** roughly 2x the forward-only count (minus deduplicates). For sandbox module: ~264 forward → ~500+ total edges.

**3b. Generate graph.html — DO NOT WRITE FROM SCRATCH. Use template + inline data.**

**🔒 The graph.html generation is a MECHANICAL operation, not a creative one:**
1. Read graph.json content into a variable
2. Insert it into the HTML template as `var GRAPH_DATA = {content};`
3. Write the file

**Use this Python script to generate graph.html (PREFERRED method):**
```bash
python -c "
import json, os

output_dir = '$OUTPUT/$MODULE/graph'
graph_json_path = os.path.join(output_dir, 'graph.json')

with open(graph_json_path, 'r', encoding='utf-8') as f:
    graph_data = f.read().strip()

# Parse to get stats
parsed = json.loads(graph_data)
node_count = len(parsed.get('nodes', []))
edge_count = len(parsed.get('edges', []))

# 🔒 Normalize edge fields: from_id/to_id → source/target (D3.js requires source/target)
for edge in parsed.get('edges', []):
    if 'from_id' in edge:
        edge['source'] = edge.pop('from_id')
    if 'to_id' in edge:
        edge['target'] = edge.pop('to_id')

graph_data = json.dumps(parsed, ensure_ascii=False)

html = '''<!DOCTYPE html>
<html>
<head>
<meta charset=\"utf-8\">
<title>Knowledge Graph — $MODULE</title>
<style>
body { margin:0; font-family:-apple-system,sans-serif; background:#1a1a2e; overflow:hidden; }
svg { width:100vw; height:100vh; display:block; }
.link { stroke-opacity:0.8; }
#tooltip { position:fixed; background:rgba(22,33,62,0.95); border:1px solid #0f3460; border-radius:6px; padding:10px; color:#e0e0e0; font-size:12px; display:none; max-width:300px; z-index:1000; }
#title { position:fixed; top:8px; left:10px; color:rgba(224,224,224,0.6); font-size:12px; z-index:10; }
</style>
</head>
<body>
<div id=\"title\">$MODULE — ''' + str(node_count) + ''' nodes, ''' + str(edge_count) + ''' edges — Drag to move · Scroll to zoom</div>
<div id=\"tooltip\"></div>
<script src=\"d3.v7.min.js\"></script>
<script>
if(typeof d3===\"undefined\"){document.body.innerHTML=\"<p style=color:red;padding:40px>D3.js not loaded. Ensure d3.v7.min.js is in same directory.</p>\";throw new Error(\"no d3\");}
</script>
<script>
var GRAPH_DATA = ''' + graph_data + ''';
(function(){
var nodes=GRAPH_DATA.nodes, edges=GRAPH_DATA.edges;
var nodeMap=new Map(nodes.map(function(n){return[n.id,n]}));
edges=edges.filter(function(e){return nodeMap.has(e.source)&&nodeMap.has(e.target)});
var colors={requirement:\"#e74c3c\",api:\"#3498db\",storage:\"#2ecc71\",page:\"#9b59b6\",job:\"#e67e22\"};
var edgeColors={implemented_by:\"#666\",writes_to:\"#2ecc71\",reads_from:\"#3498db\",calls:\"#9b59b6\",depends_on:\"#e67e22\"};
var sizes={requirement:18,api:10,storage:16,page:14,job:13};
var W=window.innerWidth,H=window.innerHeight;
var svg=d3.select(\"body\").append(\"svg\").attr(\"width\",W).attr(\"height\",H);
var g=svg.append(\"g\");
var zoom=d3.zoom().scaleExtent([0.1,4]).on(\"zoom\",function(ev){g.attr(\"transform\",ev.transform)});
svg.call(zoom);
var defs=svg.append(\"defs\");
Object.keys(edgeColors).forEach(function(r){defs.append(\"marker\").attr(\"id\",\"a-\"+r).attr(\"viewBox\",\"0 -5 10 10\").attr(\"refX\",20).attr(\"refY\",0).attr(\"markerWidth\",6).attr(\"markerHeight\",6).attr(\"orient\",\"auto\").append(\"path\").attr(\"d\",\"M0,-5L10,0L0,5\").attr(\"fill\",edgeColors[r])});
var sim=d3.forceSimulation(nodes).force(\"link\",d3.forceLink(edges).id(function(d){return d.id}).distance(80)).force(\"charge\",d3.forceManyBody().strength(-200)).force(\"center\",d3.forceCenter(W/2,H/2)).force(\"collision\",d3.forceCollide().radius(25));
var link=g.append(\"g\").selectAll(\"line\").data(edges).join(\"line\").attr(\"stroke\",function(d){return edgeColors[d.relation]||\"#555\"}).attr(\"stroke-width\",2).attr(\"stroke-opacity\",0.7).attr(\"marker-end\",function(d){return\"url(#a-\"+d.relation+\")\"});
var node=g.append(\"g\").selectAll(\"circle\").data(nodes).join(\"circle\").attr(\"r\",function(d){return sizes[d.type]||10}).attr(\"fill\",function(d){return colors[d.type]||\"#999\"}).attr(\"stroke\",\"#fff\").attr(\"stroke-width\",1.5).call(d3.drag().on(\"start\",function(ev,d){if(!ev.active)sim.alphaTarget(0.3).restart();d.fx=d.x;d.fy=d.y}).on(\"drag\",function(ev,d){d.fx=ev.x;d.fy=ev.y}).on(\"end\",function(ev,d){if(!ev.active)sim.alphaTarget(0);d.fx=null;d.fy=null}));
var lbl=g.append(\"g\").selectAll(\"text\").data(nodes.filter(function(d){return d.type!==\"api\"})).join(\"text\").text(function(d){return d.label.length>20?d.label.slice(0,19)+\"…\":d.label}).attr(\"font-size\",9).attr(\"fill\",\"#ccc\").attr(\"dx\",function(d){return(sizes[d.type]||10)+4}).attr(\"dy\",3).style(\"pointer-events\",\"none\");
var tip=d3.select(\"#tooltip\");
node.on(\"mouseover\",function(ev,d){var conn=edges.filter(function(e){return(e.source.id||e.source)===d.id||(e.target.id||e.target)===d.id});tip.style(\"display\",\"block\").html(\"<b>\"+d.label+\"</b><br>Type: \"+d.type+\"<br>Connections: \"+conn.length).style(\"left\",(ev.clientX+12)+\"px\").style(\"top\",(ev.clientY-10)+\"px\")}).on(\"mouseout\",function(){tip.style(\"display\",\"none\")});
sim.on(\"tick\",function(){link.attr(\"x1\",function(d){return d.source.x}).attr(\"y1\",function(d){return d.source.y}).attr(\"x2\",function(d){return d.target.x}).attr(\"y2\",function(d){return d.target.y});node.attr(\"cx\",function(d){return d.x}).attr(\"cy\",function(d){return d.y});lbl.attr(\"x\",function(d){return d.x}).attr(\"y\",function(d){return d.y})});
sim.on(\"end\",function(){var b=g.node().getBBox();if(!b.width||!b.height)return;var s=0.85*Math.min(W/b.width,H/b.height);var tx=W/2-s*(b.x+b.width/2);var ty=H/2-s*(b.y+b.height/2);svg.transition().duration(750).call(zoom.transform,d3.zoomIdentity.translate(tx,ty).scale(s))});
})();
</script>
</body>
</html>'''

with open(os.path.join(output_dir, 'graph.html'), 'w', encoding='utf-8') as f:
    f.write(html)
print('graph.html generated (' + str(node_count) + ' nodes, ' + str(edge_count) + ' edges)')
"
```

**If Python is not available**, generate the HTML manually following the EXACT same structure above.
The key constraint: `var GRAPH_DATA = {literal JSON};` — no fetch, no external load.

**🔒 ABSOLUTE PROHIBITIONS:**
- ❌ NEVER use `fetch()`, `XMLHttpRequest`, or any async data loading
- ❌ NEVER reference `graph.json` as a runtime dependency from HTML
- ❌ NEVER use CDN as the only d3 source
- ❌ NEVER create a `#legend` div

The COMPLETE HTML template to generate (fill in {placeholders}):

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Knowledge Graph — {module}</title>
<style>
  body { margin: 0; font-family: -apple-system, sans-serif; background: #1a1a2e; overflow: hidden; }
  svg { width: 100vw; height: 100vh; display: block; }
  .node text { font-size: 10px; fill: #e0e0e0; pointer-events: none; }
  .link { stroke-opacity: 0.8; }
  #tooltip { position: absolute; background: #16213e; border: 1px solid #0f3460; border-radius: 6px;
    padding: 10px; color: #e0e0e0; font-size: 12px; display: none; max-width: 300px; z-index: 1000; }
  #title { position: absolute; top: 8px; left: 10px; color: rgba(224,224,224,0.6); font-size: 12px; }
</style>
</head>
<body>
<div id="title">{Module} — {node_count} nodes, {edge_count} edges — Drag to move · Scroll to zoom</div>
<div id="tooltip"></div>
<script src="d3.v7.min.js"></script>
<script>
if (typeof d3 === 'undefined') { document.body.innerHTML = '<p style="color:red;padding:40px;">D3.js not loaded. Ensure d3.v7.min.js is in the same directory.</p>'; throw new Error('no d3'); }
</script>
<script>
const graph = {PASTE_FULL_GRAPH_JSON_HERE};
const nodeIds = new Set(graph.nodes.map(n => n.id));
graph.edges = graph.edges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target));
const colors = {requirement:"#e74c3c", api:"#3498db", storage:"#2ecc71", page:"#9b59b6", job:"#e67e22"};
const edgeColors = {implemented_by:"#666", writes_to:"#2ecc71", reads_from:"#3498db", calls:"#9b59b6", depends_on:"#e67e22"};
const sizes = {requirement:18, api:12, storage:16, page:14, job:13};

const width = window.innerWidth, height = window.innerHeight;
const svg = d3.select("body").append("svg").attr("width", width).attr("height", height);
const g = svg.append("g");
svg.call(d3.zoom().scaleExtent([0.2, 4]).on("zoom", (event) => g.attr("transform", event.transform)));

const simulation = d3.forceSimulation(graph.nodes)
  .force("link", d3.forceLink(graph.edges).id(d => d.id).distance(80))
  .force("charge", d3.forceManyBody().strength(-200))
  .force("center", d3.forceCenter(width/2, height/2))
  .force("collision", d3.forceCollide().radius(25));

svg.append("defs").selectAll("marker").data(["arrow"]).enter().append("marker")
  .attr("id", d => d).attr("viewBox", "0 -5 10 10").attr("refX", 20).attr("refY", 0)
  .attr("markerWidth", 6).attr("markerHeight", 6).attr("orient", "auto")
  .append("path").attr("d", "M0,-5L10,0L0,5").attr("fill", "#666");

const link = g.append("g").selectAll("line").data(graph.edges).enter().append("line")
  .attr("class", "link").attr("stroke", d => edgeColors[d.relation] || "#555")
  .attr("stroke-width", 2).attr("marker-end", "url(#arrow)");

const node = g.append("g").selectAll("g").data(graph.nodes).enter().append("g")
  .call(d3.drag().on("start", (e,d) => { if(!e.active) simulation.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; })
    .on("drag", (e,d) => { d.fx=e.x; d.fy=e.y; })
    .on("end", (e,d) => { if(!e.active) simulation.alphaTarget(0); d.fx=null; d.fy=null; }));

node.append("circle").attr("r", d => sizes[d.type]||8).attr("fill", d => colors[d.type]||"#999").attr("stroke","#fff").attr("stroke-width",1.5);
node.append("text").attr("dx", d => (sizes[d.type]||8)+4).attr("dy", 4)
  .text(d => d.label.length > 25 ? d.label.substring(0,22)+"..." : d.label);

const tooltip = d3.select("#tooltip");
node.on("mouseover", function(event, d) {
  const connected = graph.edges.filter(e => e.source.id===d.id || e.target.id===d.id);
  const info = connected.map(e => { const other = e.source.id===d.id ? e.target : e.source; return e.relation+" → "+other.label; }).join("<br>");
  tooltip.style("display","block").html("<strong>"+d.label+"</strong><br>Type: "+d.type+"<br><br>"+(info||"No connections"))
    .style("left",(event.pageX+10)+"px").style("top",(event.pageY+10)+"px");
}).on("mouseout", () => tooltip.style("display","none"));

simulation.on("tick", () => {
  link.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y).attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);
  node.attr("transform", d => "translate("+d.x+","+d.y+")");
});

simulation.on("end", () => {
  const bounds = g.node().getBBox();
  const scale = 0.85 / Math.max(bounds.width/width, bounds.height/height);
  const tx = width/2 - scale*(bounds.x + bounds.width/2);
  const ty = height/2 - scale*(bounds.y + bounds.height/2);
  svg.transition().duration(750).call(
    d3.zoom().scaleExtent([0.2,4]).on("zoom", e => g.attr("transform", e.transform)).transform,
    d3.zoomIdentity.translate(tx, ty).scale(scale));
});
</script>
</body>
</html>
```

**`{PASTE_FULL_GRAPH_JSON_HERE}`** = the ENTIRE content of graph.json, pasted literally.
Do NOT write `fetch(...)`. Do NOT write a placeholder. Paste the actual JSON object inline.

**3c. Copy d3.v7.min.js for offline use:**
```bash
D3_SOURCE=""
for candidate in \
  "$HOME/.claude/gsd-core/knowledge-base/assets/d3.v7.min.js" \
  "$HOME/.claude/gsd-core/knowledge-base/graph/d3.v7.min.js" \
  "$(pwd)/knowledge-base/assets/d3.v7.min.js"; do
  if [ -f "$candidate" ]; then
    D3_SOURCE="$candidate"
    break
  fi
done
if [ -n "$D3_SOURCE" ]; then
  cp "$D3_SOURCE" "$OUTPUT/$MODULE/graph/d3.v7.min.js"
fi
```

If d3.v7.min.js cannot be found in any candidate path, download it:
```bash
curl -sL "https://d3js.org/d3.v7.min.js" -o "$OUTPUT/$MODULE/graph/d3.v7.min.js"
```

<!-- END design reference -->

## Step 4: Verify and cleanup

**Verify ALL three files exist (🔒 mandatory):**
```bash
ls "$OUTPUT/$MODULE/graph/graph.json" "$OUTPUT/$MODULE/graph/graph.html" "$OUTPUT/$MODULE/graph/d3.v7.min.js"
```
If ANY file is missing, the step has FAILED — do not proceed.

**Verify graph.html content (🔒 mandatory):**
```bash
# Must contain inline data, not fetch
grep -q "const graph = {" "$OUTPUT/$MODULE/graph/graph.html" || echo "FAIL: no inline graph data"
grep -q "fetch(" "$OUTPUT/$MODULE/graph/graph.html" && echo "FAIL: contains fetch() — PROHIBITED"
grep -q 'src="d3.v7.min.js"' "$OUTPUT/$MODULE/graph/graph.html" || echo "FAIL: no local d3 reference"
grep -q "legend" "$OUTPUT/$MODULE/graph/graph.html" && echo "FAIL: contains legend div — PROHIBITED"
```

If any verification fails, REGENERATE the file. Do not proceed with a broken graph.html.

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
- Prefers KB CLI if available, falls back to inline generation
- graph.html is fully self-contained (inline data, local d3.js)
- Edge filter prevents D3 crash on dangling references
- Auto fit-to-screen ensures all nodes visible on load
</notes>
