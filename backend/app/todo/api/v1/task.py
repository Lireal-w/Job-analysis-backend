from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from backend.app.todo.schema.goal import GetGoalDetail
from backend.app.todo.schema.log import GetTaskLogDetail
from backend.app.todo.schema.task import (
    CreateTaskParam,
    GetTaskDetail,
    GetTaskDetailWithGoals,
    UpdateTaskParam,
    UpdateTaskProgressParam,
)
from backend.app.todo.service.goal_service import goal_service
from backend.app.todo.service.task_service import task_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get('/today', summary='获取今日待完成任务', dependencies=[DependsJwtAuth])
async def get_today_tasks(
    db: CurrentSession, request: Request
) -> ResponseSchemaModel[list[GetTaskDetail]]:
    user_id = request.user.id
    data = await task_service.get_today_tasks(db=db, user_id=user_id)
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取任务详情', dependencies=[DependsJwtAuth])
async def get_task(
    db: CurrentSession,
    pk: Annotated[int, Path(description='任务ID')],
) -> ResponseSchemaModel[GetTaskDetail]:
    data = await task_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.get('/{pk}/with-goals', summary='获取任务详情(含目标)', dependencies=[DependsJwtAuth])
async def get_task_with_goals(
    db: CurrentSession,
    pk: Annotated[int, Path(description='任务ID')],
) -> ResponseSchemaModel[GetTaskDetailWithGoals]:
    task = await task_service.get(db=db, pk=pk)
    goals = await goal_service.get_by_task(db=db, task_id=pk)
    task_dict = task.__dict__
    task_dict['goals'] = goals
    return response_base.success(data=task_dict)


@router.get(
    '',
    summary='分页获取任务列表',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_tasks_paginated(
    db: CurrentSession,
    request: Request,
    task_type: Annotated[int | None, Query(description='任务类型(0每日 1周期 2定时)')] = None,
    status: Annotated[int | None, Query(description='状态(0待办 1进行中 2已完成 3已取消)')] = None,
    priority: Annotated[int | None, Query(description='优先级(0低 1中 2高 3紧急)')] = None,
    source: Annotated[int | None, Query(description='来源(0上级分配 1自己定制 2AI生成)')] = None,
    title: Annotated[str | None, Query(description='标题关键词')] = None,
) -> ResponseSchemaModel[PageData[GetTaskDetail]]:
    user_id = request.user.id
    page_data = await task_service.get_list(
        db=db,
        user_id=user_id,
        task_type=task_type,
        status=status,
        priority=priority,
        source=source,
        title=title,
    )
    return response_base.success(data=page_data)


@router.post('', summary='创建任务', dependencies=[DependsJwtAuth])
async def create_task(
    db: CurrentSessionTransaction,
    request: Request,
    obj: CreateTaskParam,
) -> ResponseSchemaModel[GetTaskDetail]:
    user_id = request.user.id
    data = await task_service.create(db=db, obj=obj, created_by=user_id)
    return response_base.success(data=data)


@router.put('/{pk}', summary='更新任务', dependencies=[DependsJwtAuth])
async def update_task(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='任务ID')],
    obj: UpdateTaskParam,
) -> ResponseModel:
    operator = request.user.id
    await task_service.update(db=db, pk=pk, obj=obj, operator=operator)
    return response_base.success()


@router.put('/{pk}/status', summary='更新任务状态', dependencies=[DependsJwtAuth])
async def update_task_status(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='任务ID')],
    status: Annotated[int, Query(description='状态(0待办 1进行中 2已完成 3已取消)')],
) -> ResponseModel:
    operator = request.user.id
    await task_service.update_status(db=db, pk=pk, status=status, operator=operator)
    return response_base.success()


@router.put('/{pk}/progress', summary='更新任务进度', dependencies=[DependsJwtAuth])
async def update_task_progress(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='任务ID')],
    obj: UpdateTaskProgressParam,
) -> ResponseModel:
    operator = request.user.id
    await task_service.update_progress(db=db, pk=pk, obj=obj, operator=operator)
    return response_base.success()


@router.delete('/{pk}', summary='删除任务', dependencies=[DependsJwtAuth])
async def delete_task(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='任务ID')],
) -> ResponseModel:
    await task_service.delete(db=db, pk=pk)
    return response_base.success()
