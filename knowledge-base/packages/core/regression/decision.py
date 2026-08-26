"""TestDecisionEngine: 根据受影响节点决定测试类型和范围"""

from typing import List, Set

from packages.core.graph.store import Graph, Node
from .models import TestPlan


class TestDecisionEngine:
    """根据图谱影响分析结果决定测试策略"""

    def __init__(self, graph: Graph):
        self.graph = graph

    def decide(self, affected_node_ids: List[str], impact_node_ids: List[str]) -> TestPlan:
        """
        基于直接受影响节点 + 间接影响节点，决定测试计划。

        Args:
            affected_node_ids: git diff 直接映射到的节点
            impact_node_ids: Graph.impact() 扩展的所有影响节点
        """
        plan = TestPlan()

        all_scope = set(affected_node_ids) | set(impact_node_ids)

        # Classify all impacted nodes by type
        api_nodes = []
        page_nodes = []
        storage_nodes = []

        for node_id in all_scope:
            node = self.graph.get_node(node_id)
            if not node:
                continue
            if node.type == "api":
                api_nodes.append(node_id)
            elif node.type == "page":
                page_nodes.append(node_id)
            elif node.type == "storage":
                storage_nodes.append(node_id)

        # Rule 1: API nodes in scope → API contract tests
        if api_nodes:
            plan.types.add("api")
            plan.api_scope = api_nodes

        # Rule 2: Page nodes in scope → UI tests
        if page_nodes:
            plan.types.add("ui")
            plan.page_scope = page_nodes

        # Rule 3: Storage in scope → ensure APIs that write/read are tested
        if storage_nodes:
            plan.storage_scope = storage_nodes
            if not api_nodes:
                # Storage changed but no API in scope yet — find APIs that touch it
                for s_id in storage_nodes:
                    related_apis = self._find_apis_for_storage(s_id)
                    if related_apis:
                        plan.types.add("api")
                        plan.api_scope.extend(related_apis)

        # Rule 4: Detect cross-layer chains → E2E tests
        chains = self._detect_chains(affected_node_ids, all_scope)
        if chains:
            plan.types.add("e2e")
            plan.chains = chains

        # Rule 5: If page + api both affected, force E2E even without explicit chain
        if page_nodes and api_nodes:
            plan.types.add("e2e")

        # Deduplicate
        plan.api_scope = list(dict.fromkeys(plan.api_scope))
        plan.page_scope = list(dict.fromkeys(plan.page_scope))

        return plan

    def _find_apis_for_storage(self, storage_id: str) -> List[str]:
        """找到读写指定 storage 的所有 API"""
        apis = []
        for edge in self.graph.edges:
            if edge.to_id == storage_id and edge.relation in ("writes_to", "reads_from"):
                node = self.graph.get_node(edge.from_id)
                if node and node.type == "api":
                    apis.append(edge.from_id)
        return apis

    def _detect_chains(self, seed_ids: List[str], all_scope: Set[str]) -> List[List[str]]:
        """检测跨层链路: page → api → storage"""
        chains = []
        for node_id in seed_ids:
            node = self.graph.get_node(node_id)
            if not node:
                continue

            if node.type == "api":
                # Look for page→api and api→storage
                chain = self._trace_chain_from_api(node_id, all_scope)
                if chain and len(chain) >= 3:
                    chains.append(chain)
            elif node.type == "page":
                # Look for page→api→storage
                chain = self._trace_chain_from_page(node_id, all_scope)
                if chain and len(chain) >= 3:
                    chains.append(chain)

        # Deduplicate chains by content
        seen = set()
        unique = []
        for c in chains:
            key = "→".join(c)
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique

    def _trace_chain_from_api(self, api_id: str, scope: Set[str]) -> List[str]:
        """从 API 节点向上找 page，向下找 storage"""
        chain = [api_id]

        # Find page that calls this API
        for edge in self.graph.edges:
            if edge.to_id == api_id and edge.relation == "calls":
                if edge.from_id in scope:
                    chain.insert(0, edge.from_id)
                    break

        # Find storage this API writes/reads
        for edge in self.graph.edges:
            if edge.from_id == api_id and edge.relation in ("writes_to", "reads_from"):
                if edge.to_id in scope:
                    chain.append(edge.to_id)
                    break

        return chain

    def _trace_chain_from_page(self, page_id: str, scope: Set[str]) -> List[str]:
        """从 Page 节点向下找 api → storage 链"""
        chain = [page_id]

        # Find API called by this page
        for edge in self.graph.edges:
            if edge.from_id == page_id and edge.relation == "calls":
                api_id = edge.to_id
                if api_id in scope:
                    chain.append(api_id)
                    # Find storage
                    for e2 in self.graph.edges:
                        if e2.from_id == api_id and e2.relation in ("writes_to", "reads_from"):
                            if e2.to_id in scope:
                                chain.append(e2.to_id)
                                break
                    break

        return chain
