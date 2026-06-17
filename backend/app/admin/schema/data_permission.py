from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ResourcePermissionSchemaBase(SchemaBase):
    """资源权限基础模型"""

    name: str = Field(max_length=128, description='权限名称')
    resource_type: str = Field(max_length=32, description='资源类型(datasource/table/field/report/dataset)')
    resource_id: int | None = Field(default=None, description='资源 ID')
    resource_name: str | None = Field(default=None, max_length=128, description='资源名称')
    permission_type: str = Field(max_length=16, description='权限类型(read/write/admin)')
    role_id: int | None = Field(default=None, description='角色 ID')
    description: str | None = Field(default=None, max_length=256, description='描述')
    enabled: bool = Field(default=True, description='是否启用')


class CreateResourcePermissionParam(ResourcePermissionSchemaBase):
    """创建资源权限参数"""


class UpdateResourcePermissionParam(SchemaBase):
    """更新资源权限参数"""

    name: str | None = Field(default=None, max_length=128, description='权限名称')
    resource_type: str | None = Field(default=None, max_length=32, description='资源类型')
    resource_id: int | None = Field(default=None, description='资源 ID')
    resource_name: str | None = Field(default=None, max_length=128, description='资源名称')
    permission_type: str | None = Field(default=None, max_length=16, description='权限类型')
    role_id: int | None = Field(default=None, description='角色 ID')
    description: str | None = Field(default=None, max_length=256, description='描述')
    enabled: bool | None = Field(default=None, description='是否启用')


class GetResourcePermissionDetail(ResourcePermissionSchemaBase):
    """资源权限详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='权限 ID')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class DataMaskingRuleSchemaBase(SchemaBase):
    """数据脱敏规则基础模型"""

    name: str = Field(max_length=128, description='规则名称')
    mask_type: str = Field(max_length=32, description='脱敏类型(mask/truncate/hash/generalize)')
    target_table: str | None = Field(default=None, max_length=128, description='目标表名')
    target_field: str | None = Field(default=None, max_length=128, description='目标字段名')
    mask_config: dict | None = Field(default=None, description='脱敏配置(JSON)')
    enabled: bool = Field(default=True, description='是否启用')


class CreateDataMaskingRuleParam(DataMaskingRuleSchemaBase):
    """创建数据脱敏规则参数"""


class UpdateDataMaskingRuleParam(SchemaBase):
    """更新数据脱敏规则参数"""

    name: str | None = Field(default=None, max_length=128, description='规则名称')
    mask_type: str | None = Field(default=None, max_length=32, description='脱敏类型')
    target_table: str | None = Field(default=None, max_length=128, description='目标表名')
    target_field: str | None = Field(default=None, max_length=128, description='目标字段名')
    mask_config: dict | None = Field(default=None, description='脱敏配置(JSON)')
    enabled: bool | None = Field(default=None, description='是否启用')


class GetDataMaskingRuleDetail(DataMaskingRuleSchemaBase):
    """数据脱敏规则详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='规则 ID')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
