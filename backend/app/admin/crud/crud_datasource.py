from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import Datasource
from backend.app.admin.schema.datasource import CreateDatasourceParam, UpdateDatasourceParam


class CRUDDatasource(CRUDPlus[Datasource]):
    """数据源数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> Datasource | None:
        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> Datasource | None:
        return await self.select_model_by_column(db, name=name)

    async def get_all(self, db: AsyncSession) -> Sequence[Datasource]:
        return await self.select_models(db)

    async def get_select(
        self, name: str | None = None, db_type: str | None = None
    ) -> Select:
        filters = {}
        if name is not None:
            filters['name__like'] = f'%{name}%'
        if db_type is not None:
            filters['db_type'] = db_type
        return await self.select_order('id', **filters)

    async def create(self, db: AsyncSession, obj: CreateDatasourceParam) -> None:
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateDatasourceParam) -> int:
        return await self.update_model(db, pk, obj)

    async def update_status(self, db: AsyncSession, pk: int, status: int) -> int:
        return await self.update_model(db, pk, {'status': status})

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


datasource_dao: CRUDDatasource = CRUDDatasource(Datasource)
