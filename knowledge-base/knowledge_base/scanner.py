"""文档扫描器：递归扫描 knowledge-base/ 目录"""

from pathlib import Path
from typing import List


class DocumentScanner:
    """文档扫描器"""
    
    def __init__(self, base_dir: str = "knowledge-base"):
        """
        初始化文档扫描器
        
        Args:
            base_dir: 知识库根目录，默认为 "knowledge-base"
        """
        self.base_dir = Path(base_dir)
        if not self.base_dir.exists():
            raise FileNotFoundError(f"知识库目录不存在: {self.base_dir}")
    
    def scan(self) -> List[Path]:
        """
        扫描所有 MD 文档

        Returns:
            所有 MD 文档的路径列表（已排序）
        """
        md_files = set()  # 使用 set 去重
        for pattern in ["**/*.md", "**/*.MD"]:
            md_files.update(self.base_dir.glob(pattern))
        return sorted(list(md_files))
    
    def get_doc_type(self, file_path: Path) -> str:
        """
        根据路径判断文档类型
        
        Args:
            file_path: 文档路径
            
        Returns:
            文档类型：requirement/api/storage/page/job/config/error-handling/integration/module/unknown
        """
        parts = file_path.parts
        
        # 按目录名判断文档类型
        type_mapping = {
            "requirements": "requirement",
            "apis": "api",
            "storage": "storage",
            "pages": "page",
            "jobs": "job",
            "configs": "config",
            "error-handling": "error-handling",
            "integration": "integration",
            "modules": "module",
        }
        
        for dir_name, doc_type in type_mapping.items():
            if dir_name in parts:
                return doc_type
        
        return "unknown"
    
    def get_storage_type(self, file_path: Path) -> str:
        """
        判断存储文档的子类型
        
        Args:
            file_path: 文档路径
            
        Returns:
            存储类型：database/redis/mq/elasticsearch/oss/unknown
        """
        if self.get_doc_type(file_path) != "storage":
            return "unknown"
        
        filename = file_path.stem.lower()
        
        if filename.startswith("db-"):
            return "database"
        elif filename.startswith("redis-"):
            return "redis"
        elif filename.startswith("mq-"):
            return "mq"
        elif filename.startswith("es-"):
            return "elasticsearch"
        elif filename.startswith("oss-"):
            return "oss"
        else:
            return "unknown"
