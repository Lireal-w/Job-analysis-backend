from datetime import datetime

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.app.todo.enums import GoalStatus
from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.utils.timezone import timezone


class TaskGoal(Base):
    """任务阶段性目标表"""

    __tablename__ = 'todo_goal'
    __table_args__ = {'comment': '任务阶段性目标表'}

    id: Mapped[id_key] = mapped_column(init=False)
    task_id: Mapped[int] = mapped_column(sa.BigInteger, index=True, comment='任务ID')
    title: Mapped[str] = mapped_column(sa.String(256), comment='目标标题')
    description: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='目标描述')
    stage_order: Mapped[int] = mapped_column(default=0, comment='阶段顺序')
    status: Mapped[GoalStatus] = mapped_column(
        sa.SmallInteger, default=GoalStatus.PENDING, comment='状态(0待开始 1进行中 2已完成)'
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TimeZone, default=None, init=False, comment='完成时间'
    )
    ai_generated: Mapped[bool] = mapped_column(default=False, comment='是否AI生成')

    # 创建人/更新人
    created_by: Mapped[int] = mapped_column(sa.BigInteger,default=0, sort_order=998, comment='创建者')
    updated_by: Mapped[int | None] = mapped_column(
        sa.BigInteger, init=False, default=None, sort_order=998, comment='修改者'
    )
