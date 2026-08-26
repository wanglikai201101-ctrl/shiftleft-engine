"""回归测试数据模型"""

from dataclasses import dataclass, field
from typing import List, Set, Optional


@dataclass
class TestPlan:
    """测试计划：由 DecisionEngine 生成"""
    types: Set[str] = field(default_factory=set)  # 'api' | 'e2e' | 'ui'
    api_scope: List[str] = field(default_factory=list)
    page_scope: List[str] = field(default_factory=list)
    storage_scope: List[str] = field(default_factory=list)
    chains: List[List[str]] = field(default_factory=list)  # cross-layer paths

    @property
    def is_empty(self) -> bool:
        return not self.types


@dataclass
class TestFile:
    """可执行的测试文件"""
    path: str
    test_type: str  # 'api' | 'e2e' | 'ui'
    covers_nodes: List[str] = field(default_factory=list)


@dataclass
class TestResult:
    """单个回归用例的研判结果"""
    test_type: str
    name: str
    passed: bool
    details: Optional[str] = None
    duration_ms: int = 0


@dataclass
class RegressionReport:
    """回归测试完整报告"""
    module: str
    changed_files: List[str] = field(default_factory=list)
    mapped_nodes: List[str] = field(default_factory=list)
    impact_scope: List[str] = field(default_factory=list)
    test_plan: Optional[TestPlan] = None
    executed: List[TestResult] = field(default_factory=list)
    skipped_no_tests: List[str] = field(default_factory=list)
    dry_run: bool = False

    @property
    def total(self) -> int:
        return len(self.executed)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.executed if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.executed if not r.passed)

    @property
    def all_passed(self) -> bool:
        return self.total > 0 and self.failed == 0

    def summary(self) -> str:
        lines = [
            f"Module: {self.module}",
            f"Changed files: {len(self.changed_files)}",
            f"Mapped nodes: {len(self.mapped_nodes)}",
            f"Impact scope: {len(self.impact_scope)} nodes",
            f"Test plan: {', '.join(sorted(self.test_plan.types)) if self.test_plan else 'none'}",
        ]
        if self.dry_run:
            lines.append("Mode: DRY RUN (no execution)")
        else:
            lines.append(f"Results: {self.passed}/{self.total} passed, {self.failed} failed")
        if self.skipped_no_tests:
            lines.append(f"Missing test coverage: {len(self.skipped_no_tests)} nodes")
        return "\n".join(lines)
