from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from starlette.responses import StreamingResponse

from backend.app.admin.schema.audit_log import DeleteAuditLogParam, GetAuditLogDetail
from backend.app.admin.service.audit_log_service import audit_log_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get(
    '',
    summary='分页获取审计日志',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_audit_logs_paginated(
    db: CurrentSession,
    event_type: Annotated[str | None, Query(description='事件类型')] = None,
    username: Annotated[str | None, Query(description='用户名')] = None,
    ip: Annotated[str | None, Query(description='IP 地址')] = None,
    start_date: Annotated[str | None, Query(description='开始日期')] = None,
    end_date: Annotated[str | None, Query(description='结束日期')] = None,
) -> ResponseSchemaModel[PageData[GetAuditLogDetail]]:
    page_data = await audit_log_service.get_list(
        db=db, event_type=event_type, username=username, ip=ip,
        start_date=start_date, end_date=end_date,
    )
    return response_base.success(data=page_data)


@router.get(
    '/export',
    summary='导出审计日志',
    dependencies=[DependsJwtAuth],
)
async def export_audit_logs(
    db: CurrentSession,
    event_type: Annotated[str | None, Query(description='事件类型')] = None,
    username: Annotated[str | None, Query(description='用户名')] = None,
    ip: Annotated[str | None, Query(description='IP 地址')] = None,
    start_date: Annotated[str | None, Query(description='开始日期')] = None,
    end_date: Annotated[str | None, Query(description='结束日期')] = None,
):
    csv_content = await audit_log_service.export(
        db=db, event_type=event_type, username=username, ip=ip,
        start_date=start_date, end_date=end_date,
    )
    return StreamingResponse(
        iter([csv_content]),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename=audit_logs.csv'},
    )


@router.get(
    '/{pk}',
    summary='获取审计日志详情',
    dependencies=[DependsJwtAuth],
)
async def get_audit_log_detail(
    db: CurrentSession,
    pk: Annotated[int, Path(description='日志 ID')],
) -> ResponseSchemaModel[GetAuditLogDetail]:
    # Note: audit logs don't have a dedicated get service, so we reuse get_list with id filter
    from backend.app.admin.crud.crud_audit_log import audit_log_dao

    log = await audit_log_dao.get(db, pk)
    return response_base.success(data=log)


@router.delete(
    '',
    summary='批量删除审计日志',
    dependencies=[
        Depends(RequestPermission('log:audit:del')),
        DependsRBAC,
    ],
)
async def delete_audit_logs(db: CurrentSessionTransaction, obj: DeleteAuditLogParam) -> ResponseModel:
    count = await audit_log_service.delete(db=db, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '/all',
    summary='清空审计日志',
    dependencies=[
        Depends(RequestPermission('log:audit:clear')),
        DependsRBAC,
    ],
)
async def delete_all_audit_logs(db: CurrentSessionTransaction) -> ResponseModel:
    await audit_log_service.delete_all(db=db)
    return response_base.success()
