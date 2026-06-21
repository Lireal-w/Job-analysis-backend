from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from backend.app.admin.schema.data_storage import (
    CreateDataLayerParam,
    CreateDatasetParam,
    GetDataLayerDetail,
    GetDatasetDetail,
    UpdateDataLayerParam,
    UpdateDatasetParam,
)
from backend.app.admin.service.data_storage_service import data_layer_service, dataset_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


def _get_dept_id(request: Request) -> int | None:
    """非超级管理员时返回当前用户的部门ID用于数据隔离"""
    if request.user.is_superuser:
        return None
    return request.user.dept_id


# ── 数据分层 ──────────────────────────────────────────────


@router.get('/layers/all', summary='获取所有数据分层', dependencies=[DependsJwtAuth])
async def get_all_layers(db: CurrentSession) -> ResponseSchemaModel[list[GetDataLayerDetail]]:
    data = await data_layer_service.get_all(db=db)
    return response_base.success(data=data)


@router.get('/layers/{pk}', summary='获取数据分层详情', dependencies=[DependsJwtAuth])
async def get_data_layer(
    db: CurrentSession,
    pk: Annotated[int, Path(description='分层 ID')],
) -> ResponseSchemaModel[GetDataLayerDetail]:
    data = await data_layer_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.get(
    '/layers',
    summary='获取数据分层列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_layers_paginated(
    db: CurrentSession,
) -> ResponseSchemaModel[PageData[GetDataLayerDetail]]:
    page_data = await data_layer_service.get_list(db=db)
    return response_base.success(data=page_data)


@router.post('/layers', summary='创建数据分层', dependencies=[DependsJwtAuth])
async def create_data_layer(
    db: CurrentSessionTransaction,
    obj: CreateDataLayerParam,
) -> ResponseModel:
    await data_layer_service.create(db=db, obj=obj)
    return response_base.success()


@router.put('/layers/{pk}', summary='更新数据分层', dependencies=[DependsJwtAuth])
async def update_data_layer(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='分层 ID')],
    obj: UpdateDataLayerParam,
) -> ResponseModel:
    count = await data_layer_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('/layers', summary='批量删除数据分层', dependencies=[DependsJwtAuth])
async def delete_data_layers(
    db: CurrentSessionTransaction,
    pks: Annotated[list[int], Query(description='分层 ID 列表')],
) -> ResponseModel:
    count = await data_layer_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()


# ── 数据集 ────────────────────────────────────────────────


@router.get('/datasets/all', summary='获取所有数据集', dependencies=[DependsJwtAuth])
async def get_all_datasets(
    db: CurrentSession,
    request: Request,
) -> ResponseSchemaModel[list[GetDatasetDetail]]:
    data = await dataset_service.get_all(db=db, dept_id=_get_dept_id(request))
    return response_base.success(data=data)


@router.get('/datasets/{pk}', summary='获取数据集详情', dependencies=[DependsJwtAuth])
async def get_dataset(
    db: CurrentSession,
    request: Request,
    pk: Annotated[int, Path(description='数据集 ID')],
) -> ResponseSchemaModel[GetDatasetDetail]:
    data = await dataset_service.get(db=db, pk=pk, dept_id=_get_dept_id(request))
    return response_base.success(data=data)


@router.get(
    '/datasets',
    summary='分页获取数据集列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_datasets_paginated(
    db: CurrentSession,
    request: Request,
    name: Annotated[str | None, Query(description='数据集名称')] = None,
    layer_id: Annotated[int | None, Query(description='数据层 ID')] = None,
    status: Annotated[int | None, Query(description='状态(0停用 1正常)')] = None,
) -> ResponseSchemaModel[PageData[GetDatasetDetail]]:
    page_data = await dataset_service.get_list(db=db, name=name, layer_id=layer_id, status=status, dept_id=_get_dept_id(request))
    return response_base.success(data=page_data)


@router.post('/datasets', summary='创建数据集', dependencies=[
    Depends(RequestPermission('dataset:add')),
    DependsRBAC,
])
async def create_dataset(
    db: CurrentSessionTransaction,
    request: Request,
    obj: CreateDatasetParam,
) -> ResponseModel:
    # 自动设置部门ID
    if obj.dept_id is None and not request.user.is_superuser:
        obj.dept_id = request.user.dept_id
    await dataset_service.create(db=db, obj=obj)
    return response_base.success()


@router.put('/datasets/{pk}', summary='更新数据集', dependencies=[
    Depends(RequestPermission('dataset:edit')),
    DependsRBAC,
])
async def update_dataset(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='数据集 ID')],
    obj: UpdateDatasetParam,
) -> ResponseModel:
    # 先检查数据集是否存在且属于当前用户部门
    await dataset_service.get(db=db, pk=pk, dept_id=_get_dept_id(request))
    count = await dataset_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('/datasets', summary='批量删除数据集', dependencies=[
    Depends(RequestPermission('dataset:del')),
    DependsRBAC,
])
async def delete_datasets(
    db: CurrentSessionTransaction,
    request: Request,
    pks: Annotated[list[int], Query(description='数据集 ID 列表')],
) -> ResponseModel:
    # 非管理员逐个校验部门权限
    dept_id = _get_dept_id(request)
    if dept_id is not None:
        for pk in pks:
            await dataset_service.get(db=db, pk=pk, dept_id=dept_id)
    count = await dataset_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()
