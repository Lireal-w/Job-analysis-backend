from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from backend.app.todo.schema.goal import CreateGoalParam, GetGoalDetail, UpdateGoalParam, UpdateGoalStatusParam
from backend.app.todo.service.ai_service import ai_task_service
from backend.app.todo.service.goal_service import goal_service
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get('/by-task/{task_id}', summary='获取任务的所有目标', dependencies=[DependsJwtAuth])
async def get_goals_by_task(
    db: CurrentSession,
    task_id: Annotated[int, Path(description='任务ID')],
) -> ResponseSchemaModel[list[GetGoalDetail]]:
    data = await goal_service.get_by_task(db=db, task_id=task_id)
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取目标详情', dependencies=[DependsJwtAuth])
async def get_goal(
    db: CurrentSession,
    pk: Annotated[int, Path(description='目标ID')],
) -> ResponseSchemaModel[GetGoalDetail]:
    data = await goal_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.post('', summary='创建目标', dependencies=[DependsJwtAuth])
async def create_goal(
    db: CurrentSessionTransaction,
    request: Request,
    obj: CreateGoalParam,
) -> ResponseSchemaModel[GetGoalDetail]:
    user_id = request.user.id
    data = await goal_service.create(db=db, obj=obj, created_by=user_id)
    return response_base.success(data=data)


@router.put('/{pk}', summary='更新目标', dependencies=[DependsJwtAuth])
async def update_goal(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='目标ID')],
    obj: UpdateGoalParam,
) -> ResponseModel:
    operator = request.user.id
    await goal_service.update(db=db, pk=pk, obj=obj, operator=operator)
    return response_base.success()


@router.put('/{pk}/status', summary='更新目标状态', dependencies=[DependsJwtAuth])
async def update_goal_status(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='目标ID')],
    obj: UpdateGoalStatusParam,
) -> ResponseModel:
    operator = request.user.id
    await goal_service.update_status(db=db, pk=pk, obj=obj, operator=operator)
    return response_base.success()


@router.post('/ai-generate/{task_id}', summary='AI自动生成阶段性目标', dependencies=[DependsJwtAuth])
async def ai_generate_goals(
    db: CurrentSessionTransaction,
    request: Request,
    task_id: Annotated[int, Path(description='任务ID')],
) -> ResponseSchemaModel[list[GetGoalDetail]]:
    user_id = request.user.id
    data = await ai_task_service.generate_goals(db=db, task_id=task_id, user_id=user_id)
    return response_base.success(data=data)


@router.delete('/{pk}', summary='删除目标', dependencies=[DependsJwtAuth])
async def delete_goal(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='目标ID')],
) -> ResponseModel:
    await goal_service.delete(db=db, pk=pk)
    return response_base.success()
