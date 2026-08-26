"""
Core — 与框架无关的纯业务逻辑层（需求驱动架构）

核心组件（需求驱动工作流）：
- RequirementDecomposer: 需求分解器
- SkeletonGenerator: 文档骨架生成器
- DetailFiller: 技术细节填充器
- TraceabilityQuery: 追溯链查询引擎

基础组件（保留）：
- DocumentScanner / DocumentParser / DocumentIndexer / DocumentQuery: 文档索引
- ApiDocGenerator: 文档生成器（旧流程兼容）
- DocLinter: 一致性检查器
"""

# New requirement-driven components
from .requirement_decomposer.decomposer import RequirementDecomposer
from .skeleton_generator.generator import SkeletonGenerator
from .detail_filler.filler import DetailFiller
from .indexing.traceability import TraceabilityQuery

# Existing components (preserved for backward compatibility)
from .indexing.scanner import DocumentScanner
from .indexing.parser import DocumentParser
from .indexing.indexer import DocumentIndexer
from .indexing.query import DocumentQuery
from .generators.api_doc import ApiDocGenerator
from .validators.linter import DocLinter

__all__ = [
    # New (requirement-driven)
    "RequirementDecomposer",
    "SkeletonGenerator",
    "DetailFiller",
    "TraceabilityQuery",
    # Existing (preserved)
    "DocumentScanner",
    "DocumentParser",
    "DocumentIndexer",
    "DocumentQuery",
    "ApiDocGenerator",
    "DocLinter",
]
