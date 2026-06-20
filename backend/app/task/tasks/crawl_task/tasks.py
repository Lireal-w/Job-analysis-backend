"""采集任务 Celery 任务定义

负责：
1. 异步执行采集任务 (crawl_task_execute)
2. 定时调度采集任务 (crawl_task_scheduled)
3. 更新任务状态和执行日志
4. 处理增量采集状态
"""

import traceback
from typing import Any

from loguru import logger

from backend.app.admin.crud.crud_crawl_task import crawl_task_dao, crawl_task_log_dao
from backend.app.admin.service.crawl.executor import CrawlExecutor
from backend.app.task.celery import celery_app
from backend.app.task.tasks.base import TaskBase
from backend.common.enums import CrawlStatus
from backend.database.db import async_db_session
from backend.utils.timezone import timezone


@celery_app.task(
    name='crawl_task_execute',
    base=TaskBase,
    bind=True,
    track_started=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
async def crawl_task_execute(
    self,
    task_id: int,
    run_id: str,
    crawl_mode: str | None = None,
    source_datasource_id: int | None = None,
    source_config: dict | None = None,
    target_storage: str | None = None,
    target_datasource_id: int | None = None,
    target_config: dict | None = None,
    incremental_key: str | None = None,
    incremental_start: str | None = None,
    concurrency: int = 1,
    batch_size: int = 100,
    rate_limit: int = 0,
    retry_enabled: bool = True,
    max_retries: int = 3,
    retry_delay: int = 60,
    retry_backoff: bool = True,
) -> dict[str, Any]:
    """异步执行采集任务

    Args:
        task_id: 采集任务 ID
        run_id: 运行批次 ID
        crawl_mode: 采集模式 (full/incremental)
        source_datasource_id: 源数据源 ID
        source_config: 源采集配置
        target_storage: 目标存储类型
        target_datasource_id: 目标数据源 ID
        target_config: 目标存储配置
        incremental_key: 增量字段名
        incremental_start: 增量起始值
        concurrency: 并发数
        batch_size: 每批处理条数
        rate_limit: 速率限制
        retry_enabled: 是否启用重试
        max_retries: 最大重试次数
        retry_delay: 重试间隔(秒)
        retry_backoff: 是否启用退避策略

    Returns:
        执行结果摘要
    """
    source_config = source_config or {}
    target_config = target_config or {}

    logger.info(
        f'[Crawl] 开始执行采集任务 task_id={task_id}, run_id={run_id}, '
        f'mode={crawl_mode}'
    )

    # 创建执行器
    executor = CrawlExecutor(
        task_id=task_id,
        run_id=run_id,
        source_config=source_config,
        target_storage=target_storage or 'database',
        target_config=target_config,
        crawl_mode=crawl_mode or 'full',
        incremental_key=incremental_key,
        incremental_start=incremental_start,
        concurrency=concurrency,
        batch_size=batch_size,
        rate_limit=rate_limit,
        retry_enabled=retry_enabled,
        max_retries=max_retries,
        retry_delay=retry_delay,
        retry_backoff=retry_backoff,
        source_datasource_id=source_datasource_id,
        target_datasource_id=target_datasource_id,
    )

    summary: dict[str, Any] = {
        'task_id': task_id,
        'run_id': run_id,
        'status': 'success',
        'total_found': 0,
        'total_scraped': 0,
        'total_succeeded': 0,
        'total_failed': 0,
        'total_skipped': 0,
        'error_message': None,
    }

    try:
        # 执行采集
        ctx = await executor.execute()

        # 更新摘要
        summary.update({
            'total_found': ctx.total_found,
            'total_scraped': ctx.total_scraped,
            'total_succeeded': ctx.total_succeeded,
            'total_failed': ctx.total_failed,
            'total_skipped': ctx.total_skipped,
            'throughput': ctx.throughput,
            'avg_response_time': ctx.avg_response_time,
        })

        # 更新运行日志为成功
        await _update_log(run_id, ctx.to_log_dict())

        # 更新任务统计
        await _update_task_stats(
            task_id,
            status=CrawlStatus.STOPPED.value,
            total_records=ctx.total_succeeded,
            last_status='success',
            duration=ctx.duration,
            incremental_end=ctx.incremental_end,
        )

    except Exception as e:
        logger.error(f'[Crawl] 采集任务 {task_id} 执行失败: {e}')
        logger.error(traceback.format_exc())

        summary['status'] = 'failed'
        summary['error_message'] = f'{type(e).__name__}: {e}'

        # 更新运行日志为失败
        ctx = executor.context
        ctx.error_message = f'{type(e).__name__}: {e}'
        ctx.error_traceback = traceback.format_exc()
        await _update_log(run_id, ctx.to_log_dict())

        # 更新任务状态为错误
        await _update_task_stats(
            task_id,
            status=CrawlStatus.ERROR.value,
            last_status='failed',
        )

    logger.info(f'[Crawl] 采集任务 {task_id} 执行完成, 状态: {summary["status"]}')
    return summary


@celery_app.task(
    name='crawl_task_scheduled',
    base=TaskBase,
    bind=True,
    track_started=True,
)
async def crawl_task_scheduled(self, task_id: int) -> dict[str, Any]:
    """定时调度采集任务

    从数据库加载任务配置，然后触发执行。

    Args:
        task_id: 采集任务 ID

    Returns:
        执行结果摘要
    """
    logger.info(f'[Crawl] 定时调度触发 task_id={task_id}')

    # 从数据库加载任务配置
    async with async_db_session() as session:
        task = await crawl_task_dao.get(session, task_id)
        if not task:
            logger.error(f'[Crawl] 定时调度失败: 任务 {task_id} 不存在')
            return {
                'task_id': task_id,
                'status': 'failed',
                'error_message': f'任务 {task_id} 不存在',
            }

        if not task.enabled:
            logger.warning(f'[Crawl] 定时调度跳过: 任务 {task_id} 已禁用')
            return {
                'task_id': task_id,
                'status': 'skipped',
                'message': '任务已禁用',
            }

        if task.status == CrawlStatus.RUNNING.value:
            logger.warning(f'[Crawl] 定时调度跳过: 任务 {task_id} 正在运行中')
            return {
                'task_id': task_id,
                'status': 'skipped',
                'message': '任务正在运行中',
            }

    # 创建运行日志
    import uuid
    run_id = uuid.uuid4().hex

    async with async_db_session() as session:
        log_data = {
            'task_id': task_id,
            'run_id': run_id,
            'status': 'running',
            'start_time': timezone.now(),
            'total_found': 0,
            'total_scraped': 0,
            'total_succeeded': 0,
            'total_failed': 0,
            'total_skipped': 0,
        }
        await crawl_task_log_dao.create_log(session, log_data)

    # 更新任务状态为运行中
    await _update_task_stats(task_id, status=CrawlStatus.RUNNING.value)

    # 提交异步执行任务
    celery_task = celery_app.send_task(
        'crawl_task_execute',
        args=[task_id, run_id],
        kwargs={
            'crawl_mode': task.crawl_mode,
            'source_datasource_id': task.source_datasource_id,
            'source_config': task.source_config or {},
            'target_storage': task.target_storage,
            'target_datasource_id': task.target_datasource_id,
            'target_config': task.target_config or {},
            'incremental_key': task.incremental_key,
            'incremental_start': task.incremental_start,
            'concurrency': task.concurrency or 1,
            'batch_size': task.batch_size or 100,
            'rate_limit': task.rate_limit or 0,
            'retry_enabled': task.retry_enabled if task.retry_enabled is not None else True,
            'max_retries': task.max_retries or 3,
            'retry_delay': task.retry_delay or 60,
            'retry_backoff': task.retry_backoff if task.retry_backoff is not None else True,
        },
    )

    return {
        'task_id': task_id,
        'run_id': run_id,
        'celery_task_id': celery_task.id,
        'status': 'running',
        'message': '定时调度任务已触发',
    }


async def _update_log(run_id: str, log_data: dict[str, Any]) -> None:
    """更新运行日志"""
    try:
        async with async_db_session() as session:
            log = await crawl_task_log_dao.get_by_run_id(session, run_id)
            if log:
                await crawl_task_log_dao.update_log(session, log.id, log_data)
    except Exception as e:
        logger.error(f'[Crawl] 更新运行日志失败 (run_id={run_id}): {e}')


async def _update_task_stats(
    task_id: int,
    status: str | None = None,
    total_records: int | None = None,
    last_status: str | None = None,
    duration: float | None = None,
    incremental_end: str | None = None,
) -> None:
    """更新任务统计信息"""
    try:
        async with async_db_session() as session:
            task = await crawl_task_dao.get(session, task_id)
            if not task:
                logger.warning(f'[Crawl] 更新统计失败: 任务 {task_id} 不存在')
                return

            stats: dict[str, Any] = {}

            if status is not None:
                stats['status'] = status

            # 成功或失败完成时更新统计（status=RUNNING 的中间状态不更新）
            if status in (CrawlStatus.STOPPED.value, CrawlStatus.ERROR.value):
                stats['total_run_count'] = (task.total_run_count or 0) + 1

            if total_records is not None:
                # 累加总记录数
                stats['total_records'] = (task.total_records or 0) + total_records
                stats['last_run_time'] = timezone.now()
                stats['last_duration'] = duration
                stats['last_status'] = last_status

                # 更新增量起始值（增量模式）
                if incremental_end:
                    stats['incremental_start'] = incremental_end

            if stats:
                await crawl_task_dao.update_stats(session, task_id, stats)
    except Exception as e:
        logger.error(f'[Crawl] 更新任务统计失败 (task_id={task_id}): {e}')
