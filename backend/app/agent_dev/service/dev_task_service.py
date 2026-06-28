"""Agent 开发任务服务"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agent_dev.crud.crud_dev_task import dev_task_dao
from backend.app.agent_dev.enums import DevTaskStatus
from backend.app.agent_dev.model import AgentDevTask
from backend.app.agent_dev.schema.dev_task import (
    CreateAgentDevTaskParam,
    UpdateAgentDevTaskParam,
)
from backend.common.exception import errors
from backend.common.pagination import paging_data


class AgentDevTaskService:
    """开发任务服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> AgentDevTask:
        task = await dev_task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='开发任务不存在')
        return task

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[AgentDevTask]:
        return await dev_task_dao.get_all(db)

    @staticmethod
    async def get_list(
        *,
        db: AsyncSession,
        user_id: int | None = None,
        title: str | None = None,
        task_type: int | None = None,
        status: int | None = None,
        priority: int | None = None,
        source: int | None = None,
        project_name: str | None = None,
    ) -> dict[str, Any]:
        select = await dev_task_dao.get_select(
            user_id=user_id,
            title=title,
            task_type=task_type,
            status=status,
            priority=priority,
            source=source,
            project_name=project_name,
        )
        page_data = await paging_data(db, select)
        return page_data

    @staticmethod
    async def get_my_tasks(
        *,
        db: AsyncSession,
        user_id: int,
        status: int | None = None,
    ) -> Sequence[AgentDevTask]:
        """获取我的任务列表"""
        from sqlalchemy import select, desc

        stmt = (
            select(AgentDevTask)
            .where(AgentDevTask.created_by == user_id)
        )
        if status is not None:
            stmt = stmt.where(AgentDevTask.status == status)
        stmt = stmt.order_by(desc(AgentDevTask.created_time))
        results = await db.execute(stmt)
        return results.scalars().all()

    @staticmethod
    async def create(
        *,
        db: AsyncSession,
        obj: CreateAgentDevTaskParam,
        created_by: int = 0,
    ) -> AgentDevTask:
        return await dev_task_dao.create(db, obj, created_by=created_by)

    @staticmethod
    async def update(
        *,
        db: AsyncSession,
        pk: int,
        obj: UpdateAgentDevTaskParam,
    ) -> int:
        task = await dev_task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='开发任务不存在')
        if task.status in (DevTaskStatus.COMPLETED, DevTaskStatus.CANCELLED):
            raise errors.ConflictError(msg='已完成或已取消的任务不可修改')
        return await dev_task_dao.update(db, pk, obj)

    @staticmethod
    async def update_status(
        *,
        db: AsyncSession,
        pk: int,
        status: DevTaskStatus,
    ) -> int:
        task = await dev_task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='开发任务不存在')
        return await dev_task_dao.update_status(db, pk, status)

    @staticmethod
    async def cancel(
        *,
        db: AsyncSession,
        pk: int,
    ) -> int:
        """取消任务"""
        task = await dev_task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='开发任务不存在')
        if task.status == DevTaskStatus.COMPLETED:
            raise errors.ConflictError(msg='已完成的任务不可取消')
        return await dev_task_dao.update_status(db, pk, DevTaskStatus.CANCELLED)

    @staticmethod
    async def delete(
        *,
        db: AsyncSession,
        pks: list[int],
    ) -> int:
        return await dev_task_dao.delete(db, pks)


dev_task_service: AgentDevTaskService = AgentDevTaskService()
