from typing import Annotated

from fastapi import APIRouter, Path, Query

from backend.app.admin.schema.worker import (
    CreateWorkerParam,
    GetWorkerDetail,
    UpdateWorkerParam,
    WorkerDispatchParam,
    WorkerHeartbeatParam,
    WorkerRegisterParam,
)
from backend.app.admin.service.worker_service import worker_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get('/all', summary='获取所有 Worker 节点', dependencies=[DependsJwtAuth])
async def get_all_workers(db: CurrentSession) -> ResponseSchemaModel[list[GetWorkerDetail]]:
    data = await worker_service.get_all(db=db)
    return response_base.success(data=data)


@router.get('/online', summary='获取在线 Worker 节点', dependencies=[DependsJwtAuth])
async def get_online_workers(db: CurrentSession) -> ResponseSchemaModel[list[GetWorkerDetail]]:
    data = await worker_service.get_online(db=db)
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取 Worker 详情', dependencies=[DependsJwtAuth])
async def get_worker(
    db: CurrentSession,
    pk: Annotated[int, Path(description='Worker ID')],
) -> ResponseSchemaModel[GetWorkerDetail]:
    data = await worker_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.get(
    '',
    summary='分页获取 Worker 列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_workers_paginated(
    db: CurrentSession,
    name: Annotated[str | None, Query(description='节点名称')] = None,
    status: Annotated[str | None, Query(description='状态(online/offline/busy)')] = None,
) -> ResponseSchemaModel[PageData[GetWorkerDetail]]:
    page_data = await worker_service.get_list(db=db, name=name, status=status)
    return response_base.success(data=page_data)


@router.post('/register', summary='Worker 注册（从节点调用）')
async def register_worker(
    db: CurrentSessionTransaction,
    obj: WorkerRegisterParam,
) -> ResponseSchemaModel[dict]:
    """从节点启动时调用此接口注册到主节点"""
    data = await worker_service.register(db=db, obj=obj)
    return response_base.success(data={
        'id': data.id,
        'name': data.name,
        'api_key': data.api_key,
        'status': data.status,
    })


@router.put('/{pk}/heartbeat', summary='Worker 心跳上报（从节点调用）')
async def worker_heartbeat(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='Worker ID')],
    obj: WorkerHeartbeatParam,
) -> ResponseModel:
    await worker_service.heartbeat(db=db, pk=pk, obj=obj)
    return response_base.success()


@router.post('/dispatch', summary='分发爬虫任务到 Worker', dependencies=[DependsJwtAuth])
async def dispatch_task(
    db: CurrentSessionTransaction,
    obj: WorkerDispatchParam,
) -> ResponseSchemaModel[dict]:
    data = await worker_service.dispatch_task(db=db, obj=obj)
    return response_base.success(data=data)


@router.post('/check-offline', summary='检查并标记离线 Worker', dependencies=[DependsJwtAuth])
async def check_offline_workers(
    db: CurrentSessionTransaction,
    minutes: Annotated[int, Query(description='超时分钟数')] = 5,
) -> ResponseModel:
    count = await worker_service.dispatch_offline_check(db=db, minutes=minutes)
    return response_base.success(data={'marked_offline': count})


@router.post('', summary='创建 Worker 节点', dependencies=[DependsJwtAuth])
async def create_worker(
    db: CurrentSessionTransaction,
    obj: CreateWorkerParam,
) -> ResponseModel:
    await worker_service.create(db=db, obj=obj)
    return response_base.success()


@router.put('/{pk}', summary='更新 Worker 节点', dependencies=[DependsJwtAuth])
async def update_worker(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='Worker ID')],
    obj: UpdateWorkerParam,
) -> ResponseModel:
    count = await worker_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('', summary='批量删除 Worker 节点', dependencies=[DependsJwtAuth])
async def delete_workers(
    db: CurrentSessionTransaction,
    pks: Annotated[list[int], Query(description='Worker ID 列表')],
) -> ResponseModel:
    count = await worker_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()
