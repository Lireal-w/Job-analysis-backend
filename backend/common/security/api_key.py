"""
API 密钥认证依赖

提供基于 API Key 的认证功能，与 JWT 认证共存。
当请求携带 Authorization: Bearer fba_xxx 或 X-API-Key: fba_xxx 时，使用 API Key 认证。
"""

from backend.app.admin.service.api_key_service import api_key_service
from backend.app.admin.schema.user import GetUserInfoWithRelationDetail
from backend.common.exception import errors
from backend.database.db import async_db_session


async def api_key_authentication(api_key: str) -> GetUserInfoWithRelationDetail | None:
    """
    API Key 认证

    :param api_key: API 密钥
    :return: 创建者用户信息或 None
    """
    if not api_key.startswith('fba_'):
        return None

    async with async_db_session() as db:
        key_record = await api_key_service.verify_api_key(db=db, api_key=api_key)
        if not key_record:
            raise errors.TokenError(msg='API Key 无效或已过期')

        # 获取创建者用户
        from backend.common.security.jwt import get_current_user as get_jwt_current_user

        user = await get_jwt_current_user(db, key_record.user_id)
        if not user:
            raise errors.TokenError(msg='API Key 关联用户无效')

        # 如果 API Key 关联了权限，将权限注入上下文
        if key_record.permissions:
            from backend.common.context import ctx
            ctx.permission = key_record.permissions

        return user
