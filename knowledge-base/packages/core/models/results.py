"""工具执行结果的数据模型"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


class Severity(str, Enum):
    """问题严重程度"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @property
    def icon(self) -> str:
        return {"error": "❌", "warning": "⚠️ ", "info": "ℹ️ "}[self.value]


@dataclass
class LintIssue:
    """单个检查问题"""
    severity: Severity
    doc_path: str
    message: str
    line_number: Optional[int] = None

    def __str__(self) -> str:
        loc = f":{self.line_number}" if self.line_number else ""
        return f"{self.severity.icon} {self.doc_path}{loc}: {self.message}"


@dataclass
class LintReport:
    """检查报告"""
    issues: Dict[str, List[LintIssue]] = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return sum(
            1 for doc_issues in self.issues.values()
            for issue in doc_issues
            if issue.severity == Severity.ERROR
        )

    @property
    def warning_count(self) -> int:
        return sum(
            1 for doc_issues in self.issues.values()
            for issue in doc_issues
            if issue.severity == Severity.WARNING
        )

    @property
    def passed(self) -> bool:
        return self.error_count == 0


@dataclass
class GenerateResult:
    """文档生成结果"""
    success: bool
    message: str
    doc_path: Optional[str] = None
    doc_content: Optional[str] = None
    pre_filled_fields: Dict = field(default_factory=dict)


@dataclass
class FillResult:
    """技术细节填充结果"""
    success: bool
    doc_path: str = ""
    filled_fields: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    preserved_fields: List[str] = field(default_factory=list)
    message: str = ""


@dataclass
class BatchResult:
    """Batch operation outcome."""
    operation_type: str
    total_scanned: int = 0
    total_success: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    details: List[Dict[str, Any]] = field(default_factory=list)
    lint_report: Optional['LintReport'] = None


@dataclass
class TraceResult:
    """追溯链查询结果"""
    source: str
    requirement_sources: List[str] = field(default_factory=list)
    test_points: List[str] = field(default_factory=list)
    downstream_apis: List[str] = field(default_factory=list)
    downstream_storage: List[str] = field(default_factory=list)
    downstream_pages: List[str] = field(default_factory=list)
    downstream_jobs: List[str] = field(default_factory=list)
    broken_links: List[str] = field(default_factory=list)
