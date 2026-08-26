"""文档一致性检查器（主类）：编排所有子检查器"""

from pathlib import Path
from typing import List, Optional
from ..models.results import LintIssue, Severity, LintReport
from .testid_checker import PageTestIdChecker
from .requirement_checker import RequirementSourceChecker
from .field_checker import DatabaseFieldChecker
from .ref_checker import BidirectionalRefChecker
from .conformance_checker import CodeConformanceChecker


class DocLinter:
    """文档一致性检查器"""

    def __init__(self, knowledge_base_path: str = "modules"):
        self.kb_path = Path(knowledge_base_path)
        self.page_checker = PageTestIdChecker()
        self.req_checker = RequirementSourceChecker(knowledge_base_path)
        self.db_checker = DatabaseFieldChecker()
        self.ref_checker = BidirectionalRefChecker(knowledge_base_path)
        self.conformance_checker = CodeConformanceChecker()

    def check_document(self, doc_path: str) -> list:
        """检查单个文档"""
        issues = []
        full_path = self.kb_path / doc_path
        if not full_path.exists():
            return [LintIssue(Severity.ERROR, doc_path, f"文档不存在: {full_path}")]

        if "page" in doc_path.lower():
            vue_file = self._find_vue_file(doc_path)
            if vue_file:
                issues.extend(self.page_checker.check(str(full_path), vue_file))
        elif "api" in doc_path.lower():
            issues.extend(self.req_checker.check(str(full_path)))
        elif "storage" in doc_path.lower() or "db-" in doc_path.lower():
            ddl_file = self._find_ddl_file(doc_path)
            if ddl_file:
                issues.extend(self.db_checker.check(str(full_path), ddl_file))

        issues.extend(self.ref_checker.check(str(full_path)))
        return issues

    def check_module(self, module_name: str) -> LintReport:
        """检查整个模块"""
        report = LintReport()
        module_path = self.kb_path / module_name
        if not module_path.exists():
            report.issues[module_name] = [
                LintIssue(Severity.ERROR, module_name, f"模块目录不存在: {module_path}")
            ]
            return report
        for md_file in module_path.rglob("*.md"):
            relative = str(md_file.relative_to(self.kb_path))
            issues = self.check_document(relative)
            if issues:
                report.issues[relative] = issues
        return report

    def check_all(self) -> LintReport:
        """检查所有文档"""
        report = LintReport()
        for md_file in self.kb_path.rglob("*.md"):
            relative = str(md_file.relative_to(self.kb_path))
            issues = self.check_document(relative)
            if issues:
                report.issues[relative] = issues
        return report

    def check_code_conformance(
        self,
        doc_path: Optional[str] = None,
        module: Optional[str] = None,
    ) -> LintReport:
        """代码符合性检查（新方向：代码必须匹配文档）。

        编排 CodeConformanceChecker + 现有 requirement_checker / ref_checker，
        对指定文档或模块执行代码符合性检查。

        Args:
            doc_path: 单个文档的相对路径（相对于 kb_path）
            module: 模块名（检查整个模块下所有文档）

        Returns:
            LintReport
        """
        report = LintReport()

        if doc_path:
            full_path = self.kb_path / doc_path
            if not full_path.exists():
                report.issues[doc_path] = [
                    LintIssue(Severity.ERROR, doc_path, f"文档不存在: {full_path}")
                ]
                return report
            issues = self._check_single_conformance(doc_path)
            if issues:
                report.issues[doc_path] = issues
        elif module:
            module_path = self.kb_path / module
            if not module_path.exists():
                report.issues[module] = [
                    LintIssue(Severity.ERROR, module, f"模块目录不存在: {module_path}")
                ]
                return report
            for md_file in module_path.rglob("*.md"):
                relative = str(md_file.relative_to(self.kb_path))
                issues = self._check_single_conformance(relative)
                if issues:
                    report.issues[relative] = issues
        else:
            # Check all documents
            for md_file in self.kb_path.rglob("*.md"):
                relative = str(md_file.relative_to(self.kb_path))
                issues = self._check_single_conformance(relative)
                if issues:
                    report.issues[relative] = issues

        return report

    def _check_single_conformance(self, doc_path: str) -> List[LintIssue]:
        """Run conformance checks on a single document.

        Dispatches to the appropriate conformance checker based on doc type,
        plus requirement source and bidirectional reference checks.
        """
        issues: List[LintIssue] = []
        full_path = self.kb_path / doc_path

        # API conformance
        if "api" in doc_path.lower():
            code_path = self._find_code_file(doc_path)
            func_name = self._infer_function_name(doc_path)
            if code_path and func_name:
                issues.extend(
                    self.conformance_checker.check_api_conformance(
                        str(full_path), code_path, func_name
                    )
                )
            # REQ-xxx existence check
            issues.extend(self.req_checker.check(str(full_path)))

        # DB conformance
        elif "storage" in doc_path.lower() or "db-" in doc_path.lower():
            ddl_file = self._find_ddl_file(doc_path)
            if ddl_file:
                issues.extend(
                    self.conformance_checker.check_db_conformance(
                        str(full_path), ddl_file
                    )
                )

        # Page / testid conformance
        elif "page" in doc_path.lower():
            vue_file = self._find_vue_file(doc_path)
            if vue_file:
                issues.extend(
                    self.conformance_checker.check_testid_conformance(
                        str(full_path), vue_file
                    )
                )

        # Bidirectional reference check for all doc types
        issues.extend(self.ref_checker.check(str(full_path)))

        return issues

    def _find_code_file(self, api_doc_path: str) -> Optional[str]:
        """Try to locate the Python source file for an API document."""
        filename = Path(api_doc_path).stem  # e.g. POST-orders
        parts = filename.split("-", 1)
        if len(parts) == 2:
            resource = parts[1].replace("-", "_")
            for prefix in ("src/api", "src/routes", "service/api", "backend/api"):
                path = f"{prefix}/{resource}.py"
                if Path(path).exists():
                    return path
        return None

    def _infer_function_name(self, api_doc_path: str) -> Optional[str]:
        """Try to infer the function name from an API document filename."""
        filename = Path(api_doc_path).stem  # e.g. POST-orders
        parts = filename.split("-", 1)
        if len(parts) == 2:
            method = parts[0].lower()
            resource = parts[1].replace("-", "_")
            name_map = {
                "post": f"create_{resource}",
                "get": f"get_{resource}",
                "put": f"update_{resource}",
                "delete": f"delete_{resource}",
                "patch": f"patch_{resource}",
            }
            return name_map.get(method)
        return None

    def _find_vue_file(self, page_doc_path: str) -> Optional[str]:
        filename = Path(page_doc_path).stem
        vue_name = "".join(w.capitalize() for w in filename.split("-"))
        for prefix in ("src/pages", "src/views", "frontend/src/pages", "frontend/src/views"):
            path = f"{prefix}/{vue_name}.vue"
            if Path(path).exists():
                return path
        return None

    def _find_ddl_file(self, db_doc_path: str) -> Optional[str]:
        filename = Path(db_doc_path).stem
        table_name = filename[3:] if filename.startswith("db-") else filename
        for pattern in (f"migrations/*_{table_name}.sql", f"sql/{table_name}.sql"):
            matches = list(Path(".").glob(pattern))
            if matches:
                return str(matches[0])
        return None
