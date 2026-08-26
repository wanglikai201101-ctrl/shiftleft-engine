"""PageDetailFiller: fills page document skeletons from Vue parser output."""

import re
from typing import List, Tuple

from ..models.doc_types import ExtractedPageInfo, PageElement


_PLACEHOLDER = "待补充"


class PageDetailFiller:
    """Fills page document skeletons from Vue parser output."""

    def fill(
        self,
        skeleton_content: str,
        page_info: ExtractedPageInfo,
    ) -> Tuple[str, List[str], List[str], List[str]]:
        """Fill 页面元素清单 table.

        Returns: (updated_content, filled_fields, conflicts, preserved_fields)
        """
        filled_fields: List[str] = []
        conflicts: List[str] = []
        preserved_fields: List[str] = []

        content = skeleton_content
        content = self._fill_elements_table(
            content, page_info.elements, filled_fields, conflicts, preserved_fields
        )

        return content, filled_fields, conflicts, preserved_fields

    def _fill_elements_table(
        self,
        content: str,
        elements: List[PageElement],
        filled_fields: List[str],
        conflicts: List[str],
        preserved_fields: List[str],
    ) -> str:
        """Replace placeholder rows in 页面元素清单 table with element data."""
        section_match = re.search(r'^## 页面元素清单\s*\n', content, re.MULTILINE)
        if not section_match:
            return content

        section_start = section_match.end()
        next_section = re.search(r'^## ', content[section_start:], re.MULTILINE)
        section_end = section_start + next_section.start() if next_section else len(content)
        section_text = content[section_start:section_end]

        data_rows = self._extract_table_data_rows(section_text)

        if self._is_placeholder_table(data_rows):
            if elements:
                new_rows = self._render_element_rows(elements)
                section_text = self._replace_data_rows(section_text, new_rows)
                filled_fields.append("页面元素清单")
        else:
            # Preserve existing rows, check for conflicts
            existing_testids = {}
            for row in data_rows:
                if row and row[0].strip() and row[0].strip() != _PLACEHOLDER:
                    existing_testids[row[0].strip()] = row[1].strip() if len(row) > 1 else ''

            for elem in elements:
                if elem.testid in existing_testids:
                    existing_type = existing_testids[elem.testid]
                    if existing_type != _PLACEHOLDER and existing_type != elem.element_type:
                        conflicts.append(
                            f"字段 页面元素清单.{elem.testid}.元素类型: 文档值={existing_type}, 代码值={elem.element_type}"
                        )
                    preserved_fields.append(f"页面元素清单.{elem.testid}")

        return content[:section_start] + section_text + content[section_end:]

    def _render_element_rows(self, elements: List[PageElement]) -> str:
        """Render element rows for the 页面元素清单 table."""
        lines = []
        for elem in elements:
            dynamic_mark = " (动态)" if elem.is_dynamic else ""
            lines.append(
                f"| {elem.testid}{dynamic_mark} | {elem.element_type} | {_PLACEHOLDER} | {_PLACEHOLDER} | {_PLACEHOLDER} | {_PLACEHOLDER} |"
            )
        return '\n'.join(lines)

    def _extract_table_data_rows(self, section_text: str) -> List[List[str]]:
        """Extract data rows from a Markdown table (skip header + separator)."""
        lines = section_text.strip().split('\n')
        data_rows = []
        header_seen = False
        separator_seen = False
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith('|'):
                continue
            if not header_seen:
                header_seen = True
                continue
            if not separator_seen:
                separator_seen = True
                continue
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
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

    def _replace_data_rows(self, section_text: str, new_rows: str) -> str:
        """Replace data rows in a markdown table, keeping header and separator."""
        lines = section_text.split('\n')
        result = []
        header_seen = False
        separator_seen = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('|') and not header_seen:
                header_seen = True
                result.append(line)
                continue
            if stripped.startswith('|') and header_seen and not separator_seen:
                separator_seen = True
                result.append(line)
                result.append(new_rows)
                continue
            if stripped.startswith('|') and separator_seen:
                continue
            result.append(line)
        return '\n'.join(result)
