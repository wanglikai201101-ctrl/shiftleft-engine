"""索引生成器：生成 docs-index.json（v2.0 含追溯链）"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from .scanner import DocumentScanner
from .parser import DocumentParser


class DocumentIndexer:
    """文档索引生成器"""

    def __init__(self, base_dir: str = "modules"):
        self.scanner = DocumentScanner(base_dir)
        self.parser = DocumentParser()
        self.base_dir = Path(base_dir)

    def generate_index(self, output_path: str = "docs-index.json") -> Dict:
        """生成索引文件（v2.0 含追溯链信息）"""
        md_files = self.scanner.scan()
        documents = {}

        for file_path in md_files:
            try:
                relative_path = str(file_path.relative_to(self.base_dir))
                doc_type = self.scanner.get_doc_type(file_path)
                doc_info = self.parser.parse(file_path)

                if doc_type == "storage":
                    doc_info["storage_type"] = self.scanner.get_storage_type(file_path)
                if doc_type == "module":
                    content = file_path.read_text(encoding="utf-8")
                    doc_info.update(self.parser.extract_module_index(content))

                # v2.0: Extract traceability fields
                content = file_path.read_text(encoding="utf-8")
                trace_fields = self._extract_traceability(content, doc_type)
                doc_info.update(trace_fields)

                documents[relative_path] = {"type": doc_type, **doc_info}
            except Exception as e:
                print(f"  警告：解析失败 {file_path}: {e}")

        broken_links = self._detect_broken_links(documents)
        traceability_coverage = self._compute_traceability_coverage(documents)

        index = {
            "version": "2.0",
            "generated_at": datetime.now().isoformat(),
            "total_documents": len(documents),
            "traceability_coverage": traceability_coverage,
            "broken_links": broken_links,
            "documents": documents,
        }

        Path(output_path).write_text(
            json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return index

    def _extract_traceability(self, content: str, doc_type: str) -> Dict:
        """从文档内容提取追溯链字段"""
        result: Dict = {
            "requirement_id": "",
            "test_points": [],
            "downstream_apis": [],
            "downstream_storage": [],
            "downstream_pages": [],
            "downstream_jobs": [],
        }

        # Extract requirement_id from "需求来源" field in tables or header
        req_match = re.search(
            r"\|\s*需求来源\s*\|\s*(.+?)\s*\|", content
        )
        if req_match:
            raw = req_match.group(1).strip()
            # Extract REQ-xxx identifiers from the value
            req_ids = re.findall(r"(REQ-[A-Za-z0-9-]+)", raw)
            if req_ids:
                result["requirement_id"] = ", ".join(req_ids) if len(req_ids) > 1 else req_ids[0]

        # Also check for "需求来源" in blockquote format: > 需求来源: [REQ-xxx](...)
        if not result["requirement_id"]:
            bq_match = re.search(
                r">\s*需求来源[:：]\s*\[?(REQ-[A-Za-z0-9-]+)", content
            )
            if bq_match:
                result["requirement_id"] = bq_match.group(1)

        # For requirement docs, extract REQ-xxx from the "编号" field
        if doc_type == "requirement" and not result["requirement_id"]:
            id_match = re.search(
                r"\|\s*编号\s*\|\s*(REQ-[A-Za-z0-9-]+)\s*\|", content
            )
            if id_match:
                result["requirement_id"] = id_match.group(1)

        # Extract TP-xxx test points
        tp_ids = re.findall(r"(TP-[A-Za-z0-9-]+)", content)
        result["test_points"] = sorted(set(tp_ids))

        # Extract downstream document references from association tables
        # Look for relative links like [text](../apis/xxx.md) or (apis/xxx.md)
        api_links = re.findall(
            r"\[.*?\]\((?:\.\./)?(?:apis/[^\)]+\.md)\)", content
        )
        storage_links = re.findall(
            r"\[.*?\]\((?:\.\./)?(?:storage/[^\)]+\.md)\)", content
        )
        page_links = re.findall(
            r"\[.*?\]\((?:\.\./)?(?:pages/[^\)]+\.md)\)", content
        )
        job_links = re.findall(
            r"\[.*?\]\((?:\.\./)?(?:jobs/[^\)]+\.md)\)", content
        )

        # Extract just the path portion
        def extract_paths(links: List[str]) -> List[str]:
            paths = []
            for link in links:
                m = re.search(r"\((?:\.\./)?([^\)]+)\)", link)
                if m:
                    path = m.group(1).strip()
                    if path not in paths:
                        paths.append(path)
            return sorted(paths)

        result["downstream_apis"] = extract_paths(api_links)
        result["downstream_storage"] = extract_paths(storage_links)
        result["downstream_pages"] = extract_paths(page_links)
        result["downstream_jobs"] = extract_paths(job_links)

        return result

    def _detect_broken_links(self, documents: Dict) -> List[Dict]:
        """检测追溯链中的断裂链接"""
        broken = []
        all_paths = set(documents.keys())

        for doc_path, doc_info in documents.items():
            module = doc_info.get("module", "")
            for field_name in ("downstream_apis", "downstream_storage",
                               "downstream_pages", "downstream_jobs"):
                for link in doc_info.get(field_name, []):
                    # Build the full relative path with module prefix
                    if module and not link.startswith(module):
                        full_path = f"{module}/{link}"
                    else:
                        full_path = link
                    # Normalize path separators
                    full_path_normalized = full_path.replace("\\", "/")
                    # Check if the target exists in the index
                    found = False
                    for existing_path in all_paths:
                        existing_normalized = existing_path.replace("\\", "/")
                        if existing_normalized == full_path_normalized:
                            found = True
                            break
                    if not found:
                        link_type = {
                            "downstream_apis": "missing_api_doc",
                            "downstream_storage": "missing_storage_doc",
                            "downstream_pages": "missing_page_doc",
                            "downstream_jobs": "missing_job_doc",
                        }.get(field_name, "missing_doc")
                        broken.append({
                            "source": doc_path,
                            "target": link,
                            "type": link_type,
                        })

            # Check requirement_id references
            req_id = doc_info.get("requirement_id", "")
            if req_id and doc_info.get("type") != "requirement":
                req_ids = [r.strip() for r in req_id.split(",") if r.strip()]
                for rid in req_ids:
                    # Check if a requirement doc with this ID exists
                    found = False
                    for existing_path, existing_info in documents.items():
                        if (existing_info.get("type") == "requirement" and
                                existing_info.get("requirement_id") == rid):
                            found = True
                            break
                    if not found:
                        broken.append({
                            "source": doc_path,
                            "target": rid,
                            "type": "missing_requirement_source",
                        })

        return broken

    def _compute_traceability_coverage(self, documents: Dict) -> float:
        """计算追溯链覆盖率：有非空 requirement_id 的文档占比"""
        if not documents:
            return 0.0
        total = len(documents)
        with_req = sum(
            1 for doc_info in documents.values()
            if doc_info.get("requirement_id")
        )
        return round(with_req / total, 2) if total > 0 else 0.0
