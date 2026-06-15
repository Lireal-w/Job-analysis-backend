from typing import Annotated

from fastapi import APIRouter, Path, Query

from backend.app.admin.schema.server import (
    CreateServerParam,
    GetServerDetail,
    TestConnectionParam,
    UpdateServerParam,
)
from backend.app.admin.service.server_service import server_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get('/all', summary='获取所有服务器', dependencies=[DependsJwtAuth])
async def get_all_servers(db: CurrentSession) -> ResponseSchemaModel[list[GetServerDetail]]:
    data = await server_service.get_all(db=db)
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取服务器详情', dependencies=[DependsJwtAuth])
async def get_server(
    db: CurrentSession,
    pk: Annotated[int, Path(description='服务器 ID')],
) -> ResponseSchemaModel[GetServerDetail]:
    data = await server_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.get(
    '',
    summary='分页获取服务器列表',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_servers_paginated(
    db: CurrentSession,
    name: Annotated[str | None, Query(description='服务器名称')] = None,
    protocol: Annotated[str | None, Query(description='协议类型(ssh/rdp/vnc/telnet/sftp/http/https)')] = None,
) -> ResponseSchemaModel[PageData[GetServerDetail]]:
    page_data = await server_service.get_list(db=db, name=name, protocol=protocol)
    return response_base.success(data=page_data)


@router.post('/test-connection', summary='测试服务器连接', dependencies=[DependsJwtAuth])
async def test_connection(obj: TestConnectionParam) -> ResponseSchemaModel[dict]:
    data = await server_service.test_connection(obj=obj)
    return response_base.success(data=data)


@router.post('', summary='创建服务器', dependencies=[DependsJwtAuth])
async def create_server(
    db: CurrentSessionTransaction,
    obj: CreateServerParam,
) -> ResponseModel:
    await server_service.create(db=db, obj=obj)
    return response_base.success()


@router.put('/{pk}', summary='更新服务器', dependencies=[DependsJwtAuth])
async def update_server(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='服务器 ID')],
    obj: UpdateServerParam,
) -> ResponseModel:
    count = await server_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.put('/{pk}/status', summary='更新服务器状态', dependencies=[DependsJwtAuth])
async def update_server_status(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='服务器 ID')],
    status: Annotated[int, Query(description='状态(0停用 1正常)')],
) -> ResponseModel:
    count = await server_service.update_status(db=db, pk=pk, status=status)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('', summary='批量删除服务器', dependencies=[DependsJwtAuth])
async def delete_servers(
    db: CurrentSessionTransaction,
    pks: Annotated[list[int], Query(description='服务器 ID 列表')],
) -> ResponseModel:
    count = await server_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()
