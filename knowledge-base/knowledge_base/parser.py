"""文档解析器：提取文档的关联关系"""

import re
from pathlib import Path
from typing import Dict, List


class DocumentParser:
    """文档解析器"""
    
    def parse(self, file_path: Path) -> Dict:
        """
        解析单个文档，提取关联关系
        
        Args:
            file_path: 文档路径
            
        Returns:
            文档信息字典，包含 title, module, related_* 等字段
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"警告：无法读取文件 {file_path}: {e}")
            content = ""
        
        return {
            "title": self._extract_title(content),
            "module": self._extract_module(content, file_path),
            "related_requirements": self._extract_related(content, "requirement"),
            "related_apis": self._extract_related(content, "api"),
            "related_storage": self._extract_related(content, "storage"),
            "related_pages": self._extract_related(content, "page"),
            "related_configs": self._extract_related(content, "config"),
            "related_jobs": self._extract_related(content, "job"),
            "related_module": self._extract_module_link(content),
        }
    
    def _extract_title(self, content: str) -> str:
        """提取文档标题（第一个 # 标题）"""
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        return match.group(1).strip() if match else ""
    
    def _extract_module(self, content: str, file_path: Path) -> str:
        """提取模块名"""
        # 方式 1：从文件路径推导（如 modules/logistics-order/MODULE.md）
        if "modules" in file_path.parts:
            try:
                module_index = file_path.parts.index("modules")
                if module_index + 1 < len(file_path.parts):
                    return file_path.parts[module_index + 1]
            except (ValueError, IndexError):
                pass
        
        # 方式 2：从文档内容提取（如 "模块：logistics-order"）
        match = re.search(r"模块[:：]\s*(\S+)", content)
        if match:
            return match.group(1).strip()
        
        # 方式 3：从文档内容提取（如 "Module: logistics-order"）
        match = re.search(r"Module:\s*(\S+)", content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return "unknown"
    
    def _extract_related(self, content: str, doc_type: str) -> List[str]:
        """
        提取关联文档路径
        
        Args:
            content: 文档内容
            doc_type: 文档类型（requirement/api/storage/page/config/job）
            
        Returns:
            关联文档路径列表
        """
        related = []
        
        # 匹配表格中的路径（如 | 关联接口 | apis/POST-create-order.md |）
        # 支持多种表达：关联接口、关联API、关联存储、关联页面、关联配置、关联任务
        keywords = {
            "requirement": ["需求", "requirement"],
            "api": ["接口", "API", "api"],
            "storage": ["存储", "数据库", "storage", "database", "表", "Redis", "redis", "缓存"],
            "page": ["页面", "page"],
            "config": ["配置", "config"],
            "job": ["任务", "定时任务", "job"],
        }

        for keyword in keywords.get(doc_type, []):
            # 表格格式：| 关联XXX | path/to/file.md |
            # 使用更宽松的匹配，避免 [^\|]* 导致的贪婪匹配问题
            pattern = rf"\|\s*关联.*?{keyword}.*?\s*\|\s*([^\s\|]+\.md)\s*\|"
            matches = re.findall(pattern, content, re.IGNORECASE)
            related.extend([m.strip() for m in matches])
        
        # 匹配 Markdown 链接（如 [POST-create-order](apis/POST-create-order.md)）
        # 根据文档类型匹配对应的目录
        dir_names = {
            "requirement": "requirements?",
            "api": "apis?",
            "storage": "storage",
            "page": "pages?",
            "config": "configs?",
            "job": "jobs?",
        }
        
        dir_pattern = dir_names.get(doc_type, doc_type)
        pattern = rf"\[([^\]]+)\]\(({dir_pattern}/[^\)]+\.md)\)"
        matches = re.findall(pattern, content, re.IGNORECASE)
        related.extend([m[1].strip() for m in matches])
        
        return list(set(related))  # 去重
    
    def _extract_module_link(self, content: str) -> str:
        """提取关联的 MODULE.md"""
        match = re.search(r"modules/([^/\s]+)/MODULE\.md", content, re.IGNORECASE)
        return match.group(0) if match else ""
    
    def extract_module_index(self, content: str) -> Dict[str, List[str]]:
        """
        从 MODULE.md 提取文档索引
        
        Args:
            content: MODULE.md 的内容
            
        Returns:
            文档索引字典，包含 all_requirements, all_apis, all_storage 等
        """
        index = {
            "all_requirements": [],
            "all_apis": [],
            "all_storage": [],
            "all_pages": [],
            "all_jobs": [],
            "all_configs": [],
        }
        
        # 提取文档索引表格中的路径
        # 匹配格式：| REQ-001 | 订单创建 | requirements/REQ-001-order-create.md |
        for key, pattern_prefix in [
            ("all_requirements", "requirements?"),
            ("all_apis", "apis?"),
            ("all_storage", "storage"),
            ("all_pages", "pages?"),
            ("all_jobs", "jobs?"),
            ("all_configs", "configs?"),
        ]:
            pattern = rf"\|\s*[^\|]+\s*\|\s*[^\|]+\s*\|\s*({pattern_prefix}/[^\|]+\.md)\s*\|"
            matches = re.findall(pattern, content, re.IGNORECASE)
            index[key] = [m.strip() for m in matches]
        
        return index
