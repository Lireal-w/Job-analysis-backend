from typing import Annotated

from fastapi import APIRouter, Path, Query

from backend.app.admin.schema.query import (
    CreateSavedQueryParam,
    ExecuteQueryParam,
    GetQueryHistoryDetail,
    GetSavedQueryDetail,
    QueryResultSchema,
    UpdateSavedQueryParam,
)
from backend.app.admin.service.query_service import query_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.post('/execute', summary='执行查询', dependencies=[DependsJwtAuth])
async def execute_query(
    db: CurrentSessionTransaction,
    obj: ExecuteQueryParam,
) -> ResponseSchemaModel[QueryResultSchema]:
    data = await query_service.execute_query(db=db, obj=obj)
    return response_base.success(data=data)


@router.get('/history', summary='获取查询历史', dependencies=[DependsJwtAuth, DependsPagination])
async def get_query_history(
    db: CurrentSession,
) -> ResponseSchemaModel[PageData[GetQueryHistoryDetail]]:
    page_data = await query_service.get_history(db=db)
    return response_base.success(data=page_data)


@router.get('/history/{pk}', summary='获取查询历史详情', dependencies=[DependsJwtAuth])
async def get_query_history_detail(
    db: CurrentSession,
    pk: Annotated[int, Path(description='查询历史 ID')],
) -> ResponseSchemaModel[GetQueryHistoryDetail]:
    data = await query_service.get_history_detail(db=db, pk=pk)
    return response_base.success(data=data)


@router.get('/saved', summary='获取保存的查询列表', dependencies=[DependsJwtAuth, DependsPagination])
async def get_saved_queries(
    db: CurrentSession,
    name: Annotated[str | None, Query(description='查询名称')] = None,
    dataset_id: Annotated[int | None, Query(description='数据集 ID')] = None,
) -> ResponseSchemaModel[PageData[GetSavedQueryDetail]]:
    page_data = await query_service.get_saved_queries(db=db, name=name, dataset_id=dataset_id)
    return response_base.success(data=page_data)


@router.get('/saved/{pk}', summary='获取保存的查询详情', dependencies=[DependsJwtAuth])
async def get_saved_query(
    db: CurrentSession,
    pk: Annotated[int, Path(description='保存的查询 ID')],
) -> ResponseSchemaModel[GetSavedQueryDetail]:
    data = await query_service.get_saved_query(db=db, pk=pk)
    return response_base.success(data=data)


@router.post('/saved', summary='保存查询', dependencies=[DependsJwtAuth])
async def save_query(
    db: CurrentSessionTransaction,
    obj: CreateSavedQueryParam,
) -> ResponseSchemaModel[GetSavedQueryDetail]:
    data = await query_service.save_query(db=db, obj=obj)
    return response_base.success(data=data)


@router.put('/saved/{pk}', summary='更新保存的查询', dependencies=[DependsJwtAuth])
async def update_saved_query(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='保存的查询 ID')],
    obj: UpdateSavedQueryParam,
) -> ResponseModel:
    count = await query_service.update_saved_query(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('/saved', summary='批量删除保存的查询', dependencies=[DependsJwtAuth])
async def delete_saved_queries(
    db: CurrentSessionTransaction,
    pks: Annotated[list[int], Query(description='保存的查询 ID 列表')],
) -> ResponseModel:
    count = await query_service.delete_saved_query(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.get('/schema/{dataset_id}', summary='获取数据源表结构', dependencies=[DependsJwtAuth])
async def get_datasource_schema(
    db: CurrentSession,
    dataset_id: Annotated[int, Path(description='数据源 ID')],
) -> ResponseSchemaModel[dict]:
    """获取数据源的表结构信息，用于查询构建器"""
    data = await query_service.get_datasource_schema(db=db, dataset_id=dataset_id)
    return response_base.success(data=data)
