from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.todo.crud.crud_goal import goal_dao
from backend.app.todo.crud.crud_log import log_dao
from backend.app.todo.crud.crud_task import task_dao
from backend.app.todo.enums import TaskLogAction, TaskStatus
from backend.app.todo.model import Task
from backend.app.todo.schema.task import CreateTaskParam, UpdateTaskParam, UpdateTaskProgressParam
from backend.common.exception import errors
from backend.common.pagination import paging_data


class TaskService:
    """待办任务服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> Task:
        """
        获取任务详情

        :param db: 数据库会话
        :param pk: 任务ID
        :return:
        """
        task = await task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='任务不存在')
        return task

    @staticmethod
    async def get_today_tasks(*, db: AsyncSession, user_id: int) -> Sequence[Task]:
        """
        获取今日待完成任务

        :param db: 数据库会话
        :param user_id: 用户ID
        :return:
        """
        return await task_dao.get_today_tasks(db, user_id)

    @staticmethod
    async def get_list(
        *,
        db: AsyncSession,
        user_id: int | None = None,
        task_type: int | None = None,
        status: int | None = None,
        priority: int | None = None,
        source: int | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        """
        获取任务列表

        :param db: 数据库会话
        :param user_id: 用户ID
        :param task_type: 任务类型
        :param status: 状态
        :param priority: 优先级
        :param source: 来源
        :param title: 标题关键词
        :return:
        """
        task_select = await task_dao.get_select(
            user_id=user_id,
            task_type=task_type,
            status=status,
            priority=priority,
            source=source,
            title=title,
        )
        return await paging_data(db, task_select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateTaskParam, created_by: int) -> Task:
        """
        创建任务

        :param db: 数据库会话
        :param obj: 创建任务参数
        :param created_by: 创建者ID
        :return:
        """
        task = await task_dao.create(db, obj, created_by)
        await log_dao.create(
            db,
            task_id=task.id,
            action=TaskLogAction.CREATED,
            operator=created_by,
            description=f'创建任务: {obj.title}',
        )
        return task

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateTaskParam, operator: int) -> Task:
        """
        更新任务

        :param db: 数据库会话
        :param pk: 任务ID
        :param obj: 更新任务参数
        :param operator: 操作人ID
        :return:
        """
        task = await task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='任务不存在')

        count = await task_dao.update(db, pk, obj)
        if count > 0:
            await log_dao.create(
                db,
                task_id=pk,
                action=TaskLogAction.UPDATED,
                operator=operator,
                description=f'更新任务: {obj.title}',
            )
        return await task_dao.get(db, pk)

    @staticmethod
    async def update_status(*, db: AsyncSession, pk: int, status: int, operator: int) -> None:
        """
        更新任务状态

        :param db: 数据库会话
        :param pk: 任务ID
        :param status: 新状态
        :param operator: 操作人ID
        :return:
        """
        task = await task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='任务不存在')

        await task_dao.update_status(db, pk, status)

        status_map = {
            2: TaskLogAction.COMPLETED,
            3: TaskLogAction.CANCELLED,
        }
        action = status_map.get(status, TaskLogAction.UPDATED)
        await log_dao.create(
            db,
            task_id=pk,
            action=action,
            operator=operator,
            description=f'更新任务状态: {TaskStatus(status).name}',
        )

    @staticmethod
    async def update_progress(
        *, db: AsyncSession, pk: int, obj: UpdateTaskProgressParam, operator: int
    ) -> None:
        """
        更新任务进度

        :param db: 数据库会话
        :param pk: 任务ID
        :param obj: 更新进度参数
        :param operator: 操作人ID
        :return:
        """
        task = await task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='任务不存在')

        await task_dao.update_progress(db, pk, obj.progress)
        await log_dao.create(
            db,
            task_id=pk,
            action=TaskLogAction.PROGRESS_UPDATED,
            operator=operator,
            description=f'更新任务进度: {task.progress}% -> {obj.progress}%',
        )

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int) -> None:
        """
        删除任务

        :param db: 数据库会话
        :param pk: 任务ID
        :return:
        """
        task = await task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='任务不存在')
        await log_dao.delete_by_task(db, pk)
        await goal_dao.delete_by_task(db, pk)
        await task_dao.delete(db, pk)


task_service = TaskService()
