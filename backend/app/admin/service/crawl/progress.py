"""采集任务进度追踪与取消模块

负责：
1. 通过 Redis 发布采集进度（供 SocketIO 推送）
2. 通过 Redis 检查取消信号（支持任务撤销）
3. 进度百分比计算
4. 断点续传状态管理
"""

from __future__ import annotations

import json
import asyncio
from datetime import datetime
from typing import Any

from loguru import logger

from backend.database.redis import redis_client


# ── Redis Key 前缀 ──────────────────────────────────────────

PROGRESS_KEY_PREFIX = 'crawl:progress:'
CANCEL_KEY_PREFIX = 'crawl:cancel:'
CHECKPOINT_KEY_PREFIX = 'crawl:checkpoint:'


# ── 进度追踪 ─────────────────────────────────────────────────

class CrawlProgressTracker:
    """采集任务进度追踪器

    通过 Redis 存储和发布采集进度，支持：
    - 实时进度百分比计算
    - SocketIO 推送通知
    - 取消信号检测
    - 断点续传状态保存
    """

    def __init__(self, task_id: int, run_id: str) -> None:
        self.task_id = task_id
        self.run_id = run_id
        self._progress_key = f'{PROGRESS_KEY_PREFIX}{task_id}:{run_id}'
        self._cancel_key = f'{CANCEL_KEY_PREFIX}{task_id}'
        self._checkpoint_key = f'{CHECKPOINT_KEY_PREFIX}{task_id}'

    async def update_progress(
        self,
        phase: str,
        current: int,
        total: int,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """更新采集进度

        Args:
            phase: 当前阶段 (reading/filtering/transforming/writing)
            current: 当前处理数
            total: 总数
            extra: 额外信息
        """
        percentage = round((current / total) * 100, 1) if total > 0 else 0.0

        progress_data = {
            'task_id': self.task_id,
            'run_id': self.run_id,
            'phase': phase,
            'current': current,
            'total': total,
            'percentage': percentage,
            'timestamp': datetime.now().isoformat(),
            **(extra or {}),
        }

        try:
            # 存储进度到 Redis（TTL 1 小时）
            await redis_client.setex(
                self._progress_key,
                3600,
                json.dumps(progress_data, default=str),
            )

            # 通过 Redis Pub/Sub 发布进度事件
            await redis_client.publish(
                'crawl:progress',
                json.dumps(progress_data, default=str),
            )
        except Exception as e:
            logger.debug(f'[CrawlProgress] 更新进度失败（不影响任务执行）: {e}')

    async def is_cancelled(self) -> bool:
        """检查任务是否被取消

        Returns:
            True 表示任务应被取消
        """
        try:
            cancelled = await redis_client.get(self._cancel_key)
            return cancelled is not None and cancelled == '1'
        except Exception as e:
            logger.debug(f'[CrawlProgress] 检查取消信号失败: {e}')
            return False

    async def clear_cancel_signal(self) -> None:
        """清除取消信号"""
        try:
            await redis_client.delete(self._cancel_key)
        except Exception as e:
            logger.debug(f'[CrawlProgress] 清除取消信号失败: {e}')

    async def save_checkpoint(self, data: dict[str, Any]) -> None:
        """保存断点续传状态

        Args:
            data: 断点信息（包含已处理的主键列表、增量值等）
        """
        try:
            await redis_client.setex(
                self._checkpoint_key,
                86400,  # 24 小时 TTL
                json.dumps(data, default=str),
            )
        except Exception as e:
            logger.debug(f'[CrawlProgress] 保存断点失败: {e}')

    async def load_checkpoint(self) -> dict[str, Any] | None:
        """加载断点续传状态

        Returns:
            断点信息，如果不存在则返回 None
        """
        try:
            data = await redis_client.get(self._checkpoint_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.debug(f'[CrawlProgress] 加载断点失败: {e}')
            return None

    async def clear_checkpoint(self) -> None:
        """清除断点续传状态"""
        try:
            await redis_client.delete(self._checkpoint_key)
        except Exception as e:
            logger.debug(f'[CrawlProgress] 清除断点失败: {e}')

    async def clear_progress(self) -> None:
        """清除进度信息"""
        try:
            await redis_client.delete(self._progress_key)
        except Exception as e:
            logger.debug(f'[CrawlProgress] 清除进度失败: {e}')


# ── 取消信号管理 ─────────────────────────────────────────────

async def send_cancel_signal(task_id: int) -> bool:
    """发送取消信号

    Args:
        task_id: 采集任务 ID

    Returns:
        True 表示信号发送成功
    """
    try:
        await redis_client.setex(
            f'{CANCEL_KEY_PREFIX}{task_id}',
            300,  # 5 分钟 TTL，自动过期
            '1',
        )
        logger.info(f'[CrawlProgress] 已发送取消信号 task_id={task_id}')
        return True
    except Exception as e:
        logger.error(f'[CrawlProgress] 发送取消信号失败: {e}')
        return False


async def revoke_celery_task(celery_task_id: str) -> bool:
    """撤销 Celery 任务

    Args:
        celery_task_id: Celery 任务 ID

    Returns:
        True 表示撤销命令已发送
    """
    try:
        from backend.app.task.celery import celery_app
        celery_app.control.revoke(celery_task_id, terminate=True, signal='SIGTERM')
        logger.info(f'[CrawlProgress] 已发送 Celery 任务撤销信号 task_id={celery_task_id}')
        return True
    except Exception as e:
        logger.error(f'[CrawlProgress] 撤销 Celery 任务失败: {e}')
        return False


# ── SocketIO 进度推送 ─────────────────────────────────────────

async def broadcast_crawl_progress(progress_data: dict[str, Any]) -> None:
    """通过 SocketIO 广播采集进度

    Args:
        progress_data: 进度数据
    """
    try:
        from backend.common.socketio.actions import sio
        await sio.emit('crawl_progress', progress_data, namespace='/ws')
    except Exception as e:
        logger.debug(f'[CrawlProgress] SocketIO 推送失败（不影响任务执行）: {e}')


async def subscribe_crawl_progress() -> None:
    """订阅 Redis 频道，将进度推送到 SocketIO

    在应用启动时调用，持续监听 crawl:progress 频道。
    """
    try:
        pubsub = redis_client.pubsub()
        await pubsub.subscribe('crawl:progress')

        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    await broadcast_crawl_progress(data)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f'[CrawlProgress] 解析进度消息失败: {e}')
    except asyncio.CancelledError:
        logger.info('[CrawlProgress] 进度订阅已取消')
    except Exception as e:
        logger.error(f'[CrawlProgress] 进度订阅异常: {e}')