"""ORM Parser: 从 SQLAlchemy 模型文件提取表结构信息。

支持两种 SQLAlchemy 列定义风格：
- mapped_column: `name: Mapped[type] = mapped_column(SQLType, ...)`
- Column: `name = Column(SQLType, ...)`

提取字段名、类型、约束（nullable, unique, primary_key, default）及注释。
"""

import re
from pathlib import Path
from typing import List, Optional

from ..models.doc_types import ExtractedStorageInfo, StorageField, IndexInfo


# 匹配 __tablename__
_TABLENAME_RE = re.compile(r"__tablename__\s*=\s*['\"](\w+)['\"]")

# 匹配 mapped_column 风格: name: Mapped[Type] = mapped_column(...)
_MAPPED_COL_RE = re.compile(
    r"^[ \t]+(\w+)\s*:\s*Mapped\[([^\]]+)\]\s*=\s*mapped_column\(([^)]*)\)",
    re.MULTILINE,
)

# 匹配 Column 风格: name = Column(Type, ...)
_COLUMN_RE = re.compile(
    r"^[ \t]+(\w+)\s*=\s*(?:mapped_column|Column)\(([^)]*)\)",
    re.MULTILINE,
)

# 匹配行前注释作为字段说明
_COMMENT_BEFORE_RE = re.compile(r"^[ \t]+#\s*(.+)$", re.MULTILINE)

# 匹配 Index 定义
_INDEX_RE = re.compile(
    r"Index\(\s*['\"](\w+)['\"](?:\s*,\s*([^)]+))?\)",
)

# 匹配 UniqueConstraint
_UNIQUE_CONSTRAINT_RE = re.compile(
    r"UniqueConstraint\(\s*([^)]+)\)",
)

# SQL 类型 → 简化显示
_TYPE_MAP = {
    "string": "VARCHAR",
    "text": "TEXT",
    "integer": "INTEGER",
    "biginteger": "BIGINT",
    "smallinteger": "SMALLINT",
    "float": "FLOAT",
    "numeric": "DECIMAL",
    "boolean": "BOOLEAN",
    "datetime": "DATETIME",
    "date": "DATE",
    "time": "TIME",
    "json": "JSON",
    "uuid": "UUID",
    "pguuid": "UUID",
    "enum": "ENUM",
    "largebinary": "BLOB",
}


