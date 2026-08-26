"""Skill 模板加载器：从 SKILL.md 文件中提取各文档类型的必填章节。

SkillLoader 读取 skills/ 目录下的 SKILL.md 文件，解析"文档结构（必填章节）"
部分中的 Markdown 代码块，提取章节标题列表。
"""

import re
from pathlib import Path
from typing import Dict, List

from packages.core.models.doc_types import DocType


# DocType → Skill 目录名映射
DOC_TYPE_TO_SKILL: Dict[DocType, str] = {
    DocType.API: "engineering-doc-api",
    DocType.STORAGE: "engineering-doc-storage",
    DocType.PAGE: "engineering-doc-page",
    DocType.JOB: "engineering-doc-job",
}

# 当 Skill 文件缺失时使用的默认章节
DEFAULT_SECTIONS: Dict[DocType, List[str]] = {
    DocType.API: [
        "基本信息", "请求参数", "响应结构", "依赖接口", "被依赖接口",
        "关联数据库", "关联定时任务", "关联前端页面", "错误码", "变更记录",
    ],
    DocType.STORAGE: [
        "基本信息", "字段定义", "索引设计", "关联接口", "关联定时任务",
        "关联表", "关联其他存储", "变更记录",
    ],
    DocType.PAGE: [
        "基本信息", "页面元素清单", "接口调用顺序", "数据流转", "变更记录",
    ],
    DocType.JOB: [
        "基本信息", "数据流转", "触发与取消条件", "关联数据库",
        "关联接口", "监控", "变更记录",
    ],
}


class SkillLoader:
    """从 SKILL.md 文件加载文档类型的必填章节列表。

    Args:
        skills_path: Skill 规范目录路径（如 "skills"）
    """

    def __init__(self, skills_path: str = "skills"):
        self.skills_path = Path(skills_path)
        self._cache: Dict[DocType, List[str]] = {}

    def load_sections(self, doc_type: DocType) -> List[str]:
        """加载指定文档类型的必填章节列表。

        优先从 SKILL.md 的"文档结构（必填章节）"代码块中提取，
        如果 Skill 文件不存在则返回默认模板。

        Args:
            doc_type: 文档类型

        Returns:
            章节标题列表
        """
        if doc_type in self._cache:
            return self._cache[doc_type]

        skill_name = DOC_TYPE_TO_SKILL.get(doc_type)
        if not skill_name:
            return DEFAULT_SECTIONS.get(doc_type, ["基本信息", "变更记录"])

        skill_path = self.skills_path / skill_name / "SKILL.md"
        if not skill_path.exists():
            sections = DEFAULT_SECTIONS.get(doc_type, ["基本信息", "变更记录"])
            self._cache[doc_type] = sections
            return sections

        try:
            content = skill_path.read_text(encoding="utf-8")
            sections = self._extract_sections_from_skill(content, doc_type)
            if not sections:
                sections = DEFAULT_SECTIONS.get(doc_type, ["基本信息", "变更记录"])
            # Ensure "变更记录" is always present (every doc type needs it)
            if "变更记录" not in sections:
                sections.append("变更记录")
            self._cache[doc_type] = sections
            return sections
        except Exception:
            sections = DEFAULT_SECTIONS.get(doc_type, ["基本信息", "变更记录"])
            self._cache[doc_type] = sections
            return sections

    def _extract_sections_from_skill(
        self, content: str, doc_type: DocType
    ) -> List[str]:
        """从 SKILL.md 内容中提取必填章节。

        查找"文档结构（必填章节）"标题下的第一个 Markdown 代码块，
        从中提取 ## 级别的章节标题。

        Args:
            content: SKILL.md 文件内容
            doc_type: 文档类型（用于选择正确的代码块）

        Returns:
            章节标题列表
        """
        # Find the "文档结构（必填章节）" section
        section_match = re.search(
            r"^#{2,4}\s*文档结构（必填章节）",
            content,
            re.MULTILINE,
        )
        if not section_match:
            return []

        # Get content after the section header
        after_header = content[section_match.end():]

        # Find the first markdown code block (```markdown ... ```)
        code_block_match = re.search(
            r"```(?:markdown)?\s*\n(.*?)```",
            after_header,
            re.DOTALL,
        )
        if not code_block_match:
            return []

        code_block = code_block_match.group(1)

        # Extract ## section headers from the code block
        sections: List[str] = []
        for line in code_block.split("\n"):
            stripped = line.strip()
            # Match ## headers (level 2 within the template)
            header_match = re.match(r"^##\s+(.+)", stripped)
            if header_match:
                section_name = header_match.group(1).strip()
                # Clean up: remove formatting markers like （🔒 强制）
                section_name = re.sub(r"[（(][^）)]*[）)]$", "", section_name).strip()
                if section_name:
                    sections.append(section_name)

        return sections
