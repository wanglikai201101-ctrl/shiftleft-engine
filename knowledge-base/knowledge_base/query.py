"""索引查询器：供用例生成 SubAgent 使用"""

import json
from pathlib import Path
from typing import Dict, List, Set, Optional


class DocumentQuery:
    """文档索引查询器"""
    
    def __init__(self, index_path: str = "docs-index.json"):
        """
        初始化查询器
        
        Args:
            index_path: 索引文件路径，默认为 "docs-index.json"
        """
        index_file = Path(index_path)
        if not index_file.exists():
            raise FileNotFoundError(f"索引文件不存在: {index_path}")
        
        self.index = json.loads(index_file.read_text(encoding="utf-8"))
        self.documents = self.index.get("documents", {})
    
    def find_related_docs(self, doc_path: str, max_depth: int = 2) -> List[str]:
        """
        查找与指定文档相关的所有文档（递归）
        
        Args:
            doc_path: 文档路径（相对于 knowledge-base/）
            max_depth: 最大递归深度，默认为 2
            
        Returns:
            相关文档路径列表
        """
        visited = set()
        result = []
        
        def _recursive_find(path: str, depth: int):
            if depth > max_depth or path in visited:
                return
            visited.add(path)
            
            doc_info = self.documents.get(path)
            if not doc_info:
                return
            
            # 收集所有关联文档
            related = []
            for key in ["related_requirements", "related_apis", "related_storage", 
                       "related_pages", "related_configs", "related_jobs"]:
                related.extend(doc_info.get(key, []))
            
            # 添加关联的模块文档
            if doc_info.get("related_module"):
                related.append(doc_info["related_module"])
            
            # 递归查找
            for related_path in related:
                if related_path not in visited:
                    result.append(related_path)
                    _recursive_find(related_path, depth + 1)
        
        _recursive_find(doc_path, 0)
        return result
    
    def find_by_module(self, module_name: str) -> List[str]:
        """
        查找指定模块的所有文档
        
        Args:
            module_name: 模块名（如 "logistics-order"）
            
        Returns:
            文档路径列表
        """
        result = []
        for doc_path, doc_info in self.documents.items():
            if doc_info.get("module") == module_name:
                result.append(doc_path)
        return result
    
    def find_by_type(self, doc_type: str) -> List[str]:
        """
        查找指定类型的所有文档
        
        Args:
            doc_type: 文档类型（requirement/api/storage/page/job/config/module）
            
        Returns:
            文档路径列表
        """
        result = []
        for doc_path, doc_info in self.documents.items():
            if doc_info.get("type") == doc_type:
                result.append(doc_path)
        return result
    
    def find_by_keyword(self, keyword: str, doc_type: Optional[str] = None) -> List[str]:
        """
        根据关键词查找文档（搜索标题和路径）
        
        Args:
            keyword: 关键词
            doc_type: 可选，限定文档类型
            
        Returns:
            文档路径列表
        """
        result = []
        keyword_lower = keyword.lower()
        
        for doc_path, doc_info in self.documents.items():
            # 如果指定了文档类型，先过滤
            if doc_type and doc_info.get("type") != doc_type:
                continue
            
            # 搜索标题和路径
            title = doc_info.get("title", "").lower()
            path_lower = doc_path.lower()
            
            if keyword_lower in title or keyword_lower in path_lower:
                result.append(doc_path)
        
        return result
    
    def get_module_docs(self, module_path: str) -> Dict[str, List[str]]:
        """
        从 MODULE.md 获取模块的所有文档
        
        Args:
            module_path: MODULE.md 的路径（如 "modules/logistics-order/MODULE.md"）
            
        Returns:
            文档分类字典，包含 requirements, apis, storage, pages, jobs, configs
        """
        doc_info = self.documents.get(module_path)
        if not doc_info or doc_info["type"] != "module":
            return {}
        
        return {
            "requirements": doc_info.get("all_requirements", []),
            "apis": doc_info.get("all_apis", []),
            "storage": doc_info.get("all_storage", []),
            "pages": doc_info.get("all_pages", []),
            "jobs": doc_info.get("all_jobs", []),
            "configs": doc_info.get("all_configs", [])
        }
    
    def get_doc_info(self, doc_path: str) -> Optional[Dict]:
        """
        获取文档的详细信息
        
        Args:
            doc_path: 文档路径
            
        Returns:
            文档信息字典，如果不存在则返回 None
        """
        return self.documents.get(doc_path)
    
    def get_statistics(self) -> Dict:
        """
        获取索引统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            "total": len(self.documents),
            "by_type": {},
            "by_module": {},
        }
        
        for doc_info in self.documents.values():
            # 按类型统计
            doc_type = doc_info.get("type", "unknown")
            stats["by_type"][doc_type] = stats["by_type"].get(doc_type, 0) + 1
            
            # 按模块统计
            module = doc_info.get("module", "unknown")
            stats["by_module"][module] = stats["by_module"].get(module, 0) + 1
        
        return stats
