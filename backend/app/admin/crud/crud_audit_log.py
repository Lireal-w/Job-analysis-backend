from datetime import datetime

from sqlalchemy import Select
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import AuditLog
from backend.app.admin.schema.audit_log import CreateAuditLogParam


class CRUDAuditLog(CRUDPlus[AuditLog]):
    """审计日志数据库操作类"""

    async def get_select(
        self,
        event_type: str | None = None,
        user_id: int | None = None,
        username: str | None = None,
        ip: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> Select:
        filters = {}

        if event_type is not None:
            filters['event_type'] = event_type
        if user_id is not None:
            filters['user_id'] = user_id
        if username is not None:
            filters['username__like'] = f'%{username}%'
        if ip is not None:
            filters['ip__like'] = f'%{ip}%'
        if start_date is not None:
            filters['created_time__ge'] = start_date
        if end_date is not None:
            filters['created_time__le'] = end_date

        return await self.select_order('created_time', 'desc', **filters)

    async def create(self, db: AsyncSession, obj: CreateAuditLogParam) -> None:
        await self.create_model(db, obj)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)

    @staticmethod
    async def delete_all(db: AsyncSession) -> None:
        await db.execute(sa_delete(AuditLog))


audit_log_dao: CRUDAuditLog = CRUDAuditLog(AuditLog)
