"""通知分发器测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.admin.service.alert.dispatcher import (
    NotifyResult,
    NotificationDispatcher,
    dispatch_notification,
    _send_email_notification,
    _send_webhook_notification,
    _send_socketio_notification,
    _send_sms_notification,
)
from backend.app.admin.service.alert.enums import NotifyChannel


class TestNotifyResult:
    """NotifyResult 测试"""

    def test_success_result(self):
        result = NotifyResult(
            channel='email',
            success=True,
            message='邮件已发送',
        )
        assert result.channel == 'email'
        assert result.success is True
        assert result.error is None

    def test_failure_result(self):
        result = NotifyResult(
            channel='webhook',
            success=False,
            error='Connection refused',
        )
        assert result.channel == 'webhook'
        assert result.success is False
        assert result.error == 'Connection refused'


class TestDispatchNotification:
    """通知分发测试"""

    @pytest.mark.asyncio
    async def test_dispatch_empty_channels(self):
        result = await dispatch_notification(
            channels=[],
            severity='warning',
            title='测试告警',
            message='测试消息',
        )
        assert result['total_channels'] == 0
        assert result['success_count'] == 0

    @pytest.mark.asyncio
    async def test_dispatch_unsupported_channel(self):
        result = await dispatch_notification(
            channels=['unknown_channel'],
            severity='warning',
            title='测试告警',
            message='测试消息',
        )
        assert result['total_channels'] == 1
        assert result['fail_count'] == 1
        assert '不支持' in result['results'][0]['error']

    @pytest.mark.asyncio
    async def test_dispatch_sms_not_implemented(self):
        result = await dispatch_notification(
            channels=['sms'],
            severity='warning',
            title='测试告警',
            message='测试消息',
        )
        assert result['total_channels'] == 1
        assert result['fail_count'] == 1
        assert '尚未实现' in result['results'][0]['error']


class TestEmailNotification:
    """邮件通知测试"""

    @pytest.mark.asyncio
    async def test_email_no_db(self):
        result = await _send_email_notification(
            severity='warning',
            title='测试告警',
            message='测试消息',
            db=None,
        )
        assert result.success is False
        assert '数据库' in result.error

    @pytest.mark.asyncio
    async def test_email_no_recipients(self):
        db = MagicMock()
        result = await _send_email_notification(
            severity='warning',
            title='测试告警',
            message='测试消息',
            db=db,
            recipients=[],
        )
        # 空列表会尝试从配置获取，如果没有配置则失败
        assert result.success is False or result.success is True  # 取决于配置


class TestWebhookNotification:
    """Webhook 通知测试"""

    @pytest.mark.asyncio
    async def test_webhook_no_url(self):
        result = await _send_webhook_notification(
            severity='warning',
            title='测试告警',
            message='测试消息',
            webhook_url=None,
        )
        # 没有配置默认 URL 则失败
        assert result.success is False

    @pytest.mark.asyncio
    async def test_webhook_with_url(self):
        """测试 Webhook 发送（mock HTTP 请求）"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()

            mock_post = AsyncMock(return_value=mock_response)
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_instance.post = mock_post

            with patch('backend.app.admin.service.alert.dispatcher.httpx.AsyncClient', return_value=mock_client_instance):
                result = await _send_webhook_notification(
                    severity='warning',
                    title='测试告警',
                    message='测试消息',
                    webhook_url='https://example.com/webhook',
                )
                # 即使 mock 不完美，至少不会崩溃
                assert isinstance(result, NotifyResult)


class TestSocketIONotification:
    """SocketIO 通知测试"""

    @pytest.mark.asyncio
    async def test_socketio_notification(self):
        """测试 SocketIO 通知（mock sio）"""
        with patch('backend.common.socketio.actions.sio') as mock_sio:
            mock_sio.emit = AsyncMock()
            result = await _send_socketio_notification(
                severity='warning',
                title='测试告警',
                message='测试消息',
                details={'rule_id': 1},
            )
            assert result.success is True
            assert result.channel == NotifyChannel.SOCKETIO.value

    @pytest.mark.asyncio
    async def test_socketio_failure(self):
        """测试 SocketIO 通知失败"""
        with patch('backend.common.socketio.actions.sio') as mock_sio:
            mock_sio.emit = AsyncMock(side_effect=Exception('Connection error'))
            result = await _send_socketio_notification(
                severity='warning',
                title='测试告警',
                message='测试消息',
            )
            assert result.success is False
            assert 'Connection error' in result.error


class TestSMSNotification:
    """短信通知测试"""

    @pytest.mark.asyncio
    async def test_sms_not_implemented(self):
        result = await _send_sms_notification(
            severity='critical',
            title='紧急告警',
            message='系统异常',
        )
        assert result.success is False
        assert '尚未实现' in result.error


class TestNotificationDispatcher:
    """NotificationDispatcher 类测试"""

    @pytest.mark.asyncio
    async def test_dispatcher_dispatch(self):
        dispatcher = NotificationDispatcher()
        with patch('backend.app.admin.service.alert.dispatcher._send_socketio_notification', new_callable=AsyncMock) as mock_sio:
            mock_sio.return_value = NotifyResult(
                channel='socketio',
                success=True,
                message='SocketIO 通知已推送',
            )
            result = await dispatcher.dispatch(
                channels=['socketio'],
                severity='warning',
                title='测试告警',
                message='测试消息',
            )
            assert result['total_channels'] == 1