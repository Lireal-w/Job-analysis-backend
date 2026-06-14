from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.todo.crud.crud_goal import goal_dao
from backend.app.todo.crud.crud_log import log_dao
from backend.app.todo.enums import GoalStatus, TaskLogAction
from backend.app.todo.model import TaskGoal
from backend.app.todo.schema.goal import CreateGoalParam, UpdateGoalParam, UpdateGoalStatusParam
from backend.common.exception import errors


class GoalService:
    """任务目标服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> TaskGoal:
        """
        获取目标详情

        :param db: 数据库会话
        :param pk: 目标ID
        :return:
        """
        goal = await goal_dao.get(db, pk)
        if not goal:
            raise errors.NotFoundError(msg='目标不存在')
        return goal

    @staticmethod
    async def get_by_task(*, db: AsyncSession, task_id: int) -> Sequence[TaskGoal]:
        """
        获取任务的所有目标

        :param db: 数据库会话
        :param task_id: 任务ID
        :return:
        """
        return await goal_dao.get_by_task(db, task_id)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateGoalParam, created_by: int) -> TaskGoal:
        """
        创建目标

        :param db: 数据库会话
        :param obj: 创建目标参数
        :param created_by: 创建者ID
        :return:
        """
        goal = await goal_dao.create(db, obj, created_by)
        await log_dao.create(
            db,
            task_id=obj.task_id,
            goal_id=goal.id,
            action=TaskLogAction.UPDATED,
            operator=created_by,
            description=f'创建阶段性目标: {obj.title}',
        )
        return goal

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateGoalParam, operator: int) -> TaskGoal:
        """
        更新目标

        :param db: 数据库会话
        :param pk: 目标ID
        :param obj: 更新目标参数
        :param operator: 操作人ID
        :return:
        """
        goal = await goal_dao.get(db, pk)
        if not goal:
            raise errors.NotFoundError(msg='目标不存在')

        await goal_dao.update(db, pk, obj)
        await log_dao.create(
            db,
            task_id=goal.task_id,
            goal_id=pk,
            action=TaskLogAction.UPDATED,
            operator=operator,
            description=f'更新阶段性目标: {obj.title}',
        )
        return await goal_dao.get(db, pk)

    @staticmethod
    async def update_status(
        *, db: AsyncSession, pk: int, obj: UpdateGoalStatusParam, operator: int
    ) -> TaskGoal:
        """
        更新目标状态

        :param db: 数据库会话
        :param pk: 目标ID
        :param obj: 更新目标状态参数
        :param operator: 操作人ID
        :return:
        """
        goal = await goal_dao.get(db, pk)
        if not goal:
            raise errors.NotFoundError(msg='目标不存在')

        await goal_dao.update_status(db, pk, obj)

        action_map = {
            GoalStatus.COMPLETED: TaskLogAction.COMPLETED,
        }
        action = action_map.get(obj.status, TaskLogAction.UPDATED)
        await log_dao.create(
            db,
            task_id=goal.task_id,
            goal_id=pk,
            action=action,
            operator=operator,
            description=f'更新目标状态: {GoalStatus(obj.status.value).name}',
        )
        return await goal_dao.get(db, pk)

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int) -> None:
        """
        删除目标

        :param db: 数据库会话
        :param pk: 目标ID
        :return:
        """
        goal = await goal_dao.get(db, pk)
        if not goal:
            raise errors.NotFoundError(msg='目标不存在')
        await goal_dao.delete(db, pk)


goal_service = GoalService()
