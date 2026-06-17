from typing import Annotated

from fastapi import APIRouter, Path, Query

from backend.app.admin.schema.data_flow import (
    CreateDataFlowParam,
    GetDataFlowDetail,
    GetDataFlowRunDetail,
    UpdateDataFlowParam,
)
from backend.app.admin.service.data_flow_service import data_flow_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get('/all', summary='获取所有数据流', dependencies=[DependsJwtAuth])
async def get_all_data_flows(db: CurrentSession) -> ResponseSchemaModel[list[GetDataFlowDetail]]:
    data = await data_flow_service.get_all(db=db)
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取数据流详情', dependencies=[DependsJwtAuth])
async def get_data_flow(
    db: CurrentSession,
    pk: Annotated[int, Path(description='数据流 ID')],
) -> ResponseSchemaModel[GetDataFlowDetail]:
    data = await data_flow_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.get(
    '',
    summary='分页获取数据流列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_data_flows_paginated(
    db: CurrentSession,
    name: Annotated[str | None, Query(description='流程名称')] = None,
    status: Annotated[str | None, Query(description='状态(draft/published/archived)')] = None,
) -> ResponseSchemaModel[PageData[GetDataFlowDetail]]:
    page_data = await data_flow_service.get_list(db=db, name=name, status=status)
    return response_base.success(data=page_data)


@router.post('', summary='创建数据流', dependencies=[DependsJwtAuth])
async def create_data_flow(
    db: CurrentSessionTransaction,
    obj: CreateDataFlowParam,
) -> ResponseModel:
    await data_flow_service.create(db=db, obj=obj)
    return response_base.success()


@router.put('/{pk}', summary='更新数据流', dependencies=[DependsJwtAuth])
async def update_data_flow(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='数据流 ID')],
    obj: UpdateDataFlowParam,
) -> ResponseModel:
    count = await data_flow_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('', summary='批量删除数据流', dependencies=[DependsJwtAuth])
async def delete_data_flows(
    db: CurrentSessionTransaction,
    pks: Annotated[list[int], Query(description='数据流 ID 列表')],
) -> ResponseModel:
    count = await data_flow_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post('/{pk}/publish', summary='发布数据流', dependencies=[DependsJwtAuth])
async def publish_data_flow(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='数据流 ID')],
) -> ResponseModel:
    count = await data_flow_service.publish_flow(db=db, pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post('/{pk}/run', summary='运行数据流', dependencies=[DependsJwtAuth])
async def run_data_flow(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='数据流 ID')],
) -> ResponseSchemaModel[dict]:
    data = await data_flow_service.run_flow(db=db, pk=pk)
    return response_base.success(data=data)


@router.get('/{pk}/runs', summary='获取数据流运行记录', dependencies=[DependsJwtAuth])
async def get_data_flow_runs(
    db: CurrentSession,
    pk: Annotated[int, Path(description='数据流 ID')],
) -> ResponseSchemaModel[list[GetDataFlowRunDetail]]:
    data = await data_flow_service.get_runs(db=db, pk=pk)
    return response_base.success(data=data)


@router.get('/runs/{run_id}', summary='获取运行记录详情', dependencies=[DependsJwtAuth])
async def get_data_flow_run_detail(
    db: CurrentSession,
    run_id: Annotated[int, Path(description='运行记录 ID')],
) -> ResponseSchemaModel[GetDataFlowRunDetail]:
    data = await data_flow_service.get_run_detail(db=db, run_id=run_id)
    return response_base.success(data=data)
