from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import DataFlow, DataFlowRun
from backend.app.admin.schema.data_flow import CreateDataFlowParam, UpdateDataFlowParam


class CRUDDataFlow(CRUDPlus[DataFlow]):
    """数据流数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> DataFlow | None:
        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> DataFlow | None:
        return await self.select_model_by_column(db, name=name)

    async def get_all(self, db: AsyncSession) -> Sequence[DataFlow]:
        return await self.select_models(db)

    async def get_select(
        self, name: str | None = None, status: str | None = None
    ) -> Select:
        filters = {}
        if name is not None:
            filters['name__like'] = f'%{name}%'
        if status is not None:
            filters['status'] = status
        return await self.select_order('id', **filters)

    async def create(self, db: AsyncSession, obj: CreateDataFlowParam) -> None:
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateDataFlowParam) -> int:
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


class CRUDDataFlowRun(CRUDPlus[DataFlowRun]):
    """数据流运行记录数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> DataFlowRun | None:
        return await self.select_model(db, pk)

    async def get_by_flow(self, db: AsyncSession, flow_id: int) -> Sequence[DataFlowRun]:
        return await self.select_models(db, flow_id=flow_id)

    async def create_run(self, db: AsyncSession, obj: dict) -> DataFlowRun:
        model = self.model(**obj)
        db.add(model)
        await db.flush()
        await db.refresh(model)
        return model

    async def update_run(self, db: AsyncSession, pk: int, obj: dict) -> int:
        return await self.update_model(db, pk, obj)


data_flow_dao: CRUDDataFlow = CRUDDataFlow(DataFlow)
data_flow_run_dao: CRUDDataFlowRun = CRUDDataFlowRun(DataFlowRun)
