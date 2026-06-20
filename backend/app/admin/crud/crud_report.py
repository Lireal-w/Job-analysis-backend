from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import Report, ReportWidget
from backend.app.admin.schema.report import (
    CreateReportParam,
    CreateReportWidgetParam,
    UpdateReportParam,
    UpdateReportWidgetParam,
)


class CRUDReport(CRUDPlus[Report]):
    """报表数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> Report | None:
        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> Report | None:
        return await self.select_model_by_column(db, name=name)

    async def get_all(self, db: AsyncSession) -> Sequence[Report]:
        return await self.select_models(db)

    async def get_select(
        self, name: str | None = None, status: int | None = None, is_public: bool | None = None
    ) -> Select:
        filters = {}
        if name is not None:
            filters['name__like'] = f'%{name}%'
        if status is not None:
            filters['status'] = status
        if is_public is not None:
            filters['is_public'] = is_public
        return await self.select_order('id', **filters)

    async def create(self, db: AsyncSession, obj: CreateReportParam) -> Report:
        return await self.create_model(db, obj, flush=True)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateReportParam) -> int:
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


class CRUDReportWidget(CRUDPlus[ReportWidget]):
    """报表组件数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> ReportWidget | None:
        return await self.select_model(db, pk)

    async def get_by_report(self, db: AsyncSession, report_id: int) -> Sequence[ReportWidget]:
        from sqlalchemy import select as sa_select
        stmt = sa_select(ReportWidget).where(ReportWidget.report_id == report_id).order_by(ReportWidget.sort)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj: CreateReportWidgetParam) -> ReportWidget:
        return await self.create_model(db, obj, flush=True)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateReportWidgetParam) -> int:
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


report_dao: CRUDReport = CRUDReport(Report)
report_widget_dao: CRUDReportWidget = CRUDReportWidget(ReportWidget)
