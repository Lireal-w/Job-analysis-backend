"""ETL 节点执行器基类"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.app.admin.service.etl.context import ETLContext
from backend.app.admin.service.etl.exceptions import ETLNodeError


class BaseNodeExecutor(ABC):
    """节点执行器基类"""

    node_type: str = ''

    def __init__(self, node_id: str, config: dict[str, Any]) -> None:
        self.node_id = node_id
        self.config = config

    @abstractmethod
    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        """执行节点逻辑

        Args:
            context: ETL 执行上下文
            inputs: 来自前驱节点的输入数据列表 (每个前驱一个数据列表)

        Returns:
            处理后的数据行列表
        """
        ...

    def validate_config(self) -> None:
        """验证配置合法性，子类可覆盖"""
        pass

    def raise_error(self, msg: str) -> None:
        raise ETLNodeError(self.node_id, msg)
