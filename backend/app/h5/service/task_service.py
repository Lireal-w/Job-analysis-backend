"""H5 任务服务"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.todo.crud.crud_task import task_dao
from backend.app.todo.model import Task
from backend.app.todo.service.task_service import task_service as todo_task_service
from backend.common.exception import errors
from backend.utils.timezone import timezone


class H5TaskService:
    """H5 任务服务类"""

    @staticmethod
    async def get_today_tasks(*, db: AsyncSession, user_id: int) -> Sequence[Task]:
        """
        获取今日待完成任务

        :param db: 数据库会话
        :param user_id: 用户ID
        :return:
        """
        return await todo_task_service.get_today_tasks(db=db, user_id=user_id)

    @staticmethod
    async def get_list(
        *,
        db: AsyncSession,
        user_id: int,
        status: int | None = None,
        task_type: int | None = None,
        priority: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """
        获取H5任务列表（精简分页）

        :param db: 数据库会话
        :param user_id: 用户ID
        :param status: 状态筛选
        :param task_type: 类型筛选
        :param priority: 优先级筛选
        :param page: 页码
        :param page_size: 每页条数
        :return:
        """
        select = await task_dao.get_select(
            user_id=user_id,
            status=status,
            task_type=task_type,
            priority=priority,
        )
        # 使用原始的 limit/offset 分页
        from sqlalchemy import select as sa_select, func

        # 计算总数
        count_stmt = sa_select(func.count()).select_from(select.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        # 获取分页数据
        stmt = select.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        items = list(result.scalars().all())

        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size if total > 0 else 0,
        }

    @staticmethod
    async def get_detail(*, db: AsyncSession, pk: int, user_id: int) -> Task:
        """
        获取任务详情（校验负责人）

        :param db: 数据库会话
        :param pk: 任务ID
        :param user_id: 用户ID
        :return:
        """
        task = await task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='任务不存在')
        if task.assigned_to != user_id and task.created_by != user_id:
            raise errors.ForbiddenError(msg='无权访问该任务')
        return task

    @staticmethod
    async def create(
        *, db: AsyncSession, obj, created_by: int
    ) -> Task:
        """
        创建任务

        :param db: 数据库会话
        :param obj: 创建任务参数
        :param created_by: 创建者ID
        :return:
        """
        return await todo_task_service.create(db=db, obj=obj, created_by=created_by)

    @staticmethod
    async def update(
        *, db: AsyncSession, pk: int, obj, operator: int
    ) -> Task:
        """
        更新任务

        :param db: 数据库会话
        :param pk: 任务ID
        :param obj: 更新参数
        :param operator: 操作人ID
        :return:
        """
        return await todo_task_service.update(db=db, pk=pk, obj=obj, operator=operator)

    @staticmethod
    async def update_progress(
        *, db: AsyncSession, pk: int, progress: int, operator: int
    ) -> None:
        """
        更新任务进度

        :param db: 数据库会话
        :param pk: 任务ID
        :param progress: 进度值(0-100)
        :param operator: 操作人ID
        :return:
        """
        task = await task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='任务不存在')
        if task.assigned_to != operator and task.created_by != operator:
            raise errors.ForbiddenError(msg='无权操作该任务')

        await todo_task_service.update_progress(
            db=db, pk=pk,
            obj=type('obj', (), {'progress': progress})(),
            operator=operator,
        )

    @staticmethod
    async def complete(
        *, db: AsyncSession, pk: int, operator: int,
        remark: str | None = None,
        progress: int = 100,
    ) -> None:
        """
        完成任务（提交任务完成）

        :param db: 数据库会话
        :param pk: 任务ID
        :param operator: 操作人ID
        :param remark: 完成备注
        :param progress: 完成进度(默认100)
        :return:
        """
        task = await task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='任务不存在')
        if task.assigned_to != operator and task.created_by != operator:
            raise errors.ForbiddenError(msg='无权操作该任务')
        if task.status == 2:
            raise errors.RequestError(msg='任务已完成，请勿重复提交')

        # 先更新进度
        await task_dao.update_progress(db, pk, progress)

        # 再更新状态为已完成
        await task_dao.update_status(db, pk, 2)

        # 如有备注，更新备注
        if remark:
            await task_dao.update(db, pk, {'remark': remark})

        # 记录日志
        from backend.app.todo.crud.crud_log import log_dao
        from backend.app.todo.enums import TaskLogAction

        await log_dao.create(
            db,
            task_id=pk,
            action=TaskLogAction.COMPLETED,
            operator=operator,
            description=f'完成任务: {task.title}' + (f' (备注: {remark})' if remark else ''),
        )

    @staticmethod
    async def get_stats(*, db: AsyncSession, user_id: int) -> dict[str, int]:
        """
        获取任务统计（用于H5首页展示）

        :param db: 数据库会话
        :param user_id: 用户ID
        :return:
        """
        from backend.utils.timezone import timezone

        now = timezone.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        tasks = await task_dao.get_by_user(db, user_id)
        total = len(tasks)
        todo = sum(1 for t in tasks if t.status == 0)
        in_progress = sum(1 for t in tasks if t.status == 1)
        completed = sum(1 for t in tasks if t.status == 2)
        overdue = sum(
            1 for t in tasks
            if t.status in (0, 1)
            and t.due_date is not None
            and t.due_date < now
        )

        return {
            'total': total,
            'todo': todo,
            'in_progress': in_progress,
            'completed': completed,
            'overdue': overdue,
        }


h5_task_service: H5TaskService = H5TaskService()
