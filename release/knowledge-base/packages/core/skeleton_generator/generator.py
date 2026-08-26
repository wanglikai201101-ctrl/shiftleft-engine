"""骨架生成器：根据文档类型和 Skill 规范生成文档骨架。

SkeletonGenerator 读取 Skill 定义的必填章节，结合需求编号和测试点，
生成带有"待补充"占位符的 Markdown 文档骨架。
"""

from pathlib import Path
from typing import Dict, List, Optional

from packages.core.models.doc_types import DocType, SkeletonResult
from packages.core.skeleton_generator.skill_loader import SkillLoader


# DocType → 文档存放子目录
DOC_TYPE_DIR: Dict[DocType, str] = {
    DocType.API: "apis",
    DocType.STORAGE: "storage",
    DocType.PAGE: "pages",
    DocType.JOB: "jobs",
}

# 各章节的默认表格/内容模板
SECTION_TEMPLATES: Dict[str, str] = {
    "基本信息": (
        "| 字段 | 值 |\n"
        "|------|-----|\n"
        "| 模块 | {module} |\n"
        "| 负责人 | 待补充 |\n"
        "| 需求来源 | {requirement_id} |\n"
        "| 版本 | v1.0 |"
    ),
    "请求参数": (
        "| 参数 | 类型 | 必填 | 来源 | 说明 |\n"
        "|------|------|------|------|------|\n"
        "| 待补充 | 待补充 | 待补充 | 待补充 | 待补充 |"
    ),
    "响应结构": (
        "| 字段 | 类型 | 流向 | 说明 |\n"
        "|------|------|------|------|\n"
        "| 待补充 | 待补充 | 待补充 | 待补充 |"
    ),
    "依赖接口": (
        "| 接口 | 传递的字段 | 关系 |\n"
        "|------|----------|------|\n"
        "| 待补充 | 待补充 | 待补充 |"
    ),
    "被依赖接口": (
        "| 接口 | 消费的字段 | 关系 |\n"
        "|------|----------|------|\n"
        "| 待补充 | 待补充 | 待补充 |"
    ),
    "关联数据库": (
        "| 表 | 操作 | 字段 | 业务规则 | 说明 |\n"
        "|-----|------|------|---------|------|\n"
        "| 待补充 | 待补充 | 待补充 | 待补充 | 待补充 |"
    ),
    "关联定时任务": (
        "| 任务 | 关系 | 触发条件 |\n"
        "|------|------|--------|\n"
        "| 待补充 | 待补充 | 待补充 |"
    ),
    "关联前端页面": (
        "| 页面 | 触发元素(data-testid) | 触发方式 |\n"
        "|------|----------------------|--------|\n"
        "| 待补充 | 待补充 | 待补充 |"
    ),
    "错误码": (
        "| 错误码 | 说明 | 前端处理 |\n"
        "|--------|------|--------|\n"
        "| 待补充 | 待补充 | 待补充 |"
    ),
    "变更记录": (
        "| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 影响范围 |\n"
        "|------|------|--------|--------|--------|--------|\n"
        "| v1.0 | 待补充 | 待补充 | 无（新建） | 创建文档骨架 | 待补充 |"
    ),
    "字段定义": (
        "| 字段 | 类型 | 索引 | 写入来源 | 读取去向 | 业务规则 | 说明 |\n"
        "|------|------|------|---------|---------|---------|------|\n"
        "| 待补充 | 待补充 | 待补充 | 待补充 | 待补充 | 待补充 | 待补充 |"
    ),
    "索引设计": (
        "| 索引名 | 类型 | 字段 | 说明 |\n"
        "|--------|------|------|------|\n"
        "| 待补充 | 待补充 | 待补充 | 待补充 |"
    ),
    "关联接口": (
        "| 接口 | 操作 | 涉及字段 |\n"
        "|------|------|--------|\n"
        "| 待补充 | 待补充 | 待补充 |"
    ),
    "关联表": (
        "| 表 | 关系 | 关联字段 | 数据流向 |\n"
        "|-----|------|---------|--------|\n"
        "| 待补充 | 待补充 | 待补充 | 待补充 |"
    ),
    "关联其他存储": (
        "| 存储节点 | 类型 | 关系 | 说明 |\n"
        "|---------|------|------|------|\n"
        "| 待补充 | 待补充 | 待补充 | 待补充 |"
    ),
    "页面元素清单": (
        "| data-testid | 元素类型 | 功能 | 触发接口 | 绑定字段 | 数据来源 |\n"
        "|-------------|---------|------|---------|---------|--------|\n"
        "| 待补充 | 待补充 | 待补充 | 待补充 | 待补充 | 待补充 |"
    ),
    "接口调用顺序": "待补充",
    "数据流转": "待补充",
    "触发与取消条件": (
        "| 条件 | 来源 | 说明 |\n"
        "|------|------|------|\n"
        "| 待补充 | 待补充 | 待补充 |"
    ),
    "监控": (
        "| 指标 | 阈值 | 告警方式 |\n"
        "|------|------|--------|\n"
        "| 待补充 | 待补充 | 待补充 |"
    ),
}


