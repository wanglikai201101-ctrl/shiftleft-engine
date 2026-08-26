"""图谱构建器：从模块文档中提取节点和边。

解析策略：
1. MODULE.md 的需求追溯表 → requirement 节点 + implemented_by 边
2. apis/*.md 的基本信息表 → api 节点
3. apis/*.md 的依赖接口/被依赖接口/关联数据库表 → depends_on/writes_to/reads_from 边
4. storage/*.md → storage 节点
5. pages/*.md → page 节点 + calls 边
6. jobs/*.md → job 节点 + triggers 边
7. requirements/*.md 的关联实现表 → implemented_by 边
8. config/*.md → config 节点 + reads_from 边（关联接口/数据库）
9. integration/*.md → integration 节点 + depends_on/writes_to/reads_from 边
10. error-handling/*.md → error-handling 节点 + affects/writes_to 边
11. permissions/*.md → permissions 节点 + protects/reads_from/guards 边
"""

import json
import re
from pathlib import Path
from typing import List, Optional

from .store import Graph, Node, Edge, GraphStore


class GraphBuilder:
    """从模块文档目录构建图谱"""

    def __init__(self, modules_dir: str = "modules"):
        self.modules_dir = Path(modules_dir)
        # Reverse lookup: (module, METHOD, normalized_router_path) → api_node_id
        self._api_path_index: dict = {}

    REVERSE_MAP = {
        "implemented_by": "implements",
        "writes_to": "written_by",
        "reads_from": "read_by",
        "calls": "called_by",
        "depends_on": "depended_by",
        "affects": "affected_by",
        "protects": "protected_by",
        "guards": "guarded_by",
        "navigates_to": "navigated_from",
    }

    def build(self, merge: bool = False, graph_output_dir: Optional[str] = None) -> Graph:
        """构建完整图谱

        Args:
            merge: If True and existing graph.json exists, preserve nodes/edges
                   from old graph that the new scan doesn't produce. New scan
                   results take precedence (update existing, add new).
            graph_output_dir: Path to the graph output directory (where graph.json lives).
                              Required when merge=True to locate the existing graph.
        """
        # Load existing graph if merge mode
        old_graph: Optional[Graph] = None
        if merge and graph_output_dir:
            store = GraphStore(output_dir=graph_output_dir)
            old_graph = store.load()

        # Build new graph from scratch (current logic)
        graph = Graph()
        modules = [
            d for d in self.modules_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]
        graph.module_count = len(modules)

        for module_dir in modules:
            module_name = module_dir.name
            self._parse_module(module_dir, module_name, graph)

        # 过滤掉 source/target 不存在于节点集中的边（防止 D3 渲染崩溃）
        node_ids = {n.id for n in graph.nodes}
        graph.edges = [e for e in graph.edges if e.from_id in node_ids and e.to_id in node_ids]

        # Merge with old graph if requested
        if merge and old_graph:
            graph = self._merge_graphs(old_graph, graph)

        # 生成反向边（双向追溯）
        self._generate_reverse_edges(graph)

        # 检测孤岛节点
        graph.orphan_report = self._detect_orphans(graph)

        return graph

    def _merge_graphs(self, old_graph: Graph, new_graph: Graph) -> Graph:
        """Merge old graph with new graph. New graph takes precedence.

        Logic:
        - Nodes in new_graph overwrite same-ID nodes from old_graph
        - Nodes in old_graph not present in new_graph are preserved
        - Edges in new_graph overwrite same (from_id, to_id, relation) from old_graph
        - Edges in old_graph not present in new_graph are preserved
        - Result = old_graph ∪ new_graph (new overwrites old on conflicts)
        """
        merged = Graph()
        merged.module_count = new_graph.module_count
        merged.version = new_graph.version

        # Merge nodes: new takes precedence
        new_node_ids = {n.id for n in new_graph.nodes}
        # Add all new nodes first
        merged.nodes.extend(new_graph.nodes)
        # Add old nodes that are NOT in new graph (preserved)
        for node in old_graph.nodes:
            if node.id not in new_node_ids:
                merged.nodes.append(node)

        # Merge edges: new takes precedence
        new_edge_keys = {(e.from_id, e.to_id, e.relation) for e in new_graph.edges}
        # Add all new edges first
        merged.edges.extend(new_graph.edges)
        # Add old edges that are NOT in new graph (preserved)
        for edge in old_graph.edges:
            key = (edge.from_id, edge.to_id, edge.relation)
            if key not in new_edge_keys:
                # Only preserve if it's not a reverse edge (those are regenerated)
                merged.edges.append(edge)

        # Re-filter edges: remove edges pointing to non-existent nodes
        merged_node_ids = {n.id for n in merged.nodes}
        merged.edges = [
            e for e in merged.edges
            if e.from_id in merged_node_ids and e.to_id in merged_node_ids
        ]

        return merged

    def _generate_reverse_edges(self, graph: Graph):
        """为所有正向边生成反向边，实现双向追溯"""
        existing = {(e.from_id, e.to_id, e.relation) for e in graph.edges}
        reverse_edges = []
        for e in graph.edges:
            rev_relation = self.REVERSE_MAP.get(e.relation)
            if not rev_relation:
                continue
            key = (e.to_id, e.from_id, rev_relation)
            if key not in existing:
                existing.add(key)
                reverse_edges.append(Edge(
                    from_id=e.to_id,
                    to_id=e.from_id,
                    relation=rev_relation,
                    label="",
                    confidence=e.confidence,
                ))
        graph.edges.extend(reverse_edges)

    def _detect_orphans(self, graph: Graph) -> List[dict]:
        """检测孤岛节点，返回诊断报告"""
        connected = set()
        for e in graph.edges:
            connected.add(e.from_id)
            connected.add(e.to_id)

        orphans = []
        for n in graph.nodes:
            if n.id not in connected:
                orphans.append({
                    "node_id": n.id,
                    "type": n.type,
                    "label": n.label,
                    "doc_path": n.doc_path,
                })
        return orphans

    def _parse_module(self, module_dir: Path, module_name: str, graph: Graph):
        """解析单个模块"""
        module_md = module_dir / "MODULE.md"
        if module_md.exists():
            self._parse_module_md(module_md, module_name, graph)

        # 解析 requirements
        req_dir = module_dir / "requirements"
        if req_dir.exists():
            for f in req_dir.glob("*.md"):
                self._parse_requirement(f, module_name, graph)

        # 解析 apis
        api_dir = module_dir / "apis"
        if api_dir.exists():
            for f in api_dir.glob("*.md"):
                self._parse_api_doc(f, module_name, graph)

        # 解析 storage
        storage_dir = module_dir / "storage"
        if storage_dir.exists():
            for f in storage_dir.glob("*.md"):
                self._parse_storage_doc(f, module_name, graph)

        # 解析 pages
        pages_dir = module_dir / "pages"
        # 第一遍：预建 路由路径 → 页面节点ID 索引（供 navigates_to 边解析跳转目标）
        self._route_to_page = {}
        if pages_dir.exists():
            for f in pages_dir.glob("*.md"):
                p_content = f.read_text(encoding="utf-8", errors="ignore")
                p_route = self._extract_field(p_content, "路由路径")
                if p_route:
                    p_route = p_route.strip().split("?")[0].rstrip("/")
                    self._route_to_page[p_route] = f"{module_name}:page:{f.stem}"
        # 第二遍：正式解析页面文档
        if pages_dir.exists():
            for f in pages_dir.glob("*.md"):
                self._parse_page_doc(f, module_name, graph)

        # 解析 jobs
        jobs_dir = module_dir / "jobs"
        if jobs_dir.exists():
            for f in jobs_dir.glob("*.md"):
                self._parse_job_doc(f, module_name, graph)

        # 解析 config
        config_dir = module_dir / "config"
        if config_dir.exists():
            for f in config_dir.glob("*.md"):
                self._parse_config_doc(f, module_name, graph)

        # 解析 integration
        integration_dir = module_dir / "integration"
        if integration_dir.exists():
            for f in integration_dir.glob("*.md"):
                self._parse_integration_doc(f, module_name, graph)

        # 解析 error-handling
        error_dir = module_dir / "error-handling"
        if error_dir.exists():
            for f in error_dir.glob("*.md"):
                self._parse_error_handling_doc(f, module_name, graph)

        # 解析 permissions
        permissions_dir = module_dir / "permissions"
        if permissions_dir.exists():
            for f in permissions_dir.glob("*.md"):
                self._parse_permissions_doc(f, module_name, graph)

    def _parse_module_md(self, path: Path, module_name: str, graph: Graph):
        """从 MODULE.md 的需求追溯表提取关联"""
        content = path.read_text(encoding="utf-8", errors="ignore")

        # 解析需求追溯表
        table = self._extract_table_after_heading(content, "需求追溯")
        if not table:
            return

        for row in table:
            if len(row) < 5:
                continue
            req_id = row[0].strip()
            req_name = row[1].strip()
            tables_str = row[3].strip()
            pages_str = row[4].strip()

            if not req_id or req_id == "待补充":
                continue

            # 创建 requirement 节点
            req_node_id = f"{module_name}:{req_id}"
            self._add_node(graph, Node(
                id=req_node_id,
                type="requirement",
                label=f"{req_id} — {req_name}",
                module=module_name,
                doc_path=f"requirements/{req_id}.md",
            ))

            # NOTE: 不再从 MODULE.md 短名生成 API implemented_by 边
            # 短名（如 "build, run, stop"）缺少 HTTP method 前缀，无法生成正确的 node ID
            # API 的 implemented_by 边完全由 _parse_requirement 从 REQ-*.md 的"关联接口"表构建（有精确文件名链接）

            # 解析关联表（表名格式一致，可直接作为 node ID）
            for table_ref in self._split_refs(tables_str):
                table_node_id = f"{module_name}:table:{table_ref}"
                self._add_edge(graph, Edge(
                    from_id=req_node_id,
                    to_id=table_node_id,
                    relation="implemented_by",
                    label=f"{req_id} → {table_ref}",
                ))

            # 解析关联页面
            for page_ref in self._split_refs(pages_str):
                page_node_id = f"{module_name}:page:{page_ref}"
                self._add_edge(graph, Edge(
                    from_id=req_node_id,
                    to_id=page_node_id,
                    relation="implemented_by",
                    label=f"{req_id} → {page_ref}",
                ))

    def _parse_requirement(self, path: Path, module_name: str, graph: Graph):
        """解析需求文档 — 创建节点 + 从关联接口表构建 implemented_by 边"""
        content = path.read_text(encoding="utf-8", errors="ignore")
        req_id = path.stem  # e.g. REQ-SB-001

        req_node_id = f"{module_name}:{req_id}"
        title = self._extract_title(content)
        self._add_node(graph, Node(
            id=req_node_id,
            type="requirement",
            label=title or req_id,
            module=module_name,
            doc_path=str(path.relative_to(self.modules_dir)),
        ))

        # 从 "### 关联接口" 表构建 implemented_by 边
        api_table = self._extract_table_after_heading(content, "关联接口")
        if api_table:
            seen_apis = set()
            for row in api_table:
                if len(row) >= 2:
                    api_path_str = row[1].strip()  # "POST /api/v1/sandbox/build"
                    if api_path_str and api_path_str != "待补充":
                        # 尝试从第 3 列的链接提取文件名
                        api_file = None
                        if len(row) >= 3:
                            link_match = re.search(r'\[([^\]]+\.md)\]', row[2])
                            if link_match:
                                api_file = link_match.group(1)

                        if api_file:
                            # 用文件名作为 node ID（去掉 .md）
                            api_node_id = f"{module_name}:api:{api_file.replace('.md', '')}"
                        else:
                            # 用路径规范化
                            api_node_id = self._normalize_api_id(api_path_str, module_name)

                        if api_node_id not in seen_apis:
                            seen_apis.add(api_node_id)
                            self._add_edge(graph, Edge(
                                from_id=req_node_id,
                                to_id=api_node_id,
                                relation="implemented_by",
                                confidence="EXTRACTED",
                            ))

        # 从 "### 关联数据库" 表构建 REQ → Storage 可达路径（通过 writes_to）
        db_table = self._extract_table_after_heading(content, "关联数据库")
        if db_table:
            for row in db_table:
                if len(row) >= 2:
                    table_name = row[1].strip()
                    if table_name and table_name != "待补充":
                        # 可能是 "agents, sandbox_instances" 多个表
                        for t in re.split(r'[,，]', table_name):
                            t = t.strip()
                            if t:
                                table_id = f"{module_name}:table:{t}"
                                self._add_edge(graph, Edge(
                                    from_id=req_node_id,
                                    to_id=table_id,
                                    relation="implemented_by",
                                    confidence="INFERRED",
                                ))

    def _parse_api_doc(self, path: Path, module_name: str, graph: Graph):
        """解析接口文档"""
        content = path.read_text(encoding="utf-8", errors="ignore")
        title = self._extract_title(content)

        # 从基本信息表提取方法和路径
        method_path = self._extract_field(content, "方法|HTTP 方法")
        api_path = self._extract_field(content, "路径")
        req_source = self._extract_field(content, "需求来源")
        source_file = self._extract_field(content, "文件路径|源文件|文件|Source|代码位置")
        function_name = self._extract_field(content, "函数名|函数|Function")

        # Build source_path from extracted fields
        source_path = ""
        if source_file and source_file != "待补充":
            source_path = source_file
            if function_name and function_name != "待补充":
                source_path = f"{source_file}:{function_name}"

        # Fallback: parse "> 源函数: `file::function`" line (scaffold-generated docs)
        if not source_path:
            source_path = self._extract_source_function(content)

        api_id = f"{module_name}:api:{path.stem}"
        self._add_node(graph, Node(
            id=api_id,
            type="api",
            label=title or path.stem,
            module=module_name,
            doc_path=str(path.relative_to(self.modules_dir)),
            source_path=source_path,
        ))

        # Register in path index for reverse lookup by _normalize_api_id
        self._register_api_path(api_id, path.stem, method_path, api_path, module_name)

        # 需求来源 → edge
        if req_source and req_source != "待补充":
            for ref in self._split_refs(req_source):
                req_node_id = f"{module_name}:{ref}"
                self._add_edge(graph, Edge(
                    from_id=req_node_id,
                    to_id=api_id,
                    relation="implemented_by",
                ))

        # 解析依赖接口（上游）
        dep_table = self._extract_table_after_heading(content, "依赖接口")
        if dep_table:
            for row in dep_table:
                if len(row) >= 1:
                    dep_api = row[0].strip()
                    if dep_api and dep_api != "待补充":
                        dep_id = self._normalize_api_id(dep_api, module_name)
                        self._add_edge(graph, Edge(
                            from_id=api_id,
                            to_id=dep_id,
                            relation="depends_on",
                        ))

        # 解析关联数据库
        db_table = self._extract_table_after_heading(content, "关联数据库")
        if db_table:
            for row in db_table:
                if len(row) >= 2:
                    table_name = row[0].strip()
                    operation = row[1].strip() if len(row) > 1 else ""
                    if table_name and table_name != "待补充":
                        table_id = f"{module_name}:table:{table_name}"
                        relation = "writes_to" if "写" in operation or "INSERT" in operation.upper() or "UPDATE" in operation.upper() else "reads_from"
                        self._add_edge(graph, Edge(
                            from_id=api_id,
                            to_id=table_id,
                            relation=relation,
                        ))

        # 解析关联前端页面
        page_table = self._extract_table_after_heading(content, "关联前端页面")
        if page_table:
            for row in page_table:
                if len(row) >= 1:
                    page_name = row[0].strip()
                    if page_name and page_name != "待补充":
                        page_id = f"{module_name}:page:{page_name}"
                        self._add_edge(graph, Edge(
                            from_id=page_id,
                            to_id=api_id,
                            relation="calls",
                        ))

    def _parse_storage_doc(self, path: Path, module_name: str, graph: Graph):
        """解析存储文档"""
        content = path.read_text(encoding="utf-8", errors="ignore")
        title = self._extract_title(content)

        # 从文件名推断表名（如 db-t_order.md → t_order）
        stem = path.stem
        table_name = stem.replace("db-", "").replace("mq-", "").replace("redis-", "")

        storage_id = f"{module_name}:table:{table_name}"
        self._add_node(graph, Node(
            id=storage_id,
            type="storage",
            label=title or table_name,
            module=module_name,
            doc_path=str(path.relative_to(self.modules_dir)),
        ))

    def _parse_page_doc(self, path: Path, module_name: str, graph: Graph):
        """解析页面文档 — 创建节点 + 从接口调用顺序/用户操作流构建 calls 边"""
        content = path.read_text(encoding="utf-8", errors="ignore")
        title = self._extract_title(content)

        # Extract source_path: 组件路径 or 文件路径 or 代码位置
        source_file = self._extract_field(content, "组件路径|文件路径|源文件|Component|代码位置")
        source_path = source_file if source_file and source_file != "待补充" else ""
        # Fallback: parse "> 源函数:" or "> 组件:" line
        if not source_path:
            source_path = self._extract_source_function(content)

        page_id = f"{module_name}:page:{path.stem}"
        self._add_node(graph, Node(
            id=page_id,
            type="page",
            label=title or path.stem,
            module=module_name,
            doc_path=str(path.relative_to(self.modules_dir)),
            source_path=source_path,
        ))

        # 从 "接口调用顺序" 段提取 API 调用（匹配反引号内的 METHOD /path 模式）
        api_pattern = re.compile(r'`(GET|POST|PUT|PATCH|DELETE|WEBSOCKET)\s+(/[^`]+)`', re.IGNORECASE)
        seen_apis = set()

        # 提取 "接口调用顺序" 段落内容
        seq_match = re.search(r'##\s+接口调用顺序.*?\n(.*?)(?=\n##\s|\Z)', content, re.DOTALL)
        if seq_match:
            seq_content = seq_match.group(1)
            for m in api_pattern.finditer(seq_content):
                method = m.group(1).upper()
                api_path = m.group(2).strip()
                api_node_id = self._normalize_api_id(f"{method} {api_path}", module_name)
                if api_node_id not in seen_apis:
                    seen_apis.add(api_node_id)
                    self._add_edge(graph, Edge(
                        from_id=page_id,
                        to_id=api_node_id,
                        relation="calls",
                        confidence="EXTRACTED",
                    ))

        # 从 "用户操作流" 表的 "关联接口" 列提取
        flow_table = self._extract_table_after_heading(content, "用户操作流")
        if flow_table:
            for row in flow_table:
                # 关联接口通常是最后一列
                if len(row) >= 5:
                    api_col = row[4].strip()
                    if api_col and api_col != "—" and api_col != "待补充":
                        for m in api_pattern.finditer(api_col):
                            method = m.group(1).upper()
                            api_path = m.group(2).strip()
                            api_node_id = self._normalize_api_id(f"{method} {api_path}", module_name)
                            if api_node_id not in seen_apis:
                                seen_apis.add(api_node_id)
                                self._add_edge(graph, Edge(
                                    from_id=page_id,
                                    to_id=api_node_id,
                                    relation="calls",
                                    confidence="EXTRACTED",
                                ))
                        # 也尝试匹配无方法前缀的路径（如 "DELETE /{id}/sessions/{sid}"）
                        simple_match = re.search(r'(GET|POST|PUT|PATCH|DELETE)\s+(/\S+)', api_col, re.IGNORECASE)
                        if simple_match:
                            method = simple_match.group(1).upper()
                            api_path = simple_match.group(2).strip()
                            api_node_id = self._normalize_api_id(f"{method} {api_path}", module_name)
                            if api_node_id not in seen_apis:
                                seen_apis.add(api_node_id)
                                self._add_edge(graph, Edge(
                                    from_id=page_id,
                                    to_id=api_node_id,
                                    relation="calls",
                                    confidence="INFERRED",
                                ))

        # 从 "页面元素清单" 表的 "触发接口" 列提取
        elem_table = self._extract_table_after_heading(content, "页面元素清单")
        if elem_table:
            for row in elem_table:
                if len(row) >= 4:
                    trigger_api = row[3].strip()  # 触发接口列
                    if trigger_api and trigger_api != "—" and trigger_api != "待补充":
                        for m in api_pattern.finditer(trigger_api):
                            method = m.group(1).upper()
                            api_path = m.group(2).strip()
                            api_node_id = self._normalize_api_id(f"{method} {api_path}", module_name)
                            if api_node_id not in seen_apis:
                                seen_apis.add(api_node_id)
                                self._add_edge(graph, Edge(
                                    from_id=page_id,
                                    to_id=api_node_id,
                                    relation="calls",
                                    confidence="INFERRED",
                                ))

        # 从 "用户操作流" 表的 "跳转目标" 列（第 6 列）提取 page→page navigates_to 边
        # 跳转目标是跨页流程测试的结构化数据源（gen-tests-ui full_flow / regression flow-scope 消费）
        for row in flow_table:
            if len(row) >= 6:
                nav_col = row[5].strip()
                if nav_col and nav_col not in ("—", "待补充"):
                    for target_route in re.split(r'[,，、;；\s]+', nav_col):
                        target_id = self._resolve_nav_target(target_route)
                        if target_id and target_id != page_id:
                            self._add_edge(graph, Edge(
                                from_id=page_id,
                                to_id=target_id,
                                relation="navigates_to",
                                confidence="EXTRACTED",
                            ))

    def _parse_job_doc(self, path: Path, module_name: str, graph: Graph):
        """解析任务文档"""
        content = path.read_text(encoding="utf-8", errors="ignore")
        title = self._extract_title(content)

        source_file = self._extract_field(content, "文件路径|源文件|Source|任务文件|代码位置")
        source_path = source_file if source_file and source_file != "待补充" else ""
        # Fallback: parse "> 源函数:" line
        if not source_path:
            source_path = self._extract_source_function(content)

        job_id = f"{module_name}:job:{path.stem}"
        self._add_node(graph, Node(
            id=job_id,
            type="job",
            label=title or path.stem,
            module=module_name,
            doc_path=str(path.relative_to(self.modules_dir)),
            source_path=source_path,
        ))

        # 解析关联数据库
        db_table = self._extract_table_after_heading(content, "关联数据库|操作的数据")
        if db_table:
            for row in db_table:
                if len(row) >= 1:
                    table_name = row[0].strip()
                    if table_name and table_name != "待补充":
                        table_id = f"{module_name}:table:{table_name}"
                        self._add_edge(graph, Edge(
                            from_id=job_id,
                            to_id=table_id,
                            relation="writes_to",
                        ))

    def _parse_integration_doc(self, path: Path, module_name: str, graph: Graph):
        """解析集成文档 — 创建 integration 节点 + 从关联接口/关联数据库构建边"""
        content = path.read_text(encoding="utf-8", errors="ignore")
        title = self._extract_title(content)

        source_file = self._extract_field(content, "源文件|文件路径|Source|代码位置")
        source_path = source_file if source_file and source_file != "待补充" else ""
        # Fallback: parse "> 源函数:" line
        if not source_path:
            source_path = self._extract_source_function(content)

        integration_id = f"{module_name}:integration:{path.stem}"
        self._add_node(graph, Node(
            id=integration_id,
            type="integration",
            label=title or path.stem,
            module=module_name,
            doc_path=str(path.relative_to(self.modules_dir)),
            source_path=source_path,
        ))

        # 需求来源 → edge
        req_source = self._extract_field(content, "需求来源")
        if req_source and req_source != "待补充":
            for ref in self._split_refs(req_source):
                req_node_id = f"{module_name}:{ref}"
                self._add_edge(graph, Edge(
                    from_id=req_node_id,
                    to_id=integration_id,
                    relation="implemented_by",
                ))

        # 解析关联接口
        api_table = self._extract_table_after_heading(content, "关联接口")
        if api_table:
            for row in api_table:
                if len(row) >= 1:
                    api_ref = row[0].strip()
                    if api_ref and api_ref != "待补充":
                        link_match = re.search(r'\[([^\]]+\.md)\]', api_ref)
                        if link_match:
                            api_node_id = f"{module_name}:api:{link_match.group(1).replace('.md', '')}"
                        else:
                            api_node_id = self._normalize_api_id(api_ref, module_name)
                        self._add_edge(graph, Edge(
                            from_id=integration_id,
                            to_id=api_node_id,
                            relation="depends_on",
                            confidence="INFERRED",
                        ))

        # 解析关联数据库
        db_table = self._extract_table_after_heading(content, "关联数据库")
        if db_table:
            for row in db_table:
                if len(row) >= 1:
                    table_name = row[0].strip()
                    if table_name and table_name != "待补充":
                        table_id = f"{module_name}:table:{table_name}"
                        operation = row[1].strip() if len(row) > 1 else ""
                        relation = "writes_to" if "写" in operation or "INSERT" in operation.upper() or "UPDATE" in operation.upper() else "reads_from"
                        self._add_edge(graph, Edge(
                            from_id=integration_id,
                            to_id=table_id,
                            relation=relation,
                            confidence="INFERRED",
                        ))

    def _parse_error_handling_doc(self, path: Path, module_name: str, graph: Graph):
        """解析错误处理文档 — 创建 error-handling 节点 + 从关联接口/数据库/任务构建边"""
        content = path.read_text(encoding="utf-8", errors="ignore")
        title = self._extract_title(content)

        source_file = self._extract_field(content, "源文件|文件路径|Source|代码位置")
        source_path = source_file if source_file and source_file != "待补充" else ""
        # Fallback: parse "> 源函数:" line
        if not source_path:
            source_path = self._extract_source_function(content)

        error_id = f"{module_name}:error-handling:{path.stem}"
        self._add_node(graph, Node(
            id=error_id,
            type="error-handling",
            label=title or path.stem,
            module=module_name,
            doc_path=str(path.relative_to(self.modules_dir)),
            source_path=source_path,
        ))

        # 需求来源 → edge
        req_source = self._extract_field(content, "需求来源")
        if req_source and req_source != "待补充":
            for ref in self._split_refs(req_source):
                req_node_id = f"{module_name}:{ref}"
                self._add_edge(graph, Edge(
                    from_id=req_node_id,
                    to_id=error_id,
                    relation="implemented_by",
                ))

        # 解析关联接口
        api_table = self._extract_table_after_heading(content, "关联接口")
        if api_table:
            for row in api_table:
                if len(row) >= 1:
                    api_ref = row[0].strip()
                    if api_ref and api_ref != "待补充":
                        link_match = re.search(r'\[([^\]]+\.md)\]', api_ref)
                        if link_match:
                            api_node_id = f"{module_name}:api:{link_match.group(1).replace('.md', '')}"
                        else:
                            api_node_id = self._normalize_api_id(api_ref, module_name)
                        self._add_edge(graph, Edge(
                            from_id=api_node_id,
                            to_id=error_id,
                            relation="affects",
                            confidence="INFERRED",
                        ))

        # 解析关联数据库
        db_table = self._extract_table_after_heading(content, "关联数据库")
        if db_table:
            for row in db_table:
                if len(row) >= 1:
                    table_name = row[0].strip()
                    if table_name and table_name != "待补充":
                        table_id = f"{module_name}:table:{table_name}"
                        self._add_edge(graph, Edge(
                            from_id=error_id,
                            to_id=table_id,
                            relation="writes_to",
                            confidence="INFERRED",
                        ))

        # 解析关联任务
        job_table = self._extract_table_after_heading(content, "关联任务")
        if job_table:
            for row in job_table:
                if len(row) >= 1:
                    job_ref = row[0].strip()
                    if job_ref and job_ref != "待补充":
                        job_node_id = f"{module_name}:job:{job_ref.replace('.md', '')}"
                        self._add_edge(graph, Edge(
                            from_id=job_node_id,
                            to_id=error_id,
                            relation="affects",
                            confidence="INFERRED",
                        ))

    def _parse_permissions_doc(self, path: Path, module_name: str, graph: Graph):
        """解析权限文档 — 创建 permissions 节点 + 从关联接口/数据库/页面构建边"""
        content = path.read_text(encoding="utf-8", errors="ignore")
        title = self._extract_title(content)

        source_file = self._extract_field(content, "源文件|文件路径|Source|代码位置")
        source_path = source_file if source_file and source_file != "待补充" else ""
        # Fallback: parse "> 源函数:" line
        if not source_path:
            source_path = self._extract_source_function(content)

        perm_id = f"{module_name}:permissions:{path.stem}"
        self._add_node(graph, Node(
            id=perm_id,
            type="permissions",
            label=title or path.stem,
            module=module_name,
            doc_path=str(path.relative_to(self.modules_dir)),
            source_path=source_path,
        ))

        # 需求来源 → edge
        req_source = self._extract_field(content, "需求来源")
        if req_source and req_source != "待补充":
            for ref in self._split_refs(req_source):
                req_node_id = f"{module_name}:{ref}"
                self._add_edge(graph, Edge(
                    from_id=req_node_id,
                    to_id=perm_id,
                    relation="implemented_by",
                ))

        # 解析关联接口 (permissions protects APIs)
        api_table = self._extract_table_after_heading(content, "关联接口")
        if api_table:
            for row in api_table:
                if len(row) >= 1:
                    api_ref = row[0].strip()
                    if api_ref and api_ref != "待补充":
                        link_match = re.search(r'\[([^\]]+\.md)\]', api_ref)
                        if link_match:
                            api_node_id = f"{module_name}:api:{link_match.group(1).replace('.md', '')}"
                        else:
                            api_node_id = self._normalize_api_id(api_ref, module_name)
                        self._add_edge(graph, Edge(
                            from_id=perm_id,
                            to_id=api_node_id,
                            relation="protects",
                            confidence="INFERRED",
                        ))

        # 解析关联数据库
        db_table = self._extract_table_after_heading(content, "关联数据库")
        if db_table:
            for row in db_table:
                if len(row) >= 1:
                    table_name = row[0].strip()
                    if table_name and table_name != "待补充":
                        table_id = f"{module_name}:table:{table_name}"
                        self._add_edge(graph, Edge(
                            from_id=perm_id,
                            to_id=table_id,
                            relation="reads_from",
                            confidence="INFERRED",
                        ))

        # 解析关联页面
        page_table = self._extract_table_after_heading(content, "关联页面")
        if page_table:
            for row in page_table:
                if len(row) >= 1:
                    page_ref = row[0].strip()
                    if page_ref and page_ref != "待补充":
                        page_node_id = f"{module_name}:page:{page_ref.replace('.md', '')}"
                        self._add_edge(graph, Edge(
                            from_id=perm_id,
                            to_id=page_node_id,
                            relation="guards",
                            confidence="INFERRED",
                        ))

    def _parse_config_doc(self, path: Path, module_name: str, graph: Graph):
        """解析配置文档 — 创建 config 节点 + 从关联接口/关联数据库构建边"""
        content = path.read_text(encoding="utf-8", errors="ignore")
        title = self._extract_title(content)

        source_file = self._extract_field(content, "源文件|文件路径|Source|代码位置")
        source_path = source_file if source_file and source_file != "待补充" else ""
        # Fallback: parse "> 源函数:" line
        if not source_path:
            source_path = self._extract_source_function(content)

        config_id = f"{module_name}:config:{path.stem}"
        self._add_node(graph, Node(
            id=config_id,
            type="config",
            label=title or path.stem,
            module=module_name,
            doc_path=str(path.relative_to(self.modules_dir)),
            source_path=source_path,
        ))

        # 需求来源 → edge
        req_source = self._extract_field(content, "需求来源")
        if req_source and req_source != "待补充":
            for ref in self._split_refs(req_source):
                req_node_id = f"{module_name}:{ref}"
                self._add_edge(graph, Edge(
                    from_id=req_node_id,
                    to_id=config_id,
                    relation="implemented_by",
                ))

        # 解析关联接口
        api_table = self._extract_table_after_heading(content, "关联接口")
        if api_table:
            for row in api_table:
                if len(row) >= 1:
                    api_ref = row[0].strip()
                    if api_ref and api_ref != "待补充":
                        link_match = re.search(r'\[([^\]]+\.md)\]', api_ref)
                        if link_match:
                            api_node_id = f"{module_name}:api:{link_match.group(1).replace('.md', '')}"
                        else:
                            api_node_id = self._normalize_api_id(api_ref, module_name)
                        self._add_edge(graph, Edge(
                            from_id=api_node_id,
                            to_id=config_id,
                            relation="reads_from",
                            confidence="INFERRED",
                        ))

        # 解析关联数据库
        db_table = self._extract_table_after_heading(content, "关联数据库")
        if db_table:
            for row in db_table:
                if len(row) >= 1:
                    table_name = row[0].strip()
                    if table_name and table_name != "待补充":
                        table_id = f"{module_name}:table:{table_name}"
                        self._add_edge(graph, Edge(
                            from_id=config_id,
                            to_id=table_id,
                            relation="reads_from",
                            confidence="INFERRED",
                        ))

    # ── Helper methods ──

    def _add_node(self, graph: Graph, node: Node):
        """添加节点，避免重复"""
        if not graph.get_node(node.id):
            graph.nodes.append(node)

    def _add_edge(self, graph: Graph, edge: Edge):
        """添加边，避免完全重复"""
        for e in graph.edges:
            if e.from_id == edge.from_id and e.to_id == edge.to_id and e.relation == edge.relation:
                return
        graph.edges.append(edge)

    def _extract_title(self, content: str) -> str:
        """提取文档标题（第一个 # 行）"""
        m = re.search(r'^#\s+(.+)', content, re.MULTILINE)
        return m.group(1).strip() if m else ""

    def _extract_field(self, content: str, field_pattern: str) -> str:
        """从 markdown 表格中提取字段值"""
        pattern = rf'\|\s*(?:{field_pattern})\s*\|\s*([^|]+)\|'
        m = re.search(pattern, content, re.IGNORECASE)
        if not m:
            return ""
        value = m.group(1).strip()
        # Strip backticks wrapping (e.g. `OrderService#createOrder — desc`)
        if value.startswith('`') and value.endswith('`'):
            value = value[1:-1]
        return value

    def _extract_source_function(self, content: str) -> str:
        """从文档开头的 '> 源函数: `file::function`' 或 '> 组件: `file`' 行提取 source_path"""
        # Format: > 源函数: `path/to/file.py::function_name`
        m = re.search(r'>\s*源函数:\s*`([^`]+)`', content)
        if m:
            ref = m.group(1).strip()
            parts = ref.split("::")
            file_path = parts[0]
            func_name = parts[1] if len(parts) > 1 else None
            if func_name:
                return f"{file_path}:{func_name}"
            return file_path

        # Format: > 组件: `path/to/Component.tsx`
        m = re.search(r'>\s*组件:\s*`([^`]+)`', content)
        if m:
            return m.group(1).strip()

        # Format: > 来源: `path/to/file.py` (type)
        m = re.search(r'>\s*来源:\s*`([^`]+)`', content)
        if m:
            return m.group(1).strip().split(" ")[0]

        return ""

    def _extract_table_after_heading(self, content: str, heading_pattern: str) -> List[List[str]]:
        """提取指定标题下的表格数据行"""
        pattern = rf'##\s+(?:{heading_pattern}).*?\n'
        m = re.search(pattern, content, re.IGNORECASE)
        if not m:
            return []

        after = content[m.end():]
        rows = []
        for line in after.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                break
            if line.startswith("|") and not re.match(r'\|[\s\-:]+\|', line):
                cells = [c.strip() for c in line.split("|")[1:-1]]
                # 跳过表头（通常是第一行数据行，如果包含"字段""类型"等）
                if cells and not any(c in ("字段", "参数", "需求编号", "接口", "表", "页面", "任务", "索引名", "触发接口/任务", "消费接口/任务", "存储节点", "配置类型") for c in cells[:1]):
                    rows.append(cells)
                elif cells and cells[0] in ("字段", "参数", "需求编号", "接口", "表", "页面", "任务", "索引名", "触发接口/任务", "消费接口/任务", "存储节点", "配置类型"):
                    continue  # skip header
                else:
                    rows.append(cells)
        return rows

    def _split_refs(self, text: str) -> List[str]:
        """分割逗号/顿号分隔的引用列表"""
        if not text or text == "待补充" or text == "—":
            return []
        parts = re.split(r'[,，、;；]', text)
        return [p.strip() for p in parts if p.strip() and p.strip() != "待补充"]

    def _resolve_nav_target(self, target_route: str) -> str:
        """将跳转目标路由解析为页面节点 ID。精确匹配优先，动态段归一化回退。

        例："/dashboard/agent/{id}" 可匹配 "/dashboard/agent/[id]" 或 "/dashboard/agent/:id"
        """
        route = target_route.strip().split("?")[0].rstrip("/")
        if not route.startswith("/"):
            return ""
        if route in self._route_to_page:
            return self._route_to_page[route]
        norm = self._norm_route(route)
        for candidate, pid in self._route_to_page.items():
            if self._norm_route(candidate) == norm:
                return pid
        return ""

    @staticmethod
    def _norm_route(route: str) -> str:
        """把 {x}/{{x}}/[x]/:x 动态段统一为 {DYN}，用于路由模糊匹配"""
        r = route.strip().rstrip("/")
        r = re.sub(r'\{[^}]*\}', '{DYN}', r)
        r = re.sub(r'\[[^\]]*\]', '{DYN}', r)
        r = re.sub(r':[A-Za-z_][A-Za-z0-9_]*', '{DYN}', r)
        return r

    def _normalize_api_id(self, api_ref: str, module_name: str) -> str:
        """将接口引用规范化为节点 ID（查表优先，回退到字符串匹配）"""
        api_ref = api_ref.strip()
        m = re.match(r'(GET|POST|PUT|DELETE|PATCH|WEBSOCKET)\s+(/\S+)', api_ref, re.IGNORECASE)
        if not m:
            slug = re.sub(r'[^a-zA-Z0-9_-]', '-', api_ref).strip('-')
            return f"{module_name}:api:{slug}"

        method = m.group(1).upper()
        raw_path = m.group(2)

        # Strip query string
        raw_path = raw_path.split("?")[0]

        # Try lookup table first
        resolved = self._lookup_api_by_path(method, raw_path, module_name)
        if resolved:
            return resolved

        # Fallback: derive from filename convention (best-effort)
        path = raw_path
        path = re.sub(r'/api/v\d+/', '/', path)
        path = re.sub(r'/sse/', '/', path)
        # Strip module name segment
        path = re.sub(rf'^/{re.escape(module_name)}/', '/', path)
        # Normalize path params to {snake_case} and keep them
        path = re.sub(r'/\{([^}]+)\}', lambda pm: '/{' + self._to_snake_case(pm.group(1)) + '}', path)
        slug = path.strip("/").replace("/", "-")
        return f"{module_name}:api:{method}-{slug}"

    def _register_api_path(self, api_id: str, stem: str, method_field: str, path_field: str, module_name: str):
        """Register API node in the path index for reverse lookup."""
        # Extract method from stem (e.g. "POST-{agent_id}-chat" → "POST")
        stem_method_match = re.match(r'(GET|POST|PUT|DELETE|PATCH|WEBSOCKET)', stem, re.IGNORECASE)
        method = stem_method_match.group(1).upper() if stem_method_match else (method_field or "").upper().strip()

        # Use the "路径" field from the doc as the router-relative path
        router_path = (path_field or "").strip()
        if router_path and router_path != "待补充":
            key = (module_name, method, self._normalize_router_path(router_path))
            self._api_path_index[key] = api_id

        # Also register by stem-derived path (reconstruct from filename)
        # e.g. "POST-{agent_id}-chat" → method=POST, path_parts=["{agent_id}", "chat"]
        if stem_method_match:
            stem_path = stem[len(method) + 1:]  # strip "POST-" prefix
            # Reconstruct path: "agent_id}-chat" won't work, use stem directly as index key
            key_stem = (module_name, method, stem[len(method) + 1:])
            self._api_path_index.setdefault(key_stem, api_id)

    def _lookup_api_by_path(self, method: str, full_path: str, module_name: str) -> str | None:
        """Try to find an API node ID by matching a full deployed path against the index."""
        # Strategy: progressively strip known URL prefixes and try matching
        candidates = [full_path]

        # Strip /api/v1/ or /api/v2/ prefix
        stripped = re.sub(r'^/api/v\d+/', '/', full_path)
        if stripped != full_path:
            candidates.append(stripped)

        # Strip /sse/ sub-application prefix
        stripped2 = re.sub(r'^/sse/', '/', stripped)
        if stripped2 != stripped:
            candidates.append(stripped2)

        # Strip module name from path
        stripped3 = re.sub(rf'^/{re.escape(module_name)}/', '/', stripped)
        if stripped3 != stripped:
            candidates.append(stripped3)

        # Strip both /sse/ and module name
        stripped4 = re.sub(rf'^/{re.escape(module_name)}/', '/', stripped2)
        if stripped4 != stripped2:
            candidates.append(stripped4)

        for path_candidate in candidates:
            normalized = self._normalize_router_path(path_candidate)
            key = (module_name, method, normalized)
            if key in self._api_path_index:
                return self._api_path_index[key]

        # Fuzzy match: normalize param names to snake_case and try again
        for path_candidate in candidates:
            normalized = self._normalize_router_path(path_candidate)
            normalized_snake = re.sub(r'\{([^}]+)\}', lambda pm: '{' + self._to_snake_case(pm.group(1)) + '}', normalized)
            key = (module_name, method, normalized_snake)
            if key in self._api_path_index:
                return self._api_path_index[key]

        return None

    def _normalize_router_path(self, path: str) -> str:
        """Normalize a router path for index matching."""
        path = path.strip().rstrip("/")
        if not path.startswith("/"):
            path = "/" + path
        return path

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert camelCase/PascalCase to snake_case."""
        s1 = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
        s2 = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', s1)
        return s2.lower()
