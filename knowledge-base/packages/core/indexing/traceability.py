"""追溯链查询引擎：从任意标识符查询完整追溯链"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from ..models.results import TraceResult


class TraceabilityQuery:
    """追溯链查询器

    支持从任意标识符（文档路径、REQ-xxx、TP-xxx）查询完整追溯链。
    """

    def __init__(self, index_path: str = "docs-index.json"):
        index_file = Path(index_path)
        if not index_file.exists():
            raise FileNotFoundError(f"索引文件不存在: {index_path}")
        self.index = json.loads(index_file.read_text(encoding="utf-8"))
        self.documents: Dict = self.index.get("documents", {})

    def trace(self, identifier: str) -> TraceResult:
        """从任意标识符查询完整追溯链。

        - REQ-xxx: 查找所有引用该需求的下游文档
        - TP-xxx: 查找所有关联该测试点的文档
        - doc path: 查找该文档的上下游关系
        """
        if re.match(r"^REQ-", identifier, re.IGNORECASE):
            return self._trace_from_req(identifier)
        elif re.match(r"^TP-", identifier, re.IGNORECASE):
            return self._trace_from_tp(identifier)
        else:
            return self.reverse_trace(identifier)

    def find_by_req(self, req_id: str) -> List[str]:
        """从 REQ 编号查询所有下游文档路径"""
        downstream = []
        for doc_path, doc_info in self.documents.items():
            if doc_info.get("type") == "requirement":
                continue
            doc_req = doc_info.get("requirement_id", "")
            if isinstance(doc_req, str) and req_id in doc_req:
                downstream.append(doc_path)
                continue
            if isinstance(doc_req, list) and req_id in doc_req:
                downstream.append(doc_path)
        return sorted(downstream)

    def find_by_tp(self, tp_id: str) -> List[str]:
        """从 TP 编号查询关联文档路径"""
        results = []
        for doc_path, doc_info in self.documents.items():
            test_points = doc_info.get("test_points", [])
            if tp_id in test_points:
                results.append(doc_path)
        return sorted(results)

    def reverse_trace(self, doc_path: str) -> TraceResult:
        """从文档反向查询需求来源和测试点"""
        doc_info = self.documents.get(doc_path)
        if doc_info is None:
            return TraceResult(source=doc_path)

        requirement_sources = []
        req_id = doc_info.get("requirement_id", "")
        if req_id:
            if isinstance(req_id, list):
                requirement_sources = list(req_id)
            elif isinstance(req_id, str) and req_id:
                requirement_sources = [r.strip() for r in req_id.split(",") if r.strip()]

        test_points = doc_info.get("test_points", [])

        downstream_apis = doc_info.get("downstream_apis", [])
        downstream_storage = doc_info.get("downstream_storage", [])
        downstream_pages = doc_info.get("downstream_pages", [])
        downstream_jobs = doc_info.get("downstream_jobs", [])

        broken_links = []
        all_downstream = downstream_apis + downstream_storage + downstream_pages + downstream_jobs
        for link in all_downstream:
            if link not in self.documents:
                broken_links.append(link)

        return TraceResult(
            source=doc_path,
            requirement_sources=requirement_sources,
            test_points=list(test_points),
            downstream_apis=list(downstream_apis),
            downstream_storage=list(downstream_storage),
            downstream_pages=list(downstream_pages),
            downstream_jobs=list(downstream_jobs),
            broken_links=broken_links,
        )

    def _trace_from_req(self, req_id: str) -> TraceResult:
        """从 REQ 编号构建完整追溯链"""
        # Find the requirement document itself
        req_doc_path = None
        req_doc_info = None
        for doc_path, doc_info in self.documents.items():
            if doc_info.get("type") == "requirement":
                doc_req_id = doc_info.get("requirement_id", "")
                if doc_req_id == req_id:
                    req_doc_path = doc_path
                    req_doc_info = doc_info
                    break

        downstream_docs = self.find_by_req(req_id)

        downstream_apis = []
        downstream_storage = []
        downstream_pages = []
        downstream_jobs = []

        # Collect from the requirement doc's own downstream fields
        if req_doc_info:
            downstream_apis = list(req_doc_info.get("downstream_apis", []))
            downstream_storage = list(req_doc_info.get("downstream_storage", []))
            downstream_pages = list(req_doc_info.get("downstream_pages", []))
            downstream_jobs = list(req_doc_info.get("downstream_jobs", []))

        # Also categorize downstream docs found by req_id reference
        for dp in downstream_docs:
            info = self.documents.get(dp, {})
            dtype = info.get("type", "")
            if dtype == "api" and dp not in downstream_apis:
                downstream_apis.append(dp)
            elif dtype == "storage" and dp not in downstream_storage:
                downstream_storage.append(dp)
            elif dtype == "page" and dp not in downstream_pages:
                downstream_pages.append(dp)
            elif dtype == "job" and dp not in downstream_jobs:
                downstream_jobs.append(dp)

        test_points = []
        if req_doc_info:
            test_points = list(req_doc_info.get("test_points", []))

        return TraceResult(
            source=req_id,
            requirement_sources=[req_id],
            test_points=test_points,
            downstream_apis=sorted(downstream_apis),
            downstream_storage=sorted(downstream_storage),
            downstream_pages=sorted(downstream_pages),
            downstream_jobs=sorted(downstream_jobs),
        )

    def _trace_from_tp(self, tp_id: str) -> TraceResult:
        """从 TP 编号构建追溯链"""
        associated_docs = self.find_by_tp(tp_id)

        # Try to find the parent requirement
        req_sources = []
        for doc_path, doc_info in self.documents.items():
            if doc_info.get("type") == "requirement":
                tps = doc_info.get("test_points", [])
                if tp_id in tps:
                    req_id = doc_info.get("requirement_id", "")
                    if req_id and req_id not in req_sources:
                        req_sources.append(req_id)

        downstream_apis = []
        downstream_storage = []
        downstream_pages = []
        downstream_jobs = []

        for dp in associated_docs:
            info = self.documents.get(dp, {})
            dtype = info.get("type", "")
            if dtype == "api" and dp not in downstream_apis:
                downstream_apis.append(dp)
            elif dtype == "storage" and dp not in downstream_storage:
                downstream_storage.append(dp)
            elif dtype == "page" and dp not in downstream_pages:
                downstream_pages.append(dp)
            elif dtype == "job" and dp not in downstream_jobs:
                downstream_jobs.append(dp)

        return TraceResult(
            source=tp_id,
            requirement_sources=req_sources,
            test_points=[tp_id],
            downstream_apis=sorted(downstream_apis),
            downstream_storage=sorted(downstream_storage),
            downstream_pages=sorted(downstream_pages),
            downstream_jobs=sorted(downstream_jobs),
        )
