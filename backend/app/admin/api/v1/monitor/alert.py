from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.admin.schema.alert import (
    CreateAlertRuleParam,
    GetAlertHistoryDetail,
    GetAlertRuleDetail,
    UpdateAlertRuleParam,
)
from backend.app.admin.service.alert_service import alert_history_service, alert_rule_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


# ── Alert Rules ──────────────────────────────────────────────


@router.get('/rules/all', summary='获取所有告警规则', dependencies=[DependsJwtAuth])
async def get_all_rules(db: CurrentSession) -> ResponseSchemaModel[list[GetAlertRuleDetail]]:
    data = await alert_rule_service.get_all(db=db)
    return response_base.success(data=data)


@router.get('/rules/{pk}', summary='获取告警规则详情', dependencies=[DependsJwtAuth])
async def get_rule(
    db: CurrentSession,
    pk: Annotated[int, Path(description='规则 ID')],
) -> ResponseSchemaModel[GetAlertRuleDetail]:
    data = await alert_rule_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.get(
    '/rules',
    summary='分页获取告警规则列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_rules_paginated(
    db: CurrentSession,
    name: Annotated[str | None, Query(description='规则名称')] = None,
    metric_type: Annotated[str | None, Query(description='指标类型')] = None,
    severity: Annotated[str | None, Query(description='严重级别')] = None,
    enabled: Annotated[bool | None, Query(description='是否启用')] = None,
) -> ResponseSchemaModel[PageData[GetAlertRuleDetail]]:
    page_data = await alert_rule_service.get_list(
        db=db, name=name, metric_type=metric_type, severity=severity, enabled=enabled,
    )
    return response_base.success(data=page_data)


@router.post('/rules', summary='创建告警规则', dependencies=[DependsJwtAuth])
async def create_rule(
    db: CurrentSessionTransaction,
    obj: CreateAlertRuleParam,
) -> ResponseModel:
    await alert_rule_service.create(db=db, obj=obj)
    return response_base.success()


@router.put('/rules/{pk}', summary='更新告警规则', dependencies=[DependsJwtAuth])
async def update_rule(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='规则 ID')],
    obj: UpdateAlertRuleParam,
) -> ResponseModel:
    count = await alert_rule_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '/rules',
    summary='批量删除告警规则',
    dependencies=[
        Depends(RequestPermission('monitor:alert:del')),
        DependsRBAC,
    ],
)
async def delete_rules(
    db: CurrentSessionTransaction,
    pks: Annotated[list[int], Query(description='规则 ID 列表')],
) -> ResponseModel:
    count = await alert_rule_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()


# ── Alert History ────────────────────────────────────────────


@router.get(
    '/history',
    summary='分页获取告警历史',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_history_paginated(
    db: CurrentSession,
    rule_id: Annotated[int | None, Query(description='规则 ID')] = None,
    severity: Annotated[str | None, Query(description='严重级别')] = None,
    status: Annotated[str | None, Query(description='状态')] = None,
) -> ResponseSchemaModel[PageData[GetAlertHistoryDetail]]:
    page_data = await alert_history_service.get_list(
        db=db, rule_id=rule_id, severity=severity, status=status,
    )
    return response_base.success(data=page_data)


@router.get('/history/{pk}', summary='获取告警历史详情', dependencies=[DependsJwtAuth])
async def get_history_detail(
    db: CurrentSession,
    pk: Annotated[int, Path(description='历史 ID')],
) -> ResponseSchemaModel[GetAlertHistoryDetail]:
    data = await alert_history_service.get(db=db, pk=pk)
    return response_base.success(data=data)
