"""需求文档关联关系解析器

解析需求文档中的关联表（关联接口/关联数据库/关联存储/关联前端页面/关联定时任务），
提取 REQ-xxx 和 TP-xxx 编号，返回 AssociatedDoc 列表。
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple

from packages.core.models.doc_types import AssociatedDoc, DocType


class RelationParser:
    """解析需求文档中的关联关系表"""

    # Section header patterns mapped to DocType
    _SECTION_PATTERNS: List[Tuple[re.Pattern, DocType]] = [
        (re.compile(r"^#{2,4}\s*关联接口", re.MULTILINE), DocType.API),
        (re.compile(r"^#{2,4}\s*关联数据库", re.MULTILINE), DocType.STORAGE),
        (re.compile(r"^#{2,4}\s*关联其他存储", re.MULTILINE), DocType.STORAGE),
        (re.compile(r"^#{2,4}\s*关联存储", re.MULTILINE), DocType.STORAGE),
        (re.compile(r"^#{2,4}\s*关联前端页面", re.MULTILINE), DocType.PAGE),
        (re.compile(r"^#{2,4}\s*关联定时任务", re.MULTILINE), DocType.JOB),
    ]

    # Pattern to extract REQ-xxx from title or 需求概述 table
    _REQ_ID_PATTERN = re.compile(r"REQ-[A-Z0-9]+-\d+|REQ-\d+", re.IGNORECASE)

    # Pattern to extract TP-xxx from test point tables
    _TP_ID_PATTERN = re.compile(r"TP-[A-Z0-9]+-\d+-\d+|TP-\d+-\d+", re.IGNORECASE)

    # Pattern to extract markdown link paths: [text](path)
    _LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^)]+\.md)\)")

    def parse(self, content: str) -> List[AssociatedDoc]:
        """解析需求文档内容，提取所有关联文档信息。

        Args:
            content: 需求文档的 Markdown 内容

        Returns:
            关联文档列表
        """
        requirement_id = self.extract_requirement_id(content)
        test_point_ids = self.extract_test_point_ids(content)
        associations: List[AssociatedDoc] = []

        for section_pattern, doc_type in self._SECTION_PATTERNS:
            section_content = self._extract_section(content, section_pattern)
            if section_content:
                section_assocs = self._parse_association_table(
                    section_content, doc_type, requirement_id, test_point_ids
                )
                associations.extend(section_assocs)

        return associations

    def extract_requirement_id(self, content: str) -> str:
        """从文档标题或需求概述中提取 REQ-xxx 编号。"""
        # Try title first (# REQ-LO-001 — ...)
        title_match = re.search(r"^#\s+(REQ-[A-Z0-9]+-\d+|REQ-\d+)", content, re.MULTILINE | re.IGNORECASE)
        if title_match:
            return title_match.group(1).upper()

        # Try 需求概述 table (| 编号 | REQ-xxx |)
        overview_match = re.search(
            r"\|\s*编号\s*\|\s*(REQ-[A-Z0-9]+-\d+|REQ-\d+)\s*\|",
            content, re.IGNORECASE
        )
        if overview_match:
            return overview_match.group(1).upper()

        # Fallback: first REQ-xxx in document
        match = self._REQ_ID_PATTERN.search(content)
        return match.group(0).upper() if match else ""

    def extract_test_point_ids(self, content: str) -> List[str]:
        """从最小可测单元拆解表中提取所有 TP-xxx 编号。"""
        # Find the 最小可测单元拆解 section
        section_match = re.search(r"^#{2,4}\s*最小可测单元拆解", content, re.MULTILINE)
        if not section_match:
            return list(set(self._TP_ID_PATTERN.findall(content)))

        section_start = section_match.end()
        # Find next section header
        next_section = re.search(r"^#{2,4}\s+", content[section_start:], re.MULTILINE)
        section_end = section_start + next_section.start() if next_section else len(content)
        section_content = content[section_start:section_end]

        tp_ids = self._TP_ID_PATTERN.findall(section_content)
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for tp_id in tp_ids:
            tp_upper = tp_id.upper()
            if tp_upper not in seen:
                seen.add(tp_upper)
                unique.append(tp_upper)
        return unique

    def _extract_section(self, content: str, header_pattern: re.Pattern) -> Optional[str]:
        """Extract content of a section from the first matching header to the next header."""
        match = header_pattern.search(content)
        if not match:
            return None

        section_start = match.end()
        # Find next section header at same or higher level
        header_level = content[match.start():match.end()].count('#')
        next_header = re.search(
            rf"^#{{2,{header_level}}}\s+",
            content[section_start:],
            re.MULTILINE
        )
        section_end = section_start + next_header.start() if next_header else len(content)
        return content[section_start:section_end]

    def _parse_association_table(
        self,
        section_content: str,
        doc_type: DocType,
        requirement_id: str,
        all_test_point_ids: List[str],
    ) -> List[AssociatedDoc]:
        """Parse a Markdown table within a section to extract associations."""
        associations: List[AssociatedDoc] = []
        # Find table rows (skip header and separator)
        lines = section_content.strip().split('\n')
        table_rows = []
        in_table = False
        separator_seen = False

        for line in lines:
            stripped = line.strip()
            if not stripped.startswith('|'):
                if in_table:
                    break  # End of table
                continue

            if not in_table:
                in_table = True
                continue  # Skip header row

            if re.match(r'^\|[\s\-:|]+\|$', stripped):
                separator_seen = True
                continue  # Skip separator row

            if separator_seen:
                table_rows.append(stripped)

        for row in table_rows:
            cells = [c.strip() for c in row.split('|')[1:-1]]  # Remove empty first/last from split
            if len(cells) < 2:
                continue

            # Extract TP IDs from first cell (handles ranges like TP-001-04~08)
            tp_ids = self._extract_tp_ids_from_cell(cells[0])

            # Extract doc path from markdown link in any cell
            doc_path = ""
            identifier = ""
            for cell in cells[1:]:
                link_match = self._LINK_PATTERN.search(cell)
                if link_match:
                    doc_path = link_match.group(2)
                    # Clean relative path prefixes
                    doc_path = re.sub(r'^\.\./', '', doc_path)
                    break

            # Extract identifier from the second cell (interface name, table name, etc.)
            if len(cells) >= 2:
                identifier = self._extract_identifier(cells[1], doc_type, doc_path)

            if not identifier and not doc_path:
                continue

            associations.append(AssociatedDoc(
                doc_type=doc_type,
                identifier=identifier,
                test_point_ids=tp_ids,
                doc_path=doc_path,
                requirement_id=requirement_id,
            ))

        # Deduplicate by doc_path, merging test_point_ids
        return self._deduplicate_associations(associations)

    def _extract_tp_ids_from_cell(self, cell: str) -> List[str]:
        """Extract TP IDs from a cell, handling ranges like TP-001-04~08 and comma-separated lists."""
        tp_ids = []

        # Handle range patterns like TP-LO-001-04~08 or TP-LO-005-01~05
        range_pattern = re.compile(
            r"(TP-[A-Z0-9]+-\d+-)(\d+)\s*[~～]\s*(\d+)",
            re.IGNORECASE
        )
        for match in range_pattern.finditer(cell):
            prefix = match.group(1).upper()
            start = int(match.group(2))
            end = int(match.group(3))
            for i in range(start, end + 1):
                tp_ids.append(f"{prefix}{i:02d}")

        # Handle explicit TP IDs (not part of ranges)
        remaining = range_pattern.sub('', cell)
        for match in self._TP_ID_PATTERN.finditer(remaining):
            tp_id = match.group(0).upper()
            if tp_id not in tp_ids:
                tp_ids.append(tp_id)

        return tp_ids

    def _extract_identifier(self, cell: str, doc_type: DocType, doc_path: str) -> str:
        """Extract a meaningful identifier from a table cell."""
        # Clean markdown formatting
        clean = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', cell).strip()

        if doc_type == DocType.API:
            # Extract HTTP method + path like "POST /api/v1/orders"
            api_match = re.search(r'(GET|POST|PUT|DELETE|PATCH)\s+(/\S+)', clean, re.IGNORECASE)
            if api_match:
                return f"{api_match.group(1).upper()} {api_match.group(2)}"

        if doc_type == DocType.STORAGE:
            # Extract table name or storage node
            # e.g. "t_order", "order:lock:{order_no}", "order.created (MQ)"
            return clean if clean else ""

        if doc_type == DocType.PAGE:
            # Page name
            return clean if clean else ""

        if doc_type == DocType.JOB:
            # Job name
            return clean if clean else ""

        # Fallback: derive from doc_path
        if doc_path:
            return Path(doc_path).stem

        return clean

    def _deduplicate_associations(self, associations: List[AssociatedDoc]) -> List[AssociatedDoc]:
        """Deduplicate associations by doc_path, merging test_point_ids."""
        by_path: dict[str, AssociatedDoc] = {}
        result: List[AssociatedDoc] = []

        for assoc in associations:
            key = assoc.doc_path or assoc.identifier
            if key in by_path:
                existing = by_path[key]
                for tp_id in assoc.test_point_ids:
                    if tp_id not in existing.test_point_ids:
                        existing.test_point_ids.append(tp_id)
            else:
                by_path[key] = assoc
                result.append(assoc)

        return result
