"""H5 任务 Schema"""

from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class H5TaskSchemaBase(SchemaBase):
    """H5 任务基础模型"""

    title: str = Field(max_length=256, description='任务标题')
    description: str | None = Field(default=None, description='任务描述')
    task_type: int = Field(default=0, description='任务类型(0每日 1周期 2定时)')
    priority: int = Field(default=1, description='优先级(0低 1中 2高 3紧急)')
    due_date: datetime | None = Field(default=None, description='截止时间')
    start_date: datetime | None = Field(default=None, description='开始时间')
    tags: list[str] | None = Field(default=None, description='标签')
    remark: str | None = Field(default=None, description='备注')


class H5CreateTaskParam(H5TaskSchemaBase):
    """H5 创建任务参数"""


class H5UpdateTaskParam(SchemaBase):
    """H5 更新任务参数"""

    title: str | None = Field(default=None, max_length=256, description='任务标题')
    description: str | None = Field(default=None, description='任务描述')
    task_type: int | None = Field(default=None, description='任务类型')
    priority: int | None = Field(default=None, description='优先级')
    due_date: datetime | None = Field(default=None, description='截止时间')
    start_date: datetime | None = Field(default=None, description='开始时间')
    tags: list[str] | None = Field(default=None, description='标签')
    remark: str | None = Field(default=None, description='备注')


class H5UpdateTaskProgressParam(SchemaBase):
    """H5 更新任务进度参数"""

    progress: int = Field(ge=0, le=100, description='进度(0-100)')


class H5CompleteTaskParam(SchemaBase):
    """H5 完成任务提交参数"""

    progress: int = Field(default=100, ge=0, le=100, description='完成进度')
    remark: str | None = Field(default=None, description='完成备注')


class H5TaskDetail(SchemaBase):
    """H5 任务详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='任务ID')
    title: str = Field(description='任务标题')
    description: str | None = Field(None, description='任务描述')
    task_type: int = Field(description='任务类型')
    priority: int = Field(description='优先级')
    status: int = Field(description='状态(0待办 1进行中 2已完成 3已取消)')
    source: int = Field(description='来源')
    progress: int = Field(description='进度')
    assigned_to: int | None = Field(None, description='负责人ID')
    assigned_by: int | None = Field(None, description='分配人ID')
    due_date: datetime | None = Field(None, description='截止时间')
    start_date: datetime | None = Field(None, description='开始时间')
    completed_at: datetime | None = Field(None, description='完成时间')
    tags: list | None = Field(None, description='标签')
    remark: str | None = Field(None, description='备注')
    created_by: int = Field(description='创建者')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class H5TaskStats(SchemaBase):
    """H5 任务统计"""

    total: int = Field(description='总任务数')
    todo: int = Field(description='待办数')
    in_progress: int = Field(description='进行中')
    completed: int = Field(description='已完成')
    overdue: int = Field(description='已逾期')
