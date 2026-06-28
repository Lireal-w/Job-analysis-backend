"""Agent 开发任务阶段 API（管理端）"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.agent_dev.schema.dev_stage import (
    GetAgentDevStageDetail,
    UpdateAgentDevStageParam,
    UpdateAgentDevStageStatusParam,
)
from backend.app.agent_dev.service.dev_orchestrator import dev_orchestrator
from backend.app.agent_dev.service.dev_stage_service import dev_stage_service
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get('/by-task/{task_id}', summary='获取任务的所有阶段', dependencies=[DependsJwtAuth])
async def get_stages_by_task(
    db: CurrentSession,
    task_id: Annotated[int, Path(description='任务 ID')],
) -> ResponseSchemaModel[list[GetAgentDevStageDetail]]:
    data = await dev_stage_service.get_by_task(db=db, task_id=task_id)
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取阶段详情', dependencies=[DependsJwtAuth])
async def get_stage(
    db: CurrentSession,
    pk: Annotated[int, Path(description='阶段 ID')],
) -> ResponseSchemaModel[GetAgentDevStageDetail]:
    data = await dev_stage_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.put('/{pk}', summary='更新阶段信息', dependencies=[DependsJwtAuth])
async def update_stage(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='阶段 ID')],
    obj: UpdateAgentDevStageParam,
) -> ResponseModel:
    await dev_stage_service.update(db=db, pk=pk, obj=obj)
    return response_base.success()


@router.put('/{pk}/status', summary='更新阶段状态', dependencies=[DependsJwtAuth])
async def update_stage_status(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='阶段 ID')],
    obj: UpdateAgentDevStageStatusParam,
) -> ResponseModel:
    await dev_stage_service.update_status(db=db, pk=pk, obj=obj)
    return response_base.success()


@router.post('/{pk}/retry', summary='重试阶段', dependencies=[DependsJwtAuth])
async def retry_stage(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='阶段 ID')],
    task_id: Annotated[int, Query(description='所属任务 ID')],
) -> ResponseSchemaModel[dict]:
    result = await dev_orchestrator.retry_stage(task_id=task_id, stage_id=pk)
    return response_base.success(data=result)
