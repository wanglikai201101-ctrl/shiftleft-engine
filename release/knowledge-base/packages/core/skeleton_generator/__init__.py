"""骨架生成器：根据 Skill 规范和需求关联关系生成文档骨架"""

from .skill_loader import SkillLoader
from .generator import SkeletonGenerator

__all__ = ["SkillLoader", "SkeletonGenerator"]
