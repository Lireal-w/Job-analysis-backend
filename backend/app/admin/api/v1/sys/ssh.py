from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.admin.schema.ssh import (
    CreateSSHParam,
    GetSSHDetail,
    SSHTestConnectionParam,
    UpdateSSHParam,
)
from backend.app.admin.service.ssh_service import ssh_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get('/all', summary='获取所有 SSH 服务器', dependencies=[DependsJwtAuth])
async def get_all_ssh_servers(db: CurrentSession) -> ResponseSchemaModel[list[GetSSHDetail]]:
    data = await ssh_service.get_all(db=db)
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取 SSH 服务器详情', dependencies=[DependsJwtAuth])
async def get_ssh_server(
    db: CurrentSession,
    pk: Annotated[int, Path(description='SSH 服务器 ID')],
) -> ResponseSchemaModel[GetSSHDetail]:
    data = await ssh_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.get(
    '',
    summary='分页获取 SSH 服务器列表',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_ssh_servers_paginated(
    db: CurrentSession,
    name: Annotated[str | None, Query(description='服务器名称')] = None,
) -> ResponseSchemaModel[PageData[GetSSHDetail]]:
    page_data = await ssh_service.get_list(db=db, name=name)
    return response_base.success(data=page_data)


@router.post('/test-connection', summary='测试 SSH 连接', dependencies=[DependsJwtAuth])
async def test_ssh_connection(obj: SSHTestConnectionParam) -> ResponseSchemaModel[dict]:
    data = await ssh_service.test_connection(obj=obj)
    return response_base.success(data=data)


@router.post('', summary='创建 SSH 服务器', dependencies=[DependsJwtAuth])
async def create_ssh_server(
    db: CurrentSessionTransaction,
    obj: CreateSSHParam,
) -> ResponseModel:
    await ssh_service.create(db=db, obj=obj)
    return response_base.success()


@router.put('/{pk}', summary='更新 SSH 服务器', dependencies=[DependsJwtAuth])
async def update_ssh_server(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='SSH 服务器 ID')],
    obj: UpdateSSHParam,
) -> ResponseModel:
    count = await ssh_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.put('/{pk}/status', summary='更新 SSH 服务器状态', dependencies=[DependsJwtAuth])
async def update_ssh_server_status(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='SSH 服务器 ID')],
    status: Annotated[int, Query(description='状态(0停用 1正常)')],
) -> ResponseModel:
    count = await ssh_service.update_status(db=db, pk=pk, status=status)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('', summary='批量删除 SSH 服务器', dependencies=[DependsJwtAuth])
async def delete_ssh_servers(
    db: CurrentSessionTransaction,
    pks: Annotated[list[int], Query(description='SSH 服务器 ID 列表')],
) -> ResponseModel:
    count = await ssh_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()
