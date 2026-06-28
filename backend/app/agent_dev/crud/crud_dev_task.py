"""Agent 开发任务数据库操作"""

from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.agent_dev.enums import DevTaskStatus
from backend.app.agent_dev.model import AgentDevTask
from backend.app.agent_dev.schema.dev_task import CreateAgentDevTaskParam, UpdateAgentDevTaskParam


class CRUDAgentDevTask(CRUDPlus[AgentDevTask]):
    """开发任务数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> AgentDevTask | None:
        return await self.select_model(db, pk)

    async def get_all(self, db: AsyncSession) -> Sequence[AgentDevTask]:
        return await self.select_models(db)

    async def get_select(
        self,
        user_id: int | None = None,
        title: str | None = None,
        task_type: int | None = None,
        status: int | None = None,
        priority: int | None = None,
        source: int | None = None,
        project_name: str | None = None,
    ) -> Select:
        filters = {}
        if user_id is not None:
            filters['created_by'] = user_id
        if title is not None:
            filters['title__like'] = f'%{title}%'
        if task_type is not None:
            filters['task_type'] = task_type
        if status is not None:
            filters['status'] = status
        if priority is not None:
            filters['priority'] = priority
        if source is not None:
            filters['source'] = source
        if project_name is not None:
            filters['project_name__like'] = f'%{project_name}%'
        return await self.select_order('created_time', 'desc', **filters)

    async def get_by_status(self, db: AsyncSession, status: DevTaskStatus) -> Sequence[AgentDevTask]:
        """按状态获取任务"""
        return await self.select_models(db, status=status)

    async def create(self, db: AsyncSession, obj: CreateAgentDevTaskParam, created_by: int = 0) -> AgentDevTask:
        return await self.create_model(db, obj, created_by=created_by, flush=True)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateAgentDevTaskParam) -> int:
        return await self.update_model(db, pk, obj)

    async def update_status(self, db: AsyncSession, pk: int, status: DevTaskStatus) -> int:
        return await self.update_model(db, pk, {'status': status})

    async def update_progress(self, db: AsyncSession, pk: int, progress: int) -> int:
        return await self.update_model(db, pk, {'progress': progress, 'current_stage': None})

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


dev_task_dao: CRUDAgentDevTask = CRUDAgentDevTask(AgentDevTask)
