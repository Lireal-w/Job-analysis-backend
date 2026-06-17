from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import DataLayer, Dataset
from backend.app.admin.schema.data_storage import CreateDataLayerParam, CreateDatasetParam, UpdateDataLayerParam, UpdateDatasetParam


class CRUDDataLayer(CRUDPlus[DataLayer]):
    """数据分层数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> DataLayer | None:
        return await self.select_model(db, pk)

    async def get_all(self, db: AsyncSession) -> Sequence[DataLayer]:
        return await self.select_models(db)

    async def get_select(self) -> Select:
        return await self.select_order('sort')

    async def create(self, db: AsyncSession, obj: CreateDataLayerParam) -> None:
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateDataLayerParam) -> int:
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


class CRUDDataset(CRUDPlus[Dataset]):
    """数据集数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> Dataset | None:
        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> Dataset | None:
        return await self.select_model_by_column(db, name=name)

    async def get_all(self, db: AsyncSession) -> Sequence[Dataset]:
        return await self.select_models(db)

    async def get_select(
        self, name: str | None = None, layer_id: int | None = None, status: int | None = None
    ) -> Select:
        filters = {}
        if name is not None:
            filters['name__like'] = f'%{name}%'
        if layer_id is not None:
            filters['layer_id'] = layer_id
        if status is not None:
            filters['status'] = status
        return await self.select_order('id', **filters)

    async def create(self, db: AsyncSession, obj: CreateDatasetParam) -> None:
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateDatasetParam) -> int:
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


data_layer_dao: CRUDDataLayer = CRUDDataLayer(DataLayer)
dataset_dao: CRUDDataset = CRUDDataset(Dataset)
