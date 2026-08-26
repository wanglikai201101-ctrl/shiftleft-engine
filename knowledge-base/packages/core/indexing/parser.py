"""文档解析器：提取文档的关联关系"""

import re
from pathlib import Path
from typing import Dict, List


class DocumentParser:
    """文档解析器"""

    def parse(self, file_path: Path) -> Dict:
        """解析单个文档，提取关联关系"""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
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
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _extract_module(self, content: str, file_path: Path) -> str:
        if "modules" in file_path.parts:
            try:
                idx = file_path.parts.index("modules")
                if idx + 1 < len(file_path.parts):
                    return file_path.parts[idx + 1]
            except (ValueError, IndexError):
                pass
        for pattern in (r"模块[:：]\s*(\S+)", r"Module:\s*(\S+)"):
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "unknown"

    def _extract_related(self, content: str, doc_type: str) -> List[str]:
        """提取关联文档路径"""
        related = []
        keywords = {
            "requirement": ["需求", "requirement"],
            "api": ["接口", "API", "api"],
            "storage": ["存储", "数据库", "storage", "database", "表", "Redis", "redis", "缓存"],
            "page": ["页面", "page"],
            "config": ["配置", "config"],
            "job": ["任务", "定时任务", "job"],
        }
        for keyword in keywords.get(doc_type, []):
            pattern = rf"\|\s*关联.*?{keyword}.*?\s*\|\s*([^\s\|]+\.md)\s*\|"
            related.extend(m.strip() for m in re.findall(pattern, content, re.IGNORECASE))

        dir_names = {
            "requirement": "requirements?", "api": "apis?", "storage": "storage",
            "page": "pages?", "config": "configs?", "job": "jobs?",
        }
        dir_pattern = dir_names.get(doc_type, doc_type)
        pattern = rf"\[([^\]]+)\]\(({dir_pattern}/[^\)]+\.md)\)"
        related.extend(m[1].strip() for m in re.findall(pattern, content, re.IGNORECASE))
        return list(set(related))

    def _extract_module_link(self, content: str) -> str:
        match = re.search(r"modules/([^/\s]+)/MODULE\.md", content, re.IGNORECASE)
        return match.group(0) if match else ""

    def extract_module_index(self, content: str) -> Dict[str, List[str]]:
        """从 MODULE.md 提取文档索引"""
        index = {
            "all_requirements": [], "all_apis": [], "all_storage": [],
            "all_pages": [], "all_jobs": [], "all_configs": [],
        }
        for key, prefix in [
            ("all_requirements", "requirements?"), ("all_apis", "apis?"),
            ("all_storage", "storage"), ("all_pages", "pages?"),
            ("all_jobs", "jobs?"), ("all_configs", "configs?"),
        ]:
            pattern = rf"\|\s*[^\|]+\s*\|\s*[^\|]+\s*\|\s*({prefix}/[^\|]+\.md)\s*\|"
            index[key] = [m.strip() for m in re.findall(pattern, content, re.IGNORECASE)]
        return index
