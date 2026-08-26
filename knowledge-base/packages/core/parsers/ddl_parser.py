"""DDL Parser — regex-based SQL CREATE TABLE parser, no external dependencies."""

import re
from typing import List, Optional

from .base import BaseParser
from ..models.doc_types import ExtractedApiInfo, ExtractedStorageInfo, StorageField, IndexInfo


class DDLParser(BaseParser):
    """SQL DDL parser — regex-based, no external dependencies."""

    def extract_api_info(self, code: str, function_name: str) -> Optional[ExtractedApiInfo]:
        """Not applicable for DDL files. Returns None."""
        return None

    def extract_storage_info(self, sql: str) -> List[ExtractedStorageInfo]:
        """Parse CREATE TABLE statements from SQL content.

        Returns one ExtractedStorageInfo per table found.
        Empty list if no valid CREATE TABLE statements.
        """
        # Find all CREATE TABLE blocks
        # Match CREATE TABLE ... ( ... ) respecting nested parentheses
        results: List[ExtractedStorageInfo] = []

        table_header = re.compile(
            r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?'
            r'[`"\']?(\w+)[`"\']?'
            r'\s*\(',
            re.IGNORECASE,
        )

        for m in table_header.finditer(sql):
            table_name = m.group(1)
            body = self._extract_balanced_parens(sql, m.end() - 1)
            if body is not None:
                info = self._parse_create_table(table_name, body)
                if info:
                    results.append(info)

        # Also parse standalone CREATE INDEX statements
        self._parse_standalone_indexes(sql, results)

        return results

    def _parse_create_table(self, table_name: str, body: str) -> Optional[ExtractedStorageInfo]:
        """Parse a single CREATE TABLE body (content inside parentheses)."""
        columns: List[StorageField] = []
        indexes: List[IndexInfo] = []

        # Split body by commas, but respect parentheses nesting
        parts = self._split_definitions(body)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            upper = part.upper().lstrip()

            # Check for table-level constraints / indexes
            if upper.startswith('PRIMARY KEY'):
                cols = self._extract_columns_from_parens(part)
                if cols:
                    indexes.append(IndexInfo(
                        index_name='PRIMARY',
                        index_type='PRIMARY',
                        columns=cols,
                    ))
                    # Mark columns as primary key
                    for c in columns:
                        if c.name in cols:
                            c.is_primary_key = True
                continue

            if upper.startswith('UNIQUE KEY') or upper.startswith('UNIQUE INDEX') or upper.startswith('UNIQUE ('):
                name, cols = self._parse_inline_index(part, 'UNIQUE')
                if cols:
                    indexes.append(IndexInfo(index_name=name, index_type='UNIQUE', columns=cols))
                continue

            if upper.startswith('KEY ') or upper.startswith('INDEX '):
                name, cols = self._parse_inline_index(part, 'INDEX')
                if cols:
                    indexes.append(IndexInfo(index_name=name, index_type='INDEX', columns=cols))
                continue

            if upper.startswith('CONSTRAINT') or upper.startswith('FOREIGN KEY') or upper.startswith('CHECK'):
                continue

            # Regular column definition
            col = self._parse_column(part)
            if col:
                columns.append(col)

        # If any column was marked PRIMARY KEY inline, add a PRIMARY index if not already present
        pk_cols = [c.name for c in columns if c.is_primary_key]
        if pk_cols and not any(idx.index_type == 'PRIMARY' for idx in indexes):
            indexes.append(IndexInfo(index_name='PRIMARY', index_type='PRIMARY', columns=pk_cols))

        return ExtractedStorageInfo(table_name=table_name, columns=columns, indexes=indexes)

    def _parse_column(self, col_def: str) -> Optional[StorageField]:
        """Parse a column definition line."""
        col_def = col_def.strip()
        if not col_def:
            return None

        # Match: column_name TYPE(...) [constraints...]
        m = re.match(
            r'[`"\']?(\w+)[`"\']?\s+'
            r'(\w+(?:\s*\([^)]*\))?(?:\s+(?:UNSIGNED|SIGNED|ZEROFILL))*)',
            col_def,
            re.IGNORECASE,
        )
        if not m:
            return None

        name = m.group(1)
        col_type = m.group(2).strip()

        # Skip SQL keywords that aren't column names
        if name.upper() in ('PRIMARY', 'KEY', 'INDEX', 'UNIQUE', 'CONSTRAINT',
                            'FOREIGN', 'CHECK', 'PARTITION', 'ENGINE'):
            return None

        remainder = col_def[m.end():].strip()
        constraints: List[str] = []
        is_pk = False

        upper_remainder = remainder.upper()

        if 'PRIMARY KEY' in upper_remainder:
            is_pk = True
            constraints.append('PRIMARY KEY')

        if 'NOT NULL' in upper_remainder:
            constraints.append('NOT NULL')

        if 'UNIQUE' in upper_remainder and 'PRIMARY KEY' not in upper_remainder:
            constraints.append('UNIQUE')

        # Extract DEFAULT value
        default_match = re.search(r'DEFAULT\s+(\S+)', remainder, re.IGNORECASE)
        if default_match:
            constraints.append(f'DEFAULT {default_match.group(1)}')

        if 'AUTO_INCREMENT' in upper_remainder:
            constraints.append('AUTO_INCREMENT')

        return StorageField(name=name, type=col_type, constraints=constraints, is_primary_key=is_pk)

    def _parse_inline_index(self, definition: str, default_type: str) -> tuple:
        """Parse an inline KEY/INDEX/UNIQUE declaration. Returns (name, columns)."""
        # Patterns like: KEY idx_name (col1, col2) or UNIQUE KEY idx_name (col1)
        m = re.match(
            r'(?:UNIQUE\s+)?(?:KEY|INDEX)\s+[`"\']?(\w+)[`"\']?\s*\(([^)]+)\)',
            definition,
            re.IGNORECASE,
        )
        if m:
            name = m.group(1)
            cols = [c.strip().strip('`"\'') for c in m.group(2).split(',')]
            return name, cols

        # UNIQUE (col1, col2) without name
        m = re.match(r'UNIQUE\s*\(([^)]+)\)', definition, re.IGNORECASE)
        if m:
            cols = [c.strip().strip('`"\'') for c in m.group(1).split(',')]
            return f'unique_{cols[0]}', cols

        return '', []

    def _parse_standalone_indexes(self, sql: str, results: List[ExtractedStorageInfo]) -> None:
        """Parse standalone CREATE INDEX statements and attach to matching tables."""
        pattern = re.compile(
            r'CREATE\s+(?:(UNIQUE)\s+)?INDEX\s+[`"\']?(\w+)[`"\']?\s+'
            r'ON\s+[`"\']?(\w+)[`"\']?\s*\(([^)]+)\)',
            re.IGNORECASE,
        )
        for m in pattern.finditer(sql):
            is_unique = m.group(1) is not None
            idx_name = m.group(2)
            table_name = m.group(3)
            cols = [c.strip().strip('`"\'') for c in m.group(4).split(',')]
            idx_type = 'UNIQUE' if is_unique else 'INDEX'

            # Find the matching table and add the index
            for info in results:
                if info.table_name == table_name:
                    info.indexes.append(IndexInfo(index_name=idx_name, index_type=idx_type, columns=cols))
                    break

    def _extract_balanced_parens(self, text: str, start: int) -> Optional[str]:
        """Extract content between balanced parentheses starting at text[start]=='('."""
        if start >= len(text) or text[start] != '(':
            return None
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    return text[start + 1:i]
        return None

    def _split_definitions(self, body: str) -> List[str]:
        """Split column/constraint definitions by commas, respecting parentheses."""
        parts: List[str] = []
        depth = 0
        current: List[str] = []
        for char in body:
            if char == '(':
                depth += 1
                current.append(char)
            elif char == ')':
                depth -= 1
                current.append(char)
            elif char == ',' and depth == 0:
                parts.append(''.join(current))
                current = []
            else:
                current.append(char)
        if current:
            parts.append(''.join(current))
        return parts

    def _extract_columns_from_parens(self, definition: str) -> List[str]:
        """Extract column names from a parenthesized list like PRIMARY KEY (col1, col2)."""
        m = re.search(r'\(([^)]+)\)', definition)
        if m:
            return [c.strip().strip('`"\'') for c in m.group(1).split(',')]
        return []
