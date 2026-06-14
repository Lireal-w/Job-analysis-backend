from datetime import datetime

from pydantic import ConfigDict, Field

from backend.app.todo.enums import TaskLogAction
from backend.common.schema import SchemaBase


class GetTaskLogDetail(SchemaBase):
    """任务日志详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='日志ID')
    task_id: int = Field(description='任务ID')
    goal_id: int | None = Field(None, description='目标ID')
    action: TaskLogAction = Field(description='动作')
    description: str | None = Field(None, description='描述')
    operator: int = Field(description='操作人ID')
    created_time: datetime = Field(description='操作时间')
