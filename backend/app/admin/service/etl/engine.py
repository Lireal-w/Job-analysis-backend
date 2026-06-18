"""ETL 管道执行引擎

负责:
1. 解析 DAG 并执行拓扑排序
2. 按批次并行执行节点
3. 在节点间传递数据
4. 收集执行指标和错误
"""

from __future__ import annotations

import asyncio
import traceback
from datetime import datetime
from typing import Any

from loguru import logger

from backend.app.admin.service.etl.context import ETLContext
from backend.app.admin.service.etl.dag import DAG
from backend.app.admin.service.etl.exceptions import ETLNodeError
from backend.app.admin.service.etl.registry import get_node_executor


class ETLPipeline:
    """ETL 管道执行引擎"""

    def __init__(self, nodes: list[dict[str, Any]], edges: list[dict[str, str]]) -> None:
        self.dag = DAG.from_flow(nodes, edges)
        self.context = ETLContext()

    async def execute(self) -> ETLContext:
        """执行整个管道

        Returns:
            执行完成后的上下文 (包含 metrics 和最终输出)
        """
        self.context.start_time = datetime.now()
        batches = self.dag.topological_sort()
        node_outputs: dict[str, list[dict[str, Any]]] = {}
        total_nodes = len(batches)

        logger.info(f'[ETL] 开始执行管道 {self.context.pipeline_id}, 共 {total_nodes} 层')

        for batch_idx, batch in enumerate(batches):
            logger.info(f'[ETL] 执行第 {batch_idx + 1}/{len(batches)} 层: {batch}')

            tasks = []
            for node_id in batch:
                tasks.append(self._execute_node(node_id, node_outputs))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for node_id, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(f'[ETL] 节点 {node_id} 执行失败: {result}')
                    self.context.metrics[f'node_{node_id}_error'] = str(result)
                    raise result
                node_outputs[node_id] = result

        self.context.metrics['total_layers'] = len(batches)
        self.context.metrics['total_nodes'] = sum(len(b) for b in batches)
        self.context.metrics['finish_time'] = datetime.now().isoformat()
        self.context.metrics['output_nodes'] = list(node_outputs.keys())

        logger.info(f'[ETL] 管道 {self.context.pipeline_id} 执行完成')

        return self.context

    async def _execute_node(
        self,
        node_id: str,
        node_outputs: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """执行单个节点"""
        node_data = self.dag.get_node(node_id)
        node_type = node_data.get('type', '')
        config = node_data.get('config', {})
        node_label = node_data.get('label', node_id)

        logger.info(f'[ETL]   ├─ 节点 {node_label} ({node_type}) 开始执行')

        executor = get_node_executor(node_id, node_type, config)
        executor.validate_config()

        # 收集前驱节点的输出
        predecessors = self.dag.predecessors(node_id)
        inputs: list[list[dict[str, Any]]] = []
        for pred_id in predecessors:
            pred_output = node_outputs.get(pred_id)
            if pred_output is not None:
                inputs.append(pred_output)

        # 执行
        result = await executor.execute(self.context, *inputs)

        output_count = len(result) if result else 0
        logger.info(f'[ETL]   └─ 节点 {node_label} 完成, 输出 {output_count} 行')

        return result

    def get_final_output(self, node_outputs: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        """获取最终输出 (所有无后继的节点的合并输出)"""
        final = []
        for node_id in self.dag.nodes:
            successors = self.dag.successors(node_id)
            if not successors and node_id in node_outputs:
                final.extend(node_outputs[node_id])
        return final

    @classmethod
    def from_flow_config(cls, nodes: list[dict[str, Any]], edges: list[dict[str, str]]) -> ETLPipeline:
        """从数据流配置构建管道"""
        return cls(nodes, edges)
