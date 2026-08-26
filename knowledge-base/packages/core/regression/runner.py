"""RegressionRunner: 协调测试选择和执行"""

import json
import subprocess
from pathlib import Path
from typing import List, Optional, Set

from packages.core.graph.store import Graph, GraphStore
from .models import TestPlan, TestFile, TestResult, RegressionReport
from .diff_mapper import DiffNodeMapper
from .decision import TestDecisionEngine

# File extensions considered testable (source code)
TESTABLE_EXTENSIONS: Set[str] = {
    '.py', '.js', '.ts', '.vue', '.jsx', '.tsx', '.go', '.java', '.rs',
}

# File patterns that are never testable
NON_TESTABLE_PATTERNS: Set[str] = {
    'readme', 'changelog', 'license', '.gitignore', '.env',
}


def is_testable_file(file_path: str) -> bool:
    """判断文件是否具备测试价值（源码变更 vs 纯文档变更）"""
    p = Path(file_path)
    name_lower = p.name.lower()

    # Always non-testable
    if any(pat in name_lower for pat in NON_TESTABLE_PATTERNS):
        return False

    # Source code → testable
    if p.suffix.lower() in TESTABLE_EXTENSIONS:
        return True

    # KB docs with apis/pages/storage path → potentially testable (contract may have changed)
    if p.suffix.lower() == '.md':
        path_lower = file_path.lower().replace("\\", "/")
        if '/apis/' in path_lower or '/pages/' in path_lower or '/storage/' in path_lower:
            return True

    return False


def filter_testable_files(files: List[str]) -> List[str]:
    """过滤出有测试价值的文件"""
    return [f for f in files if is_testable_file(f)]


