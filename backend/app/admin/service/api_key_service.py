import hashlib
import secrets
import string

from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_api_key import api_key_dao
from backend.app.admin.model import ApiKey
from backend.app.admin.schema.api_key import (
    CreateApiKeyParam,
    CreateApiKeyResponse,
    GetApiKeyDetail,
    RegenerateApiKeyResponse,
    UpdateApiKeyParam,
)
from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.utils.timezone import timezone


def _generate_api_key() -> tuple[str, str, str]:
    """
    生成 API 密钥

    :return: (full_key, prefix, key_hash)
        - full_key: 完整密钥（仅返回一次）
        - prefix: 密钥前缀（前 12 位，用于标识）
        - key_hash: SHA256 哈希（存入数据库）
    """
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(40))
    full_key = f'fba_{random_part}'
    prefix = full_key[:12]
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, key_hash


class ApiKeyService:
    """API 密钥服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> ApiKey:
        api_key = await api_key_dao.get(db, pk)
        if not api_key:
            raise errors.NotFoundError(msg='API 密钥不存在')
        return api_key

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[ApiKey]:
        return await api_key_dao.get_all(db)

    @staticmethod
    async def get_list(
        *, db: AsyncSession, user_id: int | None = None, is_active: int | None = None
    ) -> dict[str, Any]:
        select = await api_key_dao.get_select(user_id=user_id, is_active=is_active)
        return await paging_data(db, select)

    @staticmethod
    async def get_by_user_id(*, db: AsyncSession, user_id: int) -> Sequence[ApiKey]:
        return await api_key_dao.get_by_user_id(db, user_id)

    @staticmethod
    async def create(
        *, db: AsyncSession, user_id: int, obj: CreateApiKeyParam
    ) -> CreateApiKeyResponse:
        """创建 API 密钥"""
        full_key, prefix, key_hash = _generate_api_key()

        # 解析过期时间
        expires_at = None
        if obj.expires_at:
            try:
                expires_at = timezone.from_datetime_str(obj.expires_at)
            except (ValueError, TypeError):
                raise errors.RequestError(msg='过期时间格式无效，请使用 ISO 8601 格式')

        # 使用 create_model 并传入 kwargs 方式创建（flush=True 以获取 id）
        created = await api_key_dao.create_model(
            db,
            obj,
            key_prefix=prefix,
            key_hash=key_hash,
            user_id=user_id,
            expires_at=expires_at,
            flush=True,
        )

        return CreateApiKeyResponse(
            id=created.id,
            name=created.name,
            api_key=full_key,
            key_prefix=created.key_prefix,
            permissions=created.permissions,
            is_active=created.is_active,
            expires_at=obj.expires_at,
            description=created.description,
            created_time=created.created_time,
        )

    @staticmethod
    async def update(
        *, db: AsyncSession, pk: int, obj: UpdateApiKeyParam
    ) -> int:
        api_key = await api_key_dao.get(db, pk)
        if not api_key:
            raise errors.NotFoundError(msg='API 密钥不存在')

        update_data = obj.model_dump(exclude_unset=True)

        # 解析过期时间
        if 'expires_at' in update_data and update_data['expires_at']:
            try:
                update_data['expires_at'] = timezone.from_datetime_str(update_data['expires_at'])
            except (ValueError, TypeError):
                raise errors.RequestError(msg='过期时间格式无效')

        # 使用 update_model 直接传入 dict
        return await api_key_dao.update_model(db, pk, update_data)

    @staticmethod
    async def regenerate(*, db: AsyncSession, pk: int) -> RegenerateApiKeyResponse:
        """重新生成 API 密钥值"""
        api_key = await api_key_dao.get(db, pk)
        if not api_key:
            raise errors.NotFoundError(msg='API 密钥不存在')

        full_key, prefix, key_hash = _generate_api_key()
        await api_key_dao.update_model(db, pk, {
            'key_prefix': prefix,
            'key_hash': key_hash,
        })
        return RegenerateApiKeyResponse(
            id=api_key.id,
            api_key=full_key,
        )

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        return await api_key_dao.delete(db, pks)

    @staticmethod
    async def verify_api_key(*, db: AsyncSession, api_key: str) -> ApiKey | None:
        """
        验证 API 密钥有效性

        :param db: 数据库会话
        :param api_key: 完整 API 密钥
        :return: 密钥记录（有效）或 None
        """
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_record = await api_key_dao.get_by_hash(db, key_hash)
        if not key_record:
            return None
        if not key_record.is_active:
            return None
        if key_record.expires_at and key_record.expires_at < timezone.now():
            return None

        # 更新最后使用时间
        await api_key_dao.update_last_used(db, key_record.id)
        return key_record


api_key_service: ApiKeyService = ApiKeyService()
