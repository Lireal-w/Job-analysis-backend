from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.todo.model import TaskGoal
from backend.app.todo.schema.goal import CreateGoalParam, UpdateGoalParam, UpdateGoalStatusParam


class CRUDTaskGoal(CRUDPlus[TaskGoal]):
    """任务目标数据库操作类"""

    async def get(self, db: AsyncSession, goal_id: int) -> TaskGoal | None:
        """
        获取目标详情

        :param db: 数据库会话
        :param goal_id: 目标ID
        :return:
        """
        return await self.select_model(db, goal_id)

    async def get_by_task(self, db: AsyncSession, task_id: int) -> Sequence[TaskGoal]:
        """
        获取任务的所有目标

        :param db: 数据库会话
        :param task_id: 任务ID
        :return:
        """
        return await self.select_models(db, task_id=task_id)

    async def create(self, db: AsyncSession, obj: CreateGoalParam, created_by: int) -> TaskGoal:
        """
        创建目标

        :param db: 数据库会话
        :param obj: 创建目标参数
        :param created_by: 创建者ID
        :return:
        """
        data = obj.model_dump()
        data['created_by'] = created_by
        return await self.create_model(db, data, flush=True)

    async def create_batch(
        self, db: AsyncSession, goals: list[dict], created_by: int
    ) -> list[TaskGoal]:
        """
        批量创建目标

        :param db: 数据库会话
        :param goals: 目标数据列表
        :param created_by: 创建者ID
        :return:
        """
        created_goals = []
        for goal_data in goals:
            goal_data['created_by'] = created_by
            goal = await self.create_model(db, goal_data, flush=True)
            created_goals.append(goal)
        return created_goals

    async def update(self, db: AsyncSession, goal_id: int, obj: UpdateGoalParam) -> int:
        """
        更新目标

        :param db: 数据库会话
        :param goal_id: 目标ID
        :param obj: 更新目标参数
        :return:
        """
        return await self.update_model(db, goal_id, obj)

    async def update_status(self, db: AsyncSession, goal_id: int, obj: UpdateGoalStatusParam) -> int:
        """
        更新目标状态

        :param db: 数据库会话
        :param goal_id: 目标ID
        :param obj: 更新目标状态参数
        :return:
        """
        from backend.utils.timezone import timezone

        data = {'status': obj.status.value}
        if obj.status.value == 2:  # COMPLETED
            data['completed_at'] = timezone.now()
        return await self.update_model(db, goal_id, data)

    async def delete(self, db: AsyncSession, goal_id: int) -> int:
        """
        删除目标

        :param db: 数据库会话
        :param goal_id: 目标ID
        :return:
        """
        return await self.delete_model(db, goal_id)


goal_dao = CRUDTaskGoal(TaskGoal)
