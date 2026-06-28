"""Agent 开发节点 API（管理端）"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.agent_dev.enums import DevAgentType
from backend.app.agent_dev.schema.dev_agent import (
    CreateAgentDevAgentParam,
    GetAgentDevAgentDetail,
    UpdateAgentDevAgentHeartbeatParam,
    UpdateAgentDevAgentParam,
)
from backend.app.agent_dev.service.dev_agent_service import dev_agent_service
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get('/all', summary='获取所有 Agent 节点', dependencies=[DependsJwtAuth])
async def get_all_agents(db: CurrentSession) -> ResponseSchemaModel[list[GetAgentDevAgentDetail]]:
    data = await dev_agent_service.get_all(db=db)
    return response_base.success(data=data)


@router.get('/available', summary='获取可用 Agent 节点', dependencies=[DependsJwtAuth])
async def get_available_agents(
    db: CurrentSession,
    agent_type: Annotated[str | None, Query(description='Agent 类型(coder/reviewer/tester/orchestrator/devops)')] = None,
) -> ResponseSchemaModel[list[GetAgentDevAgentDetail]]:
    atype = DevAgentType(agent_type) if agent_type else None
    data = await dev_agent_service.get_available(db=db, agent_type=atype)
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取 Agent 详情', dependencies=[DependsJwtAuth])
async def get_agent(
    db: CurrentSession,
    pk: Annotated[int, Path(description='Agent ID')],
) -> ResponseSchemaModel[GetAgentDevAgentDetail]:
    data = await dev_agent_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.post('', summary='注册 Agent 节点', dependencies=[DependsJwtAuth])
async def create_agent(
    db: CurrentSessionTransaction,
    obj: CreateAgentDevAgentParam,
) -> ResponseSchemaModel[GetAgentDevAgentDetail]:
    data = await dev_agent_service.create(db=db, obj=obj)
    return response_base.success(data=data)


@router.put('/{pk}', summary='更新 Agent 节点', dependencies=[DependsJwtAuth])
async def update_agent(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='Agent ID')],
    obj: UpdateAgentDevAgentParam,
) -> ResponseModel:
    count = await dev_agent_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.put('/{pk}/heartbeat', summary='Agent 心跳上报')
async def agent_heartbeat(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='Agent ID')],
    obj: UpdateAgentDevAgentHeartbeatParam,
) -> ResponseModel:
    await dev_agent_service.heartbeat(db=db, pk=pk, obj=obj)
    return response_base.success()


@router.delete('', summary='删除 Agent 节点', dependencies=[DependsJwtAuth])
async def delete_agents(
    db: CurrentSessionTransaction,
    pks: Annotated[str, Query(description='Agent ID 列表(逗号分隔)')],
) -> ResponseModel:
    pk_list = [int(pk.strip()) for pk in pks.split(',')]
    count = await dev_agent_service.delete(db=db, pks=pk_list)
    if count > 0:
        return response_base.success()
    return response_base.fail()
