"""索引查询器：供用例生成 SubAgent 使用"""

import json
from pathlib import Path
from typing import Dict, List, Optional


class DocumentQuery:
    """文档索引查询器"""

    def __init__(self, index_path: str = "docs-index.json"):
        index_file = Path(index_path)
        if not index_file.exists():
            raise FileNotFoundError(f"索引文件不存在: {index_path}")
        self.index = json.loads(index_file.read_text(encoding="utf-8"))
        self.documents = self.index.get("documents", {})

    def find_related_docs(self, doc_path: str, max_depth: int = 2) -> List[str]:
        """查找与指定文档相关的所有文档（递归）"""
        visited, result = set(), []

        def _find(path: str, depth: int):
            if depth > max_depth or path in visited:
                return
            visited.add(path)
            doc_info = self.documents.get(path)
            if not doc_info:
                return
            related = []
            for key in ("related_requirements", "related_apis", "related_storage",
                        "related_pages", "related_configs", "related_jobs"):
                related.extend(doc_info.get(key, []))
            if doc_info.get("related_module"):
                related.append(doc_info["related_module"])
            for rp in related:
                if rp not in visited:
                    result.append(rp)
                    _find(rp, depth + 1)

        _find(doc_path, 0)
        return result

    def find_by_module(self, module_name: str) -> List[str]:
        return [p for p, i in self.documents.items() if i.get("module") == module_name]

    def find_by_type(self, doc_type: str) -> List[str]:
        return [p for p, i in self.documents.items() if i.get("type") == doc_type]

    def find_by_keyword(self, keyword: str, doc_type: Optional[str] = None) -> List[str]:
        kw = keyword.lower()
        result = []
        for path, info in self.documents.items():
            if doc_type and info.get("type") != doc_type:
                continue
            if kw in info.get("title", "").lower() or kw in path.lower():
                result.append(path)
        return result

    def get_doc_info(self, doc_path: str) -> Optional[Dict]:
        return self.documents.get(doc_path)

    def get_statistics(self) -> Dict:
        stats = {"total": len(self.documents), "by_type": {}, "by_module": {}}
        for info in self.documents.values():
            t = info.get("type", "unknown")
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
            m = info.get("module", "unknown")
            stats["by_module"][m] = stats["by_module"].get(m, 0) + 1
        return stats
