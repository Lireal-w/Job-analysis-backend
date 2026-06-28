import hashlib
from typing import Any

from fastapi import Request, Response
from fastapi.security.utils import get_authorization_scheme_param
from starlette.authentication import AuthCredentials, AuthenticationBackend
from starlette.authentication import AuthenticationError as StarletteAuthenticationError
from starlette.requests import HTTPConnection

from backend.app.admin.schema.user import GetUserInfoWithRelationDetail
from backend.common.exception.errors import TokenError
from backend.common.log import log
from backend.common.security.jwt import jwt_authentication
from backend.core.conf import settings
from backend.utils.serializers import MsgSpecJSONResponse


class AuthenticationError(StarletteAuthenticationError):
    """重写内部认证错误类"""

    def __init__(
        self,
        *,
        code: int | None = None,
        msg: str | None = None,
        headers: dict[str, Any] | None = None,
    ) -> None:
        """
        初始化认证错误类

        :param code: 错误码
        :param msg: 错误信息
        :param headers: 响应头
        :return:
        """
        self.code = code
        self.msg = msg
        self.headers = headers


class JwtAuthMiddleware(AuthenticationBackend):
    """JWT / API Key 认证中间件

    支持三种认证方式：
    1. Authorization: Bearer <jwt_token> — JWT 认证
    2. Authorization: Bearer fba_<key> — API Key 认证
    3. X-API-Key: fba_<key> — API Key 认证
    """

    @staticmethod
    def auth_exception_handler(conn: HTTPConnection, exc: AuthenticationError) -> Response:
        """
        覆盖内部认证错误处理

        :param conn: HTTP 连接对象
        :param exc: 认证错误对象
        :return:
        """
        return MsgSpecJSONResponse(content={'code': exc.code, 'msg': exc.msg, 'data': None}, status_code=exc.code)

    @staticmethod
    def extract_token(request: Request) -> str | None:
        """
        从请求中提取 Token 或 API Key

        :param request: FastAPI 请求对象
        :return:
        """
        path = request.url.path
        if path in settings.TOKEN_REQUEST_PATH_EXCLUDE:
            return None
        for pattern in settings.TOKEN_REQUEST_PATH_EXCLUDE_PATTERN:
            if pattern.match(path):
                return None

        # 1. 优先尝试 Authorization: Bearer
        authorization = request.headers.get('Authorization')
        if authorization:
            scheme, token = get_authorization_scheme_param(authorization)
            if scheme.lower() == 'bearer' and token:
                return token

        # 2. 尝试 X-API-Key 头
        api_key = request.headers.get('X-API-Key')
        if api_key:
            return api_key

        return None

    async def authenticate(self, request: Request) -> tuple[AuthCredentials, GetUserInfoWithRelationDetail] | None:
        """
        认证请求

        :param request: FastAPI 请求对象
        :return:
        """
        token = self.extract_token(request)
        if token is None:
            return None

        try:
            # 判断是否为 API Key（以 fba_ 开头）
            if token.startswith('fba_'):
                from backend.common.security.api_key import api_key_authentication

                user = await api_key_authentication(token)
            else:
                # 标准 JWT 认证
                user = await jwt_authentication(token)
        except TokenError as exc:
            raise AuthenticationError(code=exc.code, msg=exc.detail, headers=exc.headers)
        except Exception as e:
            log.exception(f'JWT 授权异常：{e}')
            raise AuthenticationError(code=getattr(e, 'code', 500), msg=getattr(e, 'msg', 'Internal Server Error'))

        # 请注意，此返回使用非标准模式，所以在认证通过时，将丢失某些标准特性
        # 标准返回模式请查看：https://www.starlette.io/authentication/
        return AuthCredentials(['authenticated']), user
