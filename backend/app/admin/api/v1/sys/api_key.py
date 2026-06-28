from typing import Annotated

from fastapi import APIRouter, Path, Query, Request

from backend.app.admin.schema.api_key import (
    CreateApiKeyParam,
    CreateApiKeyResponse,
    GetApiKeyDetail,
    RegenerateApiKeyResponse,
    UpdateApiKeyParam,
)
from backend.app.admin.service.api_key_service import api_key_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get('/all', summary='获取所有 API 密钥', dependencies=[DependsJwtAuth])
async def get_all_api_keys(db: CurrentSession) -> ResponseSchemaModel[list[GetApiKeyDetail]]:
    data = await api_key_service.get_all(db=db)
    return response_base.success(data=data)


@router.get('/my', summary='获取当前用户的 API 密钥列表', dependencies=[DependsJwtAuth])
async def get_my_api_keys(
    request: Request,
    db: CurrentSession,
) -> ResponseSchemaModel[list[GetApiKeyDetail]]:
    data = await api_key_service.get_by_user_id(db=db, user_id=request.user.id)
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取 API 密钥详情', dependencies=[DependsJwtAuth])
async def get_api_key(
    db: CurrentSession,
    pk: Annotated[int, Path(description='API 密钥 ID')],
) -> ResponseSchemaModel[GetApiKeyDetail]:
    data = await api_key_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.get(
    '',
    summary='分页获取 API 密钥列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_api_keys_paginated(
    db: CurrentSession,
    user_id: Annotated[int | None, Query(description='创建者用户 ID')] = None,
    is_active: Annotated[int | None, Query(description='状态')] = None,
) -> ResponseSchemaModel[PageData[GetApiKeyDetail]]:
    page_data = await api_key_service.get_list(db=db, user_id=user_id, is_active=is_active)
    return response_base.success(data=page_data)


@router.post('', summary='创建 API 密钥', dependencies=[DependsJwtAuth])
async def create_api_key(
    request: Request,
    db: CurrentSessionTransaction,
    obj: CreateApiKeyParam,
) -> ResponseSchemaModel[CreateApiKeyResponse]:
    """创建 API 密钥，返回完整密钥（仅展示一次）"""
    data = await api_key_service.create(db=db, user_id=request.user.id, obj=obj)
    return response_base.success(data=data)


@router.put('/{pk}', summary='更新 API 密钥', dependencies=[DependsJwtAuth])
async def update_api_key(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='API 密钥 ID')],
    obj: UpdateApiKeyParam,
) -> ResponseModel:
    count = await api_key_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.put('/{pk}/regenerate', summary='重新生成 API 密钥', dependencies=[DependsJwtAuth])
async def regenerate_api_key(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='API 密钥 ID')],
) -> ResponseSchemaModel[RegenerateApiKeyResponse]:
    """重新生成密钥值，旧的密钥将立即失效"""
    data = await api_key_service.regenerate(db=db, pk=pk)
    return response_base.success(data=data)


@router.delete('', summary='批量删除 API 密钥', dependencies=[DependsJwtAuth])
async def delete_api_keys(
    db: CurrentSessionTransaction,
    pks: Annotated[list[int], Query(description='API 密钥 ID 列表')],
) -> ResponseModel:
    count = await api_key_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()
