from datetime import datetime

from pydantic import ConfigDict, Field

from backend.app.todo.enums import GoalStatus
from backend.common.schema import SchemaBase


class GoalSchemaBase(SchemaBase):
    """目标基础模型"""

    title: str = Field(max_length=256, description='目标标题')
    description: str | None = Field(default=None, description='目标描述')
    stage_order: int = Field(default=0, description='阶段顺序')


class CreateGoalParam(SchemaBase):
    """创建目标参数"""

    task_id: int = Field(description='任务ID')
    title: str = Field(max_length=256, description='目标标题')
    description: str | None = Field(default=None, description='目标描述')
    stage_order: int = Field(default=0, description='阶段顺序')


class UpdateGoalParam(GoalSchemaBase):
    """更新目标参数"""


class UpdateGoalStatusParam(SchemaBase):
    """更新目标状态参数"""

    status: GoalStatus = Field(description='状态(0待开始 1进行中 2已完成)')


class GetGoalDetail(GoalSchemaBase):
    """目标详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='目标ID')
    task_id: int = Field(description='任务ID')
    status: GoalStatus = Field(description='状态')
    completed_at: datetime | None = Field(None, description='完成时间')
    ai_generated: bool = Field(description='是否AI生成')
    created_by: int = Field(description='创建者')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
