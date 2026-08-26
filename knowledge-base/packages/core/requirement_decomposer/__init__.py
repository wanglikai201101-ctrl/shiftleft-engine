"""需求分解器：解析需求文档的关联关系，推导文档骨架"""

from .relation_parser import RelationParser
from .decomposer import RequirementDecomposer

__all__ = ["RelationParser", "RequirementDecomposer"]
