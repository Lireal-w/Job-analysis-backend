from datetime import datetime

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.app.todo.enums import TaskLogAction
from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.utils.timezone import timezone


class TaskLog(Base):
    """任务操作日志表"""

    __tablename__ = 'todo_log'
    __table_args__ = {'comment': '任务操作日志表'}

    id: Mapped[id_key] = mapped_column(init=False)
    task_id: Mapped[int] = mapped_column(sa.BigInteger, index=True, comment='任务ID')
    goal_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='目标ID')
    action: Mapped[TaskLogAction] = mapped_column(
        sa.SmallInteger, comment='动作(0创建 1更新 2进度更新 3完成 4取消 5重启)'
    )
    description: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='描述')
    operator: Mapped[int] = mapped_column(sa.BigInteger, comment='操作人ID')
