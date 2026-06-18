"""动态调度（RedBeat）测试

测试基于 Redis 的动态调度功能：
- RedBeatScheduleEntry 创建和序列化
- RedBeatScheduler 调度管理
- 动态调度 API（添加/删除/更新/列表）
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.task.enums import PeriodType, TaskSchedulerType
from backend.app.task.utils.redbeat_scheduler import (
    REDBEAT_KEY_PREFIX,
    RedBeatScheduleEntry,
    add_dynamic_schedule,
    get_dynamic_schedule,
    list_dynamic_schedules,
    remove_dynamic_schedule,
    toggle_dynamic_schedule,
    update_dynamic_schedule,
)


class TestRedBeatScheduleEntry:
    """RedBeatScheduleEntry 测试"""

    def test_from_model_interval(self):
        """测试从模型创建间隔调度条目"""
        model = MagicMock()
        model.name = 'test_interval_task'
        model.task = 'backend.app.task.tasks.demo.task_demo'
        model.type = TaskSchedulerType.INTERVAL
        model.interval_every = 30
        model.interval_period = PeriodType.SECONDS
        model.crontab = None
        model.args = None
        model.kwargs = None
        model.queue = None
        model.exchange = None
        model.routing_key = None
        model.expire_seconds = None
        model.expire_time = None
        model.start_time = None
        model.last_run_time = None
        model.total_run_count = 0
        model.enabled = True

        entry = RedBeatScheduleEntry.from_model(model)

        assert entry.name == 'test_interval_task'
        assert entry.task == 'backend.app.task.tasks.demo.task_demo'

    def test_from_model_crontab(self):
        """测试从模型创建定时调度条目"""
        model = MagicMock()
        model.name = 'test_crontab_task'
        model.task = 'backend.app.task.tasks.demo.task_demo'
        model.type = TaskSchedulerType.CRONTAB
        model.interval_every = None
        model.interval_period = None
        model.crontab = '* * * * *'
        model.args = None
        model.kwargs = None
        model.queue = None
        model.exchange = None
        model.routing_key = None
        model.expire_seconds = None
        model.expire_time = None
        model.start_time = None
        model.last_run_time = None
        model.total_run_count = 0
        model.enabled = True

        entry = RedBeatScheduleEntry.from_model(model)

        assert entry.name == 'test_crontab_task'

    def test_from_model_with_args(self):
        """测试从模型创建带参数的调度条目"""
        model = MagicMock()
        model.name = 'test_task_with_args'
        model.task = 'backend.app.task.tasks.demo.task_demo'
        model.type = TaskSchedulerType.INTERVAL
        model.interval_every = 60
        model.interval_period = PeriodType.SECONDS
        model.crontab = None
        model.args = json.dumps(['arg1', 'arg2'])
        model.kwargs = json.dumps({'key': 'value'})
        model.queue = 'default'
        model.exchange = None
        model.routing_key = None
        model.expire_seconds = 300
        model.expire_time = None
        model.start_time = None
        model.last_run_time = None
        model.total_run_count = 0
        model.enabled = True

        entry = RedBeatScheduleEntry.from_model(model)

        assert entry.args == ['arg1', 'arg2']
        assert entry.kwargs == {'key': 'value'}
        assert entry.options.get('queue') == 'default'
        assert entry.options.get('expires') == 300

    def test_from_redis_interval(self):
        """测试从 Redis 数据创建间隔调度条目"""
        data = {
            'name': 'test_interval',
            'task': 'backend.app.task.tasks.demo.task_demo',
            'type': TaskSchedulerType.INTERVAL,
            'interval_every': 60,
            'interval_period': PeriodType.SECONDS,
            'args': None,
            'kwargs': None,
            'options': {},
            'total_run_count': 0,
            'last_run_at': '2024-01-01 00:00:00',
        }

        entry = RedBeatScheduleEntry.from_redis('test_interval', data)

        assert entry.name == 'test_interval'
        assert entry.task == 'backend.app.task.tasks.demo.task_demo'

    def test_from_redis_crontab(self):
        """测试从 Redis 数据创建定时调度条目"""
        data = {
            'name': 'test_crontab',
            'task': 'backend.app.task.tasks.demo.task_demo',
            'type': TaskSchedulerType.CRONTAB,
            'crontab': '0 * * * *',
            'args': None,
            'kwargs': None,
            'options': {},
            'total_run_count': 0,
            'last_run_at': '2024-01-01 00:00:00',
        }

        entry = RedBeatScheduleEntry.from_redis('test_crontab', data)

        assert entry.name == 'test_crontab'

    def test_to_redis_interval(self):
        """测试序列化间隔调度到 Redis 格式"""
        from celery import schedules as celery_schedules

        entry = RedBeatScheduleEntry(
            name='test_interval',
            task='backend.app.task.tasks.demo.task_demo',
            schedule=celery_schedules.schedule(timedelta(seconds=60)),
            args=['arg1'],
            kwargs={'key': 'value'},
        )

        data = entry.to_redis()

        assert data['name'] == 'test_interval'
        assert data['task'] == 'backend.app.task.tasks.demo.task_demo'
        assert data['type'] == TaskSchedulerType.INTERVAL
        assert data['interval_every'] == 60.0
        assert data['args'] == ['arg1']
        assert data['kwargs'] == {'key': 'value'}

    def test_is_due(self):
        """测试检查任务是否到期"""
        from celery import schedules as celery_schedules

        entry = RedBeatScheduleEntry(
            name='test_task',
            task='backend.app.task.tasks.demo.task_demo',
            schedule=celery_schedules.schedule(timedelta(seconds=60)),
        )

        # 新创建的任务应该立即到期
        result = entry.is_due()
        assert result is not None

    def test_next(self):
        """测试获取下一次调度"""
        from celery import schedules as celery_schedules

        entry = RedBeatScheduleEntry(
            name='test_task',
            task='backend.app.task.tasks.demo.task_demo',
            schedule=celery_schedules.schedule(timedelta(seconds=60)),
        )

        next_entry = next(entry)
        assert next_entry.name == 'test_task'
        assert next_entry.total_run_count == 1


class TestDynamicScheduleAPI:
    """动态调度 API 测试"""

    @pytest.mark.asyncio
    async def test_add_dynamic_schedule(self):
        """测试添加动态调度"""
        with patch('backend.app.task.utils.redbeat_scheduler.redis_client') as mock_redis:
            mock_redis.setex = AsyncMock(return_value=True)
            mock_redis.set = AsyncMock(return_value=True)

            result = await add_dynamic_schedule(
                name='test_task',
                task='backend.app.task.tasks.demo.task_demo',
                schedule_type=TaskSchedulerType.INTERVAL,
                interval_every=60,
                interval_period=PeriodType.SECONDS,
            )

            assert result is True
            mock_redis.setex.assert_called_once()
            mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_dynamic_schedule_crontab(self):
        """测试添加定时调度"""
        with patch('backend.app.task.utils.redbeat_scheduler.redis_client') as mock_redis:
            mock_redis.setex = AsyncMock(return_value=True)
            mock_redis.set = AsyncMock(return_value=True)

            result = await add_dynamic_schedule(
                name='test_crontab_task',
                task='backend.app.task.tasks.demo.task_demo',
                schedule_type=TaskSchedulerType.CRONTAB,
                crontab='0 * * * *',
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_add_dynamic_schedule_error(self):
        """测试添加动态调度失败"""
        with patch('backend.app.task.utils.redbeat_scheduler.redis_client') as mock_redis:
            mock_redis.setex = AsyncMock(side_effect=Exception('Redis error'))

            result = await add_dynamic_schedule(
                name='test_task',
                task='backend.app.task.tasks.demo.task_demo',
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_remove_dynamic_schedule(self):
        """测试移除动态调度"""
        with patch('backend.app.task.utils.redbeat_scheduler.redis_client') as mock_redis:
            mock_redis.delete = AsyncMock(return_value=1)
            mock_redis.set = AsyncMock(return_value=True)

            result = await remove_dynamic_schedule('test_task')

            assert result is True
            mock_redis.delete.assert_called_once_with(f'{REDBEAT_KEY_PREFIX}test_task')

    @pytest.mark.asyncio
    async def test_remove_dynamic_schedule_error(self):
        """测试移除动态调度失败"""
        with patch('backend.app.task.utils.redbeat_scheduler.redis_client') as mock_redis:
            mock_redis.delete = AsyncMock(side_effect=Exception('Redis error'))

            result = await remove_dynamic_schedule('test_task')
            assert result is False

    @pytest.mark.asyncio
    async def test_update_dynamic_schedule(self):
        """测试更新动态调度"""
        with patch('backend.app.task.utils.redbeat_scheduler.redis_client') as mock_redis:
            existing_data = json.dumps({
                'name': 'test_task',
                'task': 'backend.app.task.tasks.demo.task_demo',
                'type': TaskSchedulerType.INTERVAL,
                'interval_every': 60,
                'interval_period': PeriodType.SECONDS,
                'enabled': True,
            })
            mock_redis.get = AsyncMock(return_value=existing_data)
            mock_redis.ttl = AsyncMock(return_value=86400)
            mock_redis.setex = AsyncMock(return_value=True)
            mock_redis.set = AsyncMock(return_value=True)

            result = await update_dynamic_schedule('test_task', interval_every=120)

            assert result is True
            mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_dynamic_schedule_not_found(self):
        """测试更新不存在的调度"""
        with patch('backend.app.task.utils.redbeat_scheduler.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)

            result = await update_dynamic_schedule('nonexistent_task', interval_every=120)
            assert result is False

    @pytest.mark.asyncio
    async def test_get_dynamic_schedule(self):
        """测试获取动态调度"""
        with patch('backend.app.task.utils.redbeat_scheduler.redis_client') as mock_redis:
            data = json.dumps({
                'name': 'test_task',
                'task': 'backend.app.task.tasks.demo.task_demo',
                'type': TaskSchedulerType.INTERVAL,
                'interval_every': 60,
            })
            mock_redis.get = AsyncMock(return_value=data)

            result = await get_dynamic_schedule('test_task')

            assert result is not None
            assert result['name'] == 'test_task'
            assert result['type'] == TaskSchedulerType.INTERVAL

    @pytest.mark.asyncio
    async def test_get_dynamic_schedule_not_found(self):
        """测试获取不存在的调度"""
        with patch('backend.app.task.utils.redbeat_scheduler.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)

            result = await get_dynamic_schedule('nonexistent_task')
            assert result is None

    @pytest.mark.asyncio
    async def test_list_dynamic_schedules(self):
        """测试列出所有动态调度"""
        with patch('backend.app.task.utils.redbeat_scheduler.redis_client') as mock_redis:
            mock_redis.get_prefix = AsyncMock(return_value=[
                f'{REDBEAT_KEY_PREFIX}task1',
                f'{REDBEAT_KEY_PREFIX}task2',
            ])
            mock_redis.get = AsyncMock(side_effect=[
                json.dumps({'name': 'task1', 'task': 'task1_func'}),
                json.dumps({'name': 'task2', 'task': 'task2_func'}),
            ])

            result = await list_dynamic_schedules()

            assert len(result) == 2
            assert result[0]['name'] == 'task1'
            assert result[1]['name'] == 'task2'

    @pytest.mark.asyncio
    async def test_list_dynamic_schedules_with_prefix(self):
        """测试按前缀列出动态调度"""
        with patch('backend.app.task.utils.redbeat_scheduler.redis_client') as mock_redis:
            mock_redis.get_prefix = AsyncMock(return_value=[
                f'{REDBEAT_KEY_PREFIX}etl_task1',
            ])
            mock_redis.get = AsyncMock(return_value=json.dumps({'name': 'etl_task1'}))

            result = await list_dynamic_schedules(prefix='etl_')

            assert len(result) == 1
            mock_redis.get_prefix.assert_called_once()

    @pytest.mark.asyncio
    async def test_toggle_dynamic_schedule_enable(self):
        """测试启用动态调度"""
        with patch('backend.app.task.utils.redbeat_scheduler.redis_client') as mock_redis:
            existing_data = json.dumps({
                'name': 'test_task',
                'task': 'backend.app.task.tasks.demo.task_demo',
                'enabled': False,
            })
            mock_redis.get = AsyncMock(return_value=existing_data)
            mock_redis.ttl = AsyncMock(return_value=86400)
            mock_redis.setex = AsyncMock(return_value=True)
            mock_redis.set = AsyncMock(return_value=True)

            result = await toggle_dynamic_schedule('test_task', enabled=True)
            assert result is True

    @pytest.mark.asyncio
    async def test_toggle_dynamic_schedule_disable(self):
        """测试禁用动态调度"""
        with patch('backend.app.task.utils.redbeat_scheduler.redis_client') as mock_redis:
            existing_data = json.dumps({
                'name': 'test_task',
                'task': 'backend.app.task.tasks.demo.task_demo',
                'enabled': True,
            })
            mock_redis.get = AsyncMock(return_value=existing_data)
            mock_redis.ttl = AsyncMock(return_value=86400)
            mock_redis.setex = AsyncMock(return_value=True)
            mock_redis.set = AsyncMock(return_value=True)

            result = await toggle_dynamic_schedule('test_task', enabled=False)
            assert result is True


class TestDynamicScheduleService:
    """DynamicScheduleService 测试"""

    @pytest.mark.asyncio
    async def test_create_schedule(self):
        """测试创建动态调度"""
        from backend.app.task.service.dynamic_schedule_service import DynamicScheduleService

        with patch('backend.app.task.service.dynamic_schedule_service.get_dynamic_schedule') as mock_get:
            mock_get.side_effect = [None, {'name': 'test_task', 'task': 'demo'}]

            with patch('backend.app.task.service.dynamic_schedule_service.add_dynamic_schedule') as mock_add:
                mock_add.return_value = True

                result = await DynamicScheduleService.create(
                    name='test_task',
                    task='backend.app.task.tasks.demo.task_demo',
                    schedule_type=TaskSchedulerType.INTERVAL,
                    interval_every=60,
                    interval_period=PeriodType.SECONDS,
                )

                assert result is not None
                mock_add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_schedule_conflict(self):
        """测试创建已存在的调度"""
        from backend.app.task.service.dynamic_schedule_service import DynamicScheduleService
        from backend.common.exception import errors

        with patch('backend.app.task.service.dynamic_schedule_service.get_dynamic_schedule') as mock_get:
            mock_get.return_value = {'name': 'test_task'}

            with pytest.raises(errors.ConflictError):
                await DynamicScheduleService.create(
                    name='test_task',
                    task='backend.app.task.tasks.demo.task_demo',
                    schedule_type=TaskSchedulerType.INTERVAL,
                    interval_every=60,
                    interval_period=PeriodType.SECONDS,
                )

    @pytest.mark.asyncio
    async def test_create_schedule_missing_interval(self):
        """测试创建间隔调度缺少参数"""
        from backend.app.task.service.dynamic_schedule_service import DynamicScheduleService
        from backend.common.exception import errors

        with patch('backend.app.task.service.dynamic_schedule_service.get_dynamic_schedule') as mock_get:
            mock_get.return_value = None

            with pytest.raises(errors.RequestError, match='间隔调度必须指定'):
                await DynamicScheduleService.create(
                    name='test_task',
                    task='backend.app.task.tasks.demo.task_demo',
                    schedule_type=TaskSchedulerType.INTERVAL,
                )

    @pytest.mark.asyncio
    async def test_create_schedule_missing_crontab(self):
        """测试创建定时调度缺少 crontab"""
        from backend.app.task.service.dynamic_schedule_service import DynamicScheduleService
        from backend.common.exception import errors

        with patch('backend.app.task.service.dynamic_schedule_service.get_dynamic_schedule') as mock_get:
            mock_get.return_value = None

            with pytest.raises(errors.RequestError, match='定时调度必须指定 crontab'):
                await DynamicScheduleService.create(
                    name='test_task',
                    task='backend.app.task.tasks.demo.task_demo',
                    schedule_type=TaskSchedulerType.CRONTAB,
                )

    @pytest.mark.asyncio
    async def test_update_schedule(self):
        """测试更新动态调度"""
        from backend.app.task.service.dynamic_schedule_service import DynamicScheduleService

        with patch('backend.app.task.service.dynamic_schedule_service.get_dynamic_schedule') as mock_get:
            mock_get.side_effect = [
                {'name': 'test_task', 'task': 'demo', 'interval_every': 60},
                {'name': 'test_task', 'task': 'demo', 'interval_every': 120},
            ]

            with patch('backend.app.task.service.dynamic_schedule_service.update_dynamic_schedule') as mock_update:
                mock_update.return_value = True

                result = await DynamicScheduleService.update(name='test_task', interval_every=120)
                assert result is not None

    @pytest.mark.asyncio
    async def test_update_schedule_not_found(self):
        """测试更新不存在的调度"""
        from backend.app.task.service.dynamic_schedule_service import DynamicScheduleService
        from backend.common.exception import errors

        with patch('backend.app.task.service.dynamic_schedule_service.get_dynamic_schedule') as mock_get:
            mock_get.return_value = None

            with pytest.raises(errors.NotFoundError):
                await DynamicScheduleService.update(name='nonexistent', interval_every=120)

    @pytest.mark.asyncio
    async def test_delete_schedule(self):
        """测试删除动态调度"""
        from backend.app.task.service.dynamic_schedule_service import DynamicScheduleService

        with patch('backend.app.task.service.dynamic_schedule_service.get_dynamic_schedule') as mock_get:
            mock_get.return_value = {'name': 'test_task'}

            with patch('backend.app.task.service.dynamic_schedule_service.remove_dynamic_schedule') as mock_remove:
                mock_remove.return_value = True

                await DynamicScheduleService.delete(name='test_task')
                mock_remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_schedule_not_found(self):
        """测试删除不存在的调度"""
        from backend.app.task.service.dynamic_schedule_service import DynamicScheduleService
        from backend.common.exception import errors

        with patch('backend.app.task.service.dynamic_schedule_service.get_dynamic_schedule') as mock_get:
            mock_get.return_value = None

            with pytest.raises(errors.NotFoundError):
                await DynamicScheduleService.delete(name='nonexistent')

    @pytest.mark.asyncio
    async def test_get_schedule(self):
        """测试获取动态调度详情"""
        from backend.app.task.service.dynamic_schedule_service import DynamicScheduleService

        with patch('backend.app.task.service.dynamic_schedule_service.get_dynamic_schedule') as mock_get:
            mock_get.return_value = {'name': 'test_task', 'task': 'demo'}

            result = await DynamicScheduleService.get(name='test_task')
            assert result['name'] == 'test_task'

    @pytest.mark.asyncio
    async def test_get_schedule_not_found(self):
        """测试获取不存在的调度"""
        from backend.app.task.service.dynamic_schedule_service import DynamicScheduleService
        from backend.common.exception import errors

        with patch('backend.app.task.service.dynamic_schedule_service.get_dynamic_schedule') as mock_get:
            mock_get.return_value = None

            with pytest.raises(errors.NotFoundError):
                await DynamicScheduleService.get(name='nonexistent')

    @pytest.mark.asyncio
    async def test_get_list(self):
        """测试获取动态调度列表"""
        from backend.app.task.service.dynamic_schedule_service import DynamicScheduleService

        with patch('backend.app.task.service.dynamic_schedule_service.list_dynamic_schedules') as mock_list:
            mock_list.return_value = [
                {'name': 'task1', 'task': 'demo1'},
                {'name': 'task2', 'task': 'demo2'},
            ]

            result = await DynamicScheduleService.get_list()
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_toggle_enable(self):
        """测试启用调度"""
        from backend.app.task.service.dynamic_schedule_service import DynamicScheduleService

        with patch('backend.app.task.service.dynamic_schedule_service.get_dynamic_schedule') as mock_get:
            mock_get.side_effect = [
                {'name': 'test_task', 'enabled': False},
                {'name': 'test_task', 'enabled': True},
            ]

            with patch('backend.app.task.service.dynamic_schedule_service.toggle_dynamic_schedule') as mock_toggle:
                mock_toggle.return_value = True

                result = await DynamicScheduleService.toggle(name='test_task', enabled=True)
                assert result is not None

    @pytest.mark.asyncio
    async def test_toggle_not_found(self):
        """测试切换不存在的调度"""
        from backend.app.task.service.dynamic_schedule_service import DynamicScheduleService
        from backend.common.exception import errors

        with patch('backend.app.task.service.dynamic_schedule_service.get_dynamic_schedule') as mock_get:
            mock_get.return_value = None

            with pytest.raises(errors.NotFoundError):
                await DynamicScheduleService.toggle(name='nonexistent', enabled=True)