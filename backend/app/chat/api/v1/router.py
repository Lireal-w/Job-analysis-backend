"""聊天 REST API - 会话和消息管理"""

from typing import Annotated

from fastapi import APIRouter, Path, Query, Request
from pydantic import BaseModel, Field

from backend.app.chat.service import chat_service
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth

router = APIRouter()


class CreateConversationBody(BaseModel):
    """创建会话请求体"""
    conv_type: str = Field(default='private', description='会话类型(private/group)')
    name: str | None = Field(default=None, description='群聊名称')
    member_ids: list[int] = Field(default_factory=list, description='成员用户 ID 列表')


@router.post('/conversations', summary='创建会话', dependencies=[DependsJwtAuth])
async def create_conversation(
    request: Request,
    body: CreateConversationBody,
) -> ResponseSchemaModel[dict]:
    """创建私聊或群聊会话"""
    all_members = list(set([request.user.id] + body.member_ids))
    data = await chat_service.create_conversation(
        conv_type=body.conv_type,
        name=body.name,
        created_by=request.user.id,
        member_ids=all_members,
    )
    return response_base.success(data=data)


@router.get('/conversations', summary='获取会话列表', dependencies=[DependsJwtAuth])
async def get_conversations(
    request: Request,
) -> ResponseSchemaModel[list[dict]]:
    """获取当前用户的会话列表"""
    data = await chat_service.get_user_conversations(user_id=request.user.id)
    return response_base.success(data=data)


@router.get('/conversations/{conv_id}', summary='获取会话详情', dependencies=[DependsJwtAuth])
async def get_conversation(
    conv_id: Annotated[str, Path(description='会话 ID')],
) -> ResponseSchemaModel[dict | None]:
    """获取会话详情"""
    data = await chat_service.get_conversation(conv_id=conv_id)
    return response_base.success(data=data)


@router.post('/conversations/{conv_id}/members', summary='添加群成员', dependencies=[DependsJwtAuth])
async def add_member(
    conv_id: Annotated[str, Path(description='会话 ID')],
    user_id: int = Query(description='用户 ID'),
) -> ResponseModel:
    ok = await chat_service.add_member(conv_id=conv_id, user_id=user_id)
    return response_base.success() if ok else response_base.fail()


@router.delete('/conversations/{conv_id}/members/{user_id}', summary='移除群成员', dependencies=[DependsJwtAuth])
async def remove_member(
    conv_id: Annotated[str, Path(description='会话 ID')],
    user_id: Annotated[int, Path(description='用户 ID')],
) -> ResponseModel:
    ok = await chat_service.remove_member(conv_id=conv_id, user_id=user_id)
    return response_base.success() if ok else response_base.fail()


@router.get('/conversations/{conv_id}/messages', summary='获取聊天消息', dependencies=[DependsJwtAuth])
async def get_messages(
    conv_id: Annotated[str, Path(description='会话 ID')],
    page: Annotated[int, Query(ge=1, description='页码')] = 1,
    size: Annotated[int, Query(gt=0, le=100, description='每页数量')] = 50,
) -> ResponseSchemaModel[dict]:
    """分页获取会话消息"""
    data = await chat_service.get_messages(conv_id=conv_id, page=page, size=size)
    return response_base.success(data=data)
