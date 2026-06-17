import sqlalchemy as sa

from backend.common.model import MappedBase, TimeZone
from backend.utils.timezone import timezone


class AlertRule(MappedBase):
    """告警规则表"""

    __tablename__ = 'sys_alert_rule'
    __table_args__ = {'comment': '告警规则表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(128), unique=True, comment='规则名称')
    description = sa.Column(sa.String(512), default=None, comment='规则描述')
    metric_type = sa.Column(sa.String(32), comment='指标类型(cpu/memory/disk/task_success/task_delay/data_quality)')
    condition = sa.Column(sa.String(16), comment='条件(gt/lt/eq/gte/lte)')
    threshold = sa.Column(sa.Float, comment='阈值')
    duration_seconds = sa.Column(sa.Integer, default=60, comment='持续时间(秒)')
    severity = sa.Column(sa.String(16), default='warning', comment='严重级别(info/warning/error/critical)')
    notify_channels = sa.Column(sa.JSON, default=None, comment='通知渠道(JSON数组: email/webhook/sms)')
    enabled = sa.Column(sa.Boolean, default=True, comment='是否启用')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')


class AlertHistory(MappedBase):
    """告警历史记录表"""

    __tablename__ = 'sys_alert_history'
    __table_args__ = {'comment': '告警历史记录表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    rule_id = sa.Column(sa.BigInteger, index=True, comment='规则 ID')
    rule_name = sa.Column(sa.String(128), default=None, comment='规则名称')
    metric_value = sa.Column(sa.Float, default=None, comment='指标值')
    threshold = sa.Column(sa.Float, default=None, comment='阈值')
    severity = sa.Column(sa.String(16), comment='严重级别')
    status = sa.Column(sa.String(16), default='firing', comment='状态(firing/resolved)')
    message = sa.Column(sa.Text, default=None, comment='告警消息')
    notify_result = sa.Column(sa.JSON, default=None, comment='通知结果(JSON)')
    fired_time = sa.Column(TimeZone, comment='触发时间')
    resolved_time = sa.Column(TimeZone, default=None, comment='恢复时间')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
