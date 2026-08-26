"""图谱数据结构和持久化"""

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class Node:
    """图谱节点"""
    id: str
    type: str  # requirement, api, storage, page, job, config
    label: str
    module: str
    doc_path: str = ""
    source_path: str = ""


@dataclass
class Edge:
    """图谱边"""
    from_id: str
    to_id: str
    relation: str  # implemented_by, writes_to, reads_from, calls, triggers, depends_on
    label: str = ""
    confidence: str = "EXTRACTED"  # EXTRACTED | INFERRED | AMBIGUOUS


@dataclass
class Graph:
    """完整图谱"""
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    version: str = "1.0"
    module_count: int = 0
    orphan_report: List[dict] = field(default_factory=list)
    _adjacency: dict = field(default_factory=dict, repr=False)

    def _build_adjacency(self):
        """构建邻接索引（延迟初始化）"""
        if self._adjacency:
            return
        self._adjacency = defaultdict(list)
        for e in self.edges:
            self._adjacency[e.from_id].append(e)

    def get_node(self, node_id: str) -> Optional[Node]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def find_nodes_by_type(self, node_type: str) -> List[Node]:
        return [n for n in self.nodes if n.type == node_type]

    def search_nodes(self, term: str, node_types: Optional[List[str]] = None,
                     synonyms: Optional[Dict] = None, limit: int = 20,
                     search_index: Optional[Dict] = None) -> List[Node]:
        """
        增强模糊搜索：同义词扩展 + 多字段加权 + 意图识别。
        支持中文和英文，不区分大小写。

        Args:
            term: 搜索词
            node_types: 节点类型过滤
            synonyms: 同义词字典 {"key": ["alias1", "alias2"]}，可由 load_synonyms() 加载
            limit: 最大返回数量
            search_index: 预构建的倒排索引（BM25），O(1) 查询。由 GraphStore.load_search_index() 加载。
        """
        # Intent detection: exact node ID
        if self._detect_intent(term) == "exact_id":
            node = self.get_node(term)
            return [node] if node else []

        # Synonym expansion
        terms = self._expand_synonyms(term, synonyms)

        # Multi-word split
        all_terms: Set[str] = set()
        for t in terms:
            all_terms.add(t.lower())
            for part in re.split(r'[\s\-_]+', t):
                if len(part) >= 2:
                    all_terms.add(part.lower())

        # Fast path: use inverted index if available
        if search_index and search_index.get("terms"):
            return self._search_via_index(all_terms, search_index, node_types, limit)

        # Fallback: linear scan with scoring
        scored = []
        for n in self.nodes:
            if node_types and n.type not in node_types:
                continue
            score = self._compute_score(n, all_terms)
            if score > 0:
                scored.append((n, score))

        scored.sort(key=lambda x: -x[1])
        return [n for n, _ in scored[:limit]]

    def _search_via_index(self, terms: Set[str], search_index: dict,
                          node_types: Optional[List[str]], limit: int) -> List[Node]:
        """使用倒排索引进行 O(1) 查询"""
        node_scores: Dict[str, float] = {}
        idx_terms = search_index["terms"]

        # Tokenize query terms for index lookup
        query_tokens = set()
        for t in terms:
            query_tokens.update(self._tokenize(t))
            query_tokens.add(t)

        for token in query_tokens:
            postings = idx_terms.get(token, [])
            for posting in postings:
                nid = posting["id"]
                score = posting["score"]
                node_scores[nid] = node_scores.get(nid, 0) + score

        # Filter by type and sort
        node_map = {n.id: n for n in self.nodes}
        scored = []
        for nid, score in node_scores.items():
            node = node_map.get(nid)
            if not node:
                continue
            if node_types and node.type not in node_types:
                continue
            scored.append((node, score))

        scored.sort(key=lambda x: -x[1])
        return [n for n, _ in scored[:limit]]

    def _detect_intent(self, term: str) -> str:
        """识别查询意图：exact_id / api_path / keyword"""
        # Pattern: module:type:slug (exact node ID)
        if re.match(r'^[a-z_-]+:[a-z]+:', term):
            return "exact_id"
        # Pattern: METHOD /path (API path lookup)
        if re.match(r'^(GET|POST|PUT|DELETE|PATCH|WEBSOCKET)\s+/', term, re.IGNORECASE):
            return "api_path"
        return "keyword"

    def _expand_synonyms(self, term: str, synonyms: Optional[Dict]) -> List[str]:
        """将 term 扩展到所有同义词"""
        terms = [term]
        if not synonyms:
            return terms
        term_lower = term.lower()
        for key, aliases in synonyms.items():
            all_variants = [key.lower()] + [a.lower() for a in aliases]
            if term_lower in all_variants:
                terms.extend([key] + aliases)
                break
        return terms

    def _compute_score(self, node: Node, terms: Set[str]) -> float:
        """多字段加权评分"""
        score = 0.0
        label_lower = node.label.lower()
        id_lower = node.id.lower()
        for t in terms:
            # Exact label match
            if t == label_lower:
                score += 10.0
            elif label_lower.startswith(t):
                score += 5.0
            elif t in label_lower:
                score += 3.0
            # ID match
            if t == id_lower:
                score += 8.0
            elif t in id_lower:
                score += 2.0
        return score

    @staticmethod
    def load_synonyms(path: Optional[Path] = None) -> Optional[Dict]:
        """加载同义词配置文件"""
        if path is None:
            path = Path(__file__).parent / "synonyms.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("aliases", {})
        except (json.JSONDecodeError, OSError):
            return None

    def find_edges_from(self, node_id: str) -> List[Edge]:
        self._build_adjacency()
        return self._adjacency.get(node_id, [])

    def find_edges_to(self, node_id: str) -> List[Edge]:
        return [e for e in self.edges if e.to_id == node_id]

    def query(
        self,
        start: str,
        max_hops: int = 1,
        relations: Optional[List[str]] = None,
        node_types: Optional[List[str]] = None,
        direction: str = "both",
        min_confidence: str = "AMBIGUOUS",
        budget: int = 0,
    ) -> List[dict]:
        """
        精确图谱查询：从 start 节点出发，按条件检索关联节点。

        Args:
            start: 起始节点 ID
            max_hops: 最大跳数（1=直接邻居，2=两跳，3=全链路）
            relations: 只走指定关系类型（None=全部）
            node_types: 只返回指定类型的节点（None=全部）
            direction: "out"=只沿出边, "in"=只沿入边, "both"=双向
            min_confidence: 最低置信度过滤 ("EXTRACTED"=最严, "INFERRED"=中, "AMBIGUOUS"=全部)
            budget: 最大返回结果数（0=不限制），防止结果过大

        Returns:
            [{node_id, node_type, label, hop, path, confidence}] 按 hop 升序
        """
        CONFIDENCE_ORDER = {"EXTRACTED": 3, "INFERRED": 2, "AMBIGUOUS": 1}
        min_conf_level = CONFIDENCE_ORDER.get(min_confidence, 1)

        self._build_adjacency()
        visited: Set[str] = {start}
        results = []
        frontier = [(start, 0, [start])]

        while frontier:
            current, hop, path = frontier.pop(0)
            if hop >= max_hops:
                continue

            neighbors = []
            if direction in ("out", "both"):
                for e in self._adjacency.get(current, []):
                    if relations and e.relation not in relations:
                        continue
                    edge_conf = CONFIDENCE_ORDER.get(getattr(e, 'confidence', 'EXTRACTED'), 3)
                    if edge_conf < min_conf_level:
                        continue
                    neighbors.append((e.to_id, e.relation, getattr(e, 'confidence', 'EXTRACTED')))
            if direction in ("in", "both"):
                for e in self.edges:
                    if e.to_id == current and e.from_id not in visited:
                        if relations and e.relation not in relations:
                            continue
                        edge_conf = CONFIDENCE_ORDER.get(getattr(e, 'confidence', 'EXTRACTED'), 3)
                        if edge_conf < min_conf_level:
                            continue
                        neighbors.append((e.from_id, e.relation, getattr(e, 'confidence', 'EXTRACTED')))

            for neighbor_id, rel, conf in neighbors:
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                node = self.get_node(neighbor_id)
                if not node:
                    continue
                if node_types and node.type not in node_types:
                    frontier.append((neighbor_id, hop + 1, path + [neighbor_id]))
                    continue
                results.append({
                    "node_id": node.id,
                    "node_type": node.type,
                    "label": node.label,
                    "hop": hop + 1,
                    "relation": rel,
                    "confidence": conf,
                    "path": path + [neighbor_id],
                })
                if budget and len(results) >= budget:
                    results.sort(key=lambda x: (x["hop"], x["node_type"]))
                    return results
                frontier.append((neighbor_id, hop + 1, path + [neighbor_id]))

        results.sort(key=lambda x: (x["hop"], x["node_type"]))
        return results

    def impact(self, node_id: str, visited: Optional[set] = None) -> List[str]:
        """从节点出发，沿边遍历找到所有影响的节点"""
        if visited is None:
            visited = set()
        if node_id in visited:
            return []
        visited.add(node_id)
        result = []
        for edge in self.find_edges_to(node_id):
            result.append(edge.from_id)
            result.extend(self.impact(edge.from_id, visited))
        for edge in self.find_edges_from(node_id):
            result.append(edge.to_id)
            result.extend(self.impact(edge.to_id, visited))
        return list(set(result) - {node_id})

    def orphans(self) -> List[Node]:
        """找到孤立节点（没有任何边连接）"""
        connected = set()
        for e in self.edges:
            connected.add(e.from_id)
            connected.add(e.to_id)
        return [n for n in self.nodes if n.id not in connected]

    def coverage(self, requirement_id: str) -> dict:
        """检查需求的实现覆盖情况"""
        edges = self.find_edges_from(requirement_id)
        covered_types = set()
        covered_nodes = []
        for e in edges:
            node = self.get_node(e.to_id)
            if node:
                covered_types.add(node.type)
                covered_nodes.append(node)
        return {
            "requirement_id": requirement_id,
            "covered_types": list(covered_types),
            "covered_nodes": [n.id for n in covered_nodes],
            "missing_types": [
                t for t in ["api", "storage", "page"]
                if t not in covered_types
            ],
        }

    @property
    def stats(self) -> dict:
        types = {}
        for n in self.nodes:
            types[n.type] = types.get(n.type, 0) + 1
        relations = {}
        for e in self.edges:
            relations[e.relation] = relations.get(e.relation, 0) + 1
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": types,
            "edge_relations": relations,
            "modules": self.module_count,
        }

    def build_adjacency_index(self) -> dict:
        """
        生成邻接索引（供外部持久化或快速查询）。
        返回 {node_id: [{neighbor, relation, direction}]}
        """
        index = defaultdict(list)
        for e in self.edges:
            index[e.from_id].append({
                "neighbor": e.to_id,
                "relation": e.relation,
                "direction": "out",
            })
            index[e.to_id].append({
                "neighbor": e.from_id,
                "relation": e.relation,
                "direction": "in",
            })
        return dict(index)

    def build_search_index(self) -> dict:
        """
        生成倒排搜索索引（BM25 预计算）。
        对每个节点的 label + id + doc_path 分词，构建 term → [{node_id, score, field}] 映射。
        """
        import math

        index: Dict[str, List[dict]] = {}
        N = len(self.nodes)
        if N == 0:
            return {"version": "1.0", "total_nodes": 0, "terms": {}}

        # Tokenize all nodes
        doc_lengths = []
        node_terms: List[Dict[str, List[str]]] = []
        for node in self.nodes:
            terms_by_field = {
                "label": self._tokenize(node.label),
                "id": self._tokenize(node.id),
            }
            node_terms.append(terms_by_field)
            doc_lengths.append(len(terms_by_field["label"]) + len(terms_by_field["id"]))

        avg_dl = sum(doc_lengths) / N if N > 0 else 1

        # Count document frequency for each term
        df: Dict[str, int] = {}
        for nt in node_terms:
            seen = set()
            for field_terms in nt.values():
                for t in field_terms:
                    if t not in seen:
                        seen.add(t)
                        df[t] = df.get(t, 0) + 1

        # BM25 parameters
        k1, b = 1.5, 0.75

        # Build inverted index with BM25 scores
        for i, node in enumerate(self.nodes):
            dl = doc_lengths[i]
            for field_name, terms in node_terms[i].items():
                tf_map: Dict[str, int] = {}
                for t in terms:
                    tf_map[t] = tf_map.get(t, 0) + 1

                for term, tf in tf_map.items():
                    idf = math.log((N - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5) + 1)
                    score = idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avg_dl))
                    # Boost label matches
                    if field_name == "label":
                        score *= 2.0

                    if term not in index:
                        index[term] = []
                    index[term].append({
                        "id": node.id,
                        "score": round(score, 3),
                        "field": field_name,
                    })

        # Sort each term's postings by score descending
        for term in index:
            index[term].sort(key=lambda x: -x["score"])

        return {
            "version": "1.0",
            "total_nodes": N,
            "total_terms": len(index),
            "terms": index,
        }

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """分词：英文按分隔符切分 + 中文按 bigram"""
        tokens = []
        # Split on non-alphanumeric (keeps Chinese chars grouped)
        parts = re.split(r'[^a-zA-Z0-9一-鿿]+', text.lower())
        for part in parts:
            if not part:
                continue
            # English word
            if part.isascii():
                if len(part) >= 2:
                    tokens.append(part)
            else:
                # Chinese: character bigrams
                tokens.append(part)
                if len(part) >= 2:
                    for j in range(len(part) - 1):
                        tokens.append(part[j:j+2])
        return tokens


