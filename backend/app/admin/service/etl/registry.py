"""ETL 节点执行器注册表"""
from __future__ import annotations

from typing import Any

from backend.app.admin.service.etl.nodes.base import BaseNodeExecutor
from backend.app.admin.service.etl.nodes.load import (
    DatabaseLoadExecutor,
    FileCSVLoadExecutor,
    FileExcelLoadExecutor,
    FileJSONLoadExecutor,
    LogLoadExecutor,
)
from backend.app.admin.service.etl.nodes.source import (
    APISourceExecutor,
    DatabaseSourceExecutor,
    FileCSVSourceExecutor,
    FileExcelSourceExecutor,
    FileJSONSourceExecutor,
    TextFileSourceExecutor,
)
from backend.app.admin.service.etl.nodes.transform import (
    AggregateTransformExecutor,
    FillNullTransformExecutor,
    FilterTransformExecutor,
    JoinTransformExecutor,
    LimitTransformExecutor,
    MapTransformExecutor,
    PythonScriptTransformExecutor,
    SelectTransformExecutor,
    SortTransformExecutor,
    UnionTransformExecutor,
    UniqueTransformExecutor,
)

_NODE_REGISTRY: dict[str, type[BaseNodeExecutor]] = {
    # Source executors
    DatabaseSourceExecutor.node_type: DatabaseSourceExecutor,
    FileCSVSourceExecutor.node_type: FileCSVSourceExecutor,
    FileExcelSourceExecutor.node_type: FileExcelSourceExecutor,
    FileJSONSourceExecutor.node_type: FileJSONSourceExecutor,
    APISourceExecutor.node_type: APISourceExecutor,
    TextFileSourceExecutor.node_type: TextFileSourceExecutor,
    # Transform executors
    FilterTransformExecutor.node_type: FilterTransformExecutor,
    SelectTransformExecutor.node_type: SelectTransformExecutor,
    MapTransformExecutor.node_type: MapTransformExecutor,
    AggregateTransformExecutor.node_type: AggregateTransformExecutor,
    SortTransformExecutor.node_type: SortTransformExecutor,
    LimitTransformExecutor.node_type: LimitTransformExecutor,
    JoinTransformExecutor.node_type: JoinTransformExecutor,
    UnionTransformExecutor.node_type: UnionTransformExecutor,
    PythonScriptTransformExecutor.node_type: PythonScriptTransformExecutor,
    UniqueTransformExecutor.node_type: UniqueTransformExecutor,
    FillNullTransformExecutor.node_type: FillNullTransformExecutor,
    # Load executors
    DatabaseLoadExecutor.node_type: DatabaseLoadExecutor,
    FileCSVLoadExecutor.node_type: FileCSVLoadExecutor,
    FileExcelLoadExecutor.node_type: FileExcelLoadExecutor,
    FileJSONLoadExecutor.node_type: FileJSONLoadExecutor,
    LogLoadExecutor.node_type: LogLoadExecutor,
}


def get_node_executor(node_id: str, node_type: str, config: dict[str, Any]) -> BaseNodeExecutor:
    """获取节点执行器实例"""
    executor_cls = _NODE_REGISTRY.get(node_type)
    if executor_cls is None:
        raise ValueError(f'不支持的节点类型: {node_type}')
    executor = executor_cls(node_id, config)
    return executor


def register_node_executor(node_type: str, executor_cls: type[BaseNodeExecutor]) -> None:
    """注册自定义节点执行器"""
    _NODE_REGISTRY[node_type] = executor_cls
