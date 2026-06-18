"""动态调度参数模型"""

from datetime import datetime

from pydantic import ConfigDict, Field

from backend.app.task.enums import PeriodType, TaskSchedulerType
from backend.common.schema import SchemaBase


class DynamicScheduleCreate(SchemaBase):
    """创建动态调度参数"""

    name: str = Field(description='任务名称（唯一标识）')
    task: str = Field(description='要运行的 Celery 任务')
    type: TaskSchedulerType = Field(description='调度类型（0间隔 1定时）')
    interval_every: int | None = Field(default=None, description='任务再次运行前的间隔周期数')
    interval_period: PeriodType | None = Field(default=None, description='任务运行之间的周期类型')
    crontab: str | None = Field(default='* * * * *', description='Crontab 表达式')
    args: list | None = Field(default=None, description='任务可接收的位置参数')
    kwargs: dict | None = Field(default=None, description='任务可接收的关键字参数')
    queue: str | None = Field(default=None, description='CELERY_TASK_QUEUES 中定义的队列')
    exchange: str | None = Field(default=None, description='低级别 AMQP 路由的交换机')
    routing_key: str | None = Field(default=None, description='低级别 AMQP 路由的路由密钥')
    enabled: bool = Field(default=True, description='是否启用任务')
    ttl: int = Field(default=86400, description='Redis 键过期时间（秒），默认 24 小时')


class DynamicScheduleUpdate(SchemaBase):
    """更新动态调度参数"""

    task: str | None = Field(default=None, description='要运行的 Celery 任务')
    type: TaskSchedulerType | None = Field(default=None, description='调度类型（0间隔 1定时）')
    interval_every: int | None = Field(default=None, description='任务再次运行前的间隔周期数')
    interval_period: PeriodType | None = Field(default=None, description='任务运行之间的周期类型')
    crontab: str | None = Field(default=None, description='Crontab 表达式')
    args: list | None = Field(default=None, description='任务可接收的位置参数')
    kwargs: dict | None = Field(default=None, description='任务可接收的关键字参数')
    queue: str | None = Field(default=None, description='CELERY_TASK_QUEUES 中定义的队列')
    exchange: str | None = Field(default=None, description='低级别 AMQP 路由的交换机')
    routing_key: str | None = Field(default=None, description='低级别 AMQP 路由的路由密钥')
    enabled: bool | None = Field(default=None, description='是否启用任务')


class DynamicScheduleDetail(SchemaBase):
    """动态调度详情"""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(description='任务名称')
    task: str = Field(description='要运行的 Celery 任务')
    type: int = Field(description='调度类型（0间隔 1定时）')
    interval_every: int | None = Field(default=None, description='间隔周期数')
    interval_period: str | None = Field(default=None, description='间隔周期类型')
    crontab: str | None = Field(default=None, description='Crontab 表达式')
    args: list | None = Field(default=None, description='任务位置参数')
    kwargs: dict | None = Field(default=None, description='任务关键字参数')
    options: dict | None = Field(default=None, description='额外选项')
    enabled: bool = Field(default=True, description='是否启用')
    total_run_count: int = Field(default=0, description='已运行总次数')
    last_run_at: str | None = Field(default=None, description='最后运行时间')