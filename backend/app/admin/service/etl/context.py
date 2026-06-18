"""ETL 执行上下文

在管道各节点之间传递数据与状态。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ETLContext:
    """ETL 执行上下文"""

    pipeline_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """管道运行唯一标识"""

    flow_id: int = 0
    """数据流 ID"""

    run_record_id: int = 0
    """运行记录 ID"""

    start_time: datetime = field(default_factory=datetime.now)
    """开始时间"""

    variables: dict[str, Any] = field(default_factory=dict)
    """全局变量"""

    metrics: dict[str, Any] = field(default_factory=dict)
    """运行指标"""

    def __getitem__(self, key: str) -> Any:
        return self.variables[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)
