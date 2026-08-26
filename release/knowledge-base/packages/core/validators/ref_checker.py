"""双向引用检查器"""

import re
from pathlib import Path
from typing import List, Tuple
from ..models.results import LintIssue, Severity


class BidirectionalRefChecker:
    """检查文档间双向引用的完整性"""

    def __init__(self, knowledge_base_path: str = "modules"):
        self.kb_path = Path(knowledge_base_path)

    def check(self, doc_path: str) -> List[LintIssue]:
        issues = []
        for _ref_type, ref_path in self._extract_references(doc_path):
            if not self._has_reverse_reference(doc_path, ref_path):
                issues.append(LintIssue(
                    severity=Severity.WARNING,
                    doc_path=doc_path,
                    message=f"引用了 {ref_path}，但对方未反向引用本文档",
                ))
        return issues

    def _extract_references(self, doc_path: str) -> List[Tuple[str, str]]:
        try:
            content = Path(doc_path).read_text(encoding="utf-8")
        except Exception:
            return []
        refs = []
        for _text, path in re.findall(r"\[([^\]]+)\]\(([^\)]+\.md)\)", content):
            ref_type = "unknown"
            for keyword, rtype in [("api", "api"), ("requirement", "requirement"), ("REQ", "requirement"),
                                   ("storage", "storage"), ("database", "storage"), ("page", "page")]:
                if keyword in path:
                    ref_type = rtype
                    break
            refs.append((ref_type, path))
        return refs

    def _has_reverse_reference(self, source_doc: str, target_doc: str) -> bool:
        target_path = self.kb_path / target_doc
        if not target_path.exists():
            return False
        try:
            content = target_path.read_text(encoding="utf-8")
        except Exception:
            return False
        return Path(source_doc).name in content
