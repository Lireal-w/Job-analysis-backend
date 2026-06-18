"""数据源连接池管理器

负责：
1. 基于 datasource_id 缓存 SQLAlchemy Engine
2. 连接健康检查和自动回收
3. 最大连接数限制和等待超时
4. 空闲连接超时回收
5. 连接使用统计

用法：
    manager = ConnectionPoolManager()
    engine = await manager.get_engine(datasource)
    async with AsyncSession(engine) as session:
        result = await session.execute(text("SELECT 1"))
    # 使用完毕后不需要手动关闭，管理器会自动管理
"""

from __future__ import annotations

import time
import asyncio
import traceback
from dataclasses import dataclass, field
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.admin.service.datasource_service import _decrypt_password
from backend.database.redis import redis_client


# ── 常量 ──────────────────────────────────────────────────────

# 连接池默认配置
DEFAULT_POOL_SIZE = 5
DEFAULT_MAX_OVERFLOW = 10
DEFAULT_POOL_TIMEOUT = 30  # 秒
DEFAULT_POOL_RECYCLE = 3600  # 秒（1小时回收连接）
DEFAULT_POOL_PRE_PING = True

# 健康检查间隔（秒）
HEALTH_CHECK_INTERVAL = 60

# 空闲连接超时（秒）
IDLE_TIMEOUT = 600  # 10 分钟

# 最大缓存引擎数
MAX_CACHED_ENGINES = 50

# Redis Key 前缀
POOL_STATS_KEY = 'datasource:pool_stats:'


@dataclass
class PoolStats:
    """连接池统计"""

    datasource_id: int
    datasource_name: str
    pool_size: int = 0
    checked_out: int = 0
    overflow: int = 0
    total_created: int = 0
    last_used: float = 0.0
    last_health_check: float = 0.0
    is_healthy: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            'datasource_id': self.datasource_id,
            'datasource_name': self.datasource_name,
            'pool_size': self.pool_size,
            'checked_out': self.checked_out,
            'overflow': self.overflow,
            'total_created': self.total_created,
            'last_used': self.last_used,
            'last_health_check': self.last_health_check,
            'is_healthy': self.is_healthy,
        }


