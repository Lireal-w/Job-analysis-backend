"""H5 任务 API"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from backend.app.h5.schema.task import (
    H5CompleteTaskParam,
    H5CreateTaskParam,
    H5TaskDetail,
    H5TaskStats,
    H5UpdateTaskParam,
    H5UpdateTaskProgressParam,
)
from backend.app.h5.service.task_service import h5_task_service
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter(prefix='/h5/tasks', dependencies=[DependsJwtAuth])


@router.get('/today', summary='获取今日待完成任务', description='H5 获取分配给当前用户的今日待完成任务')
async def h5_get_today_tasks(
    db: CurrentSession,
    request: Request,
) -> ResponseSchemaModel[list[H5TaskDetail]]:
    user_id = request.user.id
    data = await h5_task_service.get_today_tasks(db=db, user_id=user_id)
    return response_base.success(data=data)


@router.get('/stats', summary='获取任务统计', description='H5 首页任务统计概览')
async def h5_get_task_stats(
    db: CurrentSession,
    request: Request,
) -> ResponseSchemaModel[H5TaskStats]:
    user_id = request.user.id
    stats = await h5_task_service.get_stats(db=db, user_id=user_id)
    return response_base.success(data=stats)


@router.get('', summary='获取任务列表', description='H5 分页获取任务列表')
async def h5_get_task_list(
    db: CurrentSession,
    request: Request,
    status: Annotated[int | None, Query(description='状态(0待办 1进行中 2已完成 3已取消)')] = None,
    task_type: Annotated[int | None, Query(description='类型(0每日 1周期 2定时)')] = None,
    priority: Annotated[int | None, Query(description='优先级(0低 1中 2高 3紧急)')] = None,
    page: Annotated[int, Query(description='页码')] = 1,
    page_size: Annotated[int, Query(description='每页条数')] = 20,
) -> ResponseSchemaModel[dict]:
    user_id = request.user.id
    data = await h5_task_service.get_list(
        db=db,
        user_id=user_id,
        status=status,
        task_type=task_type,
        priority=priority,
        page=page,
        page_size=min(page_size, 100),
    )
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取任务详情', description='H5 获取任务详情')
async def h5_get_task_detail(
    db: CurrentSession,
    request: Request,
    pk: Annotated[int, Path(description='任务ID')],
) -> ResponseSchemaModel[H5TaskDetail]:
    user_id = request.user.id
    data = await h5_task_service.get_detail(db=db, pk=pk, user_id=user_id)
    return response_base.success(data=data)


@router.post('', summary='创建任务', description='H5 创建新任务')
async def h5_create_task(
    db: CurrentSessionTransaction,
    request: Request,
    obj: H5CreateTaskParam,
) -> ResponseSchemaModel[H5TaskDetail]:
    user_id = request.user.id
    data = await h5_task_service.create(db=db, obj=obj, created_by=user_id)
    return response_base.success(data=data)


@router.put('/{pk}', summary='更新任务', description='H5 更新任务信息')
async def h5_update_task(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='任务ID')],
    obj: H5UpdateTaskParam,
) -> ResponseModel:
    operator = request.user.id
    await h5_task_service.update(db=db, pk=pk, obj=obj, operator=operator)
    return response_base.success()


@router.put('/{pk}/progress', summary='更新任务进度', description='H5 更新任务进度百分比')
async def h5_update_task_progress(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='任务ID')],
    obj: H5UpdateTaskProgressParam,
) -> ResponseModel:
    operator = request.user.id
    await h5_task_service.update_progress(
        db=db, pk=pk, progress=obj.progress, operator=operator,
    )
    return response_base.success()


@router.post('/{pk}/complete', summary='提交完成任务', description='H5 完成任务并提交完成备注')
async def h5_complete_task(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='任务ID')],
    obj: H5CompleteTaskParam = H5CompleteTaskParam(),
) -> ResponseModel:
    operator = request.user.id
    await h5_task_service.complete(
        db=db, pk=pk, operator=operator,
        remark=obj.remark, progress=obj.progress,
    )
    return response_base.success()
