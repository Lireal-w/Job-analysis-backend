"""采集任务进度追踪与取消模块测试"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── CrawlProgressTracker 测试 ──────────────────────────────────


class TestCrawlProgressTracker:
    """CrawlProgressTracker 单元测试"""

    @pytest.fixture
    def tracker(self):
        """创建进度追踪器实例"""
        from backend.app.admin.service.crawl.progress import CrawlProgressTracker
        return CrawlProgressTracker(task_id=1, run_id='run-001')

    @pytest.mark.asyncio
    async def test_update_progress(self, tracker):
        """测试更新进度"""
        with patch('backend.app.admin.service.crawl.progress.redis_client') as mock_redis:
            mock_redis.setex = AsyncMock()
            mock_redis.publish = AsyncMock()

            await tracker.update_progress(
                phase='reading',
                current=50,
                total=100,
                extra={'source': 'test'},
            )

            # 验证 setex 被调用
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            assert call_args[0][0] == 'crawl:progress:1:run-001'  # key
            assert call_args[0][1] == 3600  # TTL

            # 验证进度数据
            progress_data = json.loads(call_args[0][2])
            assert progress_data['task_id'] == 1
            assert progress_data['run_id'] == 'run-001'
            assert progress_data['phase'] == 'reading'
            assert progress_data['current'] == 50
            assert progress_data['total'] == 100
            assert progress_data['percentage'] == 50.0
            assert progress_data['source'] == 'test'

            # 验证 publish 被调用
            mock_redis.publish.assert_called_once()
            publish_args = mock_redis.publish.call_args
            assert publish_args[0][0] == 'crawl:progress'

    @pytest.mark.asyncio
    async def test_update_progress_zero_total(self, tracker):
        """测试总数为 0 时的进度更新"""
        with patch('backend.app.admin.service.crawl.progress.redis_client') as mock_redis:
            mock_redis.setex = AsyncMock()
            mock_redis.publish = AsyncMock()

            await tracker.update_progress(phase='reading', current=0, total=0)

            progress_data = json.loads(mock_redis.setex.call_args[0][2])
            assert progress_data['percentage'] == 0.0

    @pytest.mark.asyncio
    async def test_update_progress_error_handling(self, tracker):
        """测试进度更新失败时的错误处理"""
        with patch('backend.app.admin.service.crawl.progress.redis_client') as mock_redis:
            mock_redis.setex = AsyncMock(side_effect=Exception('Redis error'))
            mock_redis.publish = AsyncMock()

            # 不应抛出异常
            await tracker.update_progress(phase='reading', current=50, total=100)

    @pytest.mark.asyncio
    async def test_is_cancelled_true(self, tracker):
        """测试任务被取消"""
        with patch('backend.app.admin.service.crawl.progress.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value='1')

            result = await tracker.is_cancelled()
            assert result is True

    @pytest.mark.asyncio
    async def test_is_cancelled_false(self, tracker):
        """测试任务未被取消"""
        with patch('backend.app.admin.service.crawl.progress.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)

            result = await tracker.is_cancelled()
            assert result is False

    @pytest.mark.asyncio
    async def test_is_cancelled_error(self, tracker):
        """测试取消检查失败时返回 False"""
        with patch('backend.app.admin.service.crawl.progress.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(side_effect=Exception('Redis error'))

            result = await tracker.is_cancelled()
            assert result is False

    @pytest.mark.asyncio
    async def test_clear_cancel_signal(self, tracker):
        """测试清除取消信号"""
        with patch('backend.app.admin.service.crawl.progress.redis_client') as mock_redis:
            mock_redis.delete = AsyncMock()

            await tracker.clear_cancel_signal()
            mock_redis.delete.assert_called_once_with('crawl:cancel:1')

    @pytest.mark.asyncio
    async def test_save_checkpoint(self, tracker):
        """测试保存断点"""
        with patch('backend.app.admin.service.crawl.progress.redis_client') as mock_redis:
            mock_redis.setex = AsyncMock()

            checkpoint_data = {
                'last_id': 100,
                'processed_count': 50,
                'offset': 200,
            }
            await tracker.save_checkpoint(checkpoint_data)

            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            assert call_args[0][0] == 'crawl:checkpoint:1'
            assert call_args[0][1] == 86400  # 24 hours TTL

            saved_data = json.loads(call_args[0][2])
            assert saved_data['last_id'] == 100
            assert saved_data['processed_count'] == 50

    @pytest.mark.asyncio
    async def test_load_checkpoint(self, tracker):
        """测试加载断点"""
        with patch('backend.app.admin.service.crawl.progress.redis_client') as mock_redis:
            checkpoint_data = json.dumps({'last_id': 100, 'offset': 200})
            mock_redis.get = AsyncMock(return_value=checkpoint_data)

            result = await tracker.load_checkpoint()
            assert result is not None
            assert result['last_id'] == 100
            assert result['offset'] == 200

    @pytest.mark.asyncio
    async def test_load_checkpoint_not_found(self, tracker):
        """测试断点不存在"""
        with patch('backend.app.admin.service.crawl.progress.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)

            result = await tracker.load_checkpoint()
            assert result is None

    @pytest.mark.asyncio
    async def test_clear_checkpoint(self, tracker):
        """测试清除断点"""
        with patch('backend.app.admin.service.crawl.progress.redis_client') as mock_redis:
            mock_redis.delete = AsyncMock()

            await tracker.clear_checkpoint()
            mock_redis.delete.assert_called_once_with('crawl:checkpoint:1')

    @pytest.mark.asyncio
    async def test_clear_progress(self, tracker):
        """测试清除进度"""
        with patch('backend.app.admin.service.crawl.progress.redis_client') as mock_redis:
            mock_redis.delete = AsyncMock()

            await tracker.clear_progress()
            mock_redis.delete.assert_called_once_with('crawl:progress:1:run-001')


# ── 取消信号管理测试 ──────────────────────────────────────────


class TestCancelSignal:
    """取消信号管理测试"""

    @pytest.mark.asyncio
    async def test_send_cancel_signal(self):
        """测试发送取消信号"""
        from backend.app.admin.service.crawl.progress import send_cancel_signal

        with patch('backend.app.admin.service.crawl.progress.redis_client') as mock_redis:
            mock_redis.setex = AsyncMock()

            result = await send_cancel_signal(task_id=1)

            assert result is True
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            assert call_args[0][0] == 'crawl:cancel:1'
            assert call_args[0][1] == 300  # 5 min TTL
            assert call_args[0][2] == '1'

    @pytest.mark.asyncio
    async def test_send_cancel_signal_error(self):
        """测试发送取消信号失败"""
        from backend.app.admin.service.crawl.progress import send_cancel_signal

        with patch('backend.app.admin.service.crawl.progress.redis_client') as mock_redis:
            mock_redis.setex = AsyncMock(side_effect=Exception('Redis error'))

            result = await send_cancel_signal(task_id=1)
            assert result is False

    @pytest.mark.asyncio
    async def test_revoke_celery_task(self):
        """测试撤销 Celery 任务"""
        from backend.app.admin.service.crawl.progress import revoke_celery_task

        with patch('backend.app.admin.service.crawl.progress.CrawlProgressTracker', autospec=True):
            with patch('backend.app.task.celery.celery_app') as mock_celery:
                mock_celery.control = MagicMock()
                mock_celery.control.revoke = MagicMock()

                result = await revoke_celery_task('task-123')

                assert result is True
                mock_celery.control.revoke.assert_called_once_with(
                    'task-123', terminate=True, signal='SIGTERM'
                )

    @pytest.mark.asyncio
    async def test_revoke_celery_task_error(self):
        """测试撤销 Celery 任务失败"""
        from backend.app.admin.service.crawl.progress import revoke_celery_task

        with patch('backend.app.admin.service.crawl.progress.CrawlProgressTracker', autospec=True):
            with patch('backend.app.task.celery.celery_app') as mock_celery:
                mock_celery.control = MagicMock()
                mock_celery.control.revoke = MagicMock(side_effect=Exception('Connection error'))

                result = await revoke_celery_task('task-123')
                assert result is False


# ── SocketIO 进度推送测试 ──────────────────────────────────────


class TestSocketIOProgress:
    """SocketIO 进度推送测试"""

    @pytest.mark.asyncio
    async def test_broadcast_crawl_progress(self):
        """测试广播采集进度"""
        from backend.app.admin.service.crawl.progress import broadcast_crawl_progress

        progress_data = {
            'task_id': 1,
            'run_id': 'run-001',
            'phase': 'reading',
            'percentage': 50.0,
        }

        with patch('backend.common.socketio.actions.sio') as mock_sio:
            mock_sio.emit = AsyncMock()

            await broadcast_crawl_progress(progress_data)

            mock_sio.emit.assert_called_once_with(
                'crawl_progress', progress_data, namespace='/ws'
            )

    @pytest.mark.asyncio
    async def test_broadcast_crawl_progress_error(self):
        """测试广播进度失败时的错误处理"""
        from backend.app.admin.service.crawl.progress import broadcast_crawl_progress

        progress_data = {'task_id': 1}

        with patch('backend.common.socketio.actions.sio') as mock_sio:
            mock_sio.emit = AsyncMock(side_effect=Exception('SocketIO error'))

            # 不应抛出异常
            await broadcast_crawl_progress(progress_data)