from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class AuditLogSchemaBase(SchemaBase):
    """审计日志基础模型"""

    event_type: str = Field(max_length=32, description='事件类型')
    action: str = Field(max_length=64, description='操作动作')
    resource_type: str | None = Field(default=None, max_length=32, description='资源类型')
    resource_id: int | None = Field(default=None, description='资源 ID')
    resource_name: str | None = Field(default=None, max_length=128, description='资源名称')
    user_id: int | None = Field(default=None, description='用户 ID')
    username: str | None = Field(default=None, max_length=64, description='用户名')
    ip: str | None = Field(default=None, max_length=64, description='IP 地址')
    user_agent: str | None = Field(default=None, max_length=512, description='User Agent')
    request_method: str | None = Field(default=None, max_length=16, description='请求方法')
    request_path: str | None = Field(default=None, max_length=256, description='请求路径')
    request_body: str | None = Field(default=None, description='请求体')
    response_code: int | None = Field(default=None, description='响应码')
    detail: dict | None = Field(default=None, description='详细信息(JSON)')
    status: int = Field(default=1, description='状态(0失败 1成功)')


class CreateAuditLogParam(AuditLogSchemaBase):
    """创建审计日志参数"""


class DeleteAuditLogParam(SchemaBase):
    """删除审计日志参数"""

    pks: list[int] = Field(description='审计日志 ID 列表')


class GetAuditLogDetail(AuditLogSchemaBase):
    """审计日志详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='日志 ID')
    created_time: datetime = Field(description='创建时间')
