"""孤岛修复器：诊断孤岛原因并尝试自动建边。

策略：
- API 孤岛：在所有 REQ 文档中搜索该 API 的路径/文件名引用
- Storage 孤岛：在所有 API 文档中搜索该表名引用
- Page 孤岛：在文档中搜索 API 路径模式
- Job 孤岛：在 REQ 文档中搜索 job 名或在 job 文档中搜索表名
"""

import re
from pathlib import Path
from typing import List

from .store import Graph, Edge


class OrphanRepairer:
    """诊断并修复图谱孤岛节点"""

    def __init__(self, modules_dir: str, graph: Graph):
        self.modules_dir = Path(modules_dir)
        self.graph = graph
        self._node_ids = {n.id for n in graph.nodes}

    def repair(self) -> dict:
        """修复所有孤岛，返回报告"""
        orphans = self.graph.orphans()
        repaired = []
        unresolved = []

        for node in orphans:
            edges_added = self._try_repair(node)
            if edges_added:
                repaired.append({
                    "node_id": node.id,
                    "type": node.type,
                    "edges_added": [
                        {"relation": e.relation, "target": e.to_id if e.from_id == node.id else e.from_id}
                        for e in edges_added
                    ],
                })
            else:
                reason = self._diagnose(node)
                unresolved.append({
                    "node_id": node.id,
                    "type": node.type,
                    "label": node.label,
                    "doc_path": node.doc_path,
                    "reason": reason,
                })

        return {"repaired": repaired, "unresolved": unresolved}

    def _try_repair(self, node) -> List[Edge]:
        """尝试修复单个孤岛节点"""
        if node.type == "api":
            return self._repair_api(node)
        elif node.type == "storage":
            return self._repair_storage(node)
        elif node.type == "page":
            return self._repair_page(node)
        elif node.type == "job":
            return self._repair_job(node)
        return []

    def _repair_api(self, node) -> List[Edge]:
        """API 孤岛：从 API 文档本身读取需求来源，或搜索 REQ/page 文档中的引用"""
        edges = []
        parts = node.id.split(":")
        module = parts[0]
        api_stem = parts[2] if len(parts) > 2 else ""

        # Strategy 1: Read API doc's "需求来源" section for REQ references
        doc_path = self._resolve_doc_path(node)
        if doc_path and doc_path.exists():
            content = doc_path.read_text(encoding="utf-8", errors="ignore")
            req_pattern = re.compile(r'REQ-\w+-\d+')
            for m in req_pattern.finditer(content):
                req_id = m.group(0)
                req_node_id = f"{module}:{req_id}"
                if req_node_id in self._node_ids:
                    edge = Edge(
                        from_id=req_node_id,
                        to_id=node.id,
                        relation="implemented_by",
                        confidence="INFERRED",
                    )
                    self._add_edge(edge)
                    edges.append(edge)
                    break

        # Strategy 2: Search all REQ docs for this API stem reference
        if not edges:
            module_dir = self._find_module_dir(module)
            req_dir = module_dir / "requirements"
            if req_dir.exists():
                for req_file in req_dir.glob("*.md"):
                    content = req_file.read_text(encoding="utf-8", errors="ignore")
                    if api_stem in content or api_stem.replace("-", "/") in content:
                        req_id = req_file.stem
                        req_node_id = f"{module}:{req_id}"
                        if req_node_id in self._node_ids:
                            edge = Edge(
                                from_id=req_node_id,
                                to_id=node.id,
                                relation="implemented_by",
                                confidence="INFERRED",
                            )
                            self._add_edge(edge)
                            edges.append(edge)
                            break

        # Strategy 3: Search page docs for this API
        if not edges:
            module_dir = self._find_module_dir(module)
            pages_dir = module_dir / "pages"
            if pages_dir.exists():
                for page_file in pages_dir.glob("*.md"):
                    content = page_file.read_text(encoding="utf-8", errors="ignore")
                    if api_stem in content:
                        page_node_id = f"{module}:page:{page_file.stem}"
                        if page_node_id in self._node_ids:
                            edge = Edge(
                                from_id=page_node_id,
                                to_id=node.id,
                                relation="calls",
                                confidence="INFERRED",
                            )
                            self._add_edge(edge)
                            edges.append(edge)
                            break

        return edges

    def _repair_storage(self, node) -> List[Edge]:
        """Storage 孤岛：从 storage 文档的"关联接口"段读取引用，或搜索 API 文档"""
        edges = []
        parts = node.id.split(":")
        module = parts[0]
        table_name = parts[2] if len(parts) > 2 else ""

        # Strategy 1: Read storage doc's "关联接口" section for API file references
        doc_path = self._resolve_doc_path(node)
        if doc_path and doc_path.exists():
            content = doc_path.read_text(encoding="utf-8", errors="ignore")
            # Look for API doc references like "POST-sync-skills.md"
            api_ref_pattern = re.compile(r'(GET|POST|PUT|DELETE|PATCH)-[a-zA-Z0-9_{}-]+\.md')
            seen = set()
            for m in api_ref_pattern.finditer(content):
                api_file = m.group(0).replace(".md", "")
                api_node_id = f"{module}:api:{api_file}"
                if api_node_id in self._node_ids and api_node_id not in seen:
                    seen.add(api_node_id)
                    # Determine read or write from context
                    line_start = content.rfind("\n", 0, m.start()) + 1
                    line = content[line_start:content.find("\n", m.end())]
                    relation = "written_by" if any(w in line.upper() for w in ["INSERT", "DELETE", "UPDATE", "写"]) else "read_by"
                    edge = Edge(
                        from_id=node.id,
                        to_id=api_node_id,
                        relation=relation,
                        confidence="INFERRED",
                    )
                    self._add_edge(edge)
                    edges.append(edge)

        # Strategy 2: Search API docs for table name references
        if not edges:
            module_dir = self._find_module_dir(module)
            api_dir = module_dir / "apis"
            if api_dir.exists():
                for api_file in api_dir.glob("*.md"):
                    content = api_file.read_text(encoding="utf-8", errors="ignore")
                    if table_name in content:
                        api_node_id = f"{module}:api:{api_file.stem}"
                        if api_node_id in self._node_ids:
                            edge = Edge(
                                from_id=api_node_id,
                                to_id=node.id,
                                relation="reads_from",
                                confidence="INFERRED",
                            )
                            self._add_edge(edge)
                            edges.append(edge)
                            break

        # Strategy 3: Search job docs for table name
        if not edges:
            module_dir = self._find_module_dir(module)
            jobs_dir = module_dir / "jobs"
            if jobs_dir.exists():
                for job_file in jobs_dir.glob("*.md"):
                    content = job_file.read_text(encoding="utf-8", errors="ignore")
                    if table_name in content:
                        job_node_id = f"{module}:job:{job_file.stem}"
                        if job_node_id in self._node_ids:
                            edge = Edge(
                                from_id=job_node_id,
                                to_id=node.id,
                                relation="writes_to",
                                confidence="INFERRED",
                            )
                            self._add_edge(edge)
                            edges.append(edge)
                            break

        return edges

    def _repair_page(self, node) -> List[Edge]:
        """Page 孤岛：读页面文档搜索 API 路径"""
        edges = []
        parts = node.id.split(":")
        module = parts[0]

        doc_path = self._resolve_doc_path(node)
        if not doc_path or not doc_path.exists():
            return edges

        content = doc_path.read_text(encoding="utf-8", errors="ignore")
        api_pattern = re.compile(r'`?(GET|POST|PUT|PATCH|DELETE)\s+(/[^`\s]+)`?', re.IGNORECASE)

        for m in api_pattern.finditer(content):
            method = m.group(1).upper()
            path = m.group(2).strip()
            # Try to find matching API node
            for n in self.graph.nodes:
                if n.type == "api" and n.module == module:
                    if method.lower() in n.id.lower() and self._path_matches(path, n.id):
                        edge = Edge(
                            from_id=node.id,
                            to_id=n.id,
                            relation="calls",
                            confidence="INFERRED",
                        )
                        self._add_edge(edge)
                        edges.append(edge)
                        break
            if edges:
                break

        # Fallback: connect to any REQ that mentions this page name
        if not edges:
            page_stem = parts[2] if len(parts) > 2 else ""
            req_dir = self._find_module_dir(module) / "requirements"
            if req_dir.exists():
                for req_file in req_dir.glob("*.md"):
                    content = req_file.read_text(encoding="utf-8", errors="ignore")
                    if page_stem in content:
                        req_node_id = f"{module}:{req_file.stem}"
                        if req_node_id in self._node_ids:
                            edge = Edge(
                                from_id=req_node_id,
                                to_id=node.id,
                                relation="implemented_by",
                                confidence="INFERRED",
                            )
                            self._add_edge(edge)
                            edges.append(edge)
                            break

        return edges

    def _repair_job(self, node) -> List[Edge]:
        """Job 孤岛：读 job 文档找表名或 REQ 引用"""
        edges = []
        parts = node.id.split(":")
        module = parts[0]

        doc_path = self._resolve_doc_path(node)
        if not doc_path or not doc_path.exists():
            return edges

        content = doc_path.read_text(encoding="utf-8", errors="ignore")

        # Search for table references in job doc
        for n in self.graph.nodes:
            if n.type == "storage" and n.module == module:
                table_name = n.id.split(":")[-1]
                if table_name in content:
                    edge = Edge(
                        from_id=node.id,
                        to_id=n.id,
                        relation="writes_to",
                        confidence="INFERRED",
                    )
                    self._add_edge(edge)
                    edges.append(edge)
                    break

        # Search for REQ references
        if not edges:
            req_pattern = re.compile(r'REQ-\w+-\d+')
            for m in req_pattern.finditer(content):
                req_id = m.group(0)
                req_node_id = f"{module}:{req_id}"
                if req_node_id in self._node_ids:
                    edge = Edge(
                        from_id=req_node_id,
                        to_id=node.id,
                        relation="implemented_by",
                        confidence="INFERRED",
                    )
                    self._add_edge(edge)
                    edges.append(edge)
                    break

        return edges

    def _diagnose(self, node) -> str:
        """诊断孤岛原因"""
        doc_path = self._resolve_doc_path(node)
        if not doc_path or not doc_path.exists():
            return f"doc not found: {node.doc_path}"

        content = doc_path.read_text(encoding="utf-8", errors="ignore")
        if not content.strip():
            return "doc is empty"

        # Check if cross-reference sections exist but are empty
        sections = ["关联接口", "关联数据库", "关联前端页面", "接口调用顺序", "需求来源"]
        found_sections = []
        empty_sections = []
        for s in sections:
            if s in content:
                found_sections.append(s)
                # Check if section content is just "待补充"
                pattern = rf'##\s+{s}.*?\n(.*?)(?=\n##|\Z)'
                match = re.search(pattern, content, re.DOTALL)
                if match and ("待补充" in match.group(1) or not match.group(1).strip()):
                    empty_sections.append(s)

        if empty_sections:
            return f"sections unfilled: {', '.join(empty_sections)}"
        if not found_sections:
            return "no cross-reference sections in doc"
        return "cross-references exist but no matching node found (path mismatch)"

    def _find_module_dir(self, module: str) -> Path:
        """查找模块目录"""
        direct = self.modules_dir / module
        if direct.exists() and (direct / "MODULE.md").exists():
            return direct
        # If modules_dir IS the module (single-module KB)
        if (self.modules_dir / "MODULE.md").exists():
            return self.modules_dir
        # modules_dir is parent of modules
        return direct

    def _resolve_doc_path(self, node) -> Path:
        """解析文档路径"""
        if not node.doc_path:
            return None
        doc_rel = node.doc_path.replace("\\", "/")

        # Try relative to modules_dir directly
        p = self.modules_dir / doc_rel
        if p.exists():
            return p

        # If doc_path starts with module name, strip it (single-module KB layout)
        module = node.module
        if doc_rel.startswith(module + "/"):
            stripped = doc_rel[len(module) + 1:]
            p = self.modules_dir / stripped
            if p.exists():
                return p

        # Try under modules_dir parent
        p = self.modules_dir.parent / doc_rel
        if p.exists():
            return p

        return None

    def _path_matches(self, url_path: str, node_id: str) -> bool:
        """检查 URL 路径是否匹配 node ID"""
        # Extract meaningful path segments
        segments = [s for s in url_path.strip("/").split("/") if s and not s.startswith("{") and s not in ("api", "v1", "v2")]
        node_lower = node_id.lower()
        return any(seg.lower() in node_lower for seg in segments[-2:]) if segments else False

    def _add_edge(self, edge: Edge):
        """添加边到图谱（去重）"""
        for e in self.graph.edges:
            if e.from_id == edge.from_id and e.to_id == edge.to_id and e.relation == edge.relation:
                return
        self.graph.edges.append(edge)