class RegressionRunner:
    """回归分析协调器（影响分析 + 用例识别，执行交由外部端点）"""

    def __init__(self, module: str, kb_path: str = "modules", graph_dir: str = "graph"):
        self.module = module
        self.kb_path = Path(kb_path)
        self.graph_dir = Path(graph_dir)
        self.test_dir = self.kb_path / module / "tests"
        self._store = GraphStore(output_dir=str(self.graph_dir))
        self._graph = self._store.load()

    def analyze(self, changed_files: List[str]) -> RegressionReport:
        """分析变更并生成回归测试计划（不执行）"""
        report = RegressionReport(module=self.module, dry_run=True)
        report.changed_files = changed_files

        if not self._graph:
            return report

        # Filter to testable files only
        testable = filter_testable_files(changed_files)
        if not testable:
            return report

        # Step 1: Map files to nodes
        mapper = DiffNodeMapper(self._graph, self.module, str(self.kb_path))
        mapped_nodes = mapper.map_files(testable)
        report.mapped_nodes = mapped_nodes

        if not mapped_nodes:
            return report

        # Step 2: Impact analysis (2-hop neighborhood via direct edge traversal)
        impact_nodes = set()
        for node_id in mapped_nodes:
            # 1-hop: direct neighbors
            for edge in self._graph.edges:
                if edge.from_id == node_id:
                    impact_nodes.add(edge.to_id)
                elif edge.to_id == node_id:
                    impact_nodes.add(edge.from_id)
        # 2-hop: neighbors of neighbors
        hop1 = set(impact_nodes)
        for nid in hop1:
            for edge in self._graph.edges:
                if edge.from_id == nid:
                    impact_nodes.add(edge.to_id)
                elif edge.to_id == nid:
                    impact_nodes.add(edge.from_id)
        impact_nodes -= set(mapped_nodes)
        report.impact_scope = list(impact_nodes)

        # Step 3: Decision engine
        engine = TestDecisionEngine(self._graph)
        plan = engine.decide(mapped_nodes, list(impact_nodes))
        report.test_plan = plan

        # Step 4: Find existing test files
        test_files = self._find_test_files(plan)
        skipped = self._find_uncovered_nodes(plan, test_files)
        report.skipped_no_tests = skipped

        return report

    def run(self, changed_files: List[str], dry_run: bool = True) -> RegressionReport:
        """完整执行: 分析 + 执行测试"""
        report = self.analyze(changed_files)
        report.dry_run = dry_run

        if dry_run or not report.test_plan or report.test_plan.is_empty:
            return report

        # Execute tests
        test_files = self._find_test_files(report.test_plan)
        for tf in test_files:
            result = self._execute_test(tf)
            if result:
                report.executed.append(result)

        return report

    def _find_test_files(self, plan: TestPlan) -> List[TestFile]:
        """从 tests/ 目录找到覆盖 scope 的已有测试文件"""
        files = []

        if not self.test_dir.exists():
            return files

        # Load TEST-INDEX.json if available
        index_path = self.test_dir / "TEST-INDEX.json"
        index = None
        if index_path.exists():
            try:
                index = json.loads(index_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        # API tests
        if "api" in plan.types:
            api_dir = self.test_dir / "api"
            if api_dir.exists():
                for f in api_dir.glob("*.json"):
                    test_data = self._safe_read_json(f)
                    if test_data:
                        covers = self._extract_covered_nodes(test_data, plan.api_scope)
                        if covers:
                            files.append(TestFile(
                                path=str(f),
                                test_type="api",
                                covers_nodes=covers,
                            ))

        # E2E tests
        if "e2e" in plan.types:
            e2e_dir = self.test_dir / "e2e"
            if e2e_dir.exists():
                for f in e2e_dir.glob("*.json"):
                    files.append(TestFile(path=str(f), test_type="e2e"))

        # UI tests
        if "ui" in plan.types:
            ui_dir = self.test_dir / "ui"
            if ui_dir.exists():
                for f in ui_dir.glob("*.json"):
                    files.append(TestFile(path=str(f), test_type="ui"))

        return files

    def _extract_covered_nodes(self, test_data: dict, scope: List[str]) -> List[str]:
        """检查测试文件是否覆盖 scope 中的节点"""
        covers = []
        # Heuristic: check if test steps' URLs match API paths in scope
        steps = test_data.get("steps", [])
        for step in steps:
            req = step.get("request", {})
            url = req.get("url", "")
            for node_id in scope:
                # Extract API path hint from node ID: sandbox:api:POST-build-agent → "build-agent"
                parts = node_id.split(":")
                if len(parts) >= 3:
                    slug = parts[2]  # e.g. POST-build-agent
                    # Remove method prefix
                    slug_no_method = slug.split("-", 1)[1] if "-" in slug else slug
                    if slug_no_method and slug_no_method in url:
                        covers.append(node_id)
        return list(set(covers))

    def _find_uncovered_nodes(self, plan: TestPlan, test_files: List[TestFile]) -> List[str]:
        """找到 scope 中没有测试覆盖的节点"""
        covered = set()
        for tf in test_files:
            covered.update(tf.covers_nodes)

        all_scope = set(plan.api_scope + plan.page_scope + plan.storage_scope)
        return [n for n in all_scope if n not in covered]

    def _execute_test(self, test_file: TestFile) -> Optional[TestResult]:
        """执行单个测试文件（返回结构化结果）"""
        test_data = self._safe_read_json(Path(test_file.path))
        if not test_data:
            return TestResult(
                test_type=test_file.test_type,
                name=Path(test_file.path).stem,
                passed=False,
                details="Failed to read test file",
            )

        # Actual test dispatch is delegated to the project's configured QA
        # execution endpoint (see ENV-CONFIG). This module only plans the
        # regression scope; it never dispatches test runs itself.
        return TestResult(
            test_type=test_file.test_type,
            name=Path(test_file.path).stem,
            passed=True,
            details=f"Planned for configured executor: {test_file.test_type}",
        )

    @staticmethod
    def _safe_read_json(path: Path) -> Optional[dict]:
        """安全读取 JSON 文件"""
        try:
            if not path.exists():
                return None
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None


def get_git_diff_files(since: str = "HEAD~1", cwd: Optional[str] = None) -> List[str]:
    """获取 git diff 的变更文件列表"""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", since],
            capture_output=True, text=True, cwd=cwd,
        )
        if result.returncode != 0:
            return []
        return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except (OSError, subprocess.SubprocessError):
        return []
