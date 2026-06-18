"""动态调度服务

提供基于 Redis 的动态调度管理功能，支持：
- 添加/移除/更新动态调度任务
- 启用/禁用调度任务
- 列出所有动态调度任务
- 与数据库调度器协同工作
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from backend.app.task.enums import TaskSchedulerType
from backend.app.task.utils.redbeat_scheduler import (
    add_dynamic_schedule,
    get_dynamic_schedule,
    list_dynamic_schedules,
    remove_dynamic_schedule,
    toggle_dynamic_schedule,
    update_dynamic_schedule,
)
from backend.common.exception import errors


class DynamicScheduleService:
    """动态调度服务类"""

    @staticmethod
    async def create(
        *,
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
    ) -> dict[str, Any]:
        """创建动态调度任务

        Args:
            name: 任务名称（唯一标识）
            task: Celery 任务路径
            schedule_type: 调度类型（0=间隔, 1=定时）
            interval_every: 间隔周期数
            interval_period: 间隔周期类型
            crontab: Crontab 表达式
            args: 任务位置参数
            kwargs: 任务关键字参数
            options: 额外选项
            enabled: 是否启用
            ttl: Redis 键过期时间（秒）

        Returns:
            创建结果
        """
        # 检查是否已存在
        existing = await get_dynamic_schedule(name)
        if existing:
            raise errors.ConflictError(msg=f'动态调度任务已存在: {name}')

        # 验证调度参数
        if schedule_type == TaskSchedulerType.INTERVAL:
            if not interval_every or not interval_period:
                raise errors.RequestError(msg='间隔调度必须指定 interval_every 和 interval_period')
        elif schedule_type == TaskSchedulerType.CRONTAB:
            if not crontab:
                raise errors.RequestError(msg='定时调度必须指定 crontab 表达式')
            from backend.app.task.utils.tzcrontab import crontab_verify
            crontab_verify(crontab)

        success = await add_dynamic_schedule(
            name=name,
            task=task,
            schedule_type=schedule_type,
            interval_every=interval_every,
            interval_period=interval_period,
            crontab=crontab,
            args=args,
            kwargs=kwargs,
            options=options,
            enabled=enabled,
            ttl=ttl,
        )

        if not success:
            raise errors.ServerError(msg='创建动态调度任务失败')

        return await get_dynamic_schedule(name) or {}

    @staticmethod
    async def update(
        *,
        name: str,
        **updates: Any,
    ) -> dict[str, Any]:
        """更新动态调度任务

        Args:
            name: 任务名称
            **updates: 要更新的字段

        Returns:
            更新后的调度配置
        """
        existing = await get_dynamic_schedule(name)
        if not existing:
            raise errors.NotFoundError(msg=f'动态调度任务不存在: {name}')

        # 如果更新了 crontab，验证格式
        if 'crontab' in updates and updates['crontab']:
            from backend.app.task.utils.tzcrontab import crontab_verify
            crontab_verify(updates['crontab'])

        success = await update_dynamic_schedule(name, **updates)
        if not success:
            raise errors.ServerError(msg='更新动态调度任务失败')

        return await get_dynamic_schedule(name) or {}

    @staticmethod
    async def delete(*, name: str) -> None:
        """删除动态调度任务

        Args:
            name: 任务名称
        """
        existing = await get_dynamic_schedule(name)
        if not existing:
            raise errors.NotFoundError(msg=f'动态调度任务不存在: {name}')

        success = await remove_dynamic_schedule(name)
        if not success:
            raise errors.ServerError(msg='删除动态调度任务失败')

    @staticmethod
    async def get(*, name: str) -> dict[str, Any]:
        """获取动态调度任务详情

        Args:
            name: 任务名称

        Returns:
            调度配置
        """
        data = await get_dynamic_schedule(name)
        if not data:
            raise errors.NotFoundError(msg=f'动态调度任务不存在: {name}')
        return data

    @staticmethod
    async def get_list(*, prefix: str = '') -> list[dict[str, Any]]:
        """获取动态调度任务列表

        Args:
            prefix: 任务名称前缀过滤

        Returns:
            调度配置列表
        """
        return await list_dynamic_schedules(prefix=prefix)

    @staticmethod
    async def toggle(*, name: str, enabled: bool) -> dict[str, Any]:
        """启用/禁用动态调度任务

        Args:
            name: 任务名称
            enabled: 是否启用

        Returns:
            更新后的调度配置
        """
        existing = await get_dynamic_schedule(name)
        if not existing:
            raise errors.NotFoundError(msg=f'动态调度任务不存在: {name}')

        success = await toggle_dynamic_schedule(name, enabled=enabled)
        if not success:
            raise errors.ServerError(msg='更新动态调度任务状态失败')

        return await get_dynamic_schedule(name) or {}


dynamic_schedule_service: DynamicScheduleService = DynamicScheduleService()