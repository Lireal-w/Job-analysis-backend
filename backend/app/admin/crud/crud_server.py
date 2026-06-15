from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import Server
from backend.app.admin.schema.server import CreateServerParam, UpdateServerParam


class CRUDServer(CRUDPlus[Server]):
    """服务器数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> Server | None:
        return await self.select_model(db, pk)

    async def get_select(
        self, name: str | None = None, protocol: str | None = None
    ) -> Select:
        filters = {}
        if name is not None:
            filters['name__like'] = f'%{name}%'
        if protocol is not None:
            filters['protocol'] = protocol
        return await self.select_order('id', **filters)

    async def get_by_name(self, db: AsyncSession, name: str) -> Server | None:
        return await self.select_model_by_column(db, name=name)

    async def get_all(self, db: AsyncSession) -> Sequence[Server]:
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj: CreateServerParam) -> None:
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateServerParam) -> int:
        return await self.update_model(db, pk, obj)

    async def update_status(self, db: AsyncSession, pk: int, status: int) -> int:
        return await self.update_model(db, pk, {'status': status})

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


server_dao: CRUDServer = CRUDServer(Server)
