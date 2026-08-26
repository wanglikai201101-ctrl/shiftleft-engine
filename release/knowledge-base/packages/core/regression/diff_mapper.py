"""Diff-to-Node Mapper: 将 git diff 文件路径映射到图谱节点 ID"""

import re
from pathlib import Path
from typing import List, Optional

from packages.core.graph.store import Graph, Node


class DiffNodeMapper:
    """将变更文件路径映射到图谱节点"""

    def __init__(self, graph: Graph, module_name: str, kb_path: str = "modules"):
        self.graph = graph
        self.module_name = module_name
        self.kb_path = Path(kb_path)
        self._doc_path_index = self._build_doc_path_index()
        self._source_path_index = self._build_source_path_index()
        self._synonyms = Graph.load_synonyms()

    def _build_doc_path_index(self) -> dict:
        """构建 doc_path → node_id 的反向索引"""
        index = {}
        for node in self.graph.nodes:
            if node.doc_path:
                normalized = node.doc_path.replace("\\", "/")
                index[normalized] = node.id
        return index

    def _build_source_path_index(self) -> dict:
        """构建 source_path → node_id 的反向索引"""
        index = {}
        for node in self.graph.nodes:
            if node.source_path:
                # source_path may be "file.py:function_name", index both full and file-only
                sp = node.source_path.replace("\\", "/")
                index[sp] = node.id
                # Also index the file part without function
                file_part = sp.split(":")[0] if ":" in sp else sp
                if file_part not in index:
                    index[file_part] = node.id
        return index

    def map_files(self, changed_files: List[str]) -> List[str]:
        """将变更文件列表映射为图谱节点 ID"""
        node_ids = set()
        for f in changed_files:
            mapped = self._map_single_file(f)
            if mapped:
                node_ids.update(mapped)
        return list(node_ids)

    def _map_single_file(self, file_path: str) -> List[str]:
        """映射单个文件到节点 ID（多策略）"""
        normalized = file_path.replace("\\", "/")

        # Strategy 0: source_path exact match (highest precision)
        result = self._match_source_path(normalized)
        if result:
            return [result]

        # Strategy 1: Direct doc_path match (KB docs)
        result = self._match_doc_path(normalized)
        if result:
            return [result]

        # Strategy 2: Directory-based type inference + filename search
        result = self._match_by_directory_and_name(normalized)
        if result:
            return result

        # Strategy 3: Fuzzy search by filename stem
        result = self._match_by_stem_search(normalized)
        if result:
            return result

        return []

    def _match_source_path(self, file_path: str) -> Optional[str]:
        """策略0: 精确匹配 source_path（适用于源码文件变更）"""
        # Try exact match
        if file_path in self._source_path_index:
            return self._source_path_index[file_path]

        # Try matching just the filename
        filename = Path(file_path).name
        for sp, node_id in self._source_path_index.items():
            sp_file = sp.split(":")[0] if ":" in sp else sp
            if sp_file.endswith(filename) or filename == Path(sp_file).name:
                return node_id

        return None

    def _match_doc_path(self, file_path: str) -> Optional[str]:
        """策略1: 精确匹配 doc_path（适用于 KB 文档变更）"""
        # Try exact match
        if file_path in self._doc_path_index:
            return self._doc_path_index[file_path]

        # Try with module prefix
        with_module = f"{self.module_name}/{file_path}"
        if with_module in self._doc_path_index:
            return self._doc_path_index[with_module]

        # Try matching the tail (filename part)
        filename = Path(file_path).name
        for doc_path, node_id in self._doc_path_index.items():
            if doc_path.endswith(filename):
                return node_id

        return None

    def _match_by_directory_and_name(self, file_path: str) -> Optional[List[str]]:
        """策略2: 根据目录推断类型，根据文件名匹配节点"""
        path_lower = file_path.lower()

        # Detect node type from directory patterns
        node_type = None
        if "/apis/" in path_lower or "/api/" in path_lower or "/routes/" in path_lower:
            node_type = "api"
        elif "/pages/" in path_lower or "/views/" in path_lower or "/components/" in path_lower:
            node_type = "page"
        elif "/models/" in path_lower or "/storage/" in path_lower or "/migrations/" in path_lower:
            node_type = "storage"
        elif "/jobs/" in path_lower or "/tasks/" in path_lower or "/celery/" in path_lower:
            node_type = "job"

        if not node_type:
            return None

        # Extract meaningful stem from filename
        stem = Path(file_path).stem
        # Remove common prefixes/suffixes
        stem = re.sub(r'^(test_|spec_)', '', stem)
        stem = re.sub(r'(_test|_spec|\.test|\.spec)$', '', stem)

        # Search graph for matching nodes of this type
        matched = self.graph.search_nodes(
            stem, node_types=[node_type], synonyms=self._synonyms, limit=3
        )
        return [n.id for n in matched] if matched else None

    def _match_by_stem_search(self, file_path: str) -> Optional[List[str]]:
        """策略3: 从文件名提取关键词，模糊搜索图谱"""
        stem = Path(file_path).stem
        # Clean up common patterns
        stem = re.sub(r'^(test_|spec_|__)', '', stem)
        stem = re.sub(r'(_test|_spec|\.test|\.spec|__)$', '', stem)
        # Skip generic filenames
        if stem in ('__init__', 'index', 'main', 'app', 'config', 'utils', 'helpers'):
            return None
        if len(stem) < 3:
            return None

        matched = self.graph.search_nodes(
            stem, synonyms=self._synonyms, limit=2
        )
        return [n.id for n in matched] if matched else None
