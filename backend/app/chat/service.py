"""聊天服务 - MongoDB 存储 + 会话管理"""

from datetime import datetime
from typing import Any

from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.conf import settings
from backend.database.mongo_db import get_mongo_db

# MongoDB 集合名称
CHAT_CONVERSATIONS_COLLECTION = 'chat_conversations'
CHAT_MESSAGES_COLLECTION = 'chat_messages'


class ChatService:
    """聊天业务服务类"""

    def __init__(self) -> None:
        # sid → user_id 映射（内存中维护）
        self._sessions: dict[str, int] = {}

    # ── WebSocket 会话管理 ──

    def register_session(self, sid: str, user_id: int) -> None:
        self._sessions[sid] = user_id

    def remove_session(self, sid: str) -> None:
        self._sessions.pop(sid, None)

    def get_user_id(self, sid: str) -> int | None:
        return self._sessions.get(sid)

    # ── MongoDB 数据库操作 ──

    async def _get_db(self) -> AsyncIOMotorDatabase:
        """获取 MongoDB 数据库实例"""
        return await get_mongo_db()

    # ==================== 会话管理 ====================

    async def create_conversation(
        self,
        *,
        conv_type: str,
        name: str | None = None,
        created_by: int,
        member_ids: list[int],
    ) -> dict[str, Any]:
        """创建聊天会话（私聊或群聊）"""
        db = await self._get_db()
        coll = db[CHAT_CONVERSATIONS_COLLECTION]

        # 私聊查重：检查两个用户是否已有私聊
        if conv_type == 'private' and len(member_ids) == 2:
            existing = await coll.find_one({
                'type': 'private',
                'member_ids': {'$all': member_ids, '$size': 2},
            })
            if existing:
                return self._format_conversation(existing)

        doc = {
            'type': conv_type,
            'name': name or ('群聊' if conv_type == 'group' else '私聊'),
            'created_by': created_by,
            'member_ids': member_ids,
            'last_message': None,
            'last_activity': datetime.utcnow().isoformat(),
            'created_at': datetime.utcnow().isoformat(),
        }
        result = await coll.insert_one(doc)
        doc['_id'] = result.inserted_id
        return self._format_conversation(doc)

    async def get_user_conversations(self, user_id: int) -> list[dict[str, Any]]:
        """获取用户的会话列表（按最近活动排序）"""
        db = await self._get_db()
        coll = db[CHAT_CONVERSATIONS_COLLECTION]

        cursor = coll.find({'member_ids': user_id}).sort('last_activity', -1).limit(50)
        results = []
        async for doc in cursor:
            results.append(self._format_conversation(doc))
        return results

    async def get_conversation(self, conv_id: str) -> dict[str, Any] | None:
        """获取会话详情"""
        db = await self._get_db()
        doc = await db[CHAT_CONVERSATIONS_COLLECTION].find_one({'_id': ObjectId(conv_id)})
        return self._format_conversation(doc) if doc else None

    async def add_member(self, conv_id: str, user_id: int) -> bool:
        """添加群成员"""
        db = await self._get_db()
        result = await db[CHAT_CONVERSATIONS_COLLECTION].update_one(
            {'_id': ObjectId(conv_id)},
            {'$addToSet': {'member_ids': user_id}},
        )
        return result.modified_count > 0

    async def remove_member(self, conv_id: str, user_id: int) -> bool:
        """移除群成员"""
        db = await self._get_db()
        result = await db[CHAT_CONVERSATIONS_COLLECTION].update_one(
            {'_id': ObjectId(conv_id)},
            {'$pull': {'member_ids': user_id}},
        )
        return result.modified_count > 0

    async def update_conversation_ts(self, conv_id: str) -> None:
        """更新会话最后活动时间"""
        db = await self._get_db()
        await db[CHAT_CONVERSATIONS_COLLECTION].update_one(
            {'_id': ObjectId(conv_id)},
            {'$set': {'last_activity': datetime.utcnow().isoformat()}},
        )

    # ==================== 消息管理 ====================

    async def save_message(
        self,
        conv_id: str,
        sender_id: int,
        content: str,
        msg_type: str = 'text',
    ) -> dict[str, Any]:
        """保存聊天消息到 MongoDB"""
        db = await self._get_db()

        # 获取发送者信息
        sender_name = f'用户 {sender_id}'
        sender_avatar = ''
        try:
            from backend.database.db import async_db_session
            from backend.app.admin.crud.crud_user import user_dao

            async with async_db_session() as s:
                user = await user_dao.get(s, sender_id)
                if user:
                    sender_name = user.nickname or user.username
                    sender_avatar = user.avatar or ''
        except Exception:
            pass

        doc = {
            'conv_id': conv_id,
            'sender_id': sender_id,
            'sender_name': sender_name,
            'sender_avatar': sender_avatar,
            'content': content,
            'msg_type': msg_type,
            'created_at': datetime.utcnow().isoformat(),
        }
        result = await db[CHAT_MESSAGES_COLLECTION].insert_one(doc)
        doc['_id'] = result.inserted_id

        # 更新会话的最新消息预览
        await db[CHAT_CONVERSATIONS_COLLECTION].update_one(
            {'_id': ObjectId(conv_id)},
            {'$set': {
                'last_message': content[:100],
                'last_activity': datetime.utcnow().isoformat(),
            }},
        )

        return doc

    async def get_messages(
        self,
        conv_id: str,
        page: int = 1,
        size: int = 50,
    ) -> dict[str, Any]:
        """分页获取会话消息"""
        db = await self._get_db()
        query = {'conv_id': conv_id}
        total = await db[CHAT_MESSAGES_COLLECTION].count_documents(query)
        skip = (page - 1) * size

        cursor = db[CHAT_MESSAGES_COLLECTION].find(query).sort('created_at', -1).skip(skip).limit(size)
        items = []
        async for doc in cursor:
            items.append({
                'message_id': str(doc['_id']),
                'conv_id': doc.get('conv_id'),
                'sender_id': doc.get('sender_id'),
                'sender_name': doc.get('sender_name', ''),
                'sender_avatar': doc.get('sender_avatar', ''),
                'content': doc.get('content', ''),
                'msg_type': doc.get('msg_type', 'text'),
                'created_at': doc.get('created_at'),
            })

        items.reverse()  # 按时间正序
        return {'items': items, 'total': total, 'page': page, 'size': size}

    # ==================== 辅助方法 ====================

    @staticmethod
    def _format_conversation(doc: dict[str, Any] | None) -> dict[str, Any] | None:
        """格式化会话文档"""
        if doc is None:
            return None
        return {
            'conv_id': str(doc['_id']),
            'type': doc.get('type', 'private'),
            'name': doc.get('name', ''),
            'created_by': doc.get('created_by'),
            'member_ids': doc.get('member_ids', []),
            'last_message': doc.get('last_message'),
            'last_activity': doc.get('last_activity'),
            'created_at': doc.get('created_at'),
        }


# 服务单例
chat_service = ChatService()
