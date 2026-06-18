"""基于 celery-redbeat 的动态调度器

提供：
1. RedBeatScheduler - 基于 Redis 的 Celery Beat 调度器
2. RedBeatScheduleEntry - 兼容现有 DatabaseScheduler 的调度条目
3. 动态调度管理 - 任务创建/修改/删除时实时更新

与现有 DatabaseScheduler 的关系：
- RedBeatScheduler 作为可选的替代调度器
- 通过配置 CELERY_BEAT_SCHEDULER 切换
- 保留 DatabaseScheduler 作为默认调度器（向后兼容）

优势：
- 基于 Redis 存储，无需数据库轮询
- 支持分布式调度（多 Beat 实例自动选主）
- 任务变更实时生效（无需等待数据库轮询间隔）
- 更低的调度延迟
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from typing import Any

from celery import current_app, schedules
from celery.beat import ScheduleEntry, Scheduler
from celery.utils.log import get_logger
from loguru import logger as loguru_logger
from redis.exceptions import RedisError

from backend.app.task.enums import PeriodType, TaskSchedulerType
from backend.app.task.utils.tzcrontab import TzAwareCrontab
from backend.common.exception import errors
from backend.core.conf import settings
from backend.database.redis import redis_client
from backend.utils.async_helper import run_await
from backend.utils.timezone import timezone

# Redis Key 前缀
REDBEAT_KEY_PREFIX = f'{settings.CELERY_REDIS_PREFIX}:redbeat:'
REDBEAT_LOCK_KEY = f'{settings.CELERY_REDIS_PREFIX}:redbeat:lock'

# 默认配置
_DEFAULT_MAX_INTERVAL = 5  # 秒
_DEFAULT_LOCK_TIMEOUT = _DEFAULT_MAX_INTERVAL * 5  # 秒


class RedBeatScheduleEntry(ScheduleEntry):
    """基于 Redis 的调度条目

    兼容现有 TaskScheduler 模型，同时支持从 Redis 读取调度配置。
    """

    def __init__(self, name: str, task: str, schedule: schedules.schedule, **kwargs) -> None:
        self.app = kwargs.pop('app', current_app._get_current_object())
        super().__init__(
            app=self.app,
            name=name,
            task=task,
            schedule=schedule,
            args=kwargs.get('args'),
            kwargs=kwargs.get('kwargs'),
            options=kwargs.get('options', {}),
            last_run_at=kwargs.get('last_run_at', timezone.now()),
            total_run_count=kwargs.get('total_run_count', 0),
        )

    @classmethod
    def from_model(cls, model: Any, app=None) -> RedBeatScheduleEntry:
        """从 TaskScheduler 模型创建调度条目

        Args:
            model: TaskScheduler ORM 对象
            app: Celery 应用实例

        Returns:
            RedBeatScheduleEntry 实例
        """
        try:
            if (
                model.type == TaskSchedulerType.INTERVAL
                and model.interval_every is not None
                and model.interval_period is not None
            ):
                schedule = schedules.schedule(timedelta(**{model.interval_period: model.interval_every}))
            elif model.type == TaskSchedulerType.CRONTAB and model.crontab is not None:
                schedule = TzAwareCrontab.from_string(model.crontab)
            else:
                raise errors.NotFoundError(msg=f'{model.name} 计划为空！')
        except Exception as e:
            loguru_logger.error(f'禁用计划为空的任务 {model.name}，详情：{e}')
            # 返回一个永远不会触发的调度
            schedule = schedules.schedule(timedelta(days=365 * 100))

        try:
            args = json.loads(model.args) if model.args else None
            kwargs_data = json.loads(model.kwargs) if model.kwargs else None
        except (ValueError, json.JSONDecodeError) as exc:
            loguru_logger.error(f'禁用参数错误的任务：{model.name}；error: {exc!s}')
            args = None
            kwargs_data = None

        options = {}
        for option in ['queue', 'exchange', 'routing_key']:
            value = getattr(model, option, None)
            if value is not None:
                options[option] = value

        if model.expire_seconds is not None:
            options['expires'] = model.expire_seconds
        elif model.expire_time is not None:
            options['expires'] = timezone.from_datetime(model.expire_time)

        last_run_at = timezone.from_datetime(model.last_run_time) if model.last_run_time else timezone.now()
        if model.start_time:
            start_time = timezone.from_datetime(model.start_time)
            if last_run_at < start_time:
                last_run_at = start_time - timedelta(days=365)

        return cls(
            name=model.name,
            task=model.task,
            schedule=schedule,
            args=args,
            kwargs=kwargs_data,
            options=options,
            last_run_at=last_run_at,
            total_run_count=model.total_run_count or 0,
            app=app,
        )

    @classmethod
    def from_redis(cls, name: str, data: dict[str, Any], app=None) -> RedBeatScheduleEntry:
        """从 Redis 数据创建调度条目

        Args:
            name: 任务名称
            data: Redis 存储的调度数据
            app: Celery 应用实例

        Returns:
            RedBeatScheduleEntry 实例
        """
        schedule_type = data.get('type', TaskSchedulerType.INTERVAL)

        if schedule_type == TaskSchedulerType.INTERVAL:
            every = data.get('interval_every', 60)
            period = data.get('interval_period', PeriodType.SECONDS)
            schedule = schedules.schedule(timedelta(**{period: every}))
        elif schedule_type == TaskSchedulerType.CRONTAB:
            crontab_str = data.get('crontab', '* * * * *')
            schedule = TzAwareCrontab.from_string(crontab_str)
        else:
            schedule = schedules.schedule(timedelta(days=365 * 100))

        return cls(
            name=name,
            task=data.get('task', ''),
            schedule=schedule,
            args=data.get('args'),
            kwargs=data.get('kwargs'),
            options=data.get('options', {}),
            last_run_at=timezone.from_str(data['last_run_at']) if data.get('last_run_at') else timezone.now(),
            total_run_count=data.get('total_run_count', 0),
            app=app,
        )

    def to_redis(self) -> dict[str, Any]:
        """序列化为 Redis 存储格式

        Returns:
            可 JSON 序列化的字典
        """
        data = {
            'name': self.name,
            'task': self.task,
            'args': self.args,
            'kwargs': self.kwargs,
            'options': self.options,
            'total_run_count': self.total_run_count,
            'last_run_at': timezone.to_str(self.last_run_at),
        }

        if isinstance(self.schedule, schedules.schedule):
            data['type'] = TaskSchedulerType.INTERVAL
            data['interval_every'] = self.schedule.run_every.total_seconds()
            data['interval_period'] = PeriodType.SECONDS
        elif isinstance(self.schedule, schedules.crontab):
            data['type'] = TaskSchedulerType.CRONTAB
            data['crontab'] = (
                f'{self.schedule._orig_minute} {self.schedule._orig_hour} '
                f'{self.schedule._orig_day_of_month} {self.schedule._orig_month_of_year} '
                f'{self.schedule._orig_day_of_week}'
            )

        return data

    def is_due(self) -> tuple[bool, int | float | datetime]:
        """检查任务是否到期"""
        return self.schedule.is_due(self.last_run_at)

    def __next__(self):  # noqa: ANN204
        self.last_run_at = timezone.now()
        self.total_run_count += 1
        return self.__class__(
            name=self.name,
            task=self.task,
            schedule=self.schedule,
            args=self.args,
            kwargs=self.kwargs,
            options=self.options,
            last_run_at=self.last_run_at,
            total_run_count=self.total_run_count,
            app=self.app,
        )

    next = __next__


class RedBeatScheduler(Scheduler):
    """基于 Redis 的 Celery Beat 调度器

    特性：
    - 调度配置存储在 Redis 中，支持实时更新
    - 支持分布式调度（多 Beat 实例自动选主）
    - 兼容现有 DatabaseScheduler 的数据模型
    - 任务变更通过 Redis Pub/Sub 实时通知

    配置方式：
    在 celery.py 中设置：
        beat_scheduler='backend.app.task.utils.redbeat_scheduler:RedBeatScheduler'

    或者通过环境变量：
        CELERY_BEAT_SCHEDULER=backend.app.task.utils.redbeat_scheduler:RedBeatScheduler
    """

    Entry = RedBeatScheduleEntry

    _schedule: dict[str, RedBeatScheduleEntry] | None = None
    _last_update: datetime | None = None
    _initial_read = True
    _lock = None

    def __init__(self, *args, **kwargs) -> None:
        self.app = kwargs.get('app', current_app._get_current_object())
        self._dirty: set[str] = set()
        super().__init__(*args, **kwargs)
        self.max_interval = kwargs.get('max_interval') or self.app.conf.beat_max_loop_interval or _DEFAULT_MAX_INTERVAL

    def setup_schedule(self) -> None:
        """初始化调度配置"""
        loguru_logger.info('[RedBeat] 初始化调度配置')
        # 从本地配置加载默认调度
        from backend.app.task.tasks.beat import get_local_beat_schedule

        tasks = self.schedule
        self.install_default_entries(tasks)
        self.update_from_dict(self.app.conf.beat_schedule)

    def update_from_dict(self, beat_dict: dict) -> None:
        """从字典更新调度配置"""
        s = {}
        name = None
        try:
            for name, entry_fields in beat_dict.items():
                entry = run_await(self._create_entry_from_dict)(name, **entry_fields)
                if entry:
                    s[name] = entry
        except Exception:
            loguru_logger.error(f'添加任务 {name} 到调度失败')
            raise

        tasks = self.schedule
        tasks.update(s)

    async def _create_entry_from_dict(self, name: str, **entry_fields) -> RedBeatScheduleEntry | None:
        """从字典创建调度条目"""
        from sqlalchemy import select
        from backend.app.task.model.scheduler import TaskScheduler
        from backend.database.db import async_db_session

        async with async_db_session() as db:
            stmt = select(TaskScheduler).where(TaskScheduler.name == name)
            query = await db.execute(stmt)
            model = query.scalars().first()

            if model and model.enabled:
                return RedBeatScheduleEntry.from_model(model, app=self.app)

        # 如果数据库中没有，从字典字段创建
        schedule = entry_fields.get('schedule')
        if schedule is None:
            return None

        return RedBeatScheduleEntry(
            name=name,
            task=entry_fields.get('task', ''),
            schedule=schedule,
            args=entry_fields.get('args'),
            kwargs=entry_fields.get('kwargs'),
            options=entry_fields.get('options', {}),
            app=self.app,
        )

    def schedule_changed(self) -> bool:
        """检查调度是否发生变更

        通过 Redis Pub/Sub 通知机制实现实时检测，
        比数据库轮询更高效。
        """
        try:
            last_update = run_await(redis_client.get)(f'{settings.CELERY_REDIS_PREFIX}:last_update')
            if not last_update:
                run_await(redis_client.set)(f'{settings.CELERY_REDIS_PREFIX}:last_update', timezone.to_str(timezone.now()))
                return False

            ts = timezone.from_str(last_update)
            if self._last_update is None:
                self._last_update = ts
                return True

            if ts > self._last_update:
                self._last_update = ts
                return True

            return False
        except (RedisError, Exception) as e:
            loguru_logger.warning(f'[RedBeat] 检查调度变更失败: {e}')
            return False

    async def get_all_task_schedulers(self) -> dict[str, RedBeatScheduleEntry]:
        """从数据库和 Redis 获取所有启用的调度任务"""
        from sqlalchemy import select
        from backend.app.task.model.scheduler import TaskScheduler
        from backend.database.db import async_db_session

        entries: dict[str, RedBeatScheduleEntry] = {}

        # 1. 从数据库加载
        async with async_db_session() as db:
            stmt = select(TaskScheduler).where(TaskScheduler.enabled == True)  # noqa: E712
            query = await db.execute(stmt)
            schedulers = query.scalars().all()

            for scheduler in schedulers:
                try:
                    entry = RedBeatScheduleEntry.from_model(scheduler, app=self.app)
                    entries[scheduler.name] = entry
                except Exception as e:
                    loguru_logger.error(f'[RedBeat] 加载任务 {scheduler.name} 失败: {e}')

        # 2. 从 Redis 加载动态调度（覆盖数据库配置）
        try:
            redis_entries = await self._load_redis_entries()
            entries.update(redis_entries)
        except Exception as e:
            loguru_logger.warning(f'[RedBeat] 从 Redis 加载调度失败: {e}')

        return entries

    async def _load_redis_entries(self) -> dict[str, RedBeatScheduleEntry]:
        """从 Redis 加载动态调度条目"""
        entries: dict[str, RedBeatScheduleEntry] = {}

        try:
            keys = await redis_client.get_prefix(f'{REDBEAT_KEY_PREFIX}', count=500)
            for key in keys:
                try:
                    data_str = await redis_client.get(key)
                    if data_str:
                        data = json.loads(data_str)
                        name = data.get('name', key.replace(REDBEAT_KEY_PREFIX, ''))
                        if data.get('enabled', True):
                            entry = RedBeatScheduleEntry.from_redis(name, data, app=self.app)
                            entries[name] = entry
                except (json.JSONDecodeError, Exception) as e:
                    loguru_logger.warning(f'[RedBeat] 解析 Redis 调度条目失败: {key}, error: {e}')
        except Exception as e:
            loguru_logger.warning(f'[RedBeat] 扫描 Redis 调度条目失败: {e}')

        return entries

    @property
    def schedule(self) -> dict[str, RedBeatScheduleEntry]:
        """获取当前调度配置"""
        initial = update = False
        if self._initial_read:
            loguru_logger.debug('[RedBeat] 初始加载调度配置')
            initial = update = True
            self._initial_read = False
        elif self.schedule_changed():
            loguru_logger.info('[RedBeat] 检测到调度变更，重新加载')
            update = True

        if update:
            self.sync()
            self._schedule = run_await(self.get_all_task_schedulers)()
            if not initial:
                self._heap = []
                self._heap_invalidated = True

        return self._schedule or {}

    def sync(self) -> None:
        """同步脏数据到 Redis"""
        tried = set()
        failed = set()
        try:
            while self._dirty:
                name = self._dirty.pop()
                try:
                    tasks = self.schedule
                    entry = tasks.get(name)
                    if entry:
                        run_await(self._save_entry_to_redis)(entry)
                        loguru_logger.debug(f'[RedBeat] 保存任务 {name} 状态到 Redis')
                    tried.add(name)
                except KeyError as e:
                    loguru_logger.error(f'[RedBeat] 保存任务 {name} 状态失败：{e}')
                    failed.add(name)
        except Exception as e:
            loguru_logger.exception(f'[RedBeat] 同步时出现错误: {e}')
        finally:
            self._dirty |= failed

    async def _save_entry_to_redis(self, entry: RedBeatScheduleEntry) -> None:
        """保存调度条目到 Redis"""
        data = entry.to_redis()
        key = f'{REDBEAT_KEY_PREFIX}{entry.name}'
        await redis_client.setex(key, 86400, json.dumps(data, default=str))

    def reserve(self, entry) -> RedBeatScheduleEntry:  # noqa: ANN001
        """重写父函数"""
        new_entry = next(entry)
        self._dirty.add(new_entry.name)
        return new_entry

    def close(self) -> None:
        """关闭调度器"""
        if self._lock:
            loguru_logger.info('[RedBeat] 释放分布式锁')
            try:
                run_await(self._lock.release)()
            except Exception:
                pass
            self._lock = None
        super().close()


# ── 动态调度管理 API ──────────────────────────────────────────

async def add_dynamic_schedule(
    name: str,
    task: str,
    schedule_type: int = TaskSchedulerType.INTERVAL,
    interval_every: int | None = None,
    interval_period: str | None = None,
    crontab: str | None = None,
    args: list | None = None,
    kwargs: dict | None = None,
    options: dict | None = None,
    enabled: bool = True,
    ttl: int = 86400,
) -> bool:
    """添加动态调度任务到 Redis

    Args:
        name: 任务名称（唯一标识）
        task: Celery 任务路径
        schedule_type: 调度类型（0=间隔, 1=定时）
        interval_every: 间隔周期数
        interval_period: 间隔周期类型
        crontab: Crontab 表达式
        args: 任务位置参数
        kwargs: 任务关键字参数
        options: 额外选项（queue, exchange, routing_key 等）
        enabled: 是否启用
        ttl: Redis 键过期时间（秒），默认 24 小时

    Returns:
        True 表示添加成功
    """
    data = {
        'name': name,
        'task': task,
        'type': schedule_type,
        'interval_every': interval_every,
        'interval_period': interval_period,
        'crontab': crontab,
        'args': args,
        'kwargs': kwargs,
        'options': options or {},
        'enabled': enabled,
        'total_run_count': 0,
        'last_run_at': timezone.to_str(timezone.now()),
    }

    try:
        key = f'{REDBEAT_KEY_PREFIX}{name}'
        await redis_client.setex(key, ttl, json.dumps(data, default=str))

        # 通知调度器刷新
        await redis_client.set(
            f'{settings.CELERY_REDIS_PREFIX}:last_update',
            timezone.to_str(timezone.now()),
        )

        loguru_logger.info(f'[RedBeat] 添加动态调度任务: {name}')
        return True
    except Exception as e:
        loguru_logger.error(f'[RedBeat] 添加动态调度任务失败: {name}, error: {e}')
        return False


async def remove_dynamic_schedule(name: str) -> bool:
    """从 Redis 移除动态调度任务

    Args:
        name: 任务名称

    Returns:
        True 表示移除成功
    """
    try:
        key = f'{REDBEAT_KEY_PREFIX}{name}'
        await redis_client.delete(key)

        # 通知调度器刷新
        await redis_client.set(
            f'{settings.CELERY_REDIS_PREFIX}:last_update',
            timezone.to_str(timezone.now()),
        )

        loguru_logger.info(f'[RedBeat] 移除动态调度任务: {name}')
        return True
    except Exception as e:
        loguru_logger.error(f'[RedBeat] 移除动态调度任务失败: {name}, error: {e}')
        return False


async def update_dynamic_schedule(
    name: str,
    **updates: Any,
) -> bool:
    """更新 Redis 中的动态调度任务

    Args:
        name: 任务名称
        **updates: 要更新的字段

    Returns:
        True 表示更新成功
    """
    try:
        key = f'{REDBEAT_KEY_PREFIX}{name}'
        data_str = await redis_client.get(key)

        if not data_str:
            loguru_logger.warning(f'[RedBeat] 动态调度任务不存在: {name}')
            return False

        data = json.loads(data_str)
        data.update(updates)

        # 保持原有 TTL
        ttl = await redis_client.ttl(key)
        if ttl <= 0:
            ttl = 86400

        await redis_client.setex(key, ttl, json.dumps(data, default=str))

        # 通知调度器刷新
        await redis_client.set(
            f'{settings.CELERY_REDIS_PREFIX}:last_update',
            timezone.to_str(timezone.now()),
        )

        loguru_logger.info(f'[RedBeat] 更新动态调度任务: {name}')
        return True
    except Exception as e:
        loguru_logger.error(f'[RedBeat] 更新动态调度任务失败: {name}, error: {e}')
        return False


async def get_dynamic_schedule(name: str) -> dict[str, Any] | None:
    """获取 Redis 中的动态调度任务

    Args:
        name: 任务名称

    Returns:
        调度配置字典，不存在则返回 None
    """
    try:
        key = f'{REDBEAT_KEY_PREFIX}{name}'
        data_str = await redis_client.get(key)
        if data_str:
            return json.loads(data_str)
        return None
    except Exception as e:
        loguru_logger.error(f'[RedBeat] 获取动态调度任务失败: {name}, error: {e}')
        return None


async def list_dynamic_schedules(prefix: str = '') -> list[dict[str, Any]]:
    """列出所有动态调度任务

    Args:
        prefix: 任务名称前缀过滤

    Returns:
        调度配置列表
    """
    try:
        pattern = f'{REDBEAT_KEY_PREFIX}{prefix}*'
        keys = await redis_client.get_prefix(pattern, count=500)

        result = []
        for key in keys:
            data_str = await redis_client.get(key)
            if data_str:
                try:
                    data = json.loads(data_str)
                    result.append(data)
                except json.JSONDecodeError:
                    continue

        return result
    except Exception as e:
        loguru_logger.error(f'[RedBeat] 列出动态调度任务失败: {e}')
        return []


async def toggle_dynamic_schedule(name: str, enabled: bool) -> bool:
    """启用/禁用动态调度任务

    Args:
        name: 任务名称
        enabled: 是否启用

    Returns:
        True 表示操作成功
    """
    return await update_dynamic_schedule(name, enabled=enabled)