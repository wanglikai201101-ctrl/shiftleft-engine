"""
兼容层 — 旧的 knowledge_base 包重新导出到 packages.core

已迁移到 packages/core/，此文件保留向后兼容。
新代码请直接使用 packages.core。
"""

from packages.core.indexing.scanner import DocumentScanner
from packages.core.indexing.parser import DocumentParser
from packages.core.indexing.indexer import DocumentIndexer
from packages.core.indexing.query import DocumentQuery

__all__ = [
    "DocumentScanner",
    "DocumentParser",
    "DocumentIndexer",
    "DocumentQuery",
]
