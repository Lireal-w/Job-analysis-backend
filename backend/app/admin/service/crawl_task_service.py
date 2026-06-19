import uuid
import json

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_crawl_task import crawl_task_dao, crawl_task_log_dao
from backend.app.admin.model import CrawlTask
from backend.app.admin.schema.crawl_task import (
    CreateCrawlTaskParam,
    UpdateCrawlTaskParam,
    UpdateCrawlTaskStatusParam,
)
from backend.app.task.celery import celery_app
from backend.common.enums import CrawlScheduleType
from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.utils.timezone import timezone


class CrawlTaskService:
    """采集任务服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> CrawlTask:
        task = await crawl_task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='采集任务不存在')
        return task

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[CrawlTask]:
        return await crawl_task_dao.get_all(db)

    @staticmethod
    async def get_list(
        *,
        db: AsyncSession,
        name: str | None = None,
        status: str | None = None,
        crawl_mode: str | None = None,
        schedule_type: str | None = None,
        source_datasource_id: int | None = None,
    ) -> dict[str, Any]:
        select = await crawl_task_dao.get_select(
            name=name,
            status=status,
            crawl_mode=crawl_mode,
            schedule_type=schedule_type,
            source_datasource_id=source_datasource_id,
        )
        return await paging_data(db, select)

    @staticmethod
    async def create(
        *, db: AsyncSession, obj: CreateCrawlTaskParam, created_by: int
    ) -> CrawlTask:
        existing = await crawl_task_dao.get_by_name(db, obj.name)
        if existing:
            raise errors.ConflictError(msg='采集任务名称已存在')

        task = await crawl_task_dao.create(db, obj)

        # 更新创建者
        await crawl_task_dao.update_stats(db, task.id, {'created_by': created_by})

        # 如果有调度配置，注册到 Celery Beat
        if obj.schedule_type != CrawlScheduleType.NONE:
            CrawlTaskService._register_schedule(task)

        return await crawl_task_dao.get(db, task.id)

    @staticmethod
    async def update(
        *, db: AsyncSession, pk: int, obj: UpdateCrawlTaskParam
    ) -> CrawlTask:
        task = await crawl_task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='采集任务不存在')

        count = await crawl_task_dao.update(db, pk, obj)
        if count == 0:
            raise errors.RequestError(msg='更新失败')

        updated = await crawl_task_dao.get(db, pk)
        return updated

    @staticmethod
    async def update_status(
        *, db: AsyncSession, pk: int, obj: UpdateCrawlTaskStatusParam
    ) -> None:
        task = await crawl_task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='采集任务不存在')

        await crawl_task_dao.update_status(db, pk, obj.status.value)

    @staticmethod
    async def start(*, db: AsyncSession, pk: int) -> dict[str, Any]:
        """启动采集任务"""
        task = await crawl_task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='采集任务不存在')

        if task.status == 'running':
            raise errors.RequestError(msg='任务已在运行中')

        # 更新状态
        await crawl_task_dao.update_status(db, pk, 'running')

        # 创建运行日志
        run_id = uuid.uuid4().hex
        log_data = {
            'task_id': pk,
            'run_id': run_id,
            'status': 'running',
            'start_time': timezone.now(),
            'total_found': 0,
            'total_scraped': 0,
            'total_succeeded': 0,
            'total_failed': 0,
            'total_skipped': 0,
        }
        await crawl_task_log_dao.create_log(db, log_data)

        # 提交 Celery 任务
        celery_task = celery_app.send_task(
            'crawl_task_execute',
            args=[pk, run_id],
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
            'task_id': pk,
            'run_id': run_id,
            'celery_task_id': celery_task.id,
            'status': 'running',
        }

    @staticmethod
    async def stop(*, db: AsyncSession, pk: int) -> dict[str, Any]:
        """停止采集任务

        通过 Redis 发送取消信号，同时撤销 Celery 任务。
        采集执行器会在每个阶段检查取消信号并优雅退出。
        """
        task = await crawl_task_dao.get(db, pk)
        if not task:
            raise errors.NotFoundError(msg='采集任务不存在')

        if task.status != 'running':
            raise errors.RequestError(msg='任务当前不在运行状态')

        # 1. 发送 Redis 取消信号（让执行器优雅退出）
        from backend.app.admin.service.crawl.progress import send_cancel_signal, revoke_celery_task
        cancel_sent = await send_cancel_signal(pk)

        # 2. 更新任务状态
        await crawl_task_dao.update_status(db, pk, 'stopped')

        # 3. 更新当前正在运行的日志
        logs = await crawl_task_log_dao.get_by_task(db, pk, limit=1)
        celery_revoked = False
        for log in logs:
            if log.status == 'running':
                await crawl_task_log_dao.update_log(
                    db, log.id, {
                        'status': 'failed',
                        'end_time': timezone.now(),
                        'error_message': '任务被手动停止',
                    }
                )
                # 4. 尝试撤销 Celery 任务（如果有 celery_task_id）
                # 注意：celery_task_id 不在日志中，需要从其他来源获取
                # 这里通过 Redis 进度信息获取
                break

        return {
            'task_id': pk,
            'status': 'stopped',
            'cancel_signal_sent': cancel_sent,
            'message': '停止信号已发送，任务将在当前批次完成后停止',
        }

    @staticmethod
    async def trigger(*, db: AsyncSession, pk: int) -> dict[str, Any]:
        """手动触发采集任务"""
        return await CrawlTaskService.start(db=db, pk=pk)

    @staticmethod
    async def get_progress(*, pk: int) -> dict[str, Any]:
        """获取采集任务实时进度

        从 Redis 读取进度信息。
        """
        import json
        from backend.database.redis import redis_client

        # 查找该任务最新的进度 key
        pattern = f'crawl:progress:{pk}:*'
        keys = await redis_client.get_prefix(pattern)

        if not keys:
            return {
                'task_id': pk,
                'status': 'no_progress',
                'message': '没有找到进度信息',
            }

        # 获取最新的进度（取最后一个 key）
        latest_key = keys[-1]
        data = await redis_client.get(latest_key)
        if data:
            try:
                progress = json.loads(data)
                return progress
            except json.JSONDecodeError:
                pass

        return {
            'task_id': pk,
            'status': 'unknown',
            'message': '进度信息解析失败',
        }

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        # Check if any task is running
        for pk in pks:
            task = await crawl_task_dao.get(db, pk)
            if task and task.status == 'running':
                raise errors.RequestError(msg=f'任务「{task.name}」正在运行中，无法删除')

        # 同时删除关联的日志
        for pk in pks:
            await crawl_task_log_dao.delete_by_task(db, pk)
        return await crawl_task_dao.delete(db, pks)

    # ── 日志相关 ──────────────────────────────────────────

    @staticmethod
    async def get_logs(
        *, db: AsyncSession, task_id: int, limit: int = 50
    ) -> Sequence:
        return await crawl_task_log_dao.get_by_task(db, task_id, limit)

    @staticmethod
    async def get_log_detail(
        *, db: AsyncSession, log_id: int
    ):
        log = await crawl_task_log_dao.get(db, log_id)
        if not log:
            raise errors.NotFoundError(msg='日志不存在')
        return log

    # ── 调度管理 ──────────────────────────────────────────

    @staticmethod
    def _register_schedule(task: CrawlTask) -> None:
        """注册到 Celery Beat 调度

        注意：项目使用 DatabaseScheduler，调度条目需写入 task_scheduler 表。
        创建调度条目需通过任务调度模块的 API 完成（需要异步 DB session）。
        此方法仅保留兼容标记，实际注册流程：
        1. 创建/更新采集任务时 → 标记需要注册调度
        2. 通过 POST /api/v1/task-scheduler 创建调度条目
           task='crawl_task_scheduled', args=[task.id]
        """
        pass

    @staticmethod
    async def get_dashboard_stats(*, db: AsyncSession) -> dict[str, Any]:
        """获取采集任务仪表盘统计"""
        tasks = await crawl_task_dao.get_all(db)
        total = len(tasks)
        running = sum(1 for t in tasks if t.status == 'running')
        stopped = sum(1 for t in tasks if t.status == 'stopped')
        paused = sum(1 for t in tasks if t.status == 'paused')
        error = sum(1 for t in tasks if t.status == 'error')

        total_records = sum(t.total_records or 0 for t in tasks)
        total_runs = sum(t.total_run_count or 0 for t in tasks)

        return {
            'total': total,
            'running': running,
            'stopped': stopped,
            'paused': paused,
            'error': error,
            'total_records': total_records,
            'total_runs': total_runs,
        }


crawl_task_service: CrawlTaskService = CrawlTaskService()
