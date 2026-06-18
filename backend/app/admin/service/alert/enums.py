"""告警相关枚举类型

为告警模块提供类型安全的枚举定义，替代模型中的字符串字段。
"""

from enum import Enum


class AlertMetricType(str, Enum):
    """告警指标类型"""

    CPU = 'cpu'
    MEMORY = 'memory'
    DISK = 'disk'
    TASK_SUCCESS = 'task_success'
    TASK_DELAY = 'task_delay'
    DATA_QUALITY = 'data_quality'


class AlertCondition(str, Enum):
    """告警条件"""

    GT = 'gt'  # 大于
    LT = 'lt'  # 小于
    EQ = 'eq'  # 等于
    GTE = 'gte'  # 大于等于
    LTE = 'lte'  # 小于等于


class AlertSeverity(str, Enum):
    """告警严重级别"""

    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


class AlertStatus(str, Enum):
    """告警状态"""

    FIRING = 'firing'
    RESOLVED = 'resolved'


class NotifyChannel(str, Enum):
    """通知渠道"""

    EMAIL = 'email'
    WEBHOOK = 'webhook'
    SMS = 'sms'
    SOCKETIO = 'socketio'