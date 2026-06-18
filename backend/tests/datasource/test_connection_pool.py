"""数据源连接池管理器测试"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.admin.service.datasource.connection_pool import (
    DEFAULT_MAX_OVERFLOW,
    DEFAULT_POOL_RECYCLE,
    DEFAULT_POOL_SIZE,
    DEFAULT_POOL_TIMEOUT,
    IDLE_TIMEOUT,
    MAX_CACHED_ENGINES,
    ConnectionPoolManager,
    PoolStats,
)


class TestPoolStats:
    """PoolStats 数据类测试"""

    def test_to_dict(self):
        """测试转换为字典"""
        stats = PoolStats(
            datasource_id=1,
            datasource_name='test_db',
            pool_size=5,
            checked_out=2,
            overflow=1,
            total_created=8,
            last_used=1000.0,
            last_health_check=1000.0,
            is_healthy=True,
        )
        result = stats.to_dict()
        assert result['datasource_id'] == 1
        assert result['datasource_name'] == 'test_db'
        assert result['pool_size'] == 5
        assert result['checked_out'] == 2
        assert result['is_healthy'] is True

    def test_default_values(self):
        """测试默认值"""
        stats = PoolStats(datasource_id=1, datasource_name='test')
        assert stats.pool_size == 0
        assert stats.checked_out == 0
        assert stats.overflow == 0
        assert stats.total_created == 0
        assert stats.is_healthy is True


class TestConnectionPoolManager:
    """ConnectionPoolManager 测试"""

    @pytest.fixture
    def mock_datasource(self):
        """创建模拟数据源对象"""
        ds = MagicMock()
        ds.id = 1
        ds.name = 'test_postgres'
        ds.db_type = 'postgresql'
        ds.host = 'localhost'
        ds.port = 5432
        ds.username = 'testuser'
        ds.password = 'testpass'
        ds.database = 'testdb'
        ds.extra_params = None
        return ds

    @pytest.fixture
    def mock_datasource2(self):
        """创建第二个模拟数据源对象"""
        ds = MagicMock()
        ds.id = 2
        ds.name = 'test_mysql'
        ds.db_type = 'mysql'
        ds.host = 'localhost'
        ds.port = 3306
        ds.username = 'root'
        ds.password = 'rootpass'
        ds.database = 'testdb'
        ds.extra_params = None
        return ds

    @pytest.fixture
    def manager(self):
        """创建连接池管理器（重置单例）"""
        ConnectionPoolManager._instance = None
        manager = ConnectionPoolManager()
        yield manager
        # 清理
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(manager.dispose_all())
            else:
                loop.run_until_complete(manager.dispose_all())
        except Exception:
            pass
        ConnectionPoolManager._instance = None

    def test_singleton_pattern(self, manager):
        """测试单例模式"""
        manager2 = ConnectionPoolManager()
        assert manager is manager2

    @pytest.mark.asyncio
    async def test_get_engine_creates_new(self, manager, mock_datasource):
        """测试获取引擎时创建新连接"""
        with patch('backend.app.admin.service.datasource.connection_pool.create_async_engine') as mock_create:
            mock_engine = MagicMock()
            mock_engine.dispose = AsyncMock()
            mock_create.return_value = mock_engine

            with patch('backend.app.admin.service.datasource.connection_pool._decrypt_password', return_value='decrypted'):
                with patch('backend.app.admin.service.query.engine.build_db_url', return_value='postgresql+asyncpg://testuser:decrypted@localhost:5432/testdb'):
                    engine = await manager.get_engine(mock_datasource)

            assert engine is mock_engine
            assert 1 in manager._engines
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_engine_cached(self, manager, mock_datasource):
        """测试获取引擎时使用缓存"""
        with patch('backend.app.admin.service.datasource.connection_pool.create_async_engine') as mock_create:
            mock_engine = MagicMock()
            mock_engine.dispose = AsyncMock()
            mock_create.return_value = mock_engine

            with patch('backend.app.admin.service.datasource.connection_pool._decrypt_password', return_value='decrypted'):
                with patch('backend.app.admin.service.query.engine.build_db_url', return_value='postgresql+asyncpg://testuser:decrypted@localhost:5432/testdb'):
                    engine1 = await manager.get_engine(mock_datasource)
                    engine2 = await manager.get_engine(mock_datasource)

            assert engine1 is engine2
            assert mock_create.call_count == 1  # 只创建一次

    @pytest.mark.asyncio
    async def test_get_engine_multiple_datasources(self, manager, mock_datasource, mock_datasource2):
        """测试多个数据源的引擎缓存"""
        with patch('backend.app.admin.service.datasource.connection_pool.create_async_engine') as mock_create:
            mock_engine1 = MagicMock()
            mock_engine1.dispose = AsyncMock()
            mock_engine2 = MagicMock()
            mock_engine2.dispose = AsyncMock()
            mock_create.side_effect = [mock_engine1, mock_engine2]

            with patch('backend.app.admin.service.datasource.connection_pool._decrypt_password', return_value='decrypted'):
                with patch('backend.app.admin.service.query.engine.build_db_url') as mock_url:
                    mock_url.side_effect = [
                        'postgresql+asyncpg://testuser:decrypted@localhost:5432/testdb',
                        'mysql+asyncmy://root:decrypted@localhost:3306/testdb',
                    ]
                    engine1 = await manager.get_engine(mock_datasource)
                    engine2 = await manager.get_engine(mock_datasource2)

            assert engine1 is mock_engine1
            assert engine2 is mock_engine2
            assert len(manager._engines) == 2

    @pytest.mark.asyncio
    async def test_dispose_engine(self, manager, mock_datasource):
        """测试释放引擎"""
        with patch('backend.app.admin.service.datasource.connection_pool.create_async_engine') as mock_create:
            mock_engine = MagicMock()
            mock_engine.dispose = AsyncMock()
            mock_create.return_value = mock_engine

            with patch('backend.app.admin.service.datasource.connection_pool._decrypt_password', return_value='decrypted'):
                with patch('backend.app.admin.service.query.engine.build_db_url', return_value='postgresql+asyncpg://testuser:decrypted@localhost:5432/testdb'):
                    await manager.get_engine(mock_datasource)

            assert 1 in manager._engines
            await manager._dispose_engine(1)
            assert 1 not in manager._engines
            mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_engine(self, manager, mock_datasource):
        """测试手动移除引擎"""
        with patch('backend.app.admin.service.datasource.connection_pool.create_async_engine') as mock_create:
            mock_engine = MagicMock()
            mock_engine.dispose = AsyncMock()
            mock_create.return_value = mock_engine

            with patch('backend.app.admin.service.datasource.connection_pool._decrypt_password', return_value='decrypted'):
                with patch('backend.app.admin.service.query.engine.build_db_url', return_value='postgresql+asyncpg://testuser:decrypted@localhost:5432/testdb'):
                    await manager.get_engine(mock_datasource)

            await manager.remove_engine(1)
            assert 1 not in manager._engines

    @pytest.mark.asyncio
    async def test_evict_oldest(self, manager):
        """测试移除最久未使用的引擎"""
        # 模拟多个引擎 - id=0 有最旧的 last_used（最小时间戳）
        for i in range(3):
            mock_engine = MagicMock()
            mock_engine.dispose = AsyncMock()
            manager._engines[i] = mock_engine
            # id=0 是最久未使用的（最小的 last_used 时间戳）
            manager._stats[i] = PoolStats(
                datasource_id=i,
                datasource_name=f'db_{i}',
                last_used=time.time() - (2 - i) * 100,  # id=0 最旧 (time-200), id=2 最新 (time)
            )

        await manager._evict_oldest()

        # 最久未使用的是 id=0（last_used 最小）
        assert 0 not in manager._engines
        assert 1 in manager._engines
        assert 2 in manager._engines

    @pytest.mark.asyncio
    async def test_max_cached_engines_limit(self, manager):
        """测试最大缓存引擎数限制"""
        # 填满缓存
        for i in range(MAX_CACHED_ENGINES):
            mock_engine = MagicMock()
            mock_engine.dispose = AsyncMock()
            manager._engines[i] = mock_engine
            manager._stats[i] = PoolStats(
                datasource_id=i,
                datasource_name=f'db_{i}',
                last_used=time.time(),
                is_healthy=True,
            )

        assert len(manager._engines) == MAX_CACHED_ENGINES

        # 添加新引擎应触发淘汰
        new_ds = MagicMock()
        new_ds.id = MAX_CACHED_ENGINES
        new_ds.name = 'new_db'
        new_ds.db_type = 'postgresql'
        new_ds.host = 'localhost'
        new_ds.port = 5432
        new_ds.username = 'user'
        new_ds.password = 'pass'
        new_ds.database = 'newdb'
        new_ds.extra_params = None

        with patch('backend.app.admin.service.datasource.connection_pool.create_async_engine') as mock_create:
            mock_engine = MagicMock()
            mock_engine.dispose = AsyncMock()
            mock_create.return_value = mock_engine

            with patch('backend.app.admin.service.datasource.connection_pool._decrypt_password', return_value='decrypted'):
                with patch('backend.app.admin.service.query.engine.build_db_url', return_value='postgresql+asyncpg://user:decrypted@localhost:5432/newdb'):
                    await manager.get_engine(new_ds)

        # 缓存数量不应超过限制
        assert len(manager._engines) <= MAX_CACHED_ENGINES

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, manager, mock_datasource):
        """测试健康检查 - 连接正常"""
        mock_engine = MagicMock()
        mock_session = AsyncMock()
        mock_engine.dispose = AsyncMock()

        # 模拟 AsyncSession 上下文管理器
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock()

        with patch('backend.app.admin.service.datasource.connection_pool.AsyncSession', return_value=mock_session):
            manager._engines[1] = mock_engine
            manager._stats[1] = PoolStats(
                datasource_id=1,
                datasource_name='test_postgres',
                last_used=time.time(),
                last_health_check=time.time(),
            )

            result = await manager.health_check(1)
            assert result is True
            assert manager._stats[1].is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, manager):
        """测试健康检查 - 连接异常"""
        mock_engine = MagicMock()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(side_effect=Exception('Connection failed'))
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch('backend.app.admin.service.datasource.connection_pool.AsyncSession', return_value=mock_session):
            manager._engines[1] = mock_engine
            manager._stats[1] = PoolStats(
                datasource_id=1,
                datasource_name='test_postgres',
                last_used=time.time(),
                last_health_check=time.time(),
            )

            result = await manager.health_check(1)
            assert result is False
            assert manager._stats[1].is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_not_found(self, manager):
        """测试健康检查 - 引擎不存在"""
        result = await manager.health_check(999)
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_all(self, manager):
        """测试批量健康检查"""
        for i in range(3):
            mock_engine = MagicMock()
            manager._engines[i] = mock_engine
            manager._stats[i] = PoolStats(
                datasource_id=i,
                datasource_name=f'db_{i}',
                last_used=time.time(),
                last_health_check=time.time(),
            )

        with patch.object(manager, 'health_check', new_callable=AsyncMock) as mock_check:
            mock_check.side_effect = [True, False, True]
            results = await manager.health_check_all()

            assert results == {0: True, 1: False, 2: True}

    @pytest.mark.asyncio
    async def test_cleanup_idle(self, manager):
        """测试清理空闲连接"""
        now = time.time()

        # 创建一个空闲超时的引擎和一个活跃的引擎
        mock_engine1 = MagicMock()
        mock_engine1.dispose = AsyncMock()
        mock_engine2 = MagicMock()
        mock_engine2.dispose = AsyncMock()

        manager._engines[1] = mock_engine1
        manager._stats[1] = PoolStats(
            datasource_id=1,
            datasource_name='idle_db',
            last_used=now - IDLE_TIMEOUT - 100,  # 超时
        )

        manager._engines[2] = mock_engine2
        manager._stats[2] = PoolStats(
            datasource_id=2,
            datasource_name='active_db',
            last_used=now,  # 活跃
        )

        count = await manager.cleanup_idle()
        assert count == 1
        assert 1 not in manager._engines
        assert 2 in manager._engines

    @pytest.mark.asyncio
    async def test_cleanup_idle_custom_timeout(self, manager):
        """测试自定义空闲超时"""
        now = time.time()

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()

        manager._engines[1] = mock_engine
        manager._stats[1] = PoolStats(
            datasource_id=1,
            datasource_name='test_db',
            last_used=now - 200,  # 200 秒前使用
        )

        # 使用 100 秒超时，应该被清理
        count = await manager.cleanup_idle(idle_timeout=100)
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_stats(self, manager):
        """测试获取统计信息"""
        manager._stats[1] = PoolStats(
            datasource_id=1,
            datasource_name='test_db',
            pool_size=5,
            checked_out=2,
        )

        # 单个数据源
        stats = manager.get_stats(ds_id=1)
        assert stats['datasource_id'] == 1
        assert stats['pool_size'] == 5
        assert stats['checked_out'] == 2

        # 所有数据源
        all_stats = manager.get_stats()
        assert len(all_stats) == 1

    @pytest.mark.asyncio
    async def test_get_stats_not_found(self, manager):
        """测试获取不存在的数据源统计"""
        stats = manager.get_stats(ds_id=999)
        assert stats == {}

    @pytest.mark.asyncio
    async def test_get_pool_info(self, manager):
        """测试获取连接池详细信息"""
        mock_engine = MagicMock()
        mock_pool = MagicMock()
        mock_pool.size.return_value = 5
        mock_pool.checkedin.return_value = 3
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        mock_pool.is_valid = True
        mock_engine.pool = mock_pool

        manager._engines[1] = mock_engine

        info = manager.get_pool_info(1)
        assert info is not None
        assert info['datasource_id'] == 1
        assert info['pool_size'] == 5
        assert info['checked_out'] == 2

    @pytest.mark.asyncio
    async def test_get_pool_info_not_found(self, manager):
        """测试获取不存在的连接池信息"""
        info = manager.get_pool_info(999)
        assert info is None

    @pytest.mark.asyncio
    async def test_dispose_all(self, manager):
        """测试释放所有连接池"""
        for i in range(3):
            mock_engine = MagicMock()
            mock_engine.dispose = AsyncMock()
            manager._engines[i] = mock_engine

        await manager.dispose_all()
        assert len(manager._engines) == 0

    @pytest.mark.asyncio
    async def test_create_engine_with_extra_params(self, manager):
        """测试创建带额外参数的引擎"""
        ds = MagicMock()
        ds.id = 1
        ds.name = 'test_db'
        ds.db_type = 'postgresql'
        ds.host = 'localhost'
        ds.port = 5432
        ds.username = 'user'
        ds.password = 'pass'
        ds.database = 'testdb'
        ds.extra_params = '{"connect_args": {"sslmode": "require"}}'

        with patch('backend.app.admin.service.datasource.connection_pool.create_async_engine') as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine

            with patch('backend.app.admin.service.datasource.connection_pool._decrypt_password', return_value='decrypted'):
                with patch('backend.app.admin.service.query.engine.build_db_url', return_value='postgresql+asyncpg://user:decrypted@localhost:5432/testdb'):
                    await manager.get_engine(ds)

            # 验证 create_async_engine 被调用时包含 connect_args
            call_kwargs = mock_create.call_args[1]
            assert 'connect_args' in call_kwargs
            assert call_kwargs['connect_args'] == {'sslmode': 'require'}

    @pytest.mark.asyncio
    async def test_start_background_tasks(self, manager):
        """测试启动后台任务"""
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task

            manager.start_background_tasks()

            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_background_tasks_already_running(self, manager):
        """测试后台任务已在运行"""
        mock_task = MagicMock()
        mock_task.done.return_value = False
        manager._health_check_task = mock_task

        with patch('asyncio.create_task') as mock_create_task:
            manager.start_background_tasks()
            mock_create_task.assert_not_called()