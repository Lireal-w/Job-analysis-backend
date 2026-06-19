"""AI 助手 WebSocket 处理模块

使用 SocketIO 在 /ws/assistant 命名空间提供实时 AI 对话。
消息格式 (JSON):
    客户端 → 服务端: {"session_id": "...", "content": "...", "stream": true}
    服务端 → 客户端: {"type": "message|tool_call|tool_result|done|error", "content": "...", ...}
"""

from __future__ import annotations

import json
import uuid

from loguru import logger

from backend.app.assistant.service.chat_service import ChatStreamResult, ai_chat_service
from backend.common.socketio.server import sio


ASSISTANT_NAMESPACE = '/ws/assistant'


@sio.on('connect', namespace=ASSISTANT_NAMESPACE)
async def connect(sid, environ, auth) -> bool:
    """AI 助手 WebSocket 连接"""
    logger.info(f'[AI Assistant] WebSocket 已连接: sid={sid}')
    return True


@sio.on('disconnect', namespace=ASSISTANT_NAMESPACE)
async def disconnect(sid) -> None:
    """AI 助手 WebSocket 断开"""
    logger.info(f'[AI Assistant] WebSocket 已断开: sid={sid}')


@sio.on('chat', namespace=ASSISTANT_NAMESPACE)
async def handle_chat(sid, data: dict) -> None:
    """处理 AI 对话消息

    接收的 data 格式:
        {
            "session_id": "uuid-string",  # 会话 ID，客户端生成
            "content": "用户消息文本",
            "stream": true                 # 是否流式输出 (默认 true)
        }

    发送的响应格式:
        {"type": "message",  "content": "文本片段"}      ← 流式文本片段
        {"type": "tool_call",  "tool_name": "...", "tool_args": {...}}  ← AI 发起工具调用
        {"type": "tool_result", "tool_name": "...", "content": "结果"} ← 工具执行结果
        {"type": "done", "tokens_used": 123}              ← 本轮对话结束
        {"type": "error", "content": "错误信息"}           ← 错误
    """
    try:
        session_id = data.get('session_id')
        content = data.get('content', '')
        stream = data.get('stream', True)

        if not session_id:
            session_id = uuid.uuid4().hex

        if not content.strip():
            await sio.emit('chat_response', {
                'type': 'error',
                'content': '消息不能为空',
                'session_id': session_id,
            }, to=sid, namespace=ASSISTANT_NAMESPACE)
            return

        # 用户 ID（WebSocket 简化处理，固定为 1）
        user_id = 1

        # 调用 AI 对话服务
        async for result in ai_chat_service.chat(
            session_id=session_id,
            user_id=user_id,
            user_message=content,
            stream=stream,
        ):
            if result.error:
                await sio.emit('chat_response', {
                    'type': 'error',
                    'content': result.error,
                    'session_id': session_id,
                }, to=sid, namespace=ASSISTANT_NAMESPACE)
                return

            response = {
                'type': result.type,
                'content': result.content,
                'session_id': session_id,
            }
            if result.tool_name:
                response['tool_name'] = result.tool_name
            if result.tool_args:
                response['tool_args'] = result.tool_args
            if result.tokens_used is not None:
                response['tokens_used'] = result.tokens_used

            await sio.emit('chat_response', response, to=sid, namespace=ASSISTANT_NAMESPACE)

    except Exception as e:
        logger.error(f'[AI Assistant] 对话处理失败: {e}')
        await sio.emit('chat_response', {
            'type': 'error',
            'content': f'对话处理失败: {type(e).__name__}: {e}',
            'session_id': data.get('session_id', ''),
        }, to=sid, namespace=ASSISTANT_NAMESPACE)


@sio.on('clear_session', namespace=ASSISTANT_NAMESPACE)
async def handle_clear_session(sid, data: dict) -> None:
    """清除对话历史"""
    from backend.app.assistant.crud import ai_chat_history_dao
    from backend.database.db import async_db_session

    session_id = data.get('session_id', '')
    if not session_id:
        return

    async with async_db_session() as db:
        await ai_chat_history_dao.clear_session(db, session_id)
        await db.commit()

    await sio.emit('chat_response', {
        'type': 'message',
        'content': '✅ 对话历史已清除',
        'session_id': session_id,
    }, to=sid, namespace=ASSISTANT_NAMESPACE)