class SkeletonGenerator:
    """文档骨架生成器

    根据文档类型和 Skill 规范生成 Markdown 文档骨架，
    包含所有必填章节、需求编号、测试点和"待补充"占位符。

    Args:
        knowledge_base_path: 模块文档根目录（如 "modules"）
        skills_path: Skill 规范目录（如 "skills"）
    """

    def __init__(self, knowledge_base_path: str = "modules",
                 skills_path: str = "skills"):
        self.knowledge_base_path = Path(knowledge_base_path)
        self.skills_path = Path(skills_path)
        self._skill_loader = SkillLoader(skills_path)

    def generate(
        self,
        doc_type: DocType,
        identifier: str,
        module: str,
        requirement_id: str,
        test_point_ids: Optional[List[str]] = None,
    ) -> SkeletonResult:
        """根据文档类型和 Skill 规范生成文档骨架。

        1. 确定目标文件路径
        2. 如果文件已存在，跳过生成
        3. 加载对应 Skill 的必填章节
        4. 渲染骨架内容（填入 REQ/TP 编号 + 双向引用 + 待补充占位符）
        5. 写入文件

        Args:
            doc_type: 文档类型 (API/STORAGE/PAGE/JOB)
            identifier: 文档标识符 (如 POST-orders, db-t_order)
            module: 模块名 (如 logistics-order)
            requirement_id: 需求编号 (如 REQ-LO-001)
            test_point_ids: 关联测试点列表

        Returns:
            SkeletonResult
        """
        if test_point_ids is None:
            test_point_ids = []

        # Determine target file path
        doc_dir = DOC_TYPE_DIR.get(doc_type)
        if not doc_dir:
            return SkeletonResult(
                success=False,
                message=f"不支持的文档类型: {doc_type}",
            )

        target_path = self.knowledge_base_path / module / doc_dir / f"{identifier}.md"

        # Skip if file already exists
        if target_path.exists():
            return SkeletonResult(
                success=False,
                doc_path=str(target_path),
                message=f"文件已存在: {target_path}",
            )

        # Load mandatory sections from Skill
        sections = self._skill_loader.load_sections(doc_type)

        # Render skeleton content
        doc_content = self._render_skeleton(
            doc_type=doc_type,
            identifier=identifier,
            module=module,
            requirement_id=requirement_id,
            test_point_ids=test_point_ids,
            sections=sections,
        )

        # Write file
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(doc_content, encoding="utf-8")
        except Exception as e:
            return SkeletonResult(
                success=False,
                doc_path=str(target_path),
                doc_content=doc_content,
                sections=sections,
                message=f"无法写入: {e}",
            )

        return SkeletonResult(
            success=True,
            doc_path=str(target_path),
            doc_content=doc_content,
            sections=sections,
            message=f"骨架生成成功: {target_path}",
        )

    def _render_skeleton(
        self,
        doc_type: DocType,
        identifier: str,
        module: str,
        requirement_id: str,
        test_point_ids: List[str],
        sections: List[str],
    ) -> str:
        """渲染文档骨架 Markdown 内容。"""
        lines: List[str] = []

        # Title
        title = self._make_title(doc_type, identifier)
        lines.append(f"# {title}")
        lines.append("")

        # Bidirectional reference to requirement
        if requirement_id:
            lines.append(
                f"> 需求来源: [{requirement_id}]"
                f"(../requirements/{requirement_id}.md)"
            )
            lines.append("")

        # Test points reference
        if test_point_ids:
            tp_str = ", ".join(test_point_ids)
            lines.append(f"> 关联测试点: {tp_str}")
            lines.append("")

        # Render each section
        for section in sections:
            lines.append(f"## {section}")
            lines.append("")

            # Get section template content
            template = self._get_section_content(
                section, module, requirement_id, test_point_ids
            )
            lines.append(template)
            lines.append("")

        return "\n".join(lines)

    def _make_title(self, doc_type: DocType, identifier: str) -> str:
        """Generate the document title based on type and identifier."""
        if doc_type == DocType.API:
            # Convert identifier like "POST-orders" to "POST /orders"
            parts = identifier.split("-", 1)
            if len(parts) == 2:
                method = parts[0].upper()
                resource = parts[1]
                return f"{method} /{resource} — 待补充"
            return f"{identifier} — 待补充"
        elif doc_type == DocType.STORAGE:
            return f"{identifier} — 待补充"
        elif doc_type == DocType.PAGE:
            return f"{identifier} — 待补充"
        elif doc_type == DocType.JOB:
            return f"{identifier} — 待补充"
        return f"{identifier} — 待补充"

    def _get_section_content(
        self,
        section: str,
        module: str,
        requirement_id: str,
        test_point_ids: List[str],
    ) -> str:
        """Get the template content for a section, with placeholders filled."""
        if section == "基本信息":
            template = SECTION_TEMPLATES["基本信息"]
            return template.format(
                module=module,
                requirement_id=requirement_id,
            )

        if section in SECTION_TEMPLATES:
            return SECTION_TEMPLATES[section]

        # Fallback for unknown sections
        return "待补充"
