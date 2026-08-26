"""需求来源检查器"""

import re
from pathlib import Path
from typing import List
from ..models.results import LintIssue, Severity


class RequirementSourceChecker:
    """检查接口文档的需求来源（REQ-xxx）是否有对应文档"""

    def __init__(self, knowledge_base_path: str = "modules"):
        self.kb_path = Path(knowledge_base_path)

    def check(self, api_doc_path: str) -> List[LintIssue]:
        issues = []
        for req_id in self._extract_requirement_ids(api_doc_path):
            if not self._requirement_exists(req_id):
                issues.append(LintIssue(
                    severity=Severity.ERROR,
                    doc_path=api_doc_path,
                    message=f"需求来源 {req_id} 的文档不存在",
                ))
        return issues

    def _extract_requirement_ids(self, doc_path: str) -> List[str]:
        try:
            content = Path(doc_path).read_text(encoding="utf-8")
        except Exception:
            return []
        return re.findall(r"REQ-[A-Z]*-?\d{3}", content)

    def _requirement_exists(self, req_id: str) -> bool:
        patterns = [f"*/requirements/{req_id}.md", f"requirements/{req_id}.md"]
        return any(list(self.kb_path.glob(p)) for p in patterns)
