from datetime import datetime

from pydantic import ConfigDict, Field

from backend.app.todo.enums import TaskPriority, TaskSource, TaskStatus, TaskType
from backend.app.todo.schema.goal import GetGoalDetail
from backend.common.schema import SchemaBase


class TaskSchemaBase(SchemaBase):
    """任务基础模型"""

    title: str = Field(max_length=256, description='任务标题')
    description: str | None = Field(default=None, description='任务描述')
    task_type: TaskType = Field(default=TaskType.DAILY, description='任务类型(0每日 1周期 2定时)')
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description='优先级(0低 1中 2高 3紧急)')
    source: TaskSource = Field(default=TaskSource.SELF_CREATED, description='来源(0上级分配 1自己定制 2AI生成)')
    assigned_to: int | None = Field(default=None, description='负责人ID')
    parent_id: int | None = Field(default=None, description='父任务ID(用于目标拆解)')
    due_date: datetime | None = Field(default=None, description='截止时间')
    start_date: datetime | None = Field(default=None, description='开始时间')
    tags: list[str] | None = Field(default=None, description='标签')
    sort_order: int = Field(default=0, description='排序')
    remark: str | None = Field(default=None, description='备注')
    cron_expr: str | None = Field(default=None, max_length=64, description='定时cron表达式')
    period_days: int | None = Field(default=None, description='周期(天)')


class CreateTaskParam(TaskSchemaBase):
    """创建任务参数"""


class UpdateTaskParam(TaskSchemaBase):
    """更新任务参数"""


class UpdateTaskProgressParam(SchemaBase):
    """更新任务进度参数"""

    progress: int = Field(ge=0, le=100, description='进度(0-100)')


class GetTaskDetail(TaskSchemaBase):
    """任务详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='任务ID')
    status: TaskStatus = Field(description='状态')
    progress: int = Field(description='进度')
    assigned_by: int | None = Field(None, description='分配人ID')
    completed_at: datetime | None = Field(None, description='完成时间')
    created_by: int = Field(description='创建者')
    updated_by: int | None = Field(None, description='修改者')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class GetTaskDetailWithGoals(GetTaskDetail):
    """任务详情(含目标)"""

    goals: list[GetGoalDetail] | None = Field(None, description='阶段性目标')
