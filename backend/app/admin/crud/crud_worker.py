from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import WorkerNode
from backend.app.admin.schema.worker import CreateWorkerParam, UpdateWorkerParam


class CRUDWorkerNode(CRUDPlus[WorkerNode]):
    """Worker 节点数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> WorkerNode | None:
        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> WorkerNode | None:
        return await self.select_model_by_column(db, name=name)

    async def get_all(self, db: AsyncSession) -> Sequence[WorkerNode]:
        return await self.select_models(db)

    async def get_online(self, db: AsyncSession) -> Sequence[WorkerNode]:
        return await self.select_models(db, status='online')

    async def get_select(
        self, name: str | None = None, status: str | None = None
    ) -> Select:
        filters = {}
        if name is not None:
            filters['name__like'] = f'%{name}%'
        if status is not None:
            filters['status'] = status
        return await self.select_order('id', **filters)

    async def create(self, db: AsyncSession, obj: CreateWorkerParam) -> None:
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateWorkerParam) -> int:
        return await self.update_model(db, pk, obj)

    async def update_heartbeat(
        self, db: AsyncSession, pk: int, data: dict
    ) -> int:
        return await self.update_model(db, pk, data)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


worker_dao: CRUDWorkerNode = CRUDWorkerNode(WorkerNode)
