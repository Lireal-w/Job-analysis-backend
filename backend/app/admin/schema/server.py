from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.enums import ProtocolType
from backend.common.schema import SchemaBase

# 协议默认端口映射
PROTOCOL_DEFAULT_PORTS: dict[ProtocolType, int] = {
    ProtocolType.SSH: 22,
    ProtocolType.RDP: 3389,
    ProtocolType.VNC: 5900,
    ProtocolType.TELNET: 23,
    ProtocolType.SFTP: 22,
    ProtocolType.HTTP: 80,
    ProtocolType.HTTPS: 443,
}


class ServerSchemaBase(SchemaBase):
    """服务器基础模型"""

    name: str = Field(max_length=128, description='服务器名称')
    host: str = Field(max_length=256, description='主机地址')
    port: int = Field(default=22, description='端口号')
    protocol: ProtocolType = Field(default=ProtocolType.SSH, description='协议类型')
    username: str | None = Field(default=None, max_length=128, description='用户名')
    password: str | None = Field(default=None, max_length=512, description='密码')
    ssh_key: str | None = Field(default=None, description='SSH 密钥')
    description: str | None = Field(default=None, max_length=256, description='描述')


class CreateServerParam(ServerSchemaBase):
    """创建服务器参数"""


class UpdateServerParam(ServerSchemaBase):
    """更新服务器参数"""


class GetServerDetail(ServerSchemaBase):
    """服务器详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='服务器 ID')
    status: int = Field(description='状态(0停用 1正常)')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class TestConnectionParam(SchemaBase):
    """测试连接参数"""

    host: str = Field(max_length=256, description='主机地址')
    port: int = Field(default=22, description='端口号')
    protocol: ProtocolType = Field(default=ProtocolType.SSH, description='协议类型')
    username: str | None = Field(default=None, max_length=128, description='用户名')
    password: str | None = Field(default=None, max_length=512, description='密码')
    ssh_key: str | None = Field(default=None, description='SSH 密钥')
