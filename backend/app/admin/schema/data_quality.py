from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class QualityRuleSchemaBase(SchemaBase):
    """数据质量规则基础模型"""

    name: str = Field(max_length=128, description='规则名称')
    description: str | None = Field(default=None, max_length=512, description='规则描述')
    rule_type: str = Field(max_length=32, description='规则类型(not_null/unique/range/regex/custom_sql)')
    target_table: str | None = Field(default=None, max_length=128, description='目标表名')
    target_field: str | None = Field(default=None, max_length=128, description='目标字段名')
    rule_config: dict | None = Field(default=None, description='规则配置(JSON)')
    severity: str = Field(default='warning', max_length=16, description='严重级别(info/warning/error/critical)')
    enabled: bool = Field(default=True, description='是否启用')


class CreateQualityRuleParam(QualityRuleSchemaBase):
    """创建数据质量规则参数"""


class UpdateQualityRuleParam(SchemaBase):
    """更新数据质量规则参数"""

    name: str | None = Field(default=None, max_length=128, description='规则名称')
    description: str | None = Field(default=None, max_length=512, description='规则描述')
    rule_type: str | None = Field(default=None, max_length=32, description='规则类型(not_null/unique/range/regex/custom_sql)')
    target_table: str | None = Field(default=None, max_length=128, description='目标表名')
    target_field: str | None = Field(default=None, max_length=128, description='目标字段名')
    rule_config: dict | None = Field(default=None, description='规则配置(JSON)')
    severity: str | None = Field(default=None, max_length=16, description='严重级别(info/warning/error/critical)')
    enabled: bool | None = Field(default=None, description='是否启用')


class GetQualityRuleDetail(QualityRuleSchemaBase):
    """数据质量规则详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='规则 ID')
    enabled: bool = Field(description='是否启用')
    status: int = Field(description='状态(0停用 1正常)')
    created_by: int | None = Field(None, description='创建者')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class QualityCheckSchemaBase(SchemaBase):
    """数据质量检查基础模型"""

    rule_id: int = Field(description='规则 ID')
    run_id: str = Field(max_length=64, description='运行批次 ID')
    status: str = Field(max_length=16, description='状态(running/success/failed)')
    start_time: datetime = Field(description='开始时间')
    end_time: datetime | None = Field(default=None, description='结束时间')
    duration: float | None = Field(default=None, description='耗时(秒)')
    total_checked: int = Field(default=0, description='检查总数')
    total_passed: int = Field(default=0, description='通过数')
    total_failed: int = Field(default=0, description='失败数')
    score: float | None = Field(default=None, description='质量评分(0-100)')
    error_message: str | None = Field(default=None, description='错误信息')


class GetQualityCheckDetail(QualityCheckSchemaBase):
    """数据质量检查详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='检查 ID')
    created_time: datetime = Field(description='创建时间')
