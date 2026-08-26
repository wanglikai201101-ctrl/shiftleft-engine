"""需求分解器：解析需求文档，提取关联关系，生成文档骨架。

RequirementDecomposer 是需求驱动架构的核心入口组件。
它从需求文档（REQ-xxx.md）出发，解析关联关系表，
为每个关联文档调用 SkeletonGenerator 生成文档骨架。
"""

from pathlib import Path
from typing import List

from packages.core.models.doc_types import AssociatedDoc, DecomposeResult
from packages.core.requirement_decomposer.relation_parser import RelationParser
from packages.core.skeleton_generator.generator import SkeletonGenerator


class RequirementDecomposer:
    """需求分解器

    从需求文档出发，解析关联关系，生成文档骨架。

    Args:
        knowledge_base_path: 模块文档根目录（如 "modules"）
        skills_path: Skill 规范目录（如 "skills"）
    """

    def __init__(self, knowledge_base_path: str = "modules",
                 skills_path: str = "skills"):
        self.knowledge_base_path = Path(knowledge_base_path)
        self.skills_path = Path(skills_path)
        self._parser = RelationParser()
        self._skeleton_generator = SkeletonGenerator(
            knowledge_base_path=knowledge_base_path,
            skills_path=skills_path,
        )

    def decompose(self, requirement_doc_path: str) -> DecomposeResult:
        """解析需求文档，提取关联关系，生成文档骨架。

        1. 读取并解析需求文档
        2. 提取关联接口/数据库/页面/任务表
        3. 提取 REQ-xxx 和 TP-xxx 编号
        4. 检查引用的文档路径是否存在
        5. 为每个关联文档调用 SkeletonGenerator（待 Task 3 接入）

        Args:
            requirement_doc_path: 需求文档路径

        Returns:
            DecomposeResult 包含关联文档列表、生成的骨架路径和警告
        """
        doc_path = Path(requirement_doc_path)

        # Check document exists
        if not doc_path.exists():
            return DecomposeResult(
                success=False,
                requirement_id="",
                message=f"文档不存在: {requirement_doc_path}",
            )

        # Read document content
        try:
            content = doc_path.read_text(encoding="utf-8")
        except Exception as e:
            return DecomposeResult(
                success=False,
                requirement_id="",
                message=f"无法读取文档: {e}",
            )

        # Parse associations
        requirement_id = self._parser.extract_requirement_id(content)
        associated_docs = self._parser.parse(content)

        if not associated_docs:
            return DecomposeResult(
                success=True,
                requirement_id=requirement_id,
                associated_docs=[],
                message="需求文档无关联表",
            )

        # Check for missing referenced documents
        warnings = self._check_missing_references(associated_docs, doc_path.parent)

        # Generate skeletons for each associated document
        generated_skeletons: List[str] = []
        module = self._resolve_module(doc_path)
        for assoc in associated_docs:
            result = self._skeleton_generator.generate(
                doc_type=assoc.doc_type,
                identifier=self._derive_identifier(assoc),
                module=module,
                requirement_id=requirement_id,
                test_point_ids=assoc.test_point_ids,
            )
            if result.success:
                generated_skeletons.append(result.doc_path)

        return DecomposeResult(
            success=True,
            requirement_id=requirement_id,
            associated_docs=associated_docs,
            generated_skeletons=generated_skeletons,
            warnings=warnings,
            message=f"解析完成: {len(associated_docs)} 个关联文档",
        )

    def parse_associations(self, requirement_doc_path: str) -> List[AssociatedDoc]:
        """仅解析关联关系，不生成骨架。

        Args:
            requirement_doc_path: 需求文档路径

        Returns:
            关联文档列表
        """
        doc_path = Path(requirement_doc_path)
        if not doc_path.exists():
            return []

        try:
            content = doc_path.read_text(encoding="utf-8")
        except Exception:
            return []

        return self._parser.parse(content)

    def _check_missing_references(
        self,
        associated_docs: List[AssociatedDoc],
        requirement_dir: Path,
    ) -> List[str]:
        """Check if referenced document paths exist on the filesystem.

        Args:
            associated_docs: parsed association list
            requirement_dir: directory containing the requirement document

        Returns:
            list of warning messages for missing paths
        """
        warnings: List[str] = []
        for assoc in associated_docs:
            if not assoc.doc_path:
                continue
            # Resolve relative to the requirement document's directory
            resolved = requirement_dir / assoc.doc_path
            if not resolved.exists():
                warnings.append(f"文档不存在: {assoc.doc_path}")
        return warnings

    def _resolve_module(self, doc_path: Path) -> str:
        """Resolve the module name from the requirement document path.

        Expects paths like modules/{module}/requirements/REQ-xxx.md
        """
        # Walk up from the requirement doc to find the module directory
        # The module dir is the parent of 'requirements/'
        parts = doc_path.resolve().parts
        for i, part in enumerate(parts):
            if part == "requirements" and i > 0:
                return parts[i - 1]
        # Fallback: use the grandparent directory name
        if len(doc_path.parts) >= 3:
            return doc_path.parts[-3]
        return "unknown"

    def _derive_identifier(self, assoc: AssociatedDoc) -> str:
        """Derive a file-safe identifier from an AssociatedDoc.

        If doc_path is available, use the stem of the path.
        Otherwise, sanitize the identifier string.
        """
        if assoc.doc_path:
            return Path(assoc.doc_path).stem
        # Sanitize identifier for use as filename
        ident = assoc.identifier
        # Replace spaces and slashes
        ident = ident.replace(" ", "-").replace("/", "-")
        # Remove leading/trailing dashes
        ident = ident.strip("-")
        return ident if ident else "unknown"
