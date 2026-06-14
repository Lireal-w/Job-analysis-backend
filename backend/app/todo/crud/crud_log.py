from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.todo.enums import TaskLogAction
from backend.app.todo.model import TaskLog


class CRUDTaskLog(CRUDPlus[TaskLog]):
    """任务日志数据库操作类"""

    async def get_by_task(self, db: AsyncSession, task_id: int) -> Sequence[TaskLog]:
        """
        获取任务的所有日志

        :param db: 数据库会话
        :param task_id: 任务ID
        :return:
        """
        return await self.select_models(db, task_id=task_id)

    async def create(
        self,
        db: AsyncSession,
        task_id: int,
        action: TaskLogAction,
        operator: int,
        description: str | None = None,
        goal_id: int | None = None,
    ) -> TaskLog:
        """
        创建操作日志

        :param db: 数据库会话
        :param task_id: 任务ID
        :param action: 操作动作
        :param operator: 操作人ID
        :param description: 操作描述
        :param goal_id: 目标ID
        :return:
        """
        from backend.app.todo.schema.log import CreateTaskLogParam

        obj = CreateTaskLogParam(
            task_id=task_id,
            action=action.value,
            operator=operator,
            description=description,
        )
        return await self.create_model(db, obj, flush=True, goal_id=goal_id)

    async def delete_by_task(self, db: AsyncSession, task_id: int) -> int:
        """
        删除任务的所有日志

        :param db: 数据库会话
        :param task_id: 任务ID
        :return:
        """
        return await self.delete_model_by_column(db, task_id=task_id)


log_dao = CRUDTaskLog(TaskLog)
