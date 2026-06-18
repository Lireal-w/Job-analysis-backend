"""通知分发器

负责将告警通知发送到不同渠道：邮件、Webhook、SocketIO。

支持的渠道：
- email: 通过 plugin/email 发送告警邮件
- webhook: HTTP POST 到外部 URL（钉钉/企微/Slack 等）
- socketio: 通过 WebSocket 实时推送
- sms: 短信通知（预留接口）
"""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from typing import Any

import httpx
from loguru import logger

from backend.app.admin.service.alert.enums import NotifyChannel


@dataclass
class NotifyResult:
    """通知发送结果"""

    channel: str
    success: bool
    message: str = ''
    error: str | None = None


async def dispatch_notification(
    channels: list[str],
    severity: str,
    title: str,
    message: str,
    details: dict[str, Any] | None = None,
    db: Any = None,
    webhook_url: str | None = None,
    email_recipients: list[str] | None = None,
) -> dict[str, Any]:
    """分发通知到多个渠道

    Args:
        channels: 通知渠道列表 (email/webhook/sms/socketio)
        severity: 告警严重级别
        title: 通知标题
        message: 通知内容
        details: 额外详情
        db: 数据库会话（邮件发送需要）
        webhook_url: Webhook URL（覆盖规则配置）
        email_recipients: 邮件接收者列表（覆盖规则配置）

    Returns:
        各渠道发送结果
    """
    results: list[NotifyResult] = []

    for channel in channels:
        try:
            if channel == NotifyChannel.EMAIL.value:
                result = await _send_email_notification(
                    severity=severity,
                    title=title,
                    message=message,
                    details=details,
                    db=db,
                    recipients=email_recipients,
                )
            elif channel == NotifyChannel.WEBHOOK.value:
                result = await _send_webhook_notification(
                    severity=severity,
                    title=title,
                    message=message,
                    details=details,
                    webhook_url=webhook_url,
                )
            elif channel == NotifyChannel.SOCKETIO.value:
                result = await _send_socketio_notification(
                    severity=severity,
                    title=title,
                    message=message,
                    details=details,
                )
            elif channel == NotifyChannel.SMS.value:
                result = await _send_sms_notification(
                    severity=severity,
                    title=title,
                    message=message,
                )
            else:
                result = NotifyResult(
                    channel=channel,
                    success=False,
                    error=f'不支持的通知渠道: {channel}',
                )
        except Exception as e:
            logger.error(f'[NotificationDispatcher] 渠道 {channel} 通知发送失败: {e}')
            result = NotifyResult(
                channel=channel,
                success=False,
                error=f'{type(e).__name__}: {e}',
            )

        results.append(result)

    # 汇总结果
    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count

    summary = {
        'total_channels': len(channels),
        'success_count': success_count,
        'fail_count': fail_count,
        'results': [
            {
                'channel': r.channel,
                'success': r.success,
                'message': r.message,
                'error': r.error,
            }
            for r in results
        ],
    }

    logger.info(
        f'[NotificationDispatcher] 通知发送完成: '
        f'成功={success_count}, 失败={fail_count}, 渠道={channels}'
    )

    return summary


async def _send_email_notification(
    severity: str,
    title: str,
    message: str,
    details: dict[str, Any] | None = None,
    db: Any = None,
    recipients: list[str] | None = None,
) -> NotifyResult:
    """发送邮件通知

    复用 plugin/email 的 send_email 函数。
    """
    if db is None:
        return NotifyResult(
            channel=NotifyChannel.EMAIL.value,
            success=False,
            error='邮件通知需要数据库会话',
        )

    if not recipients:
        # 从配置获取默认告警接收者
        from backend.core.conf import settings
        recipients = getattr(settings, 'ALERT_EMAIL_RECIPIENTS', [])
        if not recipients:
            return NotifyResult(
                channel=NotifyChannel.EMAIL.value,
                success=False,
                error='未配置告警邮件接收者',
            )

    # 构建邮件内容
    severity_emoji = {
        'info': 'ℹ️',
        'warning': '⚠️',
        'error': '🔴',
        'critical': '🚨',
    }.get(severity, '📢')

    content = {
        'title': f'{severity_emoji} {title}',
        'message': message,
        'severity': severity,
        'details': details or {},
    }

    try:
        from backend.plugin.email.utils.send import send_email

        await send_email(
            db=db,
            recipients=recipients,
            subject=f'{severity_emoji} {title}',
            content=content,
            template='alert.html',
        )

        return NotifyResult(
            channel=NotifyChannel.EMAIL.value,
            success=True,
            message=f'邮件已发送至 {len(recipients)} 个接收者',
        )
    except Exception as e:
        logger.error(f'[NotificationDispatcher] 邮件发送失败: {e}')
        return NotifyResult(
            channel=NotifyChannel.EMAIL.value,
            success=False,
            error=f'{type(e).__name__}: {e}',
        )


