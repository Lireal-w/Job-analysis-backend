from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ReportSchemaBase(SchemaBase):
    """报表基础模型"""

    name: str = Field(max_length=128, description='报表名称')
    description: str | None = Field(default=None, max_length=512, description='报表描述')
    layout: list | None = Field(default=None, description='布局配置(JSON数组)')
    theme: str = Field(default='default', max_length=32, description='主题(default/dark/colorful)')
    refresh_interval: int | None = Field(default=None, description='自动刷新间隔(秒)')
    is_public: bool = Field(default=False, description='是否公开')
    status: int = Field(default=1, description='状态(0停用 1正常)')


class CreateReportParam(ReportSchemaBase):
    """创建报表参数"""


class UpdateReportParam(SchemaBase):
    """更新报表参数"""

    name: str | None = Field(default=None, max_length=128, description='报表名称')
    description: str | None = Field(default=None, max_length=512, description='报表描述')
    layout: list | None = Field(default=None, description='布局配置(JSON数组)')
    theme: str | None = Field(default=None, max_length=32, description='主题(default/dark/colorful)')
    refresh_interval: int | None = Field(default=None, description='自动刷新间隔(秒)')
    is_public: bool | None = Field(default=None, description='是否公开')
    status: int | None = Field(default=None, description='状态(0停用 1正常)')


class GetReportDetail(ReportSchemaBase):
    """报表详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='报表 ID')
    created_by: int | None = Field(default=None, description='创建者')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class ReportWidgetSchemaBase(SchemaBase):
    """报表组件基础模型"""

    widget_type: str = Field(max_length=32, description='组件类型(bar/line/pie/scatter/area/table/stat/map/heatmap/radar/funnel/gauge)')
    title: str | None = Field(default=None, max_length=128, description='组件标题')
    query_id: int | None = Field(default=None, description='关联查询 ID')
    query_sql: str | None = Field(default=None, description='查询 SQL')
    config: dict | None = Field(default=None, description='组件配置(JSON)')
    position: dict | None = Field(default=None, description='位置配置(JSON: x/y/w/h)')
    sort: int = Field(default=0, description='排序')


class CreateReportWidgetParam(ReportWidgetSchemaBase):
    """创建报表组件参数"""

    report_id: int = Field(description='报表 ID')


class UpdateReportWidgetParam(SchemaBase):
    """更新报表组件参数"""

    widget_type: str | None = Field(default=None, max_length=32, description='组件类型')
    title: str | None = Field(default=None, max_length=128, description='组件标题')
    query_id: int | None = Field(default=None, description='关联查询 ID')
    query_sql: str | None = Field(default=None, description='查询 SQL')
    config: dict | None = Field(default=None, description='组件配置(JSON)')
    position: dict | None = Field(default=None, description='位置配置(JSON: x/y/w/h)')
    sort: int | None = Field(default=None, description='排序')


class GetReportWidgetDetail(ReportWidgetSchemaBase):
    """报表组件详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='组件 ID')
    report_id: int = Field(description='报表 ID')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
