from typing import Annotated

from fastapi import APIRouter, Path, Query

from backend.app.admin.schema.datasource import (
    CreateDatasourceParam,
    DatasourceTestParam,
    GetDatasourceDetail,
    UpdateDatasourceParam,
)
from backend.app.admin.service.datasource_service import datasource_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get('/all', summary='获取所有数据源', dependencies=[DependsJwtAuth])
async def get_all_datasources(db: CurrentSession) -> ResponseSchemaModel[list[GetDatasourceDetail]]:
    data = await datasource_service.get_all(db=db)
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取数据源详情', dependencies=[DependsJwtAuth])
async def get_datasource(
    db: CurrentSession,
    pk: Annotated[int, Path(description='数据源 ID')],
) -> ResponseSchemaModel[GetDatasourceDetail]:
    data = await datasource_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.get(
    '',
    summary='分页获取数据源列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_datasources_paginated(
    db: CurrentSession,
    name: Annotated[str | None, Query(description='数据源名称')] = None,
    db_type: Annotated[str | None, Query(description='数据库类型')] = None,
) -> ResponseSchemaModel[PageData[GetDatasourceDetail]]:
    page_data = await datasource_service.get_list(db=db, name=name, db_type=db_type)
    return response_base.success(data=page_data)


@router.post('/test-connection', summary='测试数据源连接', dependencies=[DependsJwtAuth])
async def test_datasource_connection(obj: DatasourceTestParam) -> ResponseSchemaModel[dict]:
    data = await datasource_service.test_connection(obj=obj)
    return response_base.success(data=data)


@router.post('', summary='创建数据源', dependencies=[DependsJwtAuth])
async def create_datasource(
    db: CurrentSessionTransaction,
    obj: CreateDatasourceParam,
) -> ResponseModel:
    await datasource_service.create(db=db, obj=obj)
    return response_base.success()


@router.put('/{pk}', summary='更新数据源', dependencies=[DependsJwtAuth])
async def update_datasource(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='数据源 ID')],
    obj: UpdateDatasourceParam,
) -> ResponseModel:
    count = await datasource_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.put('/{pk}/status', summary='更新数据源状态', dependencies=[DependsJwtAuth])
async def update_datasource_status(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='数据源 ID')],
    status: Annotated[int, Query(description='状态(0停用 1正常)')],
) -> ResponseModel:
    count = await datasource_service.update_status(db=db, pk=pk, status=status)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('', summary='批量删除数据源', dependencies=[DependsJwtAuth])
async def delete_datasources(
    db: CurrentSessionTransaction,
    pks: Annotated[list[int], Query(description='数据源 ID 列表')],
) -> ResponseModel:
    count = await datasource_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()
