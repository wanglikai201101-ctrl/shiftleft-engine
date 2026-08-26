"""DetailFiller: 从代码提取技术细节，填入文档骨架的"待补充"占位符。

DetailFiller 接受一个已存在的文档骨架和一个代码文件，通过 ParserRegistry
获取对应语言的解析器，提取 HTTP 方法、路径、参数等技术细节，然后定位骨架中
的"待补充"标记并替换为提取的值。

核心原则：
- 仅填充标记为"待补充"的字段
- 保留已有的手工填写内容
- 检测冲突（代码值 vs 已有文档值）但不覆盖
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple

from packages.core.models.results import FillResult
from packages.core.models.doc_types import ExtractedApiInfo, ApiField
from packages.core.parsers.registry import ParserRegistry


# Placeholder marker used in skeleton documents
_PLACEHOLDER = "待补充"


class DetailFiller:
    """技术细节填充器

    从代码中提取参数/字段/装饰器信息，填入文档骨架的"待补充"占位符。
    Supports API, storage, and page document types via routing.
    """

    def fill(
        self,
        skeleton_path: str,
        code_path: str,
        function_name: Optional[str] = None,
    ) -> FillResult:
        """从代码提取技术细节，填入文档骨架。

        Routes to the appropriate filling strategy based on document type.

        Args:
            skeleton_path: 文档骨架文件路径
            code_path: 代码文件路径
            function_name: 函数名（可选，API文档不指定时尝试从骨架标题推断）

        Returns:
            FillResult
        """
        skeleton_file = Path(skeleton_path)
        code_file = Path(code_path)

        # Validate skeleton exists
        if not skeleton_file.exists():
            return FillResult(
                success=False,
                doc_path=skeleton_path,
                message=f"骨架不存在: {skeleton_path}",
            )

        # Validate code file exists
        if not code_file.exists():
            return FillResult(
                success=False,
                doc_path=skeleton_path,
                message=f"代码文件不存在: {code_path}",
            )

        # Read skeleton content for routing
        skeleton_content = skeleton_file.read_text(encoding="utf-8")

        # Detect document type and route
        doc_type = self._detect_doc_type(skeleton_path, skeleton_content)

        if doc_type == "api":
            return self._fill_api(skeleton_path, code_path, skeleton_file, code_file, skeleton_content, function_name)
        elif doc_type == "storage":
            return self._fill_storage(skeleton_path, code_path, skeleton_file, code_file, skeleton_content)
        elif doc_type == "page":
            return self._fill_page(skeleton_path, code_path, skeleton_file, code_file, skeleton_content)
        else:
            return FillResult(
                success=False,
                doc_path=skeleton_path,
                message="无法识别文档类型",
            )

    def _detect_doc_type(self, skeleton_path: str, content: str) -> str:
        """Detect document type from path patterns and content.

        Returns: "api", "storage", "page", or "unknown"
        """
        path_str = skeleton_path.replace("\\", "/")
        filename = Path(skeleton_path).name

        # Check for API: path contains "apis/" or H1 matches HTTP method pattern
        if "/apis/" in path_str or "\\apis\\" in skeleton_path:
            return "api"
        title_match = re.match(
            r"^#\s+(GET|POST|PUT|DELETE|PATCH)\s+/",
            content,
            re.MULTILINE,
        )
        if title_match:
            return "api"

        # Check for storage: path contains "storage/" or filename starts with db-/redis-/mq-/es-/oss-
        if "/storage/" in path_str or "\\storage\\" in skeleton_path:
            return "storage"
        storage_prefixes = ("db-", "redis-", "mq-", "es-", "oss-")
        if any(filename.startswith(p) for p in storage_prefixes):
            return "storage"

        # Check for page: path contains "pages/"
        if "/pages/" in path_str or "\\pages\\" in skeleton_path:
            return "page"

        return "unknown"

    # ------------------------------------------------------------------
    # API fill (existing logic, extracted)
    # ------------------------------------------------------------------

    def _fill_api(
        self,
        skeleton_path: str,
        code_path: str,
        skeleton_file: Path,
        code_file: Path,
        skeleton_content: str,
        function_name: Optional[str],
    ) -> FillResult:
        """Fill API document skeleton — original Phase R1 logic."""
        # Get parser via registry
        try:
            parser = ParserRegistry.get_parser(code_path)
        except ValueError as e:
            return FillResult(
                success=False,
                doc_path=skeleton_path,
                message=f"不支持的文件类型: {e}",
            )

        code_content = code_file.read_text(encoding="utf-8")

        # Infer function name from skeleton title if not provided
        if not function_name:
            function_name = self._infer_function_name(skeleton_content, code_content, parser)

        if not function_name:
            return FillResult(
                success=False,
                doc_path=skeleton_path,
                message="未指定函数名且无法从骨架推断",
            )

        # Extract API info from code
        api_info = parser.extract_api_info(code_content, function_name)
        if api_info is None:
            return FillResult(
                success=False,
                doc_path=skeleton_path,
                message=f"未找到函数: {function_name}",
            )

        # Fill the skeleton
        filled_fields: List[str] = []
        conflicts: List[str] = []
        preserved_fields: List[str] = []

        updated_content = self._fill_basic_info(
            skeleton_content, api_info, filled_fields, conflicts, preserved_fields
        )
        updated_content = self._fill_request_params(
            updated_content, api_info, filled_fields, conflicts, preserved_fields
        )
        updated_content = self._fill_response_structure(
            updated_content, api_info, filled_fields, conflicts, preserved_fields
        )

        # Write back
        skeleton_file.write_text(updated_content, encoding="utf-8")

        return FillResult(
            success=True,
            doc_path=skeleton_path,
            filled_fields=filled_fields,
            conflicts=conflicts,
            preserved_fields=preserved_fields,
            message=f"填充完成: {len(filled_fields)} 个字段已填充",
        )

    # ------------------------------------------------------------------
    # Storage fill
    # ------------------------------------------------------------------

    def _fill_storage(
        self,
        skeleton_path: str,
        code_path: str,
        skeleton_file: Path,
        code_file: Path,
        skeleton_content: str,
    ) -> FillResult:
        """Fill storage document skeleton from DDL or ORM model."""
        from packages.core.detail_filler.storage_filler import StorageDetailFiller

        code_content = code_file.read_text(encoding="utf-8")
        target_info = None

        # Strategy 1: Try DDL parser for .sql files
        if code_file.suffix.lower() == ".sql":
            from packages.core.parsers.ddl_parser import DDLParser
            parser = DDLParser()
            storage_infos = parser.extract_storage_info(code_content)
            if storage_infos:
                target_info = self._match_storage_info(storage_infos, skeleton_path)

        # Strategy 2: Try ORM parser for .py files (SQLAlchemy models)
        if target_info is None and code_file.suffix.lower() == ".py":
            from packages.core.parsers.orm_parser import ORMParser
            parser = ORMParser()
            storage_infos = parser.extract_storage_info(code_content)
            if storage_infos:
                target_info = self._match_storage_info(storage_infos, skeleton_path)

        # Strategy 3: If code_path is .py but no results, try DDL parser anyway (mixed content)
        if target_info is None and code_file.suffix.lower() != ".sql":
            from packages.core.parsers.ddl_parser import DDLParser
            parser = DDLParser()
            storage_infos = parser.extract_storage_info(code_content)
            if storage_infos:
                target_info = self._match_storage_info(storage_infos, skeleton_path)

        if not target_info:
            return FillResult(
                success=False,
                doc_path=skeleton_path,
                message="未找到表定义（DDL 和 ORM 均未匹配）",
            )

        filler = StorageDetailFiller()
        updated_content, filled_fields, conflicts, preserved_fields = filler.fill(
            skeleton_content, target_info
        )

        # Write back
        skeleton_file.write_text(updated_content, encoding="utf-8")

        return FillResult(
            success=True,
            doc_path=skeleton_path,
            filled_fields=filled_fields,
            conflicts=conflicts,
            preserved_fields=preserved_fields,
            message=f"填充完成: {len(filled_fields)} 个字段已填充",
        )

    def _match_storage_info(self, storage_infos, skeleton_path: str):
        """Match a storage info entry to the skeleton filename."""
        filename = Path(skeleton_path).stem
        # Try to match table name to filename
        for info in storage_infos:
            if info.table_name in filename or filename.replace("db-", "") == info.table_name:
                return info
            # Also try without common prefixes
            clean_name = filename.replace("db-", "").replace("mq-", "").replace("redis-", "")
            if clean_name == info.table_name or info.table_name.endswith(clean_name):
                return info
        # Default to first match
        return storage_infos[0] if storage_infos else None

    # ------------------------------------------------------------------
    # Page fill
    # ------------------------------------------------------------------

    def _fill_page(
        self,
        skeleton_path: str,
        code_path: str,
        skeleton_file: Path,
        code_file: Path,
        skeleton_content: str,
    ) -> FillResult:
        """Fill page document skeleton from Vue component."""
        from packages.core.parsers.vue_parser import VueParser
        from packages.core.detail_filler.page_filler import PageDetailFiller

        code_content = code_file.read_text(encoding="utf-8")

        parser = VueParser()
        page_info = parser.extract_page_info(code_content)

        if not page_info.elements:
            return FillResult(
                success=False,
                doc_path=skeleton_path,
                message="Vue组件中未找到data-testid元素",
            )

        filler = PageDetailFiller()
        updated_content, filled_fields, conflicts, preserved_fields = filler.fill(
            skeleton_content, page_info
        )

        # Write back
        skeleton_file.write_text(updated_content, encoding="utf-8")

        return FillResult(
            success=True,
            doc_path=skeleton_path,
            filled_fields=filled_fields,
            conflicts=conflicts,
            preserved_fields=preserved_fields,
            message=f"填充完成: {len(filled_fields)} 个字段已填充",
        )

    # ------------------------------------------------------------------
    # API fill helpers (unchanged from Phase R1)
    # ------------------------------------------------------------------

    def _infer_function_name(self, skeleton_content: str, code: str, parser) -> Optional[str]:
        """Try to infer the function name from the skeleton title and code."""
        title_match = re.match(
            r"^#\s+(GET|POST|PUT|DELETE|PATCH)\s+(/\S+)",
            skeleton_content,
            re.MULTILINE,
        )
        if not title_match:
            return None

        target_method = title_match.group(1).upper()
        target_path = title_match.group(2)

        import ast
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                info = parser.extract_api_info(code, node.name)
                if info and info.method.upper() == target_method and info.path == target_path:
                    return node.name

        return None

    def _fill_basic_info(
        self,
        content: str,
        api_info: ExtractedApiInfo,
        filled_fields: List[str],
        conflicts: List[str],
        preserved_fields: List[str],
    ) -> str:
        """Fill the 基本信息 table with HTTP method and path."""
        section_match = re.search(r"^## 基本信息\s*\n", content, re.MULTILINE)
        if not section_match:
            return content

        section_start = section_match.end()
        next_section = re.search(r"^## ", content[section_start:], re.MULTILINE)
        section_end = section_start + next_section.start() if next_section else len(content)
        section_text = content[section_start:section_end]

        table_rows = re.findall(r"^\|([^|]+)\|([^|]+)\|$", section_text, re.MULTILINE)

        updated_section = section_text

        method_value = api_info.method
        updated_section = self._fill_table_field(
            updated_section, "HTTP 方法", method_value,
            filled_fields, conflicts, preserved_fields,
            add_before_version=True,
        )

        path_value = api_info.path
        updated_section = self._fill_table_field(
            updated_section, "路径", path_value,
            filled_fields, conflicts, preserved_fields,
            add_before_version=True,
        )

        return content[:section_start] + updated_section + content[section_end:]

    def _fill_table_field(
        self,
        section_text: str,
        field_name: str,
        code_value: str,
        filled_fields: List[str],
        conflicts: List[str],
        preserved_fields: List[str],
        add_before_version: bool = False,
    ) -> str:
        """Fill or check a single field in a key-value table."""
        row_pattern = re.compile(
            r"^(\|\s*" + re.escape(field_name) + r"\s*\|)\s*([^|]*)\|$",
            re.MULTILINE,
        )
        match = row_pattern.search(section_text)

        if match:
            existing_value = match.group(2).strip()
            if _PLACEHOLDER in existing_value:
                new_row = f"| {field_name} | {code_value} |"
                section_text = section_text[:match.start()] + new_row + section_text[match.end():]
                filled_fields.append(f"基本信息.{field_name}")
            elif existing_value != code_value:
                conflicts.append(
                    f"字段 基本信息.{field_name}: 文档值={existing_value}, 代码值={code_value}"
                )
                preserved_fields.append(f"基本信息.{field_name}")
            else:
                preserved_fields.append(f"基本信息.{field_name}")
        else:
            new_row = f"| {field_name} | {code_value} |"
            if add_before_version:
                version_match = re.search(r"^\| 版本 \|", section_text, re.MULTILINE)
                if version_match:
                    section_text = (
                        section_text[:version_match.start()]
                        + new_row + "\n"
                        + section_text[version_match.start():]
                    )
                else:
                    section_text = section_text.rstrip("\n") + "\n" + new_row + "\n\n"
            else:
                section_text = section_text.rstrip("\n") + "\n" + new_row + "\n\n"
            filled_fields.append(f"基本信息.{field_name}")

        return section_text

    def _fill_request_params(
        self,
        content: str,
        api_info: ExtractedApiInfo,
        filled_fields: List[str],
        conflicts: List[str],
        preserved_fields: List[str],
    ) -> str:
        """Fill the 请求参数 table with extracted parameters."""
        section_match = re.search(r"^## 请求参数\s*\n", content, re.MULTILINE)
        if not section_match:
            return content

        section_start = section_match.end()
        next_section = re.search(r"^## ", content[section_start:], re.MULTILINE)
        section_end = section_start + next_section.start() if next_section else len(content)
        section_text = content[section_start:section_end]

        if not api_info.request_params:
            return content

        data_rows = self._extract_table_data_rows(section_text)

        if self._is_placeholder_table(data_rows):
            new_table = self._render_params_table(api_info.request_params)
            table_match = re.search(
                r"(\|[^\n]*\|\n\|[-| ]+\|\n)((?:\|[^\n]*\|\n?)*)",
                section_text,
            )
            if table_match:
                header = table_match.group(1)
                new_section = header + new_table + "\n"
                section_text = section_text[:table_match.start()] + new_section + section_text[table_match.end():]
                filled_fields.append("请求参数")
        else:
            existing_params = self._parse_params_from_table(data_rows)
            code_params = {p.name: p for p in api_info.request_params}

            for param_name, param in code_params.items():
                if param_name in existing_params:
                    existing = existing_params[param_name]
                    if existing.get("type") and existing["type"] != _PLACEHOLDER:
                        if existing["type"] != param.type:
                            conflicts.append(
                                f"字段 请求参数.{param_name}.类型: "
                                f"文档值={existing['type']}, 代码值={param.type}"
                            )
                    preserved_fields.append(f"请求参数.{param_name}")

        return content[:section_start] + section_text + content[section_end:]

    def _fill_response_structure(
        self,
        content: str,
        api_info: ExtractedApiInfo,
        filled_fields: List[str],
        conflicts: List[str],
        preserved_fields: List[str],
    ) -> str:
        """Fill the 响应结构 table if response fields are available."""
        section_match = re.search(r"^## 响应结构\s*\n", content, re.MULTILINE)
        if not section_match:
            return content

        if not api_info.response_fields:
            return content

        section_start = section_match.end()
        next_section = re.search(r"^## ", content[section_start:], re.MULTILINE)
        section_end = section_start + next_section.start() if next_section else len(content)
        section_text = content[section_start:section_end]

        data_rows = self._extract_table_data_rows(section_text)

        if self._is_placeholder_table(data_rows):
            new_table = self._render_response_table(api_info.response_fields)
            table_match = re.search(
                r"(\|[^\n]*\|\n\|[-| ]+\|\n)((?:\|[^\n]*\|\n?)*)",
                section_text,
            )
            if table_match:
                header = table_match.group(1)
                new_section = header + new_table + "\n"
                section_text = section_text[:table_match.start()] + new_section + section_text[table_match.end():]
                filled_fields.append("响应结构")
        else:
            preserved_fields.append("响应结构")

        return content[:section_start] + section_text + content[section_end:]

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _extract_table_data_rows(self, section_text: str) -> List[List[str]]:
        """Extract data rows from a Markdown table (skip header + separator)."""
        lines = section_text.strip().split("\n")
        data_rows = []
        header_seen = False
        separator_seen = False
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            if not header_seen:
                header_seen = True
                continue
            if not separator_seen:
                separator_seen = True
                continue
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            data_rows.append(cells)
        return data_rows

    def _is_placeholder_table(self, data_rows: List[List[str]]) -> bool:
        """Check if all data rows contain only placeholder values."""
        if not data_rows:
            return True
        for row in data_rows:
            for cell in row:
                if cell and cell != _PLACEHOLDER:
                    return False
        return True

    def _render_params_table(self, params: List[ApiField]) -> str:
        """Render parameter rows for the 请求参数 table."""
        lines = []
        for p in params:
            required = "是" if p.required else "否"
            source = p.source or "body"
            desc = p.description or "待补充"
            lines.append(self._render_row(p.name, p.type, required, source, desc))
        return "\n".join(lines)

    def _render_response_table(self, fields: List[ApiField]) -> str:
        """Render field rows for the 响应结构 table."""
        lines = []
        for f in fields:
            flow = f.source or "out"
            desc = f.description or "待补充"
            lines.append(self._render_row(f.name, f.type, flow, desc=desc))
        return "\n".join(lines)

    @staticmethod
    def _render_row(*cells: str, desc: str = "") -> str:
        """渲染一行 markdown 表格，转义单元格内的 | 避免 PEP 604 联合类型破坏表格"""
        esc = lambda s: s.replace("|", "\\|")
        if desc:
            return "| " + " | ".join(esc(c) for c in cells) + f" | {esc(desc)} |"
        return "| " + " | ".join(esc(c) for c in cells) + " |"

    def _parse_params_from_table(self, data_rows: List[List[str]]) -> dict:
        """Parse existing parameter rows into a dict keyed by param name."""
        params = {}
        for row in data_rows:
            if len(row) >= 2:
                name = row[0].strip()
                if name and name != _PLACEHOLDER:
                    params[name] = {
                        "type": row[1].strip() if len(row) > 1 else "",
                        "required": row[2].strip() if len(row) > 2 else "",
                    }
        return params
