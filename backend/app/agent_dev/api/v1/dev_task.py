"""Agent 开发任务 API

同时面向移动端和管理端:
- 移动端: 创建任务、查看我的任务、查看任务进度
- 管理端: 完整的 CRUD + 启动编排 + 取消
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from backend.app.agent_dev.schema.dev_task import (
    CreateAgentDevTaskParam,
    GetAgentDevTaskDetail,
    StartAgentDevTaskParam,
    UpdateAgentDevTaskParam,
)
from backend.app.agent_dev.schema.dev_stage import GetAgentDevStageDetail
from backend.app.agent_dev.service.dev_orchestrator import dev_orchestrator
from backend.app.agent_dev.service.dev_stage_service import dev_stage_service
from backend.app.agent_dev.service.dev_task_service import dev_task_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


# ═══════════════════════════════════════════════════
# 移动端 API（带 JWT 认证）
# ═══════════════════════════════════════════════════

@router.post('/mobile', summary='移动端创建开发任务', description='从移动端发起一个开发任务，进入编排流程')
async def create_task_from_mobile(
    db: CurrentSessionTransaction,
    request: Request,
    obj: CreateAgentDevTaskParam,
) -> ResponseSchemaModel[GetAgentDevTaskDetail]:
    """移动端创建开发任务，自动进入编排流程"""
    user_id = request.user.id
    task = await dev_task_service.create(db=db, obj=obj, created_by=user_id)
    await db.flush()

    # 异步启动编排
    import asyncio
    asyncio.create_task(dev_orchestrator.start_orchestration(task.id))

    return response_base.success(data=task)


@router.get('/mobile/my-tasks', summary='获取我的开发任务列表(移动端)', dependencies=[DependsJwtAuth])
async def get_my_tasks(
    db: CurrentSession,
    request: Request,
    status: Annotated[int | None, Query(description='状态(0待处理 1规划中 2进行中 3评审中 4已完成 5失败 6已取消)')] = None,
) -> ResponseSchemaModel[list[GetAgentDevTaskDetail]]:
    """移动端获取当前用户发起的开发任务"""
    user_id = request.user.id
    data = await dev_task_service.get_my_tasks(db=db, user_id=user_id, status=status)
    return response_base.success(data=data)


@router.get('/mobile/{pk}', summary='获取任务详情(含阶段)', dependencies=[DependsJwtAuth])
async def get_task_detail_with_stages(
    db: CurrentSession,
    pk: Annotated[int, Path(description='任务 ID')],
) -> dict:
    """获取任务详情，包含所有执行阶段"""
    task = await dev_task_service.get(db=db, pk=pk)
    stages = await dev_stage_service.get_by_task(db=db, task_id=pk)
    return response_base.success(data={
        'task': task,
        'stages': stages,
    })


@router.post('/mobile/{pk}/cancel', summary='取消开发任务(移动端)', dependencies=[DependsJwtAuth])
async def cancel_task_from_mobile(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='任务 ID')],
) -> ResponseModel:
    """取消指定的开发任务"""
    await dev_task_service.cancel(db=db, pk=pk)
    return response_base.success()


# ═══════════════════════════════════════════════════
# 管理端 API（带分页 + 权限）
# ═══════════════════════════════════════════════════

@router.get(
    '',
    summary='分页获取开发任务列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_tasks_paginated(
    db: CurrentSession,
    title: Annotated[str | None, Query(description='任务标题')] = None,
    task_type: Annotated[int | None, Query(description='任务类型(0功能 1Bug 2重构 3优化 4集成 5配置)')] = None,
    status: Annotated[int | None, Query(description='状态')] = None,
    priority: Annotated[int | None, Query(description='优先级')] = None,
    source: Annotated[int | None, Query(description='来源(0移动端 1管理后台)')] = None,
    project_name: Annotated[str | None, Query(description='项目名称')] = None,
) -> ResponseSchemaModel[PageData[GetAgentDevTaskDetail]]:
    page_data = await dev_task_service.get_list(
        db=db,
        title=title,
        task_type=task_type,
        status=status,
        priority=priority,
        source=source,
        project_name=project_name,
    )
    return response_base.success(data=page_data)


@router.get('/{pk}', summary='获取任务详情', dependencies=[DependsJwtAuth])
async def get_task(
    db: CurrentSession,
    pk: Annotated[int, Path(description='任务 ID')],
) -> ResponseSchemaModel[GetAgentDevTaskDetail]:
    data = await dev_task_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.post('', summary='创建开发任务(管理端)', dependencies=[DependsJwtAuth])
async def create_task(
    db: CurrentSessionTransaction,
    request: Request,
    obj: CreateAgentDevTaskParam,
) -> ResponseSchemaModel[GetAgentDevTaskDetail]:
    user_id = request.user.id
    obj.source = 1  # ADMIN
    task = await dev_task_service.create(db=db, obj=obj, created_by=user_id)
    return response_base.success(data=task)


@router.put('/{pk}', summary='更新开发任务', dependencies=[DependsJwtAuth])
async def update_task(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='任务 ID')],
    obj: UpdateAgentDevTaskParam,
) -> ResponseModel:
    await dev_task_service.update(db=db, pk=pk, obj=obj)
    return response_base.success()


@router.delete('', summary='删除开发任务', dependencies=[DependsJwtAuth])
async def delete_tasks(
    db: CurrentSessionTransaction,
    pks: Annotated[str, Query(description='任务 ID 列表(逗号分隔)')],
) -> ResponseModel:
    pk_list = [int(pk.strip()) for pk in pks.split(',')]
    count = await dev_task_service.delete(db=db, pks=pk_list)
    if count > 0:
        return response_base.success()
    return response_base.fail()


# ═══════════════════════════════════════════════════
# 编排控制 API
# ═══════════════════════════════════════════════════

@router.post('/{pk}/start', summary='启动编排', dependencies=[DependsJwtAuth])
async def start_orchestration(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='任务 ID')],
    _param: StartAgentDevTaskParam | None = None,
) -> ResponseModel:
    """启动任务的编排流程（将任务拆解为多阶段并调度 Agent 执行）"""
    import asyncio
    asyncio.create_task(dev_orchestrator.start_orchestration(pk))
    return response_base.success()


@router.post('/{pk}/cancel', summary='取消编排任务', dependencies=[DependsJwtAuth])
async def cancel_task(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='任务 ID')],
) -> ResponseModel:
    await dev_task_service.cancel(db=db, pk=pk)
    return response_base.success()
