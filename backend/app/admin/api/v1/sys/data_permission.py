from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.admin.schema.data_permission import (
    CreateDataMaskingRuleParam,
    CreateResourcePermissionParam,
    GetDataMaskingRuleDetail,
    GetResourcePermissionDetail,
    UpdateDataMaskingRuleParam,
    UpdateResourcePermissionParam,
)
from backend.app.admin.service.data_permission_service import (
    data_masking_rule_service,
    resource_permission_service,
)
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


# ── Resource Permissions ─────────────────────────────────────


@router.get('/permissions/all', summary='获取所有资源权限', dependencies=[DependsJwtAuth])
async def get_all_permissions(db: CurrentSession) -> ResponseSchemaModel[list[GetResourcePermissionDetail]]:
    data = await resource_permission_service.get_all(db=db)
    return response_base.success(data=data)


@router.get('/permissions/{pk}', summary='获取资源权限详情', dependencies=[DependsJwtAuth])
async def get_permission(
    db: CurrentSession,
    pk: Annotated[int, Path(description='权限 ID')],
) -> ResponseSchemaModel[GetResourcePermissionDetail]:
    data = await resource_permission_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.get(
    '/permissions',
    summary='分页获取资源权限列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_permissions_paginated(
    db: CurrentSession,
    name: Annotated[str | None, Query(description='权限名称')] = None,
    resource_type: Annotated[str | None, Query(description='资源类型')] = None,
    role_id: Annotated[int | None, Query(description='角色 ID')] = None,
) -> ResponseSchemaModel[PageData[GetResourcePermissionDetail]]:
    page_data = await resource_permission_service.get_list(db=db, name=name, resource_type=resource_type, role_id=role_id)
    return response_base.success(data=page_data)


@router.post('/permissions', summary='创建资源权限', dependencies=[DependsJwtAuth])
async def create_permission(
    db: CurrentSessionTransaction,
    obj: CreateResourcePermissionParam,
) -> ResponseModel:
    await resource_permission_service.create(db=db, obj=obj)
    return response_base.success()


@router.put('/permissions/{pk}', summary='更新资源权限', dependencies=[DependsJwtAuth])
async def update_permission(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='权限 ID')],
    obj: UpdateResourcePermissionParam,
) -> ResponseModel:
    count = await resource_permission_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '/permissions',
    summary='批量删除资源权限',
    dependencies=[
        Depends(RequestPermission('sys:permission:del')),
        DependsRBAC,
    ],
)
async def delete_permissions(
    db: CurrentSessionTransaction,
    pks: Annotated[list[int], Query(description='权限 ID 列表')],
) -> ResponseModel:
    count = await resource_permission_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()


# ── Data Masking Rules ───────────────────────────────────────


@router.get('/masking-rules/all', summary='获取所有脱敏规则', dependencies=[DependsJwtAuth])
async def get_all_masking_rules(db: CurrentSession) -> ResponseSchemaModel[list[GetDataMaskingRuleDetail]]:
    data = await data_masking_rule_service.get_all(db=db)
    return response_base.success(data=data)


@router.get('/masking-rules/{pk}', summary='获取脱敏规则详情', dependencies=[DependsJwtAuth])
async def get_masking_rule(
    db: CurrentSession,
    pk: Annotated[int, Path(description='规则 ID')],
) -> ResponseSchemaModel[GetDataMaskingRuleDetail]:
    data = await data_masking_rule_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.get(
    '/masking-rules',
    summary='分页获取脱敏规则列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_masking_rules_paginated(
    db: CurrentSession,
    name: Annotated[str | None, Query(description='规则名称')] = None,
    mask_type: Annotated[str | None, Query(description='脱敏类型')] = None,
) -> ResponseSchemaModel[PageData[GetDataMaskingRuleDetail]]:
    page_data = await data_masking_rule_service.get_list(db=db, name=name, mask_type=mask_type)
    return response_base.success(data=page_data)


@router.post('/masking-rules', summary='创建脱敏规则', dependencies=[DependsJwtAuth])
async def create_masking_rule(
    db: CurrentSessionTransaction,
    obj: CreateDataMaskingRuleParam,
) -> ResponseModel:
    await data_masking_rule_service.create(db=db, obj=obj)
    return response_base.success()


@router.put('/masking-rules/{pk}', summary='更新脱敏规则', dependencies=[DependsJwtAuth])
async def update_masking_rule(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='规则 ID')],
    obj: UpdateDataMaskingRuleParam,
) -> ResponseModel:
    count = await data_masking_rule_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '/masking-rules',
    summary='批量删除脱敏规则',
    dependencies=[
        Depends(RequestPermission('sys:masking:del')),
        DependsRBAC,
    ],
)
async def delete_masking_rules(
    db: CurrentSessionTransaction,
    pks: Annotated[list[int], Query(description='规则 ID 列表')],
) -> ResponseModel:
    count = await data_masking_rule_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()
