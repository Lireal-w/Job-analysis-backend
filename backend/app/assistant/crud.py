"""AI 助手 CRUD 操作"""

from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.assistant.model import AiConfig, AiChatHistory
from backend.app.assistant.schema.ai_config import CreateAiConfigParam, UpdateAiConfigParam


class CRUDAiConfig(CRUDPlus[AiConfig]):
    """AI 配置数据库操作"""

    async def get(self, db: AsyncSession, pk: int) -> AiConfig | None:
        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> AiConfig | None:
        return await self.select_model_by_column(db, name=name)

    async def get_active(self, db: AsyncSession) -> AiConfig | None:
        """获取当前激活的配置"""
        return await self.select_model_by_column(db, is_active=True)

    async def get_all(self, db: AsyncSession) -> Sequence[AiConfig]:
        return await self.select_models(db)

    async def get_select(
        self,
        name: str | None = None,
        provider: str | None = None,
        enabled: bool | None = None,
    ) -> Select:
        filters = {}
        if name is not None:
            filters['name__like'] = f'%{name}%'
        if provider is not None:
            filters['provider'] = provider
        if enabled is not None:
            filters['enabled'] = enabled
        return await self.select_order('created_time', 'desc', **filters)

    async def create(self, db: AsyncSession, obj: CreateAiConfigParam) -> AiConfig:
        return await self.create_model(db, obj, flush=True)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateAiConfigParam) -> int:
        return await self.update_model(db, pk, obj)

    async def set_active(self, db: AsyncSession, pk: int) -> None:
        """将指定配置设为激活，同时取消其他配置的激活状态"""
        # 取消所有激活
        await self.update_model_by_column(db, {'is_active': False}, is_active=True)
        # 激活指定配置
        await self.update_model(db, pk, {'is_active': True})

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


class CRUDAiChatHistory(CRUDPlus[AiChatHistory]):
    """AI 对话历史数据库操作"""

    async def get_session_messages(
        self, db: AsyncSession, session_id: str, limit: int = 50
    ) -> Sequence[AiChatHistory]:
        stmt = await self.select_order('created_time', 'asc', session_id=session_id)
        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def add_message(
        self, db: AsyncSession, session_id: str, user_id: int,
        role: str, content: str, *,
        tool_calls: dict | None = None,
        tokens_used: int = 0,
        model: str | None = None,
    ) -> AiChatHistory:
        obj = AiChatHistory(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tokens_used=tokens_used,
            model=model,
        )
        db.add(obj)
        await db.flush()
        return obj

    async def clear_session(self, db: AsyncSession, session_id: str) -> int:
        return await self.delete_model_by_column(db, session_id=session_id)

    async def delete_by_user(self, db: AsyncSession, user_id: int) -> int:
        return await self.delete_model_by_column(db, user_id=user_id)


ai_config_dao: CRUDAiConfig = CRUDAiConfig(AiConfig)
ai_chat_history_dao: CRUDAiChatHistory = CRUDAiChatHistory(AiChatHistory)
