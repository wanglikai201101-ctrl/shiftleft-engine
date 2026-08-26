"""测试结果反馈：将执行结果写回图谱节点，生成 risk-scores.json"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import RegressionReport, TestResult


class RiskScorer:
    """将测试结果反馈到图谱节点，维护历史风险评分"""

    def __init__(self, graph_dir: str = "graph"):
        self.graph_dir = Path(graph_dir)
        self.scores_path = self.graph_dir / "risk-scores.json"
        self._scores = self._load()

    def _load(self) -> dict:
        """加载已有的风险评分数据"""
        if self.scores_path.exists():
            try:
                return json.loads(self.scores_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"version": "1.0", "updated_at": "", "nodes": {}}

    def save(self):
        """持久化风险评分"""
        self._scores["updated_at"] = datetime.now().isoformat()
        self.graph_dir.mkdir(parents=True, exist_ok=True)
        self.scores_path.write_text(
            json.dumps(self._scores, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def record_results(self, report: RegressionReport):
        """从回归报告中提取结果，更新节点的风险评分"""
        timestamp = datetime.now().isoformat()

        for result in report.executed:
            node_ids = self._resolve_node_ids(result, report)
            for node_id in node_ids:
                self._update_node_score(node_id, result, timestamp)

        self.save()

    def _update_node_score(self, node_id: str, result: TestResult, timestamp: str):
        """更新单个节点的风险评分"""
        nodes = self._scores.setdefault("nodes", {})
        entry = nodes.get(node_id, {
            "total_runs": 0,
            "fail_count": 0,
            "pass_count": 0,
            "last_run": "",
            "last_fail": "",
            "risk_score": 0.0,
            "history": [],
        })

        entry["total_runs"] += 1
        entry["last_run"] = timestamp
        if result.passed:
            entry["pass_count"] += 1
        else:
            entry["fail_count"] += 1
            entry["last_fail"] = timestamp

        # Risk score: weighted failure rate with recency bias
        # Higher = more risky. Range [0, 1]
        total = entry["total_runs"]
        fail_rate = entry["fail_count"] / total if total > 0 else 0

        # Recency: recent failures count more (last 5 runs)
        history = entry.setdefault("history", [])
        history.append({"passed": result.passed, "time": timestamp})
        history = history[-10:]  # keep last 10
        entry["history"] = history

        recent_fails = sum(1 for h in history[-5:] if not h["passed"])
        recent_rate = recent_fails / min(5, len(history))

        # Composite: 40% overall fail rate + 60% recent failure rate
        entry["risk_score"] = round(0.4 * fail_rate + 0.6 * recent_rate, 3)

        nodes[node_id] = entry

    def _resolve_node_ids(self, result: TestResult, report: RegressionReport) -> List[str]:
        """从测试结果推断关联的图谱节点 ID"""
        # Best effort: match test name to mapped nodes
        name_lower = result.name.lower()
        matched = []
        for node_id in report.mapped_nodes + report.impact_scope:
            parts = node_id.split(":")
            if len(parts) >= 3:
                slug = parts[2].lower()
                if slug in name_lower or name_lower in slug:
                    matched.append(node_id)
        # If no match, attribute to all mapped nodes (conservative)
        return matched if matched else report.mapped_nodes[:3]

    def get_high_risk_nodes(self, threshold: float = 0.5) -> List[dict]:
        """获取高风险节点列表"""
        result = []
        for node_id, entry in self._scores.get("nodes", {}).items():
            if entry.get("risk_score", 0) >= threshold:
                result.append({
                    "node_id": node_id,
                    "risk_score": entry["risk_score"],
                    "fail_count": entry["fail_count"],
                    "total_runs": entry["total_runs"],
                    "last_fail": entry.get("last_fail", ""),
                })
        result.sort(key=lambda x: -x["risk_score"])
        return result

    def get_node_risk(self, node_id: str) -> Optional[dict]:
        """获取单个节点的风险评分"""
        return self._scores.get("nodes", {}).get(node_id)
