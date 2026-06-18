"""动态调度 API

提供基于 Redis 的动态调度管理接口，支持任务的实时创建、修改、删除。
与数据库调度器（DatabaseScheduler）不同，动态调度通过 Redis 存储，
变更实时生效，无需等待数据库轮询间隔。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.task.schema.dynamic_schedule import (
    DynamicScheduleCreate,
    DynamicScheduleDetail,
    DynamicScheduleUpdate,
)
from backend.app.task.service.dynamic_schedule_service import dynamic_schedule_service
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC

router = APIRouter()


@router.get(
    '/all',
    summary='获取所有动态调度',
    dependencies=[DependsJwtAuth],
)
async def get_all_dynamic_schedules(
    prefix: Annotated[str | None, Query(description='任务名称前缀过滤')] = None,
) -> ResponseSchemaModel[list[DynamicScheduleDetail]]:
    """获取所有动态调度任务"""
    data = await dynamic_schedule_service.get_list(prefix=prefix or '')
    return response_base.success(data=data)


@router.get(
    '/{name}',
    summary='获取动态调度详情',
    dependencies=[DependsJwtAuth],
)
async def get_dynamic_schedule(
    name: Annotated[str, Path(description='任务名称')],
) -> ResponseSchemaModel[DynamicScheduleDetail]:
    """获取指定动态调度任务详情"""
    data = await dynamic_schedule_service.get(name=name)
    return response_base.success(data=data)


@router.post(
    '',
    summary='创建动态调度',
    dependencies=[
        Depends(RequestPermission('sys:task:add')),
        DependsRBAC,
    ],
)
async def create_dynamic_schedule(obj: DynamicScheduleCreate) -> ResponseSchemaModel[DynamicScheduleDetail]:
    """创建动态调度任务"""
    # 构建 options
    options = {}
    if obj.queue:
        options['queue'] = obj.queue
    if obj.exchange:
        options['exchange'] = obj.exchange
    if obj.routing_key:
        options['routing_key'] = obj.routing_key

    data = await dynamic_schedule_service.create(
        name=obj.name,
        task=obj.task,
        schedule_type=obj.type,
        interval_every=obj.interval_every,
        interval_period=obj.interval_period,
        crontab=obj.crontab,
        args=obj.args,
        kwargs=obj.kwargs,
        options=options or None,
        enabled=obj.enabled,
        ttl=obj.ttl,
    )
    return response_base.success(data=data)


@router.put(
    '/{name}',
    summary='更新动态调度',
    dependencies=[
        Depends(RequestPermission('sys:task:edit')),
        DependsRBAC,
    ],
)
async def update_dynamic_schedule(
    name: Annotated[str, Path(description='任务名称')],
    obj: DynamicScheduleUpdate,
) -> ResponseSchemaModel[DynamicScheduleDetail]:
    """更新动态调度任务"""
    updates = obj.model_dump(exclude_unset=True)

    # 处理 options 字段
    options = {}
    for key in ['queue', 'exchange', 'routing_key']:
        if key in updates:
            options[key] = updates.pop(key)
    if options:
        updates['options'] = options

    data = await dynamic_schedule_service.update(name=name, **updates)
    return response_base.success(data=data)


@router.delete(
    '/{name}',
    summary='删除动态调度',
    dependencies=[
        Depends(RequestPermission('sys:task:del')),
        DependsRBAC,
    ],
)
async def delete_dynamic_schedule(
    name: Annotated[str, Path(description='任务名称')],
) -> ResponseModel:
    """删除动态调度任务"""
    await dynamic_schedule_service.delete(name=name)
    return response_base.success()


@router.put(
    '/{name}/toggle',
    summary='启用/禁用动态调度',
    dependencies=[
        Depends(RequestPermission('sys:task:edit')),
        DependsRBAC,
    ],
)
async def toggle_dynamic_schedule(
    name: Annotated[str, Path(description='任务名称')],
    enabled: Annotated[bool, Query(description='是否启用')],
) -> ResponseSchemaModel[DynamicScheduleDetail]:
    """启用或禁用动态调度任务"""
    data = await dynamic_schedule_service.toggle(name=name, enabled=enabled)
    return response_base.success(data=data)