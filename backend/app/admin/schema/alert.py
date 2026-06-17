from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class AlertRuleSchemaBase(SchemaBase):
    """告警规则基础模型"""

    name: str = Field(max_length=128, description='规则名称')
    description: str | None = Field(default=None, max_length=512, description='规则描述')
    metric_type: str = Field(max_length=32, description='指标类型')
    condition: str = Field(max_length=16, description='条件(gt/lt/eq/gte/lte)')
    threshold: float = Field(description='阈值')
    duration_seconds: int = Field(default=60, description='持续时间(秒)')
    severity: str = Field(default='warning', max_length=16, description='严重级别')
    notify_channels: list | None = Field(default=None, description='通知渠道(JSON数组)')
    enabled: bool = Field(default=True, description='是否启用')


class CreateAlertRuleParam(AlertRuleSchemaBase):
    """创建告警规则参数"""


class UpdateAlertRuleParam(SchemaBase):
    """更新告警规则参数"""

    name: str | None = Field(default=None, max_length=128, description='规则名称')
    description: str | None = Field(default=None, max_length=512, description='规则描述')
    metric_type: str | None = Field(default=None, max_length=32, description='指标类型')
    condition: str | None = Field(default=None, max_length=16, description='条件')
    threshold: float | None = Field(default=None, description='阈值')
    duration_seconds: int | None = Field(default=None, description='持续时间(秒)')
    severity: str | None = Field(default=None, max_length=16, description='严重级别')
    notify_channels: list | None = Field(default=None, description='通知渠道(JSON数组)')
    enabled: bool | None = Field(default=None, description='是否启用')


class GetAlertRuleDetail(AlertRuleSchemaBase):
    """告警规则详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='规则 ID')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class AlertHistorySchemaBase(SchemaBase):
    """告警历史基础模型"""

    rule_id: int = Field(description='规则 ID')
    rule_name: str | None = Field(default=None, max_length=128, description='规则名称')
    metric_value: float | None = Field(default=None, description='指标值')
    threshold: float | None = Field(default=None, description='阈值')
    severity: str = Field(max_length=16, description='严重级别')
    status: str = Field(default='firing', max_length=16, description='状态(firing/resolved)')
    message: str | None = Field(default=None, description='告警消息')
    notify_result: dict | None = Field(default=None, description='通知结果(JSON)')
    fired_time: datetime = Field(description='触发时间')
    resolved_time: datetime | None = Field(default=None, description='恢复时间')


class CreateAlertHistoryParam(AlertHistorySchemaBase):
    """创建告警历史参数"""


class GetAlertHistoryDetail(AlertHistorySchemaBase):
    """告警历史详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='历史 ID')
    created_time: datetime = Field(description='创建时间')