class GraphStore:
    """图谱持久化（JSON 格式）"""

    def __init__(self, output_dir: str = "graph"):
        self.output_dir = Path(output_dir)

    def save(self, graph: Graph):
        """保存图谱到 JSON 文件"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "version": graph.version,
            "module_count": graph.module_count,
            "stats": graph.stats,
            "nodes": [asdict(n) for n in graph.nodes],
            "edges": [
                {"source": e.from_id, "target": e.to_id, "relation": e.relation,
                 "label": e.label, "confidence": e.confidence}
                for e in graph.edges
            ],
        }
        output_path = self.output_dir / "graph.json"
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(output_path)

    def save_adjacency_index(self, graph: Graph):
        """保存邻接索引到独立文件（O(1) 单跳查询）"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        index = graph.build_adjacency_index()
        output_path = self.output_dir / "adjacency-index.json"
        output_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(output_path)

    def save_search_index(self, graph: Graph):
        """保存倒排搜索索引（BM25 预计算）"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        index = graph.build_search_index()
        output_path = self.output_dir / "search-index.json"
        output_path.write_text(
            json.dumps(index, ensure_ascii=False),
            encoding="utf-8",
        )
        return str(output_path)

    def load_search_index(self) -> Optional[dict]:
        """加载倒排搜索索引"""
        index_path = self.output_dir / "search-index.json"
        if not index_path.exists():
            return None
        try:
            return json.loads(index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def load(self) -> Optional[Graph]:
        """从 JSON 文件加载图谱"""
        graph_path = self.output_dir / "graph.json"
        if not graph_path.exists():
            return None
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        graph = Graph(
            version=data.get("version", "1.0"),
            module_count=data.get("module_count", 0),
        )
        for n in data.get("nodes", []):
            graph.nodes.append(Node(
                id=n["id"],
                type=n["type"],
                label=n.get("label", ""),
                module=n.get("module", ""),
                doc_path=n.get("doc_path", ""),
                source_path=n.get("source_path", ""),
            ))
        for e in data.get("edges", []):
            graph.edges.append(Edge(
                from_id=e.get("from_id", e.get("source", "")),
                to_id=e.get("to_id", e.get("target", "")),
                relation=e.get("relation", ""),
                label=e.get("label", ""),
                confidence=e.get("confidence", "EXTRACTED"),
            ))
        return graph

    def load_adjacency_index(self) -> Optional[dict]:
        """加载邻接索引"""
        index_path = self.output_dir / "adjacency-index.json"
        if not index_path.exists():
            return None
        return json.loads(index_path.read_text(encoding="utf-8"))
