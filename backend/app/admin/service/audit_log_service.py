import csv
import io

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_audit_log import audit_log_dao
from backend.app.admin.schema.audit_log import CreateAuditLogParam, DeleteAuditLogParam
from backend.common.pagination import paging_data


class AuditLogService:
    """审计日志服务类"""

    @staticmethod
    async def get_list(
        *,
        db: AsyncSession,
        event_type: str | None = None,
        user_id: int | None = None,
        username: str | None = None,
        ip: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        log_select = await audit_log_dao.get_select(
            event_type=event_type, user_id=user_id, username=username, ip=ip,
            start_date=start_date, end_date=end_date,
        )
        return await paging_data(db, log_select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateAuditLogParam) -> None:
        await audit_log_dao.create(db, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, obj: DeleteAuditLogParam) -> int:
        count = await audit_log_dao.delete(db, obj.pks)
        return count

    @staticmethod
    async def delete_all(*, db: AsyncSession) -> None:
        await audit_log_dao.delete_all(db)

    @staticmethod
    async def export(
        *,
        db: AsyncSession,
        event_type: str | None = None,
        username: str | None = None,
        ip: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> bytes:
        """导出审计日志为 CSV"""
        log_select = await audit_log_dao.get_select(
            event_type=event_type, username=username, ip=ip,
            start_date=start_date, end_date=end_date,
        )
        result = await db.execute(log_select)
        logs = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'ID', '事件类型', '操作动作', '资源类型', '资源ID', '资源名称',
            '用户ID', '用户名', 'IP地址', '请求方法', '请求路径', '响应码',
            '状态', '创建时间',
        ])
        for log in logs:
            writer.writerow([
                log.id, log.event_type, log.action, log.resource_type, log.resource_id,
                log.resource_name, log.user_id, log.username, log.ip,
                log.request_method, log.request_path, log.response_code,
                log.status, log.created_time,
            ])
        return output.getvalue().encode('utf-8-sig')


audit_log_service: AuditLogService = AuditLogService()
