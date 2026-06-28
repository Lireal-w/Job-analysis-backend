"""聊天 WebSocket 处理模块

基于 Socket.IO，在 /ws/chat 命名空间提供实时聊天功能。
支持群聊和私聊。

WebSocket 事件:
  客户端 → 服务端:
    chat:join       {"conv_id": "..."}            加入会话房间
    chat:send       {"conv_id": "...", "content": "..."}  发送消息
    chat:typing     {"conv_id": "...", "typing": true}    输入状态

  服务端 → 客户端:
    chat:message    {"conv_id": "...", "sender_id": ..., "sender_name": "...", "content": "...", "created_at": "..."}
    chat:typing     {"conv_id": "...", "user_id": ..., "typing": true}
    chat:error      {"message": "..."}
"""

from __future__ import annotations

from datetime import datetime

from loguru import logger

from backend.app.chat.service import chat_service
from backend.common.socketio.server import sio

CHAT_NAMESPACE = '/ws/chat'


@sio.on('connect', namespace=CHAT_NAMESPACE)
async def connect(sid, environ, auth) -> bool:
    """聊天 WebSocket 连接"""
    user_id = auth.get('user_id') if auth else None
    if user_id:
        # 关联 sid → user_id
        chat_service.register_session(sid, user_id)
    logger.info(f'[Chat] 已连接: sid={sid}, user_id={user_id}')
    return True


@sio.on('disconnect', namespace=CHAT_NAMESPACE)
async def disconnect(sid) -> None:
    """聊天 WebSocket 断开"""
    user_id = chat_service.get_user_id(sid)
    logger.info(f'[Chat] 已断开: sid={sid}, user_id={user_id}')
    chat_service.remove_session(sid)


@sio.on('chat:join', namespace=CHAT_NAMESPACE)
async def handle_join(sid, data: dict) -> None:
    """用户加入会话房间"""
    conv_id = data.get('conv_id')
    if not conv_id:
        await sio.emit('chat:error', {'message': 'conv_id is required'}, to=sid, namespace=CHAT_NAMESPACE)
        return

    # 将 sid 加入 Socket.IO 房间 (房间名 = conv_id)
    sio.enter_room(sid, conv_id, namespace=CHAT_NAMESPACE)
    logger.info(f'[Chat] sid={sid} 加入房间 {conv_id}')


@sio.on('chat:leave', namespace=CHAT_NAMESPACE)
async def handle_leave(sid, data: dict) -> None:
    """用户离开会话房间"""
    conv_id = data.get('conv_id')
    if conv_id:
        sio.leave_room(sid, conv_id, namespace=CHAT_NAMESPACE)


@sio.on('chat:send', namespace=CHAT_NAMESPACE)
async def handle_send(sid, data: dict) -> None:
    """用户发送聊天消息"""
    conv_id = data.get('conv_id')
    content = data.get('content', '').strip()
    msg_type = data.get('msg_type', 'text')

    if not conv_id or not content:
        await sio.emit('chat:error', {'message': 'conv_id and content are required'}, to=sid, namespace=CHAT_NAMESPACE)
        return

    user_id = chat_service.get_user_id(sid)
    if not user_id:
        await sio.emit('chat:error', {'message': '未登录或会话已过期'}, to=sid, namespace=CHAT_NAMESPACE)
        return

    # 保存消息到 MongoDB
    saved = await chat_service.save_message(conv_id, user_id, content, msg_type)

    # 广播消息给房间内所有成员（包括发送者回显）
    now = datetime.utcnow().isoformat()
    await sio.emit('chat:message', {
        'conv_id': conv_id,
        'message_id': str(saved['_id']),
        'sender_id': user_id,
        'sender_name': saved.get('sender_name', ''),
        'sender_avatar': saved.get('sender_avatar', ''),
        'content': content,
        'msg_type': msg_type,
        'created_at': now,
    }, room=conv_id, namespace=CHAT_NAMESPACE)

    # 更新会话的最近消息时间戳
    await chat_service.update_conversation_ts(conv_id)


@sio.on('chat:typing', namespace=CHAT_NAMESPACE)
async def handle_typing(sid, data: dict) -> None:
    """用户输入状态广播"""
    conv_id = data.get('conv_id')
    typing = data.get('typing', False)
    user_id = chat_service.get_user_id(sid)
    if conv_id and user_id:
        await sio.emit('chat:typing', {
            'conv_id': conv_id,
            'user_id': user_id,
            'typing': typing,
        }, room=conv_id, skip_sid=sid, namespace=CHAT_NAMESPACE)
