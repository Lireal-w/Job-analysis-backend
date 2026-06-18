"""DAG (有向无环图) 调度器

管理 ETL 节点的依赖关系、拓扑排序、并行执行策略。
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from backend.app.admin.service.etl.exceptions import ETLDagError

NodeId = str


class DAG:
    """有向无环图"""

    def __init__(self) -> None:
        self._nodes: dict[NodeId, dict[str, Any]] = {}
        self._edges: list[tuple[NodeId, NodeId]] = []
        self._graph: dict[NodeId, list[NodeId]] = defaultdict(list)
        self._reverse: dict[NodeId, list[NodeId]] = defaultdict(list)

    def add_node(self, node_id: NodeId, **attrs: Any) -> None:
        if node_id in self._nodes:
            raise ETLDagError(f'节点 {node_id} 已存在')
        self._nodes[node_id] = attrs

    def add_edge(self, source: NodeId, target: NodeId) -> None:
        if source not in self._nodes:
            raise ETLDagError(f'源节点 {source} 不存在')
        if target not in self._nodes:
            raise ETLDagError(f'目标节点 {target} 不存在')
        self._edges.append((source, target))
        self._graph[source].append(target)
        self._reverse[target].append(source)

    def get_node(self, node_id: NodeId) -> dict[str, Any]:
        node = self._nodes.get(node_id)
        if node is None:
            raise ETLDagError(f'节点 {node_id} 不存在')
        return node

    @property
    def nodes(self) -> dict[NodeId, dict[str, Any]]:
        return dict(self._nodes)

    @property
    def edges(self) -> list[tuple[NodeId, NodeId]]:
        return list(self._edges)

    def predecessors(self, node_id: NodeId) -> list[NodeId]:
        """获取节点的所有前驱节点"""
        return list(self._reverse.get(node_id, []))

    def successors(self, node_id: NodeId) -> list[NodeId]:
        """获取节点的所有后继节点"""
        return list(self._graph.get(node_id, []))

    def topological_sort(self) -> list[list[NodeId]]:
        """拓扑排序，返回分层结果 (每层可并行执行)

        Returns:
            按执行顺序排列的节点列表，每个元素是同一批次可并行执行的节点列表。
            例: [['a'], ['b', 'c'], ['d']]
        """
        if not self._nodes:
            return []

        in_degree: dict[NodeId, int] = {nid: len(self._reverse[nid]) for nid in self._nodes}
        queue: deque[NodeId] = deque(nid for nid, deg in in_degree.items() if deg == 0)

        if not queue:
            raise ETLDagError('图中不存在入度为 0 的节点，可能包含循环依赖')

        result: list[list[NodeId]] = []
        visited_count = 0

        while queue:
            batch: list[NodeId] = []
            for _ in range(len(queue)):
                nid = queue.popleft()
                batch.append(nid)
                visited_count += 1
                for succ in self._graph[nid]:
                    in_degree[succ] -= 1
                    if in_degree[succ] == 0:
                        queue.append(succ)
            result.append(batch)

        if visited_count != len(self._nodes):
            raise ETLDagError('图中检测到循环依赖，无法进行拓扑排序')

        return result

    def has_cycle(self) -> bool:
        """检测是否有环"""
        try:
            self.topological_sort()
            return False
        except ETLDagError:
            return True

    @classmethod
    def from_flow(cls, nodes: list[dict[str, Any]], edges: list[dict[str, str]]) -> DAG:
        """从数据流配置构建 DAG"""
        dag = cls()
        for node in nodes:
            dag.add_node(node['id'], **node)
        for edge in edges:
            dag.add_edge(edge['source'], edge['target'])
        if dag.has_cycle():
            raise ETLDagError('数据流配置包含循环依赖')
        return dag
