"""数据库字段检查器"""

import re
from pathlib import Path
from typing import List
from ..models.results import LintIssue, Severity


class DatabaseFieldChecker:
    """检查数据库文档字段是否与 DDL 一致"""

    def check(self, db_doc_path: str, ddl_file_path: str) -> List[LintIssue]:
        doc_fields = self._extract_fields_from_doc(db_doc_path)
        ddl_fields = self._extract_fields_from_ddl(ddl_file_path)
        issues = []

        for field in ddl_fields - doc_fields:
            issues.append(LintIssue(
                severity=Severity.WARNING,
                doc_path=db_doc_path,
                message=f'字段 "{field}" 在 DDL 中存在，但在文档中未记录',
            ))
        for field in doc_fields - ddl_fields:
            issues.append(LintIssue(
                severity=Severity.ERROR,
                doc_path=db_doc_path,
                message=f'字段 "{field}" 在文档中存在，但在 DDL {ddl_file_path} 中未找到',
            ))
        return issues

    def _extract_fields_from_doc(self, doc_path: str) -> set:
        try:
            content = Path(doc_path).read_text(encoding="utf-8")
        except Exception:
            return set()
        fields = set()
        in_table = False
        for line in content.split("\n"):
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    if parts[1] in ("字段", "字段名", "Field", "---", ""):
                        in_table = True
                        continue
                    if in_table and parts[1]:
                        fields.add(parts[1])
            else:
                in_table = False
        return fields

    def _extract_fields_from_ddl(self, ddl_path: str) -> set:
        try:
            content = Path(ddl_path).read_text(encoding="utf-8")
        except Exception:
            return set()
        return set(re.findall(r"`([a-z_]+)`\s+\w+", content, re.IGNORECASE))
