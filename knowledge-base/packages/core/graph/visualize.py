"""图谱 HTML 可视化生成器

生成一个独立的 HTML 文件，用 D3.js force-directed graph 展示节点和边。
浏览器打开即可交互查看。
"""

import json
from pathlib import Path

from .store import Graph


_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Knowledge Graph — {title}</title>
<style>
  body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #1a1a2e; }}
  svg {{ width: 100vw; height: 100vh; display: block; }}
  .node {{ cursor: pointer; }}
  .node circle {{ stroke: #fff; stroke-width: 1.5px; }}
  .node text {{ font-size: 11px; fill: #e0e0e0; pointer-events: none; }}
  .link {{ stroke-opacity: 0.4; }}
  .link-label {{ font-size: 9px; fill: #888; pointer-events: none; }}
  #tooltip {{ position: absolute; background: #16213e; border: 1px solid #0f3460; border-radius: 6px;
    padding: 10px; color: #e0e0e0; font-size: 12px; display: none; max-width: 300px; z-index: 100; }}
  #legend {{ position: absolute; top: 10px; right: 10px; background: #16213e; border: 1px solid #0f3460;
    border-radius: 6px; padding: 12px; color: #e0e0e0; font-size: 12px; }}
  #legend div {{ margin: 4px 0; display: flex; align-items: center; }}
  #legend span {{ display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }}
  #stats {{ position: absolute; bottom: 10px; left: 10px; background: #16213e; border: 1px solid #0f3460;
    border-radius: 6px; padding: 10px; color: #888; font-size: 11px; }}
  #d3-error {{ display: none; color: #e74c3c; padding: 40px; font-size: 16px; }}
</style>
</head>
<body>
<div id="tooltip"></div>
<div id="legend">
  <div><span style="background:#e74c3c"></span>Requirement</div>
  <div><span style="background:#3498db"></span>API</div>
  <div><span style="background:#2ecc71"></span>Storage</div>
  <div><span style="background:#9b59b6"></span>Page</div>
  <div><span style="background:#f39c12"></span>Job</div>
  <div><span style="background:#95a5a6"></span>Config</div>
</div>
<div id="stats">{stats_text}</div>
<div id="d3-error">
  <h2>D3.js 加载失败</h2>
  <p>无法加载 D3.js（可能是网络限制且本地文件缺失）。</p>
  <p>解决方案：</p>
  <ol><li>手动下载 <a href="https://d3js.org/d3.v7.min.js" style="color:#3498db">d3.v7.min.js</a> 放到与 graph.html 同目录下</li>
  <li>或使用能访问外网的浏览器打开</li></ol>
  <p id="d3-error-stats"></p>
</div>
<script src="./d3.v7.min.js"></script>
<script>
if (typeof d3 === 'undefined') {{
  var s = document.createElement('script');
  s.src = 'https://d3js.org/d3.v7.min.js';
  s.onload = function() {{ if (typeof d3 !== 'undefined') location.reload(); }};
  s.onerror = function() {{
    document.getElementById('d3-error').style.display = 'block';
    document.getElementById('d3-error-stats').textContent = '数据已就绪: {node_count} 节点, {edge_count} 边';
  }};
  document.head.appendChild(s);
}}
</script>
<script>
if (typeof d3 === 'undefined') {{ throw new Error('D3 not available — waiting for async load'); }}
const graph = {graph_json};
const colors = {{
  requirement: "#e74c3c", api: "#3498db", storage: "#2ecc71",
  page: "#9b59b6", job: "#f39c12", config: "#95a5a6"
}};
const edgeColors = {{
  implemented_by: "#e74c3c", writes_to: "#2ecc71", reads_from: "#27ae60",
  calls: "#9b59b6", depends_on: "#3498db", triggers: "#f39c12", navigates_to: "#16a085"
}};

const width = window.innerWidth, height = window.innerHeight;
const svg = d3.select("body").append("svg");
const g = svg.append("g");

svg.call(d3.zoom().on("zoom", (e) => g.attr("transform", e.transform)));

const simulation = d3.forceSimulation(graph.nodes)
  .force("link", d3.forceLink(graph.edges).id(d => d.id).distance(120))
  .force("charge", d3.forceManyBody().strength(-300))
  .force("center", d3.forceCenter(width/2, height/2))
  .force("collision", d3.forceCollide(40));

const link = g.append("g").selectAll("line")
  .data(graph.edges).join("line")
  .attr("class", "link")
  .attr("stroke", d => edgeColors[d.relation] || "#555")
  .attr("stroke-width", 1.5)
  .attr("marker-end", "url(#arrow)");

svg.append("defs").append("marker")
  .attr("id", "arrow").attr("viewBox", "0 -5 10 10")
  .attr("refX", 20).attr("refY", 0)
  .attr("markerWidth", 6).attr("markerHeight", 6)
  .attr("orient", "auto")
  .append("path").attr("d", "M0,-5L10,0L0,5").attr("fill", "#555");

const linkLabel = g.append("g").selectAll("text")
  .data(graph.edges).join("text")
  .attr("class", "link-label")
  .text(d => d.relation);

const node = g.append("g").selectAll("g")
  .data(graph.nodes).join("g")
  .attr("class", "node")
  .call(d3.drag()
    .on("start", (e,d) => {{ if(!e.active) simulation.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }})
    .on("drag", (e,d) => {{ d.fx=e.x; d.fy=e.y; }})
    .on("end", (e,d) => {{ if(!e.active) simulation.alphaTarget(0); d.fx=null; d.fy=null; }}));

node.append("circle")
  .attr("r", d => d.type === "requirement" ? 14 : 10)
  .attr("fill", d => colors[d.type] || "#555");

node.append("text")
  .attr("dx", 15).attr("dy", 4)
  .text(d => d.label.length > 30 ? d.label.slice(0,30)+"..." : d.label);

const tooltip = d3.select("#tooltip");
node.on("mouseover", (e, d) => {{
  tooltip.style("display", "block")
    .html(`<b>${{d.label}}</b><br>Type: ${{d.type}}<br>Module: ${{d.module}}<br>ID: ${{d.id}}${{d.doc_path ? '<br>Doc: '+d.doc_path : ''}}`)
    .style("left", (e.pageX+10)+"px").style("top", (e.pageY-10)+"px");
}}).on("mouseout", () => tooltip.style("display", "none"));

simulation.on("tick", () => {{
  link.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y).attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);
  linkLabel.attr("x",d=>(d.source.x+d.target.x)/2).attr("y",d=>(d.source.y+d.target.y)/2);
  node.attr("transform", d=>`translate(${{d.x}},${{d.y}})`);
}});
</script>
</body>
</html>"""


def generate_html(graph: Graph, output_path: str = "graph/graph.html", title: str = "Knowledge Base") -> str:
    """生成图谱 HTML 可视化文件"""
    nodes_data = [
        {"id": n.id, "type": n.type, "label": n.label, "module": n.module, "doc_path": n.doc_path}
        for n in graph.nodes
    ]
    edges_data = [
        {"source": e.from_id, "target": e.to_id, "relation": e.relation}
        for e in graph.edges
    ]
    graph_json = json.dumps({"nodes": nodes_data, "edges": edges_data}, ensure_ascii=False)

    stats = graph.stats
    stats_text = f"Nodes: {stats['total_nodes']} | Edges: {stats['total_edges']} | Modules: {stats['modules']}"

    html = _HTML_TEMPLATE.format(
        title=title,
        graph_json=graph_json,
        stats_text=stats_text,
        node_count=stats['total_nodes'],
        edge_count=stats['total_edges'],
    )

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    # Copy bundled d3.js to output directory for offline use
    d3_local = out_path.parent / "d3.v7.min.js"
    if not d3_local.exists():
        # Look for bundled d3 in assets directory
        d3_bundled = Path(__file__).resolve().parent.parent.parent.parent / "assets" / "d3.v7.min.js"
        if d3_bundled.exists():
            import shutil
            shutil.copy2(str(d3_bundled), str(d3_local))
        else:
            # Fallback: try to download
            try:
                import urllib.request
                urllib.request.urlretrieve(
                    "https://d3js.org/d3.v7.min.js",
                    str(d3_local),
                )
            except Exception:
                pass

    return str(out_path)
