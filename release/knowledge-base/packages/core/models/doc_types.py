"""文档类型与代码解析结果的数据模型"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional


class DocType(str, Enum):
    """文档类型"""
    REQUIREMENT = "requirement"
    API = "api"
    STORAGE = "storage"
    PAGE = "page"
    JOB = "job"
    CONFIG = "config"
    ERROR_HANDLING = "error-handling"
    INTEGRATION = "integration"
    MODULE = "module"
    UNKNOWN = "unknown"


class StorageType(str, Enum):
    """存储文档子类型"""
    DATABASE = "database"
    REDIS = "redis"
    MQ = "mq"
    ELASTICSEARCH = "elasticsearch"
    OSS = "oss"
    UNKNOWN = "unknown"


@dataclass
class ApiField:
    """接口参数/响应字段"""
    name: str
    type: str = "string"
    required: bool = True
    description: str = ""
    source: str = ""


@dataclass
class ExtractedApiInfo:
    """从代码中提取的接口信息"""
    path: str
    method: str
    description: str
    function_name: str
    request_params: List[ApiField] = field(default_factory=list)
    response_fields: List[ApiField] = field(default_factory=list)


@dataclass
class AssociatedDoc:
    """从需求文档解析出的关联文档信息"""
    doc_type: DocType
    identifier: str
    test_point_ids: List[str] = field(default_factory=list)
    doc_path: str = ""
    requirement_id: str = ""


@dataclass
class DecomposeResult:
    """需求分解结果"""
    success: bool
    requirement_id: str
    associated_docs: List[AssociatedDoc] = field(default_factory=list)
    generated_skeletons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    message: str = ""


@dataclass
class SkeletonResult:
    """骨架生成结果"""
    success: bool
    doc_path: str = ""
    doc_content: str = ""
    sections: List[str] = field(default_factory=list)
    message: str = ""


# --- Phase 2 data models ---


@dataclass
class StorageField:
    """A column extracted from a CREATE TABLE statement."""
    name: str
    type: str
    constraints: List[str] = field(default_factory=list)
    is_primary_key: bool = False


@dataclass
class IndexInfo:
    """An index extracted from DDL."""
    index_name: str
    index_type: str  # "PRIMARY", "UNIQUE", "INDEX"
    columns: List[str] = field(default_factory=list)


@dataclass
class ExtractedStorageInfo:
    """DDL parser output for a single table."""
    table_name: str
    columns: List[StorageField] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)


@dataclass
class PageElement:
    """A data-testid element extracted from a Vue component."""
    testid: str
    element_type: str  # "button", "input", "el-table", etc.
    is_dynamic: bool = False


@dataclass
class ExtractedPageInfo:
    """Vue parser output."""
    component_name: str = ""
    elements: List[PageElement] = field(default_factory=list)
