"""移动端认证 Schema"""

from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class MobileLoginParam(SchemaBase):
    """移动端登录参数"""

    username: str = Field(description='用户名')
    password: str = Field(description='密码')


class MobileRefreshTokenParam(SchemaBase):
    """移动端刷新 Token 参数"""

    refresh_token: str = Field(description='刷新令牌')


class MobileUserDetail(SchemaBase):
    """移动端用户信息"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='用户 ID')
    uuid: str = Field(description='用户 UUID')
    username: str = Field(description='用户名')
    nickname: str = Field(description='昵称')
    avatar: str | None = Field(None, description='头像地址')
    email: str | None = Field(None, description='邮箱')
    phone: str | None = Field(None, description='手机号')


class MobileLoginToken(SchemaBase):
    """移动端登录返回 Token"""

    access_token: str = Field(description='访问令牌')
    access_token_expire_time: datetime = Field(description='访问令牌过期时间')
    refresh_token: str = Field(description='刷新令牌')
    refresh_token_expire_time: datetime = Field(description='刷新令牌过期时间')
    session_uuid: str = Field(description='会话 UUID')
    user: MobileUserDetail = Field(description='用户信息')


class MobileNewToken(SchemaBase):
    """移动端刷新返回 Token"""

    access_token: str = Field(description='新的访问令牌')
    access_token_expire_time: datetime = Field(description='新的访问令牌过期时间')
    refresh_token: str = Field(description='新的刷新令牌')
    refresh_token_expire_time: datetime = Field(description='新的刷新令牌过期时间')
    session_uuid: str = Field(description='新的会话 UUID')
