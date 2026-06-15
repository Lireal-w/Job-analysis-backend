from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class SSHSchemaBase(SchemaBase):
    """SSH 服务器基础模型"""

    name: str = Field(max_length=128, description='服务器名称')
    host: str = Field(max_length=256, description='主机地址')
    port: int = Field(default=22, description='端口号')
    username: str = Field(max_length=128, description='用户名')
    password: str | None = Field(default=None, max_length=512, description='密码')
    ssh_key: str | None = Field(default=None, description='SSH 密钥')
    description: str | None = Field(default=None, max_length=256, description='描述')


class CreateSSHParam(SSHSchemaBase):
    """创建 SSH 服务器参数"""


class UpdateSSHParam(SSHSchemaBase):
    """更新 SSH 服务器参数"""


class GetSSHDetail(SSHSchemaBase):
    """SSH 服务器详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='服务器 ID')
    status: int = Field(description='状态(0停用 1正常)')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class SSHToggleStatusParam(SchemaBase):
    """切换 SSH 服务器状态参数"""

    status: int = Field(description='状态(0停用 1正常)')


class SSHTestConnectionParam(SchemaBase):
    """测试 SSH 连接参数"""

    host: str = Field(max_length=256, description='主机地址')
    port: int = Field(default=22, description='端口号')
    username: str = Field(max_length=128, description='用户名')
    password: str | None = Field(default=None, max_length=512, description='密码')
    ssh_key: str | None = Field(default=None, description='SSH 密钥')
