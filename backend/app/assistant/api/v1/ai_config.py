"""AI 助手配置管理 API"""

from typing import Annotated

from fastapi import APIRouter, Path, Query, Request

from backend.app.assistant.crud import ai_config_dao
from backend.app.assistant.schema import (
    CreateAiConfigParam,
    GetAiConfigDetail,
    UpdateAiConfigParam,
)
from backend.app.assistant.service.config_service import ai_config_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter(prefix='/ai-config', dependencies=[DependsJwtAuth])


@router.get('', summary='获取 AI 配置列表', dependencies=[DependsJwtAuth, DependsPagination])
async def get_ai_config_list(
    db: CurrentSession,
    name: Annotated[str | None, Query(description='配置名称')] = None,
    provider: Annotated[str | None, Query(description='提供商')] = None,
) -> ResponseSchemaModel[PageData[GetAiConfigDetail]]:
    page_data = await ai_config_service.get_list(
        db=db, name=name, provider=provider,
    )
    return response_base.success(data=page_data)


@router.get('/active', summary='获取当前激活的 AI 配置')
async def get_active_config(
    db: CurrentSession,
) -> ResponseSchemaModel[GetAiConfigDetail | None]:
    data = await ai_config_service.get_active(db=db)
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取 AI 配置详情')
async def get_ai_config(
    db: CurrentSession,
    pk: Annotated[int, Path(description='配置 ID')],
) -> ResponseSchemaModel[GetAiConfigDetail]:
    data = await ai_config_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.post('', summary='创建 AI 配置')
async def create_ai_config(
    db: CurrentSessionTransaction,
    request: Request,
    obj: CreateAiConfigParam,
) -> ResponseSchemaModel[GetAiConfigDetail]:
    user_id = request.user.id
    data = await ai_config_service.create(db=db, obj=obj, created_by=user_id)
    return response_base.success(data=data)


@router.put('/{pk}', summary='更新 AI 配置')
async def update_ai_config(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='配置 ID')],
    obj: UpdateAiConfigParam,
) -> ResponseSchemaModel[GetAiConfigDetail]:
    data = await ai_config_service.update(db=db, pk=pk, obj=obj)
    return response_base.success(data=data)


@router.put('/{pk}/activate', summary='激活 AI 配置')
async def activate_ai_config(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='配置 ID')],
) -> ResponseModel:
    await ai_config_service.set_active(db=db, pk=pk)
    return response_base.success()


@router.delete('', summary='删除 AI 配置')
async def delete_ai_config(
    db: CurrentSessionTransaction,
    pks: Annotated[list[int], Query(description='配置 ID 列表')],
) -> ResponseModel:
    count = await ai_config_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()
