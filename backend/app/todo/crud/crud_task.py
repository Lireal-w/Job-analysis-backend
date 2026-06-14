from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.todo.model import Task
from backend.app.todo.schema.task import CreateTaskParam, UpdateTaskParam


class CRUDTask(CRUDPlus[Task]):
    """待办任务数据库操作类"""

    async def get(self, db: AsyncSession, task_id: int) -> Task | None:
        """
        获取任务详情

        :param db: 数据库会话
        :param task_id: 任务ID
        :return:
        """
        return await self.select_model(db, task_id)

    async def get_by_user(
        self, db: AsyncSession, user_id: int, status: int | None = None
    ) -> Sequence[Task]:
        """
        获取用户的任务列表

        :param db: 数据库会话
        :param user_id: 用户ID
        :param status: 任务状态筛选
        :return:
        """
        filters: dict = {'assigned_to': user_id}
        if status is not None:
            filters['status'] = status
        return await self.select_models(db, **filters)

    async def get_today_tasks(self, db: AsyncSession, user_id: int) -> Sequence[Task]:
        """
        获取用户今日待完成任务

        :param db: 数据库会话
        :param user_id: 用户ID
        :return:
        """
        from backend.utils.timezone import timezone

        now = timezone.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        filters = {
            'assigned_to': user_id,
            'status__in': [0, 1],  # TODO or IN_PROGRESS
        }

        # 获取未完成的任务 (due_date 在今天之前或没有截止日期但未完成)
        tasks = await self.select_models(db, **filters)

        # 过滤出今天的任务: due_date 在今天范围内，或每日任务，或无截止日期
        today_tasks = []
        for task in tasks:
            if task.task_type == 0:  # DAILY
                today_tasks.append(task)
            elif task.due_date and start_of_day <= task.due_date <= end_of_day:
                today_tasks.append(task)
            elif task.due_date is None:
                today_tasks.append(task)

        return today_tasks

    async def get_select(
        self,
        user_id: int | None = None,
        task_type: int | None = None,
        status: int | None = None,
        priority: int | None = None,
        source: int | None = None,
        title: str | None = None,
    ) -> Select:
        """
        获取任务列表查询表达式

        :param user_id: 用户ID
        :param task_type: 任务类型
        :param status: 状态
        :param priority: 优先级
        :param source: 来源
        :param title: 标题关键词
        :return:
        """
        filters: dict = {}

        if user_id is not None:
            filters['assigned_to'] = user_id
        if task_type is not None:
            filters['task_type'] = task_type
        if status is not None:
            filters['status'] = status
        if priority is not None:
            filters['priority'] = priority
        if source is not None:
            filters['source'] = source
        if title is not None:
            filters['title__like'] = f'%{title}%'

        return await self.select_order('sort_order', 'asc', 'id', 'desc', **filters)

    async def create(self, db: AsyncSession, obj: CreateTaskParam, created_by: int) -> Task:
        """
        创建任务

        :param db: 数据库会话
        :param obj: 创建任务参数
        :param created_by: 创建者ID
        :return:
        """
        data = obj.model_dump()
        data['created_by'] = created_by
        if data.get('assigned_to') is None:
            data['assigned_to'] = created_by
        return await self.create_model(db, data, flush=True)

    async def update(self, db: AsyncSession, task_id: int, obj: UpdateTaskParam) -> int:
        """
        更新任务

        :param db: 数据库会话
        :param task_id: 任务ID
        :param obj: 更新任务参数
        :return:
        """
        return await self.update_model(db, task_id, obj)

    async def update_status(self, db: AsyncSession, task_id: int, status: int) -> int:
        """
        更新任务状态

        :param db: 数据库会话
        :param task_id: 任务ID
        :param status: 新状态
        :return:
        """
        from backend.utils.timezone import timezone

        data = {'status': status}
        if status == 2:  # COMPLETED
            data['completed_at'] = timezone.now()
            data['progress'] = 100
        elif status == 3:  # CANCELLED
            data['completed_at'] = None
        return await self.update_model(db, task_id, data)

    async def update_progress(self, db: AsyncSession, task_id: int, progress: int) -> int:
        """
        更新任务进度

        :param db: 数据库会话
        :param task_id: 任务ID
        :param progress: 新进度(0-100)
        :return:
        """
        from backend.utils.timezone import timezone

        data = {'progress': progress}
        if progress >= 100:
            data['status'] = 2  # COMPLETED
            data['completed_at'] = timezone.now()
        return await self.update_model(db, task_id, data)

    async def delete(self, db: AsyncSession, task_id: int) -> int:
        """
        删除任务

        :param db: 数据库会话
        :param task_id: 任务ID
        :return:
        """
        return await self.delete_model(db, task_id)


task_dao = CRUDTask(Task)
