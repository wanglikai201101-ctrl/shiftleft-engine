"""页面 data-testid 检查器"""

import re
from pathlib import Path
from typing import List
from ..models.results import LintIssue, Severity


class PageTestIdChecker:
    """检查页面文档中的 data-testid 是否在前端代码中存在"""

    def check(self, page_doc_path: str, frontend_file_path: str) -> List[LintIssue]:
        doc_testids = self._extract_testids_from_doc(page_doc_path)
        code_testids = self._extract_testids_from_code(frontend_file_path)

        issues = []
        for testid in doc_testids - code_testids:
            issues.append(LintIssue(
                severity=Severity.ERROR,
                doc_path=page_doc_path,
                message=f'data-testid "{testid}" 在文档中存在，但在代码 {frontend_file_path} 中未找到',
            ))
        for testid in code_testids - doc_testids:
            issues.append(LintIssue(
                severity=Severity.WARNING,
                doc_path=page_doc_path,
                message=f'data-testid "{testid}" 在代码中存在，但在文档中未记录',
            ))
        return issues

    def _extract_testids_from_doc(self, doc_path: str) -> set:
        try:
            content = Path(doc_path).read_text(encoding="utf-8")
        except Exception:
            return set()
        matches = re.findall(r"\|\s*([a-z0-9\-]+)\s*\|", content)
        return {m for m in matches if "-" in m and not m.startswith("---")}

    def _extract_testids_from_code(self, file_path: str) -> set:
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except Exception:
            return set()
        testids = set()
        testids.update(re.findall(r':?data-testid=["\']([^"\']+)["\']', content))
        testids.update(re.findall(r'data-testid=\{["\']?([^}"\']+)["\']?\}', content))
        testids.update(re.findall(r"data-testid=\{`([^`]+)`\}", content))
        return testids
