"""移动端认证服务"""

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask, BackgroundTasks

from backend.app.admin.crud.crud_user import user_dao
from backend.app.admin.model import User
from backend.app.admin.service.login_log_service import login_log_service
from backend.app.admin.service.user_password_history_service import password_security_service
from backend.app.admin.utils.password_security import password_verify
from backend.app.mobile.schema.auth import MobileLoginParam, MobileLoginToken, MobileNewToken, MobileUserDetail
from backend.common.context import ctx
from backend.common.enums import LoginLogStatusType
from backend.common.exception import errors
from backend.common.log import log
from backend.common.security.jwt import (
    create_access_token,
    create_new_token,
    create_refresh_token,
    get_token,
    jwt_decode,
)
from backend.core.conf import settings
from backend.database.db import uuid4_str
from backend.database.redis import redis_client
from backend.utils.timezone import timezone


class MobileAuthService:
    """移动端认证服务类"""

    @staticmethod
    async def _user_verify(db: AsyncSession, username: str, password: str) -> tuple[User, int | None]:
        """
        验证用户名和密码

        :param db: 数据库会话
        :param username: 用户名
        :param password: 密码
        :return:
        """
        user = await user_dao.get_by_username(db, username)
        if not user:
            raise errors.NotFoundError(msg='用户名或密码有误')

        await password_security_service.check_status(user.id, user.status)

        if user.password is None or not password_verify(password, user.password):
            await password_security_service.handle_login_failure(db, user.id)
            raise errors.AuthorizationError(msg='用户名或密码有误')

        days_remaining = await password_security_service.check_password_expiry_status(
            db, user.last_password_changed_time
        )

        await password_security_service.handle_login_success(user.id)

        return user, days_remaining

    async def login(
        self,
        *,
        db: AsyncSession,
        obj: MobileLoginParam,
        background_tasks: BackgroundTasks,
    ) -> MobileLoginToken:
        """
        移动端用户登录

        :param db: 数据库会话
        :param obj: 登录参数
        :param background_tasks: 后台任务
        :return:
        """
        user = None
        try:
            user, _ = await self._user_verify(db, obj.username, obj.password)
            await user_dao.update_login_time(db, obj.username)
            await db.refresh(user)

            access_token_data = await create_access_token(
                user.id,
                multi_login=user.is_multi_login,
                # extra info
                username=user.username,
                nickname=user.nickname,
                last_login_time=timezone.to_str(user.last_login_time),
                ip=ctx.ip,
                os=ctx.os,
                browser=ctx.browser,
                device=ctx.device,
            )
            refresh_token_data = await create_refresh_token(
                access_token_data.session_uuid,
                user.id,
                multi_login=user.is_multi_login,
            )
        except errors.NotFoundError as e:
            log.error(f'移动端登陆错误: {e.msg}')
            task = BackgroundTask(
                login_log_service.create,
                user_uuid=user.uuid if user else uuid4_str(),
                username=obj.username,
                login_time=timezone.now(),
                status=LoginLogStatusType.fail.value,
                msg=e.msg,
            )
            raise errors.NotFoundError(msg=e.msg, background=task)
        except errors.AuthorizationError as e:
            log.error(f'移动端登陆错误: {e.msg}')
            task = BackgroundTask(
                login_log_service.create,
                user_uuid=user.uuid if user else uuid4_str(),
                username=obj.username,
                login_time=timezone.now(),
                status=LoginLogStatusType.fail.value,
                msg=e.msg,
            )
            raise errors.AuthorizationError(msg=e.msg, background=task)
        except Exception as e:
            log.error(f'移动端登陆错误: {e}')
            raise
        else:
            background_tasks.add_task(
                login_log_service.create,
                user_uuid=user.uuid,
                username=obj.username,
                login_time=timezone.now(),
                status=LoginLogStatusType.success.value,
                msg='移动端登录成功',
            )
            data = MobileLoginToken(
                access_token=access_token_data.access_token,
                access_token_expire_time=access_token_data.access_token_expire_time,
                refresh_token=refresh_token_data.refresh_token,
                refresh_token_expire_time=refresh_token_data.refresh_token_expire_time,
                session_uuid=access_token_data.session_uuid,
                user=MobileUserDetail(
                    id=user.id,
                    uuid=user.uuid,
                    username=user.username,
                    nickname=user.nickname,
                    avatar=user.avatar,
                    email=user.email,
                    phone=user.phone,
                ),
            )
            return data

    @staticmethod
    async def refresh_token(*, db: AsyncSession, request: Request, obj) -> MobileNewToken:
        """
        移动端刷新令牌

        :param db: 数据库会话
        :param request: FastAPI 请求对象
        :param obj: 刷新令牌参数
        :return:
        """
        refresh_token = obj.refresh_token
        if not refresh_token:
            raise errors.RequestError(msg='Refresh Token 不能为空，请重新登录')

        try:
            token_payload = jwt_decode(refresh_token)
        except errors.TokenError:
            raise errors.RequestError(msg='Refresh Token 已过期或无效，请重新登录')

        user = await user_dao.get(db, token_payload.user_id)
        if not user:
            raise errors.NotFoundError(msg='用户不存在')
        if not user.status:
            raise errors.AuthorizationError(msg='用户已被锁定，请联系系统管理员')

        token_keys = await redis_client.get_prefix(f'{settings.TOKEN_REDIS_PREFIX}:{user.id}:*')
        if not user.is_multi_login and [
            key for key in token_keys if not key.endswith(f':{token_payload.session_uuid}')
        ]:
            raise errors.ForbiddenError(msg='此用户已在异地登录，请重新登录并及时修改密码')

        new_token = await create_new_token(
            refresh_token,
            token_payload.session_uuid,
            user.id,
            multi_login=user.is_multi_login,
            # extra info
            username=user.username,
            nickname=user.nickname,
            last_login_time=timezone.to_str(user.last_login_time),
            ip=ctx.ip,
            os=ctx.os,
            browser=ctx.browser,
            device_type=ctx.device,
        )
        data = MobileNewToken(
            access_token=new_token.new_access_token,
            access_token_expire_time=new_token.new_access_token_expire_time,
            refresh_token=new_token.new_refresh_token,
            refresh_token_expire_time=new_token.new_refresh_token_expire_time,
            session_uuid=new_token.session_uuid,
        )
        return data

    @staticmethod
    async def logout(*, request: Request, response: Response) -> None:
        """
        移动端用户登出

        :param request: FastAPI 请求对象
        :param response: FastAPI 响应对象
        :return:
        """
        try:
            token = get_token(request)
            token_payload = jwt_decode(token)
            user_id = token_payload.user_id
            session_uuid = token_payload.session_uuid
        except errors.TokenError:
            return

        await redis_client.delete(f'{settings.TOKEN_REDIS_PREFIX}:{user_id}:{session_uuid}')
        await redis_client.delete(f'{settings.TOKEN_EXTRA_INFO_REDIS_PREFIX}:{user_id}:{session_uuid}')
        await redis_client.delete(f'{settings.TOKEN_REFRESH_REDIS_PREFIX}:{user_id}:{session_uuid}')


mobile_auth_service: MobileAuthService = MobileAuthService()
