"""采集任务 Celery 任务定义"""

import asyncio
from typing import Any

from backend.app.task.celery import celery_app
from backend.app.task.tasks.base import TaskBase
from backend.common.enums import CrawlStatus


@celery_app.task(name='crawl_task_execute', base=TaskBase)
async def crawl_task_execute(
    task_id: int,
    run_id: str,
    crawl_mode: str | None = None,
    source_datasource_id: int | None = None,
    source_config: dict | None = None,
    target_storage: str | None = None,
    target_datasource_id: int | None = None,
    target_config: dict | None = None,
) -> dict[str, Any]:
    """执行采集任务"""
    # TODO: 实现实际采集逻辑
    # 当前为 M1 基础框架，采集执行器将在后续迭代中完善
    return {
        'task_id': task_id,
        'run_id': run_id,
        'status': 'success',
        'message': '采集任务执行完成（M1 基础框架占位）',
    }


@celery_app.task(name='crawl_task_scheduled', base=TaskBase)
async def crawl_task_scheduled(task_id: int) -> dict[str, Any]:
    """定时调度采集任务"""
    # TODO: 实现定时调度逻辑
    # 当前为 M1 基础框架，调度执行器将在后续迭代中完善
    return {
        'task_id': task_id,
        'status': 'success',
        'message': '定时调度任务触发完成（M1 基础框架占位）',
    }
