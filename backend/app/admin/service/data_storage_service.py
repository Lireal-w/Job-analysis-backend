from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_data_storage import data_layer_dao, dataset_dao
from backend.app.admin.model import DataLayer, Dataset
from backend.app.admin.schema.data_storage import CreateDataLayerParam, CreateDatasetParam, UpdateDataLayerParam, UpdateDatasetParam
from backend.common.exception import errors
from backend.common.pagination import paging_data


class DataLayerService:
    """数据分层服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> DataLayer:
        data_layer = await data_layer_dao.get(db, pk)
        if not data_layer:
            raise errors.NotFoundError(msg='数据分层不存在')
        return data_layer

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[DataLayer]:
        return await data_layer_dao.get_all(db)

    @staticmethod
    async def get_list(*, db: AsyncSession) -> dict[str, Any]:
        select = await data_layer_dao.get_select()
        page_data = await paging_data(db, select)
        return page_data

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateDataLayerParam) -> None:
        await data_layer_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateDataLayerParam) -> int:
        data_layer = await data_layer_dao.get(db, pk)
        if not data_layer:
            raise errors.NotFoundError(msg='数据分层不存在')
        return await data_layer_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        return await data_layer_dao.delete(db, pks)


class DatasetService:
    """数据集服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int, dept_id: int | None = None) -> Dataset:
        dataset = await dataset_dao.get(db, pk, dept_id=dept_id)
        if not dataset:
            raise errors.NotFoundError(msg='数据集不存在')
        return dataset

    @staticmethod
    async def get_all(*, db: AsyncSession, dept_id: int | None = None) -> Sequence[Dataset]:
        return await dataset_dao.get_all(db, dept_id=dept_id)

    @staticmethod
    async def get_list(
        *, db: AsyncSession, name: str | None = None, layer_id: int | None = None, status: int | None = None, dept_id: int | None = None
    ) -> dict[str, Any]:
        select = await dataset_dao.get_select(name=name, layer_id=layer_id, status=status, dept_id=dept_id)
        page_data = await paging_data(db, select)
        return page_data

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateDatasetParam) -> None:
        existing = await dataset_dao.get_by_name(db, obj.name)
        if existing:
            raise errors.ConflictError(msg='数据集名称已存在')
        await dataset_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateDatasetParam, dept_id: int | None = None) -> int:
        dataset = await dataset_dao.get(db, pk, dept_id=dept_id)
        if not dataset:
            raise errors.NotFoundError(msg='数据集不存在')
        return await dataset_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        return await dataset_dao.delete(db, pks)


data_layer_service: DataLayerService = DataLayerService()
dataset_service: DatasetService = DatasetService()
