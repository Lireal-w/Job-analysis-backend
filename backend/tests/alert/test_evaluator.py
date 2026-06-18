"""告警评估器测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.app.admin.service.alert.enums import (
    AlertCondition,
    AlertMetricType,
    AlertSeverity,
    AlertStatus,
    NotifyChannel,
)
from backend.app.admin.service.alert.evaluator import (
    AlertEvaluator,
    AlertEvaluationResult,
    MetricValue,
    evaluate_alert_rule,
)


class TestAlertEnums:
    """告警枚举测试"""

    def test_metric_types(self):
        assert AlertMetricType.CPU.value == 'cpu'
        assert AlertMetricType.MEMORY.value == 'memory'
        assert AlertMetricType.DISK.value == 'disk'
        assert AlertMetricType.TASK_SUCCESS.value == 'task_success'
        assert AlertMetricType.TASK_DELAY.value == 'task_delay'
        assert AlertMetricType.DATA_QUALITY.value == 'data_quality'

    def test_conditions(self):
        assert AlertCondition.GT.value == 'gt'
        assert AlertCondition.LT.value == 'lt'
        assert AlertCondition.EQ.value == 'eq'
        assert AlertCondition.GTE.value == 'gte'
        assert AlertCondition.LTE.value == 'lte'

    def test_severities(self):
        assert AlertSeverity.INFO.value == 'info'
        assert AlertSeverity.WARNING.value == 'warning'
        assert AlertSeverity.ERROR.value == 'error'
        assert AlertSeverity.CRITICAL.value == 'critical'

    def test_statuses(self):
        assert AlertStatus.FIRING.value == 'firing'
        assert AlertStatus.RESOLVED.value == 'resolved'

    def test_notify_channels(self):
        assert NotifyChannel.EMAIL.value == 'email'
        assert NotifyChannel.WEBHOOK.value == 'webhook'
        assert NotifyChannel.SMS.value == 'sms'
        assert NotifyChannel.SOCKETIO.value == 'socketio'


class TestMetricValue:
    """MetricValue 测试"""

    def test_default_values(self):
        mv = MetricValue(value=85.5)
        assert mv.value == 85.5
        assert mv.timestamp is None
        assert mv.source == ''

    def test_custom_values(self):
        now = datetime.now()
        mv = MetricValue(value=92.3, timestamp=now, source='redis')
        assert mv.value == 92.3
        assert mv.timestamp == now
        assert mv.source == 'redis'


class TestAlertEvaluationResult:
    """AlertEvaluationResult 测试"""

    def test_default_values(self):
        result = AlertEvaluationResult()
        assert result.triggered is False
        assert result.metric_value is None
        assert result.threshold is None
        assert result.condition == ''
        assert result.severity == AlertSeverity.WARNING.value
        assert result.message == ''
        assert result.details == {}

    def test_triggered_result(self):
        result = AlertEvaluationResult(
            triggered=True,
            metric_value=95.0,
            threshold=80.0,
            condition='gt',
            severity='critical',
            message='CPU 使用率超过阈值',
            details={'rule_id': 1},
        )
        assert result.triggered is True
        assert result.metric_value == 95.0
        assert result.threshold == 80.0


class TestAlertEvaluatorEvaluateCondition:
    """告警条件评估测试"""

    def test_gt_condition(self):
        assert AlertEvaluator._evaluate_condition(95, 'gt', 80) is True
        assert AlertEvaluator._evaluate_condition(75, 'gt', 80) is False
        assert AlertEvaluator._evaluate_condition(80, 'gt', 80) is False

    def test_lt_condition(self):
        assert AlertEvaluator._evaluate_condition(75, 'lt', 80) is True
        assert AlertEvaluator._evaluate_condition(95, 'lt', 80) is False
        assert AlertEvaluator._evaluate_condition(80, 'lt', 80) is False

    def test_eq_condition(self):
        assert AlertEvaluator._evaluate_condition(80, 'eq', 80) is True
        assert AlertEvaluator._evaluate_condition(81, 'eq', 80) is False

    def test_gte_condition(self):
        assert AlertEvaluator._evaluate_condition(80, 'gte', 80) is True
        assert AlertEvaluator._evaluate_condition(81, 'gte', 80) is True
        assert AlertEvaluator._evaluate_condition(79, 'gte', 80) is False

    def test_lte_condition(self):
        assert AlertEvaluator._evaluate_condition(80, 'lte', 80) is True
        assert AlertEvaluator._evaluate_condition(79, 'lte', 80) is True
        assert AlertEvaluator._evaluate_condition(81, 'lte', 80) is False

    def test_unknown_condition(self):
        assert AlertEvaluator._evaluate_condition(80, 'unknown', 80) is False


class TestAlertEvaluatorBuildMessage:
    """告警消息构建测试"""

    def test_triggered_message(self):
        rule = MagicMock(
            name='CPU 使用率告警',
            metric_type='cpu',
            condition='gt',
            threshold=80.0,
            severity='warning',
        )
        msg = AlertEvaluator._build_message(rule, 95.0, triggered=True)
        assert '告警触发' in msg
        assert '95.0' in msg
        assert '大于' in msg
        assert '80.0' in msg

    def test_normal_message(self):
        rule = MagicMock(
            name='CPU 使用率告警',
            metric_type='cpu',
            condition='gt',
            threshold=80.0,
            severity='warning',
        )
        msg = AlertEvaluator._build_message(rule, 75.0, triggered=False)
        assert '指标正常' in msg
        assert '75.0' in msg


class TestAlertEvaluatorEvaluate:
    """告警评估器完整评估测试"""

    @pytest.fixture
    def mock_rule(self):
        rule = MagicMock()
        rule.id = 1
        rule.name = 'CPU 使用率告警'
        rule.metric_type = 'cpu'
        rule.condition = 'gt'
        rule.threshold = 80.0
        rule.severity = 'warning'
        rule.enabled = True
        rule.duration_seconds = 60
        rule.notify_channels = ['socketio']
        return rule

    @pytest.mark.asyncio
    async def test_evaluate_triggered(self, mock_rule):
        evaluator = AlertEvaluator()
        result = await evaluator.evaluate(mock_rule, metric_value=95.0)
        assert result.triggered is True
        assert result.metric_value == 95.0
        assert result.threshold == 80.0
        assert result.condition == 'gt'

    @pytest.mark.asyncio
    async def test_evaluate_not_triggered(self, mock_rule):
        evaluator = AlertEvaluator()
        result = await evaluator.evaluate(mock_rule, metric_value=75.0)
        assert result.triggered is False
        assert result.metric_value == 75.0

    @pytest.mark.asyncio
    async def test_evaluate_disabled_rule(self, mock_rule):
        mock_rule.enabled = False
        evaluator = AlertEvaluator()
        result = await evaluator.evaluate(mock_rule, metric_value=95.0)
        assert result.triggered is False
        assert '禁用' in result.message

    @pytest.mark.asyncio
    async def test_evaluate_with_metric_values(self, mock_rule):
        evaluator = AlertEvaluator()
        values = [
            MetricValue(value=70.0, timestamp=datetime.now()),
            MetricValue(value=85.0, timestamp=datetime.now()),
            MetricValue(value=95.0, timestamp=datetime.now()),
        ]
        result = await evaluator.evaluate(mock_rule, metric_values=values)
        assert result.triggered is True
        assert result.metric_value == 95.0  # 使用最新值

    @pytest.mark.asyncio
    async def test_evaluate_lt_condition(self, mock_rule):
        mock_rule.condition = 'lt'
        mock_rule.threshold = 50.0
        evaluator = AlertEvaluator()
        result = await evaluator.evaluate(mock_rule, metric_value=30.0)
        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_evaluate_data_quality_condition(self, mock_rule):
        mock_rule.metric_type = 'data_quality'
        mock_rule.condition = 'lt'
        mock_rule.threshold = 60.0
        evaluator = AlertEvaluator()
        result = await evaluator.evaluate(mock_rule, metric_value=45.0)
        assert result.triggered is True
        assert result.metric_value == 45.0