async def _send_webhook_notification(
    severity: str,
    title: str,
    message: str,
    details: dict[str, Any] | None = None,
    webhook_url: str | None = None,
) -> NotifyResult:
    """发送 Webhook 通知

    支持 HTTP POST 到外部 URL，兼容钉钉、企微、Slack 等格式。
    """
    if not webhook_url:
        # 从配置获取默认 Webhook URL
        from backend.core.conf import settings
        webhook_url = getattr(settings, 'ALERT_WEBHOOK_URL', None)
        if not webhook_url:
            return NotifyResult(
                channel=NotifyChannel.WEBHOOK.value,
                success=False,
                error='未配置 Webhook URL',
            )

    # 构建通用 Webhook 载荷
    payload = {
        'title': title,
        'message': message,
        'severity': severity,
        'details': details or {},
        'timestamp': __import__('datetime').datetime.now().isoformat(),
    }

    # 检测 Webhook 类型并适配格式
    if 'dingtalk' in webhook_url or 'oapi.dingtalk.com' in webhook_url:
        # 钉钉格式
        payload = {
            'msgtype': 'markdown',
            'markdown': {
                'title': title,
                'text': f'### {title}\n\n> **级别**: {severity}\n\n> {message}\n\n'
                        f'> 时间: {payload["timestamp"]}',
            },
        }
    elif 'qyapi.weixin' in webhook_url or 'work.weixin.qq.com' in webhook_url:
        # 企微格式
        payload = {
            'msgtype': 'markdown',
            'markdown': {
                'content': f'### {title}\n> **级别**: {severity}\n> {message}\n> 时间: {payload["timestamp"]}',
            },
        }
    elif 'hooks.slack.com' in webhook_url or 'slack.com' in webhook_url:
        # Slack 格式
        payload = {
            'text': f'{title}',
            'blocks': [
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': f'*{title}*\n级别: `{severity}`\n{message}',
                    },
                },
            ],
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
            )
            response.raise_for_status()

        return NotifyResult(
            channel=NotifyChannel.WEBHOOK.value,
            success=True,
            message=f'Webhook 通知已发送 (HTTP {response.status_code})',
        )
    except httpx.HTTPStatusError as e:
        return NotifyResult(
            channel=NotifyChannel.WEBHOOK.value,
            success=False,
            error=f'HTTP {e.response.status_code}: {e.response.text[:200]}',
        )
    except Exception as e:
        return NotifyResult(
            channel=NotifyChannel.WEBHOOK.value,
            success=False,
            error=f'{type(e).__name__}: {e}',
        )


async def _send_socketio_notification(
    severity: str,
    title: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> NotifyResult:
    """发送 SocketIO 实时通知

    通过 WebSocket 推送告警到前端。
    """
    try:
        from backend.common.socketio.actions import sio

        payload = {
            'type': 'alert',
            'severity': severity,
            'title': title,
            'message': message,
            'details': details or {},
        }

        await sio.emit('alert_notification', payload, namespace='/ws')

        return NotifyResult(
            channel=NotifyChannel.SOCKETIO.value,
            success=True,
            message='SocketIO 通知已推送',
        )
    except Exception as e:
        logger.error(f'[NotificationDispatcher] SocketIO 通知发送失败: {e}')
        return NotifyResult(
            channel=NotifyChannel.SOCKETIO.value,
            success=False,
            error=f'{type(e).__name__}: {e}',
        )


async def _send_sms_notification(
    severity: str,
    title: str,
    message: str,
) -> NotifyResult:
    """发送短信通知（预留接口）

    短信通知需要接入第三方短信服务商（如阿里云短信、腾讯云短信等）。
    当前为占位实现。
    """
    logger.warning('[NotificationDispatcher] 短信通知渠道尚未实现，请接入第三方短信服务商')
    return NotifyResult(
        channel=NotifyChannel.SMS.value,
        success=False,
        error='短信通知渠道尚未实现',
    )


class NotificationDispatcher:
    """通知分发器（面向对象封装）

    用法：
        dispatcher = NotificationDispatcher()
        result = await dispatcher.dispatch(
            channels=['email', 'webhook'],
            severity='warning',
            title='告警标题',
            message='告警内容',
            db=db,
        )
    """

    async def dispatch(
        self,
        channels: list[str],
        severity: str,
        title: str,
        message: str,
        details: dict[str, Any] | None = None,
        db: Any = None,
        webhook_url: str | None = None,
        email_recipients: list[str] | None = None,
    ) -> dict[str, Any]:
        """分发通知"""
        return await dispatch_notification(
            channels=channels,
            severity=severity,
            title=title,
            message=message,
            details=details,
            db=db,
            webhook_url=webhook_url,
            email_recipients=email_recipients,
        )