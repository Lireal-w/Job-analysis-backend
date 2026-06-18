from typing import Annotated

from fastapi import APIRouter, Path, Query

from backend.app.admin.schema.data_quality import (
    CreateQualityRuleParam,
    GetQualityCheckDetail,
    GetQualityRuleDetail,
    UpdateQualityRuleParam,
)
from backend.app.admin.service.data_quality_service import quality_rule_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get('/rules/all', summary='获取所有质量规则', dependencies=[DependsJwtAuth])
async def get_all_quality_rules(db: CurrentSession) -> ResponseSchemaModel[list[GetQualityRuleDetail]]:
    data = await quality_rule_service.get_all(db=db)
    return response_base.success(data=data)


@router.get('/rules/{pk}', summary='获取质量规则详情', dependencies=[DependsJwtAuth])
async def get_quality_rule(
    db: CurrentSession,
    pk: Annotated[int, Path(description='规则 ID')],
) -> ResponseSchemaModel[GetQualityRuleDetail]:
    data = await quality_rule_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.get(
    '/rules',
    summary='分页获取质量规则列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_quality_rules_paginated(
    db: CurrentSession,
    name: Annotated[str | None, Query(description='规则名称')] = None,
    rule_type: Annotated[str | None, Query(description='规则类型')] = None,
    severity: Annotated[str | None, Query(description='严重级别')] = None,
    enabled: Annotated[bool | None, Query(description='是否启用')] = None,
) -> ResponseSchemaModel[PageData[GetQualityRuleDetail]]:
    page_data = await quality_rule_service.get_list(
        db=db,
        name=name,
        rule_type=rule_type,
        severity=severity,
        enabled=enabled,
    )
    return response_base.success(data=page_data)


@router.post('/rules', summary='创建质量规则', dependencies=[DependsJwtAuth])
async def create_quality_rule(
    db: CurrentSessionTransaction,
    obj: CreateQualityRuleParam,
) -> ResponseModel:
    await quality_rule_service.create(db=db, obj=obj)
    return response_base.success()


@router.put('/rules/{pk}', summary='更新质量规则', dependencies=[DependsJwtAuth])
async def update_quality_rule(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='规则 ID')],
    obj: UpdateQualityRuleParam,
) -> ResponseModel:
    count = await quality_rule_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('/rules', summary='批量删除质量规则', dependencies=[DependsJwtAuth])
async def delete_quality_rules(
    db: CurrentSessionTransaction,
    pks: Annotated[list[int], Query(description='规则 ID 列表')],
) -> ResponseModel:
    count = await quality_rule_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post('/rules/{pk}/check', summary='运行质量检查', dependencies=[DependsJwtAuth])
async def run_quality_check(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='规则 ID')],
) -> ResponseSchemaModel[dict]:
    data = await quality_rule_service.run_check(db=db, pk=pk)
    return response_base.success(data=data)


@router.get('/rules/{pk}/checks', summary='获取规则检查记录', dependencies=[DependsJwtAuth])
async def get_rule_checks(
    db: CurrentSession,
    pk: Annotated[int, Path(description='规则 ID')],
) -> ResponseSchemaModel[list[GetQualityCheckDetail]]:
    data = await quality_rule_service.get_checks(db=db, pk=pk)
    return response_base.success(data=data)


@router.get('/checks/{check_id}', summary='获取检查记录详情', dependencies=[DependsJwtAuth])
async def get_check_detail(
    db: CurrentSession,
    check_id: Annotated[int, Path(description='检查记录 ID')],
) -> ResponseSchemaModel[GetQualityCheckDetail]:
    data = await quality_rule_service.get_check_detail(db=db, check_id=check_id)
    return response_base.success(data=data)