class ORMParser:
    """从 SQLAlchemy ORM 模型提取 ExtractedStorageInfo"""

    def extract_storage_info(self, content: str) -> List[ExtractedStorageInfo]:
        """从 Python 源文件内容提取所有表定义"""
        results = []

        # 按类拆分
        class_blocks = self._split_classes(content)

        for class_name, class_body in class_blocks:
            tablename_match = _TABLENAME_RE.search(class_body)
            if not tablename_match:
                continue

            table_name = tablename_match.group(1)
            columns = self._extract_columns(class_body)
            indexes = self._extract_indexes(class_body)

            results.append(ExtractedStorageInfo(
                table_name=table_name,
                columns=columns,
                indexes=indexes,
            ))

        return results

    def _split_classes(self, content: str) -> List[tuple]:
        """拆分文件中的类定义"""
        class_pattern = re.compile(r"^class\s+(\w+)\s*\([^)]*\)\s*:", re.MULTILINE)
        matches = list(class_pattern.finditer(content))

        blocks = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            blocks.append((m.group(1), content[start:end]))

        return blocks

    def _extract_columns(self, class_body: str) -> List[StorageField]:
        """提取列定义"""
        columns = []
        lines = class_body.split("\n")
        comment_buffer = ""

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 收集注释
            if stripped.startswith("#"):
                comment_buffer = stripped.lstrip("# ").strip()
                continue

            # mapped_column 风格
            m = re.match(
                r"\s+(\w+)\s*:\s*Mapped\[([^\]]+)\]\s*=\s*mapped_column\((.*)$",
                line,
            )
            if m:
                name = m.group(1)
                python_type = m.group(2)
                args_str = m.group(3).rstrip(")")

                col = self._parse_column_args(name, python_type, args_str, comment_buffer)
                if col and name not in ("__tablename__", "__table_args__"):
                    columns.append(col)
                comment_buffer = ""
                continue

            # Column() 风格 (无类型注解)
            m = re.match(
                r"\s+(\w+)\s*=\s*(?:mapped_column|Column)\((.*)$",
                line,
            )
            if m:
                name = m.group(1)
                args_str = m.group(2).rstrip(")")

                if name.startswith("_") or name in ("__tablename__", "__table_args__", "metadata"):
                    comment_buffer = ""
                    continue

                col = self._parse_column_args(name, "", args_str, comment_buffer)
                if col:
                    columns.append(col)
                comment_buffer = ""
                continue

            # 非列定义行，清除注释缓冲
            if stripped and not stripped.startswith("#"):
                comment_buffer = ""

        return columns

    def _parse_column_args(self, name: str, python_type: str, args_str: str, comment: str) -> Optional[StorageField]:
        """解析列参数"""
        constraints = []
        is_pk = False
        sql_type = ""

        # 从参数中提取 SQL 类型
        type_match = re.match(r"\s*(\w+)(?:\([^)]*\))?", args_str)
        if type_match:
            raw_type = type_match.group(1).lower()
            if raw_type in _TYPE_MAP:
                sql_type = _TYPE_MAP[raw_type]
            elif raw_type in ("pguuid", "uuid"):
                sql_type = "UUID"
            else:
                sql_type = raw_type.upper()

        # 提取长度
        length_match = re.search(r"String\((\d+)\)", args_str)
        if length_match:
            sql_type = f"VARCHAR({length_match.group(1)})"

        # 如果没从 args 解析到类型，从 python 类型推断
        if not sql_type and python_type:
            clean_type = python_type.strip().split("[")[0].lower()
            type_mapping = {
                "str": "VARCHAR", "int": "INTEGER", "float": "FLOAT",
                "bool": "BOOLEAN", "uuid": "UUID", "datetime": "DATETIME",
                "date": "DATE", "optional": "NULLABLE",
            }
            sql_type = type_mapping.get(clean_type, python_type.upper())

        # 解析约束
        if "primary_key=True" in args_str or "primary_key = True" in args_str:
            is_pk = True
            constraints.append("PK")
        if "unique=True" in args_str or "unique = True" in args_str:
            constraints.append("UNIQUE")
        if "nullable=False" in args_str or "nullable = False" in args_str:
            constraints.append("NOT NULL")
        if "nullable=True" in args_str or "nullable = True" in args_str:
            constraints.append("NULLABLE")

        # 提取 default
        default_match = re.search(r"default=([^,)]+)", args_str)
        if default_match:
            default_val = default_match.group(1).strip()
            if default_val not in ("None",):
                constraints.append(f"DEFAULT {default_val}")

        # server_default
        server_default_match = re.search(r"server_default=([^,)]+)", args_str)
        if server_default_match:
            constraints.append(f"SERVER_DEFAULT")

        return StorageField(
            name=name,
            type=sql_type or "UNKNOWN",
            constraints=constraints,
            is_primary_key=is_pk,
        )

    def _extract_indexes(self, class_body: str) -> List[IndexInfo]:
        """提取索引定义"""
        indexes = []

        # __table_args__ 中的 Index(...)
        for m in _INDEX_RE.finditer(class_body):
            index_name = m.group(1)
            cols_str = m.group(2) or ""
            columns = [c.strip().strip("'\"") for c in cols_str.split(",") if c.strip().strip("'\"")]
            indexes.append(IndexInfo(
                index_name=index_name,
                index_type="INDEX",
                columns=columns,
            ))

        # UniqueConstraint(...)
        for m in _UNIQUE_CONSTRAINT_RE.finditer(class_body):
            cols_str = m.group(1)
            columns = []
            for part in cols_str.split(","):
                part = part.strip().strip("'\"")
                if part and not part.startswith("name="):
                    columns.append(part)
            if columns:
                name_match = re.search(r"name=['\"](\w+)['\"]", cols_str)
                idx_name = name_match.group(1) if name_match else f"uq_{'_'.join(columns[:2])}"
                indexes.append(IndexInfo(
                    index_name=idx_name,
                    index_type="UNIQUE",
                    columns=columns,
                ))

        # unique=True on individual columns
        for m in _MAPPED_COL_RE.finditer(class_body):
            name = m.group(1)
            args = m.group(3)
            if "unique=True" in args or "unique = True" in args:
                indexes.append(IndexInfo(
                    index_name=f"uq_{name}",
                    index_type="UNIQUE",
                    columns=[name],
                ))

        return indexes
