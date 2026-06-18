"""DAG 调度器单元测试"""

from __future__ import annotations

import pytest

from backend.app.admin.service.etl.dag import DAG
from backend.app.admin.service.etl.exceptions import ETLDagError


class TestDAG:
    """DAG 基本操作测试"""

    def test_add_node(self) -> None:
        dag = DAG()
        dag.add_node('a', type='source', label='Node A')
        assert 'a' in dag.nodes
        assert dag.get_node('a')['type'] == 'source'

    def test_add_node_duplicate(self) -> None:
        dag = DAG()
        dag.add_node('a', type='source')
        with pytest.raises(ETLDagError, match='节点 a 已存在'):
            dag.add_node('a', type='transform')

    def test_add_node_not_found(self) -> None:
        dag = DAG()
        with pytest.raises(ETLDagError, match='节点 a 不存在'):
            dag.get_node('a')

    def test_add_edge(self) -> None:
        dag = DAG()
        dag.add_node('a', type='source')
        dag.add_node('b', type='transform')
        dag.add_edge('a', 'b')
        assert dag.predecessors('b') == ['a']
        assert dag.successors('a') == ['b']
        assert ('a', 'b') in dag.edges

    def test_add_edge_missing_source(self) -> None:
        dag = DAG()
        dag.add_node('b', type='transform')
        with pytest.raises(ETLDagError, match='源节点 a 不存在'):
            dag.add_edge('a', 'b')

    def test_add_edge_missing_target(self) -> None:
        dag = DAG()
        dag.add_node('a', type='source')
        with pytest.raises(ETLDagError, match='目标节点 b 不存在'):
            dag.add_edge('a', 'b')


class TestDAGTopologicalSort:
    """拓扑排序测试"""

    def test_linear_dag(self) -> None:
        """线性链: a -> b -> c"""
        dag = DAG()
        dag.add_node('a')
        dag.add_node('b')
        dag.add_node('c')
        dag.add_edge('a', 'b')
        dag.add_edge('b', 'c')

        result = dag.topological_sort()
        assert result == [['a'], ['b'], ['c']]

    def test_parallel_dag(self) -> None:
        """并行: a -> b, a -> c"""
        dag = DAG()
        dag.add_node('a')
        dag.add_node('b')
        dag.add_node('c')
        dag.add_edge('a', 'b')
        dag.add_edge('a', 'c')

        result = dag.topological_sort()
        assert result == [['a'], ['b', 'c']] or result == [['a'], ['c', 'b']]

    def test_diamond_dag(self) -> None:
        """菱形: a -> b -> d, a -> c -> d"""
        dag = DAG()
        dag.add_node('a')
        dag.add_node('b')
        dag.add_node('c')
        dag.add_node('d')
        dag.add_edge('a', 'b')
        dag.add_edge('a', 'c')
        dag.add_edge('b', 'd')
        dag.add_edge('c', 'd')

        result = dag.topological_sort()
        assert result[0] == ['a']
        assert set(result[1]) == {'b', 'c'}
        assert result[2] == ['d']

    def test_single_node(self) -> None:
        """单节点"""
        dag = DAG()
        dag.add_node('a')
        assert dag.topological_sort() == [['a']]

    def test_disconnected_nodes(self) -> None:
        """多个独立节点"""
        dag = DAG()
        dag.add_node('a')
        dag.add_node('b')
        dag.add_node('c')

        result = dag.topological_sort()
        assert len(result) == 1
        assert set(result[0]) == {'a', 'b', 'c'}

    def test_no_edges(self) -> None:
        """无边的图"""
        dag = DAG()
        dag.add_node('x')
        dag.add_node('y')
        result = dag.topological_sort()
        assert len(result) == 1
        assert set(result[0]) == {'x', 'y'}


class TestDAGCycleDetection:
    """环检测测试"""

    def test_direct_cycle(self) -> None:
        """直接环: a -> b -> a"""
        dag = DAG()
        dag.add_node('a')
        dag.add_node('b')
        dag.add_edge('a', 'b')
        dag.add_edge('b', 'a')
        assert dag.has_cycle()
        with pytest.raises(ETLDagError, match='循环依赖'):
            dag.topological_sort()

    def test_indirect_cycle(self) -> None:
        """间接环: a -> b -> c -> a"""
        dag = DAG()
        dag.add_node('a')
        dag.add_node('b')
        dag.add_node('c')
        dag.add_edge('a', 'b')
        dag.add_edge('b', 'c')
        dag.add_edge('c', 'a')
        assert dag.has_cycle()

    def test_self_loop(self) -> None:
        """自环: a -> a"""
        dag = DAG()
        dag.add_node('a')
        dag.add_edge('a', 'a')
        assert dag.has_cycle()

    def test_no_cycle(self) -> None:
        dag = DAG()
        dag.add_node('a')
        dag.add_node('b')
        dag.add_edge('a', 'b')
        assert not dag.has_cycle()
        dag.topological_sort()  # 不应抛出异常


class TestDAGFromFlow:
    """from_flow 工厂方法测试"""

    def test_basic_flow(self) -> None:
        nodes = [
            {'id': 's1', 'type': 'source', 'config': {}},
            {'id': 't1', 'type': 'transform', 'config': {}},
            {'id': 'l1', 'type': 'load', 'config': {}},
        ]
        edges = [
            {'source': 's1', 'target': 't1'},
            {'source': 't1', 'target': 'l1'},
        ]
        dag = DAG.from_flow(nodes, edges)
        assert dag.topological_sort() == [['s1'], ['t1'], ['l1']]

    def test_flow_with_cycle(self) -> None:
        nodes = [
            {'id': 'a', 'type': 'source', 'config': {}},
            {'id': 'b', 'type': 'transform', 'config': {}},
        ]
        edges = [
            {'source': 'a', 'target': 'b'},
            {'source': 'b', 'target': 'a'},
        ]
        with pytest.raises(ETLDagError, match='循环依赖'):
            DAG.from_flow(nodes, edges)

    def test_empty_nodes(self) -> None:
        dag = DAG.from_flow([], [])
        assert dag.topological_sort() == []

    def test_flow_preserves_config(self) -> None:
        nodes = [
            {'id': 'n1', 'type': 'source_database', 'config': {'query': 'SELECT 1'}, 'label': 'MyNode'},
        ]
        dag = DAG.from_flow(nodes, [])
        node = dag.get_node('n1')
        assert node['type'] == 'source_database'
        assert node['config']['query'] == 'SELECT 1'
        assert node['label'] == 'MyNode'
