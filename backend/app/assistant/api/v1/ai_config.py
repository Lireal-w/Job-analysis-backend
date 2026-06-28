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

# 内置 AI 服务商列表
BUILTIN_PROVIDERS = [
    {
        'provider': 'openai',
        'name': 'OpenAI',
        'api_base': 'https://api.openai.com/v1',
        'models': ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'o1-mini', 'o3-mini'],
        'default_model': 'gpt-4o-mini',
    },
    {
        'provider': 'deepseek',
        'name': 'DeepSeek',
        'api_base': 'https://api.deepseek.com',
        'models': ['deepseek-chat', 'deepseek-reasoner'],
        'default_model': 'deepseek-chat',
    },
    {
        'provider': 'anthropic',
        'name': 'Anthropic Claude',
        'api_base': 'https://api.anthropic.com/v1',
        'models': ['claude-sonnet-4-20250514', 'claude-haiku-3-5-sonnet', 'claude-opus-4-5'],
        'default_model': 'claude-sonnet-4-20250514',
    },
    {
        'provider': 'gemini',
        'name': 'Google Gemini',
        'api_base': 'https://generativelanguage.googleapis.com/v1beta',
        'models': ['gemini-2.0-flash', 'gemini-2.5-pro-exp-03-25'],
        'default_model': 'gemini-2.0-flash',
    },
    {
        'provider': 'moonshot',
        'name': 'Moonshot / 月之暗面',
        'api_base': 'https://api.moonshot.cn/v1',
        'models': ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k'],
        'default_model': 'moonshot-v1-8k',
    },
    {
        'provider': 'qwen',
        'name': '通义千问 (阿里云)',
        'api_base': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'models': ['qwen-plus', 'qwen-turbo', 'qwen-max', 'qwen2.5-72b-instruct'],
        'default_model': 'qwen-plus',
    },
    {
        'provider': 'zhipu',
        'name': '智谱清言',
        'api_base': 'https://open.bigmodel.cn/api/paas/v4',
        'models': ['glm-4-plus', 'glm-4-0520', 'glm-4-air', 'glm-4-flash'],
        'default_model': 'glm-4-plus',
    },
    {
        'provider': 'custom',
        'name': '自定义 (兼容 OpenAI API)',
        'api_base': '',
        'models': [],
        'default_model': '',
    },
]


@router.get('/providers', summary='获取内置 AI 服务商列表')
async def get_ai_providers() -> ResponseSchemaModel[list[dict]]:
    """获取系统内置的 AI 服务商列表，包含默认 API 地址和可用模型"""
    return response_base.success(data=BUILTIN_PROVIDERS)


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
