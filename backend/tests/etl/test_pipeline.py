"""ETL 管道集成测试

测试完整管道的 DAG 执行、节点通信、指标收集、错误传播等。
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.app.admin.service.etl.dag import DAG
from backend.app.admin.service.etl.engine import ETLPipeline
from backend.app.admin.service.etl.exceptions import ETLDagError, ETLNodeError
from backend.app.admin.service.etl.nodes.base import BaseNodeExecutor
from backend.app.admin.service.etl.registry import register_node_executor


# ── 辅助: 自定义测试节点 ──────────────────────────────────────


class SourceNode(BaseNodeExecutor):
    """测试用源节点"""
    node_type = 'test_source'

    def validate_config(self) -> None:
        pass  # Test node allows empty config

    async def execute(self, context, *inputs):
        return [{'value': 1}, {'value': 2}, {'value': 3}]


class DoubleNode(BaseNodeExecutor):
    """测试用转换节点：将值翻倍"""
    node_type = 'test_double'

    def validate_config(self) -> None:
        pass

    async def execute(self, context, *inputs):
        data = inputs[0]
        return [{'value': r['value'] * 2} for r in data]


class SumNode(BaseNodeExecutor):
    """测试用汇聚节点：求和"""
    node_type = 'test_sum'

    def validate_config(self) -> None:
        pass

    async def execute(self, context, *inputs):
        # 合并多个输入
        all_rows = []
        for inp in inputs:
            all_rows.extend(inp)
        total = sum(r['value'] for r in all_rows)
        return [{'total': total}]


class FailNode(BaseNodeExecutor):
    """测试用失败节点"""
    node_type = 'test_fail'

    def validate_config(self) -> None:
        pass

    async def execute(self, context, *inputs):
        raise ETLNodeError(self.node_id, 'intentional failure')


# 注册测试节点
register_node_executor('test_source', SourceNode)
register_node_executor('test_double', DoubleNode)
register_node_executor('test_sum', SumNode)
register_node_executor('test_fail', FailNode)


@pytest.mark.asyncio
class TestETLPipeline:
    """ETL 管道集成测试"""

    async def test_linear_pipeline(self) -> None:
        """线性链: source → double → sum"""
        nodes = [
            {'id': 's1', 'type': 'test_source', 'label': 'Source', 'config': {}},
            {'id': 'd1', 'type': 'test_double', 'label': 'Double', 'config': {}},
            {'id': 'sum1', 'type': 'test_sum', 'label': 'Sum', 'config': {}},
        ]
        edges = [
            {'source': 's1', 'target': 'd1'},
            {'source': 'd1', 'target': 'sum1'},
        ]
        pipeline = ETLPipeline(nodes, edges)
        ctx = await pipeline.execute()

        assert ctx is not None
        assert 'total_nodes' in ctx.metrics
        assert ctx.metrics['total_nodes'] == 3

    async def test_parallel_execution(self) -> None:
        """并行执行: source → double1, source → double2"""
        nodes = [
            {'id': 's1', 'type': 'test_source', 'label': 'Source', 'config': {}},
            {'id': 'd1', 'type': 'test_double', 'label': 'Double1', 'config': {}},
            {'id': 'd2', 'type': 'test_double', 'label': 'Double2', 'config': {}},
        ]
        edges = [
            {'source': 's1', 'target': 'd1'},
            {'source': 's1', 'target': 'd2'},
        ]
        pipeline = ETLPipeline(nodes, edges)
        ctx = await pipeline.execute()
        assert ctx.metrics['total_nodes'] == 3

    async def test_diamond_pipeline(self) -> None:
        """菱形: s1 → d1 → sum1, s1 → d2 → sum1"""
        nodes = [
            {'id': 's1', 'type': 'test_source', 'label': 'Source', 'config': {}},
            {'id': 'd1', 'type': 'test_double', 'label': 'Double1', 'config': {}},
            {'id': 'd2', 'type': 'test_double', 'label': 'Double2', 'config': {}},
            {'id': 'sum1', 'type': 'test_sum', 'label': 'Sum', 'config': {}},
        ]
        edges = [
            {'source': 's1', 'target': 'd1'},
            {'source': 's1', 'target': 'd2'},
            {'source': 'd1', 'target': 'sum1'},
            {'source': 'd2', 'target': 'sum1'},
        ]
        pipeline = ETLPipeline(nodes, edges)
        ctx = await pipeline.execute()
        assert ctx.metrics['total_nodes'] == 4

    async def test_pipeline_error_propagation(self) -> None:
        """错误传播: source → fail_node"""
        nodes = [
            {'id': 's1', 'type': 'test_source', 'label': 'Source', 'config': {}},
            {'id': 'f1', 'type': 'test_fail', 'label': 'Fail', 'config': {}},
        ]
        edges = [{'source': 's1', 'target': 'f1'}]
        pipeline = ETLPipeline(nodes, edges)
        with pytest.raises(ETLNodeError, match='intentional failure'):
            await pipeline.execute()

    async def test_empty_nodes(self) -> None:
        """空节点列表"""
        pipeline = ETLPipeline([], [])
        ctx = await pipeline.execute()
        assert ctx is not None

    async def test_flow_with_different_node_types(self) -> None:
        """混合多种节点类型"""
        nodes = [
            {'id': 's1', 'type': 'test_source', 'label': 'Source', 'config': {}},
            {'id': 'd1', 'type': 'test_double', 'label': 'Double', 'config': {}},
        ]
        edges = [{'source': 's1', 'target': 'd1'}]
        pipeline = ETLPipeline(nodes, edges)
        ctx = await pipeline.execute()
        assert ctx.metrics['total_nodes'] == len(nodes)

    async def test_from_flow_config(self) -> None:
        """from_flow_config 工厂方法"""
        nodes = [
            {'id': 's1', 'type': 'test_source', 'config': {}},
            {'id': 'd1', 'type': 'test_double', 'config': {}},
        ]
        edges = [{'source': 's1', 'target': 'd1'}]
        pipeline = ETLPipeline.from_flow_config(nodes, edges)
        assert isinstance(pipeline, ETLPipeline)
        assert isinstance(pipeline.dag, DAG)

    async def test_context_flow_id_propagation(self) -> None:
        """验证 flow_id 和 run_record_id 传递"""
        nodes = [{'id': 's1', 'type': 'test_source', 'config': {}}]
        pipeline = ETLPipeline(nodes, [])
        pipeline.context.flow_id = 42
        pipeline.context.run_record_id = 99
        ctx = await pipeline.execute()
        assert ctx.flow_id == 42
        assert ctx.run_record_id == 99


@pytest.mark.asyncio
class TestETLPipelineRealNodes:
    """使用真实节点类型的管道测试"""

    async def test_csv_source_to_log_load(self, temp_csv_file: str) -> None:
        """CSV 源 → Log 输出"""
        nodes = [
            {'id': 'csv1', 'type': 'source_file_csv', 'config': {
                'file_path': temp_csv_file,
                'has_header': True,
            }},
            {'id': 'log1', 'type': 'load_log', 'config': {}},
        ]
        edges = [{'source': 'csv1', 'target': 'log1'}]
        pipeline = ETLPipeline(nodes, edges)
        ctx = await pipeline.execute()
        assert ctx.metrics['node_csv1_rows'] == 3

    async def test_json_source_filter_transform(self, temp_json_file: str) -> None:
        """JSON 源 → 过滤 → Log 输出"""
        nodes = [
            {'id': 'src', 'type': 'source_file_json', 'config': {
                'file_path': temp_json_file,
            }},
            {'id': 'flt', 'type': 'transform_filter', 'config': {
                'conditions': [{'field': 'score', 'operator': 'gt', 'value': 90}],
            }},
            {'id': 'log', 'type': 'load_log', 'config': {}},
        ]
        edges = [
            {'source': 'src', 'target': 'flt'},
            {'source': 'flt', 'target': 'log'},
        ]
        pipeline = ETLPipeline(nodes, edges)
        ctx = await pipeline.execute()
        assert ctx.metrics['node_src_rows'] == 3

    async def test_filter_then_sort(self, sample_data) -> None:
        """过滤 → 排序 (纯内存节点)"""
        nodes = [
            {'id': 'src', 'type': 'test_source', 'config': {}},
            # 用 test_source 生成 [1,2,3]，然后我们用 Python 脚本来模拟过滤
            {'id': 'scr', 'type': 'transform_python_script', 'config': {
                'script': 'result = [{"x": 3}, {"x": 1}, {"x": 2}]',
            }},
            {'id': 'sort', 'type': 'transform_sort', 'config': {
                'sort_by': [{'field': 'x', 'order': 'asc'}],
            }},
            {'id': 'log', 'type': 'load_log', 'config': {}},
        ]
        edges = [
            {'source': 'scr', 'target': 'sort'},
            {'source': 'sort', 'target': 'log'},
        ]
        pipeline = ETLPipeline(nodes, edges)
        ctx = await pipeline.execute()
        assert ctx.metrics['total_nodes'] == 4  # src, scr, sort, log

    async def test_cycle_detection_at_construction(self) -> None:
        """构造时检测循环依赖"""
        nodes = [
            {'id': 'a', 'type': 'test_source', 'config': {}},
            {'id': 'b', 'type': 'test_double', 'config': {}},
        ]
        edges = [
            {'source': 'a', 'target': 'b'},
            {'source': 'b', 'target': 'a'},
        ]
        with pytest.raises(ETLDagError, match='循环依赖'):
            ETLPipeline(nodes, edges)
