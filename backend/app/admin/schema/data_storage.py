from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class DataLayerSchemaBase(SchemaBase):
    """数据分层基础模型"""

    name: str = Field(max_length=64, description='层级名称')
    layer_type: str = Field(max_length=16, description='层级类型(ODS/DWD/DWS/ADS)')
    description: str | None = Field(default=None, max_length=256, description='层级描述')
    sort: int = Field(default=0, description='排序')


class CreateDataLayerParam(DataLayerSchemaBase):
    """创建数据分层参数"""


class UpdateDataLayerParam(SchemaBase):
    """更新数据分层参数"""

    name: str | None = Field(default=None, max_length=64, description='层级名称')
    layer_type: str | None = Field(default=None, max_length=16, description='层级类型(ODS/DWD/DWS/ADS)')
    description: str | None = Field(default=None, max_length=256, description='层级描述')
    sort: int | None = Field(default=None, description='排序')


class GetDataLayerDetail(DataLayerSchemaBase):
    """数据分层详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='分层 ID')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class DatasetSchemaBase(SchemaBase):
    """数据集基础模型"""

    name: str = Field(max_length=128, description='数据集名称')
    description: str | None = Field(default=None, max_length=512, description='数据集描述')
    layer_id: int | None = Field(default=None, description='所属数据层 ID')
    schema_config: dict | None = Field(default=None, description='Schema 配置(JSON)')
    source_type: str | None = Field(default=None, max_length=32, description='数据来源类型(datasource/flow/manual)')
    source_id: int | None = Field(default=None, description='数据来源 ID')
    dept_id: int | None = Field(default=None, description='所属部门 ID')
    lifecycle_days: int | None = Field(default=None, description='生命周期(天)')


class CreateDatasetParam(DatasetSchemaBase):
    """创建数据集参数"""


class UpdateDatasetParam(SchemaBase):
    """更新数据集参数"""

    name: str | None = Field(default=None, max_length=128, description='数据集名称')
    description: str | None = Field(default=None, max_length=512, description='数据集描述')
    layer_id: int | None = Field(default=None, description='所属数据层 ID')
    schema_config: dict | None = Field(default=None, description='Schema 配置(JSON)')
    source_type: str | None = Field(default=None, max_length=32, description='数据来源类型(datasource/flow/manual)')
    source_id: int | None = Field(default=None, description='数据来源 ID')
    dept_id: int | None = Field(default=None, description='所属部门 ID')
    record_count: int | None = Field(default=None, description='记录数')
    storage_size: int | None = Field(default=None, description='存储大小(字节)')
    lifecycle_days: int | None = Field(default=None, description='生命周期(天)')
    status: int | None = Field(default=None, description='状态(0停用 1正常)')


class GetDatasetDetail(DatasetSchemaBase):
    """数据集详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='数据集 ID')
    record_count: int = Field(default=0, description='记录数')
    storage_size: int = Field(default=0, description='存储大小(字节)')
    status: int = Field(description='状态(0停用 1正常)')
    created_by: int | None = Field(default=None, description='创建者')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
