"""文档扫描器：递归扫描知识库目录"""

from pathlib import Path
from typing import List
from ..models.doc_types import DocType, StorageType


class DocumentScanner:
    """文档扫描器"""

    def __init__(self, base_dir: str = "modules"):
        self.base_dir = Path(base_dir)
        if not self.base_dir.exists():
            raise FileNotFoundError(f"知识库目录不存在: {self.base_dir}")

    def scan(self) -> List[Path]:
        """扫描所有 MD 文档"""
        md_files = set()
        for pattern in ("**/*.md", "**/*.MD"):
            md_files.update(self.base_dir.glob(pattern))
        return sorted(md_files)

    def get_doc_type(self, file_path: Path) -> str:
        """根据路径判断文档类型"""
        parts = file_path.parts
        type_mapping = {
            "requirements": DocType.REQUIREMENT,
            "apis": DocType.API,
            "storage": DocType.STORAGE,
            "pages": DocType.PAGE,
            "jobs": DocType.JOB,
            "configs": DocType.CONFIG,
            "error-handling": DocType.ERROR_HANDLING,
            "integration": DocType.INTEGRATION,
            "modules": DocType.MODULE,
        }
        for dir_name, doc_type in type_mapping.items():
            if dir_name in parts:
                return doc_type.value
        return DocType.UNKNOWN.value

    def get_storage_type(self, file_path: Path) -> str:
        """判断存储文档的子类型"""
        if self.get_doc_type(file_path) != DocType.STORAGE.value:
            return StorageType.UNKNOWN.value
        filename = file_path.stem.lower()
        prefix_map = {
            "db-": StorageType.DATABASE,
            "redis-": StorageType.REDIS,
            "mq-": StorageType.MQ,
            "es-": StorageType.ELASTICSEARCH,
            "oss-": StorageType.OSS,
        }
        for prefix, stype in prefix_map.items():
            if filename.startswith(prefix):
                return stype.value
        return StorageType.UNKNOWN.value
