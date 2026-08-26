"""StorageDetailFiller: fills storage document skeletons (db-*.md) from DDL parser output."""

import re
from typing import List, Tuple

from ..models.doc_types import ExtractedStorageInfo, StorageField, IndexInfo


_PLACEHOLDER = "待补充"


class StorageDetailFiller:
    """Fills storage document skeletons (db-*.md) from DDL parser output."""

    def fill(
        self,
        skeleton_content: str,
        storage_info: ExtractedStorageInfo,
    ) -> Tuple[str, List[str], List[str], List[str]]:
        """Fill 字段定义 and 索引设计 tables.

        Returns: (updated_content, filled_fields, conflicts, preserved_fields)
        """
        filled_fields: List[str] = []
        conflicts: List[str] = []
        preserved_fields: List[str] = []

        content = skeleton_content
        content = self._fill_field_table(
            content, storage_info.columns, filled_fields, conflicts, preserved_fields
        )
        content = self._fill_index_table(
            content, storage_info.indexes, filled_fields, conflicts, preserved_fields
        )

        return content, filled_fields, conflicts, preserved_fields

    def _fill_field_table(
        self,
        content: str,
        columns: List[StorageField],
        filled_fields: List[str],
        conflicts: List[str],
        preserved_fields: List[str],
    ) -> str:
        """Replace placeholder rows in 字段定义 table with column data."""
        section_match = re.search(r'^## 字段定义\s*\n', content, re.MULTILINE)
        if not section_match:
            return content

        section_start = section_match.end()
        next_section = re.search(r'^## ', content[section_start:], re.MULTILINE)
        section_end = section_start + next_section.start() if next_section else len(content)
        section_text = content[section_start:section_end]

        data_rows = self._extract_table_data_rows(section_text)

        if self._is_placeholder_table(data_rows):
            # Replace placeholder rows with column data
            new_rows = self._render_field_rows(columns)
            section_text = self._replace_data_rows(section_text, new_rows)
            filled_fields.append("字段定义")
        else:
            # Preserve existing rows, check for conflicts
            existing_fields = {}
            for row in data_rows:
                if len(row) >= 2:
                    name = row[0].strip()
                    if name and name != _PLACEHOLDER:
                        existing_fields[name] = row[1].strip()

            for col in columns:
                if col.name in existing_fields:
                    existing_type = existing_fields[col.name]
                    if existing_type != _PLACEHOLDER and existing_type.lower() != col.type.lower():
                        conflicts.append(
                            f"字段 字段定义.{col.name}.类型: 文档值={existing_type}, 代码值={col.type}"
                        )
                    preserved_fields.append(f"字段定义.{col.name}")

        return content[:section_start] + section_text + content[section_end:]

    def _fill_index_table(
        self,
        content: str,
        indexes: List[IndexInfo],
        filled_fields: List[str],
        conflicts: List[str],
        preserved_fields: List[str],
    ) -> str:
        """Replace placeholder rows in 索引设计 table with index data."""
        section_match = re.search(r'^## 索引设计\s*\n', content, re.MULTILINE)
        if not section_match:
            return content

        section_start = section_match.end()
        next_section = re.search(r'^## ', content[section_start:], re.MULTILINE)
        section_end = section_start + next_section.start() if next_section else len(content)
        section_text = content[section_start:section_end]

        data_rows = self._extract_table_data_rows(section_text)

        if self._is_placeholder_table(data_rows):
            if indexes:
                new_rows = self._render_index_rows(indexes)
                section_text = self._replace_data_rows(section_text, new_rows)
                filled_fields.append("索引设计")
        else:
            # Preserve existing rows
            existing_indexes = set()
            for row in data_rows:
                if row and row[0].strip() and row[0].strip() != _PLACEHOLDER:
                    existing_indexes.add(row[0].strip())
            for idx in indexes:
                if idx.index_name in existing_indexes:
                    preserved_fields.append(f"索引设计.{idx.index_name}")

        return content[:section_start] + section_text + content[section_end:]

    def _render_field_rows(self, columns: List[StorageField]) -> str:
        """Render column rows for the 字段定义 table."""
        lines = []
        for col in columns:
            index_mark = "PK" if col.is_primary_key else "待补充"
            lines.append(
                f"| {col.name} | {col.type} | {index_mark} | {_PLACEHOLDER} | {_PLACEHOLDER} | {_PLACEHOLDER} | {_PLACEHOLDER} |"
            )
        return '\n'.join(lines)

    def _render_index_rows(self, indexes: List[IndexInfo]) -> str:
        """Render index rows for the 索引设计 table."""
        lines = []
        for idx in indexes:
            cols_str = ', '.join(idx.columns)
            lines.append(f"| {idx.index_name} | {idx.index_type} | {cols_str} | {_PLACEHOLDER} |")
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
        data_replaced = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('|') and not header_seen:
                header_seen = True
                result.append(line)
                continue
            if stripped.startswith('|') and header_seen and not separator_seen:
                separator_seen = True
                result.append(line)
                # Insert new data rows right after separator
                result.append(new_rows)
                data_replaced = True
                continue
            if stripped.startswith('|') and separator_seen:
                # Skip old data rows
                continue
            result.append(line)
        return '\n'.join(result)
