from typing import Annotated

from fastapi import APIRouter, Path, Query, Request

from backend.app.admin.schema.crawl_task import (
    CreateCrawlTaskParam,
    GetCrawlTaskDetail,
    GetCrawlTaskLogDetail,
    UpdateCrawlTaskParam,
    UpdateCrawlTaskStatusParam,
)
from backend.app.admin.service.crawl_task_service import crawl_task_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


# ── 仪表盘 ──────────────────────────────────────────

@router.get('/dashboard', summary='采集任务仪表盘统计', dependencies=[DependsJwtAuth])
async def get_dashboard_stats(
    db: CurrentSession,
) -> ResponseSchemaModel[dict]:
    data = await crawl_task_service.get_dashboard_stats(db=db)
    return response_base.success(data=data)


# ── CRUD ─────────────────────────────────────────────

@router.get('/all', summary='获取所有采集任务', dependencies=[DependsJwtAuth])
async def get_all_tasks(db: CurrentSession) -> ResponseSchemaModel[list[GetCrawlTaskDetail]]:
    data = await crawl_task_service.get_all(db=db)
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取采集任务详情', dependencies=[DependsJwtAuth])
async def get_crawl_task(
    db: CurrentSession,
    pk: Annotated[int, Path(description='任务 ID')],
) -> ResponseSchemaModel[GetCrawlTaskDetail]:
    data = await crawl_task_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.get(
    '',
    summary='分页获取采集任务列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_crawl_tasks_paginated(
    db: CurrentSession,
    name: Annotated[str | None, Query(description='任务名称')] = None,
    status: Annotated[str | None, Query(description='状态(stopped/running/paused/error)')] = None,
    crawl_mode: Annotated[str | None, Query(description='采集模式(full/incremental)')] = None,
    schedule_type: Annotated[str | None, Query(description='调度类型(none/cron/interval)')] = None,
    source_datasource_id: Annotated[int | None, Query(description='源数据源 ID')] = None,
) -> ResponseSchemaModel[PageData[GetCrawlTaskDetail]]:
    page_data = await crawl_task_service.get_list(
        db=db,
        name=name,
        status=status,
        crawl_mode=crawl_mode,
        schedule_type=schedule_type,
        source_datasource_id=source_datasource_id,
    )
    return response_base.success(data=page_data)


@router.post('', summary='创建采集任务', dependencies=[DependsJwtAuth])
async def create_crawl_task(
    db: CurrentSessionTransaction,
    request: Request,
    obj: CreateCrawlTaskParam,
) -> ResponseSchemaModel[GetCrawlTaskDetail]:
    user_id = request.user.id
    data = await crawl_task_service.create(db=db, obj=obj, created_by=user_id)
    return response_base.success(data=data)


@router.put('/{pk}', summary='更新采集任务', dependencies=[DependsJwtAuth])
async def update_crawl_task(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='任务 ID')],
    obj: UpdateCrawlTaskParam,
) -> ResponseSchemaModel[GetCrawlTaskDetail]:
    data = await crawl_task_service.update(db=db, pk=pk, obj=obj)
    return response_base.success(data=data)


@router.put('/{pk}/status', summary='更新采集任务状态', dependencies=[DependsJwtAuth])
async def update_crawl_task_status(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='任务 ID')],
    obj: UpdateCrawlTaskStatusParam,
) -> ResponseModel:
    await crawl_task_service.update_status(db=db, pk=pk, obj=obj)
    return response_base.success()


@router.delete('', summary='批量删除采集任务', dependencies=[DependsJwtAuth])
async def delete_tasks(
    db: CurrentSessionTransaction,
    pks: Annotated[list[int], Query(description='任务 ID 列表')],
) -> ResponseModel:
    count = await crawl_task_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()


# ── 任务控制 ──────────────────────────────────────────

@router.post('/{pk}/start', summary='启动采集任务', dependencies=[DependsJwtAuth])
async def start_crawl_task(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='任务 ID')],
) -> ResponseSchemaModel[dict]:
    data = await crawl_task_service.start(db=db, pk=pk)
    return response_base.success(data=data)


@router.post('/{pk}/stop', summary='停止采集任务', dependencies=[DependsJwtAuth])
async def stop_crawl_task(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='任务 ID')],
) -> ResponseModel:
    await crawl_task_service.stop(db=db, pk=pk)
    return response_base.success()


@router.post('/{pk}/trigger', summary='手动触发采集任务', dependencies=[DependsJwtAuth])
async def trigger_crawl_task(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='任务 ID')],
) -> ResponseSchemaModel[dict]:
    data = await crawl_task_service.trigger(db=db, pk=pk)
    return response_base.success(data=data)


# ── 日志 ──────────────────────────────────────────────

@router.get('/{pk}/logs', summary='获取采集任务日志列表', dependencies=[DependsJwtAuth])
async def get_crawl_task_logs(
    db: CurrentSession,
    pk: Annotated[int, Path(description='任务 ID')],
    limit: Annotated[int, Query(description='日志数量')] = 50,
) -> ResponseSchemaModel[list[GetCrawlTaskLogDetail]]:
    data = await crawl_task_service.get_logs(db=db, task_id=pk, limit=limit)
    return response_base.success(data=data)


@router.get('/logs/{log_id}', summary='获取采集任务日志详情', dependencies=[DependsJwtAuth])
async def get_crawl_task_log_detail(
    db: CurrentSession,
    log_id: Annotated[int, Path(description='日志 ID')],
) -> ResponseSchemaModel[GetCrawlTaskLogDetail]:
    data = await crawl_task_service.get_log_detail(db=db, log_id=log_id)
    return response_base.success(data=data)
