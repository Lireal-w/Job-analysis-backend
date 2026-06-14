from datetime import datetime

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.app.todo.enums import TaskPriority, TaskSource, TaskStatus, TaskType
from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.utils.timezone import timezone


class Task(Base):
    """待办任务表"""

    __tablename__ = 'todo_task'
    __table_args__ = {'comment': '待办任务表'}

    id: Mapped[id_key] = mapped_column(init=False)
    title: Mapped[str] = mapped_column(sa.String(256), comment='任务标题')
    description: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='任务描述')
    task_type: Mapped[TaskType] = mapped_column(
        sa.SmallInteger, default=TaskType.DAILY, comment='任务类型(0每日 1周期 2定时)'
    )
    priority: Mapped[TaskPriority] = mapped_column(
        sa.SmallInteger, default=TaskPriority.MEDIUM, comment='优先级(0低 1中 2高 3紧急)'
    )
    status: Mapped[TaskStatus] = mapped_column(
        sa.SmallInteger, default=TaskStatus.TODO, comment='状态(0待办 1进行中 2已完成 3已取消)'
    )
    source: Mapped[TaskSource] = mapped_column(
        sa.SmallInteger, default=TaskSource.SELF_CREATED, comment='来源(0上级分配 1自己定制 2AI生成)'
    )
    assigned_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='分配人ID')
    assigned_to: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='负责人ID')
    parent_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='父任务ID(用于目标拆解)')
    due_date: Mapped[datetime | None] = mapped_column(TimeZone, default=None, comment='截止时间')
    start_date: Mapped[datetime | None] = mapped_column(TimeZone, default=None, comment='开始时间')
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None, init=False, comment='完成时间')
    progress: Mapped[int] = mapped_column(sa.SmallInteger, default=0, comment='进度(0-100)')
    tags: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='标签')
    sort_order: Mapped[int] = mapped_column(default=0, comment='排序')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='备注')

    # 周期/定时任务配置
    cron_expr: Mapped[str | None] = mapped_column(sa.String(64), default=None, comment='定时cron表达式')
    period_days: Mapped[int | None] = mapped_column(default=None, comment='周期(天)')

    # 创建人/更新人
    created_by: Mapped[int] = mapped_column(sa.BigInteger, default=0, sort_order=998, comment='创建者')
    updated_by: Mapped[int | None] = mapped_column(
        sa.BigInteger, init=False, default=None, sort_order=998, comment='修改者'
    )