class ConnectionPoolManager:
    """数据源连接池管理器

    基于 datasource_id 缓存 SQLAlchemy Engine，提供连接健康检查、
    自动回收、最大连接数限制等功能。

    用法：
        manager = ConnectionPoolManager()
        engine = await manager.get_engine(datasource)
        async with AsyncSession(engine) as session:
            result = await session.execute(text("SELECT 1"))
    """

    _instance: ConnectionPoolManager | None = None

    def __new__(cls) -> ConnectionPoolManager:
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._engines: dict[int, Any] = {}
        self._stats: dict[int, PoolStats] = {}
        self._lock = asyncio.Lock()
        self._health_check_task: asyncio.Task | None = None

    async def get_engine(
        self,
        datasource: Any,
        pool_size: int = DEFAULT_POOL_SIZE,
        max_overflow: int = DEFAULT_MAX_OVERFLOW,
        pool_timeout: int = DEFAULT_POOL_TIMEOUT,
        pool_recycle: int = DEFAULT_POOL_RECYCLE,
    ) -> Any:
        """获取数据源的 SQLAlchemy Engine

        如果缓存中存在且健康，直接返回；否则创建新连接。

        Args:
            datasource: 数据源 ORM 对象
            pool_size: 连接池大小
            max_overflow: 最大溢出连接数
            pool_timeout: 获取连接超时（秒）
            pool_recycle: 连接回收时间（秒）

        Returns:
            SQLAlchemy AsyncEngine
        """
        async with self._lock:
            ds_id = datasource.id

            # 检查缓存
            if ds_id in self._engines:
                engine = self._engines[ds_id]
                stats = self._stats.get(ds_id)

                # 检查数据源配置是否变更（通过比较密码和连接参数）
                if stats and stats.is_healthy:
                    stats.last_used = time.time()
                    return engine

                # 不健康，移除旧引擎
                await self._dispose_engine(ds_id)

            # 检查缓存数量限制
            if len(self._engines) >= MAX_CACHED_ENGINES:
                # 移除最久未使用的引擎
                await self._evict_oldest()

            # 创建新引擎
            engine = await self._create_engine(
                datasource,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,
            )

            # 缓存引擎
            self._engines[ds_id] = engine
            self._stats[ds_id] = PoolStats(
                datasource_id=ds_id,
                datasource_name=datasource.name,
                pool_size=pool_size,
                last_used=time.time(),
                last_health_check=time.time(),
                is_healthy=True,
            )

            return engine

    async def _create_engine(
        self,
        datasource: Any,
        pool_size: int = DEFAULT_POOL_SIZE,
        max_overflow: int = DEFAULT_MAX_OVERFLOW,
        pool_timeout: int = DEFAULT_POOL_TIMEOUT,
        pool_recycle: int = DEFAULT_POOL_RECYCLE,
    ) -> Any:
        """创建 SQLAlchemy AsyncEngine"""
        from backend.app.admin.service.query.engine import build_db_url

        password = _decrypt_password(datasource.password)
        url = build_db_url(datasource, password)

        # 处理额外参数
        import json
        connect_args = {}
        if datasource.extra_params:
            try:
                extra = json.loads(datasource.extra_params) if isinstance(datasource.extra_params, str) else datasource.extra_params
                if isinstance(extra, dict):
                    connect_args = extra.get('connect_args', {})
            except (json.JSONDecodeError, TypeError):
                pass

        engine = create_async_engine(
            url,
            echo=False,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=DEFAULT_POOL_PRE_PING,
            connect_args=connect_args,
        )

        logger.info(
            f'[ConnectionPool] 创建数据源连接池: '
            f'id={datasource.id}, name={datasource.name}, type={datasource.db_type}'
        )

        return engine

    async def _dispose_engine(self, ds_id: int) -> None:
        """释放引擎连接"""
        engine = self._engines.pop(ds_id, None)
        self._stats.pop(ds_id, None)

        if engine is not None:
            try:
                await engine.dispose()
                logger.info(f'[ConnectionPool] 释放数据源连接池: id={ds_id}')
            except Exception as e:
                logger.warning(f'[ConnectionPool] 释放连接池失败: id={ds_id}, error={e}')

    async def _evict_oldest(self) -> None:
        """移除最久未使用的引擎"""
        if not self._stats:
            return

        oldest_id = min(self._stats, key=lambda k: self._stats[k].last_used)
        await self._dispose_engine(oldest_id)

    async def health_check(self, ds_id: int) -> bool:
        """检查数据源连接健康状态

        Args:
            ds_id: 数据源 ID

        Returns:
            True 表示连接健康
        """
        engine = self._engines.get(ds_id)
        if engine is None:
            return False

        try:
            from sqlalchemy import text
            async with AsyncSession(engine) as session:
                await session.execute(text('SELECT 1'))
            stats = self._stats.get(ds_id)
            if stats:
                stats.is_healthy = True
                stats.last_health_check = time.time()
            return True
        except Exception as e:
            logger.warning(f'[ConnectionPool] 健康检查失败: id={ds_id}, error={e}')
            stats = self._stats.get(ds_id)
            if stats:
                stats.is_healthy = False
            return False

    async def health_check_all(self) -> dict[int, bool]:
        """检查所有缓存连接的健康状态

        Returns:
            {datasource_id: is_healthy} 字典
        """
        results = {}
        for ds_id in list(self._engines.keys()):
            results[ds_id] = await self.health_check(ds_id)
        return results

    async def remove_engine(self, ds_id: int) -> None:
        """手动移除指定数据源的连接池

        Args:
            ds_id: 数据源 ID
        """
        await self._dispose_engine(ds_id)

    async def cleanup_idle(self, idle_timeout: int = IDLE_TIMEOUT) -> int:
        """清理空闲超时的连接池

        Args:
            idle_timeout: 空闲超时时间（秒）

        Returns:
            清理的连接池数量
        """
        now = time.time()
        to_remove = []

        for ds_id, stats in self._stats.items():
            if now - stats.last_used > idle_timeout:
                to_remove.append(ds_id)

        for ds_id in to_remove:
            await self._dispose_engine(ds_id)

        if to_remove:
            logger.info(f'[ConnectionPool] 清理空闲连接池: {len(to_remove)} 个')

        return len(to_remove)

    def get_stats(self, ds_id: int | None = None) -> dict[str, Any] | list[dict[str, Any]]:
        """获取连接池统计信息

        Args:
            ds_id: 数据源 ID，为 None 时返回所有

        Returns:
            统计信息字典
        """
        if ds_id is not None:
            stats = self._stats.get(ds_id)
            return stats.to_dict() if stats else {}

        return [stats.to_dict() for stats in self._stats.values()]

    def get_pool_info(self, ds_id: int) -> dict[str, Any] | None:
        """获取连接池详细信息

        Args:
            ds_id: 数据源 ID

        Returns:
            连接池信息，包含底层连接池状态
        """
        engine = self._engines.get(ds_id)
        if engine is None:
            return None

        pool = engine.pool
        return {
            'datasource_id': ds_id,
            'pool_size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'is_valid': pool.is_valid,
        }

    async def dispose_all(self) -> None:
        """释放所有连接池"""
        for ds_id in list(self._engines.keys()):
            await self._dispose_engine(ds_id)
        logger.info('[ConnectionPool] 已释放所有连接池')

    async def start_health_check_loop(self, interval: int = HEALTH_CHECK_INTERVAL) -> None:
        """启动健康检查循环

        Args:
            interval: 检查间隔（秒）
        """
        logger.info(f'[ConnectionPool] 启动健康检查循环，间隔 {interval} 秒')

        while True:
            try:
                await asyncio.sleep(interval)
                await self.health_check_all()
                await self.cleanup_idle()
            except asyncio.CancelledError:
                logger.info('[ConnectionPool] 健康检查循环已取消')
                break
            except Exception as e:
                logger.error(f'[ConnectionPool] 健康检查异常: {e}')

    def start_background_tasks(self) -> None:
        """启动后台任务（健康检查循环）"""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(
                self.start_health_check_loop()
            )


# 全局单例
connection_pool_manager = ConnectionPoolManager()