"""代码符合性检查器：验证代码是否匹配文档（方向：代码→文档）

核心原则：文档是权威，代码必须匹配文档。
- 文档中有但代码中没有 → ERROR "代码不符合文档: 缺少..."
- 代码中有但文档中没有 → WARNING "未文档化的代码实现: ..."
- 类型不一致 → ERROR "代码不符合文档: ...类型不一致"
"""

import re
from pathlib import Path
from typing import List

from ..models.results import LintIssue, Severity
from ..models.doc_types import ApiField
from ..parsers.registry import ParserRegistry


class CodeConformanceChecker:
    """代码符合性检查器：验证代码是否匹配文档"""

    def check_api_conformance(
        self,
        api_doc_path: str,
        code_path: str,
        function_name: str,
    ) -> List[LintIssue]:
        """检查代码接口参数是否与文档一致。

        从 API 文档的"请求参数"表提取声明的参数，从代码中通过
        ParserRegistry 提取实际参数，然后比较两者。

        Args:
            api_doc_path: 接口文档路径
            code_path: 代码文件路径
            function_name: 函数名

        Returns:
            检查发现的问题列表
        """
        doc_params = self._extract_params_from_doc(api_doc_path)
        code_params = self._extract_params_from_code(code_path, function_name)

        if doc_params is None:
            return [LintIssue(
                severity=Severity.ERROR,
                doc_path=api_doc_path,
                message=f"无法读取文档: {api_doc_path}",
            )]
        if code_params is None:
            return [LintIssue(
                severity=Severity.WARNING,
                doc_path=api_doc_path,
                message=f"无法解析代码: {code_path} 函数 {function_name}",
            )]

        issues: List[LintIssue] = []
        doc_param_map = {p.name: p for p in doc_params}
        code_param_map = {p.name: p for p in code_params}

        # Params in doc but not in code → ERROR
        for name in doc_param_map:
            if name not in code_param_map:
                issues.append(LintIssue(
                    severity=Severity.ERROR,
                    doc_path=api_doc_path,
                    message=f"代码不符合文档: 缺少参数 {name}",
                ))

        # Params in code but not in doc → WARNING
        for name in code_param_map:
            if name not in doc_param_map:
                issues.append(LintIssue(
                    severity=Severity.WARNING,
                    doc_path=api_doc_path,
                    message=f"未文档化的代码实现: 参数 {name}",
                ))

        # Type mismatch → ERROR
        for name in doc_param_map:
            if name in code_param_map:
                doc_type = self._normalize_type(doc_param_map[name].type)
                code_type = self._normalize_type(code_param_map[name].type)
                if doc_type != code_type:
                    issues.append(LintIssue(
                        severity=Severity.ERROR,
                        doc_path=api_doc_path,
                        message=f"代码不符合文档: 参数 {name} 类型不一致 (文档: {doc_type}, 代码: {code_type})",
                    ))

        return issues

    def check_db_conformance(
        self,
        db_doc_path: str,
        ddl_path: str,
    ) -> List[LintIssue]:
        """检查数据库字段是否与文档一致。

        Args:
            db_doc_path: 数据库文档路径
            ddl_path: DDL 文件路径

        Returns:
            检查发现的问题列表
        """
        doc_fields = self._extract_fields_from_doc(db_doc_path)
        ddl_fields = self._extract_fields_from_ddl(ddl_path)

        issues: List[LintIssue] = []

        # Fields in doc but not in DDL → ERROR
        for field_name in doc_fields - ddl_fields:
            issues.append(LintIssue(
                severity=Severity.ERROR,
                doc_path=db_doc_path,
                message=f"代码不符合文档: 缺少字段 {field_name}",
            ))

        # Fields in DDL but not in doc → WARNING
        for field_name in ddl_fields - doc_fields:
            issues.append(LintIssue(
                severity=Severity.WARNING,
                doc_path=db_doc_path,
                message=f"未文档化的代码实现: 字段 {field_name}",
            ))

        return issues

    def check_testid_conformance(
        self,
        page_doc_path: str,
        frontend_path: str,
    ) -> List[LintIssue]:
        """检查 data-testid 是否与文档一致。

        Args:
            page_doc_path: 页面文档路径
            frontend_path: 前端代码文件路径

        Returns:
            检查发现的问题列表
        """
        doc_testids = self._extract_testids_from_doc(page_doc_path)
        code_testids = self._extract_testids_from_code(frontend_path)

        issues: List[LintIssue] = []

        # testids in doc but not in code → ERROR
        for testid in doc_testids - code_testids:
            issues.append(LintIssue(
                severity=Severity.ERROR,
                doc_path=page_doc_path,
                message=f"代码不符合文档: 缺少 data-testid {testid}",
            ))

        # testids in code but not in doc → WARNING
        for testid in code_testids - doc_testids:
            issues.append(LintIssue(
                severity=Severity.WARNING,
                doc_path=page_doc_path,
                message=f"未文档化的代码实现: data-testid {testid}",
            ))

        return issues

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_params_from_doc(self, doc_path: str) -> "List[ApiField] | None":
        """Extract declared parameters from the 请求参数 table in an API doc."""
        try:
            content = Path(doc_path).read_text(encoding="utf-8")
        except Exception:
            return None

        params: List[ApiField] = []
        in_section = False
        header_seen = False
        separator_seen = False

        for line in content.split("\n"):
            stripped = line.strip()
            # Detect the 请求参数 section
            if re.match(r"^##\s+请求参数", stripped):
                in_section = True
                header_seen = False
                separator_seen = False
                continue
            # End section on next ##
            if in_section and re.match(r"^##\s+", stripped) and not re.match(r"^##\s+请求参数", stripped):
                break
            if not in_section:
                continue
            if not stripped.startswith("|"):
                continue
            # Skip table header row
            if not header_seen:
                header_seen = True
                continue
            # Skip separator row (|---|---|...)
            if not separator_seen:
                separator_seen = True
                continue
            # Parse data row
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if len(cells) >= 2 and cells[0]:
                name = cells[0]
                param_type = cells[1] if len(cells) > 1 else "string"
                required = True
                if len(cells) > 2:
                    required = cells[2] in ("是", "true", "True", "yes", "Yes")
                params.append(ApiField(
                    name=name,
                    type=param_type,
                    required=required,
                ))

        return params

    def _extract_params_from_code(
        self, code_path: str, function_name: str
    ) -> "List[ApiField] | None":
        """Extract actual parameters from code via ParserRegistry."""
        try:
            parser = ParserRegistry.get_parser(code_path)
        except ValueError:
            return None

        try:
            code_content = Path(code_path).read_text(encoding="utf-8")
        except Exception:
            return None

        api_info = parser.extract_api_info(code_content, function_name)
        if api_info is None:
            return None

        return api_info.request_params

    def _normalize_type(self, type_str: str) -> str:
        """Normalize type names for comparison (e.g. 'string' == 'str')."""
        t = type_str.lower().strip()
        aliases = {
            "str": "string",
            "int": "integer",
            "bool": "boolean",
            "float": "number",
            "dict": "object",
            "list": "array",
        }
        return aliases.get(t, t)

    def _extract_fields_from_doc(self, doc_path: str) -> set:
        """Extract field names from a database document's 字段定义 table."""
        try:
            content = Path(doc_path).read_text(encoding="utf-8")
        except Exception:
            return set()

        fields: set = set()
        in_table = False
        for line in content.split("\n"):
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    # Skip header row
                    if parts[1] in ("字段", "字段名", "Field", ""):
                        in_table = True
                        continue
                    # Skip separator row (e.g. |------|------|)
                    if in_table and re.match(r"^-+$", parts[1]):
                        continue
                    if in_table and parts[1]:
                        fields.add(parts[1])
            else:
                in_table = False
        return fields

    def _extract_fields_from_ddl(self, ddl_path: str) -> set:
        """Extract field names from a DDL file."""
        try:
            content = Path(ddl_path).read_text(encoding="utf-8")
        except Exception:
            return set()
        return set(re.findall(r"`([a-z_]+)`\s+\w+", content, re.IGNORECASE))

    def _extract_testids_from_doc(self, doc_path: str) -> set:
        """Extract data-testid values from a page document."""
        try:
            content = Path(doc_path).read_text(encoding="utf-8")
        except Exception:
            return set()
        # Exclude header-like values and separator rows
        _header_values = {"data-testid", "元素类型", "功能", "触发接口", "绑定字段", "数据来源"}
        matches = re.findall(r"\|\s*([a-z0-9\-]+)\s*\|", content)
        return {
            m for m in matches
            if "-" in m
            and not m.startswith("---")
            and m not in _header_values
        }

    def _extract_testids_from_code(self, file_path: str) -> set:
        """Extract data-testid values from frontend code."""
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except Exception:
            return set()
        testids: set = set()
        testids.update(re.findall(r':?data-testid=["\']([^"\']+)["\']', content))
        testids.update(re.findall(r'data-testid=\{["\']?([^}"\']+)["\']?\}', content))
        testids.update(re.findall(r"data-testid=\{`([^`]+)`\}", content))
        return testids
