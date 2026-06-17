from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ExecuteQueryParam(SchemaBase):
    """执行查询参数"""

    dataset_id: int | None = Field(default=None, description='数据集 ID')
    query_sql: str | None = Field(default=None, description='查询 SQL')
    query_config: dict | None = Field(default=None, description='可视化查询配置(JSON)')
    query_type: str = Field(default='sql', max_length=16, description='查询类型(sql/visual)')
    limit: int = Field(default=100, ge=1, le=10000, description='结果限制行数')


class QueryResultSchema(SchemaBase):
    """查询结果模型"""

    columns: list[str] = Field(default_factory=list, description='列名列表')
    rows: list[list] = Field(default_factory=list, description='数据行列表')
    total: int = Field(default=0, description='总行数')
    duration: float = Field(default=0.0, description='执行耗时(秒)')
    status: str = Field(default='success', description='状态(success/failed)')
    error_message: str | None = Field(default=None, description='错误信息')


class QueryHistorySchemaBase(SchemaBase):
    """查询历史基础模型"""

    name: str | None = Field(default=None, max_length=128, description='查询名称')
    dataset_id: int | None = Field(default=None, description='数据集 ID')
    query_type: str = Field(default='sql', max_length=16, description='查询类型(sql/visual)')
    query_sql: str | None = Field(default=None, description='查询 SQL')
    query_config: dict | None = Field(default=None, description='可视化查询配置(JSON)')
    result_count: int = Field(default=0, description='结果行数')
    duration: float | None = Field(default=None, description='执行耗时(秒)')
    status: str = Field(default='success', max_length=16, description='状态(success/failed)')
    error_message: str | None = Field(default=None, description='错误信息')


class GetQueryHistoryDetail(QueryHistorySchemaBase):
    """查询历史详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='查询历史 ID')
    created_by: int | None = Field(default=None, description='执行者')
    created_time: datetime = Field(description='创建时间')


class SavedQuerySchemaBase(SchemaBase):
    """保存的查询基础模型"""

    name: str = Field(max_length=128, description='查询名称')
    description: str | None = Field(default=None, max_length=512, description='查询描述')
    dataset_id: int | None = Field(default=None, description='数据集 ID')
    query_type: str = Field(default='sql', max_length=16, description='查询类型(sql/visual)')
    query_sql: str | None = Field(default=None, description='查询 SQL')
    query_config: dict | None = Field(default=None, description='可视化查询配置(JSON)')
    tags: str | None = Field(default=None, max_length=256, description='标签(逗号分隔)')
    is_public: bool = Field(default=False, description='是否公开')


class CreateSavedQueryParam(SavedQuerySchemaBase):
    """创建保存的查询参数"""


class UpdateSavedQueryParam(SchemaBase):
    """更新保存的查询参数"""

    name: str | None = Field(default=None, max_length=128, description='查询名称')
    description: str | None = Field(default=None, max_length=512, description='查询描述')
    dataset_id: int | None = Field(default=None, description='数据集 ID')
    query_type: str | None = Field(default=None, max_length=16, description='查询类型(sql/visual)')
    query_sql: str | None = Field(default=None, description='查询 SQL')
    query_config: dict | None = Field(default=None, description='可视化查询配置(JSON)')
    tags: str | None = Field(default=None, max_length=256, description='标签(逗号分隔)')
    is_public: bool | None = Field(default=None, description='是否公开')


class GetSavedQueryDetail(SavedQuerySchemaBase):
    """保存的查询详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='保存的查询 ID')
    created_by: int | None = Field(default=None, description='创建者')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
