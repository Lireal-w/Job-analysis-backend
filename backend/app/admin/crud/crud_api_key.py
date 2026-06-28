from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import ApiKey
from backend.app.admin.schema.api_key import CreateApiKeyParam, UpdateApiKeyParam


class CRUDApiKey(CRUDPlus[ApiKey]):
    """API 密钥数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> ApiKey | None:
        return await self.select_model(db, pk)

    async def get_by_hash(self, db: AsyncSession, key_hash: str) -> ApiKey | None:
        return await self.select_model_by_column(db, key_hash=key_hash)

    async def get_all(self, db: AsyncSession) -> Sequence[ApiKey]:
        return await self.select_models(db)

    async def get_by_user_id(self, db: AsyncSession, user_id: int) -> Sequence[ApiKey]:
        return await self.select_models(db, user_id=user_id)

    async def get_select(
        self, user_id: int | None = None, is_active: int | None = None
    ) -> Select:
        filters = {}
        if user_id is not None:
            filters['user_id'] = user_id
        if is_active is not None:
            filters['is_active'] = is_active
        return await self.select_order('created_time', 'desc', **filters)

    async def update_last_used(self, db: AsyncSession, pk: int) -> None:
        from backend.utils.timezone import timezone

        await self.update_model(db, pk, {'last_used_at': timezone.now()})

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


api_key_dao: CRUDApiKey = CRUDApiKey(ApiKey)
