from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ApiKeySchemaBase(SchemaBase):
    """API 密钥基础模型"""

    name: str = Field(max_length=128, description='密钥名称')
    permissions: str | None = Field(default=None, description='权限标识列表(JSON 数组)')
    is_active: int = Field(default=1, description='状态(0禁用 1启用)')
    expires_at: str | None = Field(default=None, description='过期时间')
    description: str | None = Field(default=None, max_length=256, description='描述')


class CreateApiKeyParam(ApiKeySchemaBase):
    """创建 API 密钥参数"""


class UpdateApiKeyParam(SchemaBase):
    """更新 API 密钥参数"""

    name: str | None = Field(default=None, max_length=128, description='密钥名称')
    permissions: str | None = Field(default=None, description='权限标识列表(JSON 数组)')
    is_active: int | None = Field(default=None, description='状态(0禁用 1启用)')
    expires_at: str | None = Field(default=None, description='过期时间')
    description: str | None = Field(default=None, max_length=256, description='描述')


class GetApiKeyDetail(SchemaBase):
    """API 密钥详情（不含完整 key）"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='主键 ID')
    name: str = Field(description='密钥名称')
    key_prefix: str = Field(description='密钥前缀')
    user_id: int = Field(description='创建者用户 ID')
    permissions: str | None = Field(None, description='权限标识列表')
    is_active: int = Field(description='状态')
    expires_at: datetime | None = Field(None, description='过期时间')
    last_used_at: datetime | None = Field(None, description='最后使用时间')
    description: str | None = Field(None, description='描述')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class CreateApiKeyResponse(SchemaBase):
    """创建 API 密钥响应（含完整 key，仅展示一次）"""

    id: int = Field(description='主键 ID')
    name: str = Field(description='密钥名称')
    api_key: str = Field(description='完整 API 密钥(请妥善保管，仅在此处展示一次)')
    key_prefix: str = Field(description='密钥前缀')
    permissions: str | None = Field(None, description='权限标识列表')
    is_active: int = Field(description='状态')
    expires_at: str | None = Field(None, description='过期时间')
    description: str | None = Field(None, description='描述')
    created_time: datetime = Field(description='创建时间')


class RegenerateApiKeyResponse(SchemaBase):
    """重新生成 API 密钥响应"""

    id: int = Field(description='主键 ID')
    api_key: str = Field(description='新的完整 API 密钥(请妥善保管)')
