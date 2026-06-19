"""AI 配置管理服务"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.assistant.crud import ai_config_dao
from backend.app.assistant.model import AiConfig
from backend.app.assistant.schema import CreateAiConfigParam, UpdateAiConfigParam
from backend.common.exception import errors
from backend.common.pagination import paging_data


class AiConfigService:
    """AI 配置管理服务"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> AiConfig:
        config = await ai_config_dao.get(db, pk)
        if not config:
            raise errors.NotFoundError(msg='AI 配置不存在')
        return config

    @staticmethod
    async def get_active(*, db: AsyncSession) -> AiConfig | None:
        return await ai_config_dao.get_active(db)

    @staticmethod
    async def get_list(
        *,
        db: AsyncSession,
        name: str | None = None,
        provider: str | None = None,
    ) -> dict[str, Any]:
        select = await ai_config_dao.get_select(name=name, provider=provider)
        return await paging_data(db, select)

    @staticmethod
    async def create(
        *, db: AsyncSession, obj: CreateAiConfigParam, created_by: int
    ) -> AiConfig:
        existing = await ai_config_dao.get_by_name(db, obj.name)
        if existing:
            raise errors.ConflictError(msg='AI 配置名称已存在')

        config = await ai_config_dao.create(db, obj)

        # 如果是第一个配置，自动设为激活
        await db.flush()
        all_configs = await ai_config_dao.get_all(db)
        if len(all_configs) == 1:
            await ai_config_dao.update(db, config.id, {'is_active': True, 'created_by': created_by})
        else:
            await ai_config_dao.update(db, config.id, {'created_by': created_by})

        await db.commit()
        return await ai_config_dao.get(db, config.id)

    @staticmethod
    async def update(
        *, db: AsyncSession, pk: int, obj: UpdateAiConfigParam
    ) -> AiConfig:
        config = await ai_config_dao.get(db, pk)
        if not config:
            raise errors.NotFoundError(msg='AI 配置不存在')

        count = await ai_config_dao.update(db, pk, obj)
        if count == 0:
            raise errors.RequestError(msg='更新失败')

        await db.commit()
        return await ai_config_dao.get(db, pk)

    @staticmethod
    async def set_active(*, db: AsyncSession, pk: int) -> None:
        config = await ai_config_dao.get(db, pk)
        if not config:
            raise errors.NotFoundError(msg='AI 配置不存在')
        await ai_config_dao.set_active(db, pk)
        await db.commit()

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        count = 0
        for pk in pks:
            config = await ai_config_dao.get(db, pk)
            if not config:
                continue
            # 如果删除的是激活配置，自动激活其他配置
            if config.is_active:
                await ai_config_dao.delete(db, [pk])
                remaining = await ai_config_dao.get_all(db)
                if remaining:
                    await ai_config_dao.set_active(db, remaining[0].id)
                count += 1
            else:
                await ai_config_dao.delete(db, [pk])
                count += 1
        await db.commit()
        return count


ai_config_service: AiConfigService = AiConfigService()
