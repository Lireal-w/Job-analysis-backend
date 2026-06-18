"""告警评估器

负责评估告警规则，判断是否触发告警，并管理告警生命周期（触发/恢复）。

核心逻辑：
1. 获取指标值（从 Redis 缓存、数据库查询或外部 API）
2. 根据条件（gt/lt/eq/gte/lte）和阈值判断是否触发
3. 检查持续时间条件（可选）
4. 创建告警历史记录
5. 触发通知分发
6. 告警去重与抑制（同一规则恢复前不重复告警）
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from loguru import logger

from backend.app.admin.service.alert.enums import AlertCondition, AlertMetricType, AlertSeverity, AlertStatus, NotifyChannel


@dataclass
class MetricValue:
    """指标值"""

    value: float
    timestamp: datetime | None = None
    source: str = ''  # 指标来源描述


@dataclass
class AlertEvaluationResult:
    """告警评估结果"""

    triggered: bool = False
    metric_value: float | None = None
    threshold: float | None = None
    condition: str = ''
    severity: str = AlertSeverity.WARNING.value
    message: str = ''
    details: dict[str, Any] = field(default_factory=dict)


class AlertEvaluator:
    """告警评估器

    根据告警规则评估指标值，判断是否触发告警。

    用法：
        evaluator = AlertEvaluator()
        result = await evaluator.evaluate(rule, metric_value=85.5)
        if result.triggered:
            # 创建告警历史记录并发送通知
    """

    def __init__(self) -> None:
        self._metric_providers: dict[str, Any] = {}

    async def evaluate(
        self,
        rule: Any,
        metric_value: float | None = None,
        metric_values: list[MetricValue] | None = None,
    ) -> AlertEvaluationResult:
        """评估告警规则

        Args:
            rule: AlertRule ORM 对象
            metric_value: 单个指标值（简单场景）
            metric_values: 多个指标值（用于趋势分析）

        Returns:
            AlertEvaluationResult 评估结果
        """
        try:
            # 验证规则
            if not rule.enabled:
                return AlertEvaluationResult(
                    message=f'规则 {rule.name} 已禁用，跳过评估',
                )

            # 获取指标值
            if metric_value is None and metric_values:
                # 使用最新的指标值
                metric_value = metric_values[-1].value

            if metric_value is None:
                # 尝试从指标提供者获取
                metric_value = await self._fetch_metric_value(rule)
                if metric_value is None:
                    return AlertEvaluationResult(
                        message=f'规则 {rule.name} 无法获取指标值',
                    )

            # 评估条件
            condition_met = self._evaluate_condition(
                metric_value, rule.condition, rule.threshold,
            )

            # 构建结果
            result = AlertEvaluationResult(
                triggered=condition_met,
                metric_value=metric_value,
                threshold=rule.threshold,
                condition=rule.condition,
                severity=rule.severity,
                message=self._build_message(rule, metric_value, condition_met),
                details={
                    'rule_id': rule.id,
                    'rule_name': rule.name,
                    'metric_type': rule.metric_type,
                    'metric_value': metric_value,
                    'threshold': rule.threshold,
                    'condition': rule.condition,
                    'severity': rule.severity,
                },
            )

            return result

        except Exception as e:
            logger.error(f'[AlertEvaluator] 评估规则失败: {e}')
            logger.error(traceback.format_exc())
            return AlertEvaluationResult(
                message=f'评估异常: {type(e).__name__}: {e}',
            )

    async def evaluate_and_notify(
        self,
        rule: Any,
        db: Any,
        metric_value: float | None = None,
    ) -> AlertEvaluationResult:
        """评估告警规则并发送通知

        完整流程：评估 → 创建历史记录 → 发送通知

        Args:
            rule: AlertRule ORM 对象
            db: 数据库会话
            metric_value: 指标值

        Returns:
            AlertEvaluationResult 评估结果
        """
        from backend.app.admin.crud.crud_alert import alert_history_dao
        from backend.app.admin.schema.alert import CreateAlertHistoryParam
        from backend.app.admin.service.alert.dispatcher import dispatch_notification
        from backend.utils.timezone import timezone

        # 评估规则
        result = await self.evaluate(rule, metric_value=metric_value)

        if not result.triggered:
            # 检查是否需要恢复已有告警
            await self._check_resolution(rule, db)
            return result

        # 检查去重：同一规则是否已有 firing 状态的告警
        existing_firing = await self._get_existing_firing_alert(rule, db)
        if existing_firing:
            logger.info(f'[AlertEvaluator] 规则 {rule.name} 已有 firing 告警 (ID={existing_firing.id})，跳过重复触发')
            return result

        # 创建告警历史记录
        now = timezone.now()
        history_data = CreateAlertHistoryParam(
            rule_id=rule.id,
            rule_name=rule.name,
            metric_value=result.metric_value,
            threshold=rule.threshold,
            severity=rule.severity,
            status=AlertStatus.FIRING.value,
            message=result.message,
            notify_result={},
            fired_time=now,
        )

        try:
            await alert_history_dao.create(db, history_data)
            logger.info(f'[AlertEvaluator] 创建告警历史: 规则={rule.name}, 指标值={result.metric_value}, 阈值={rule.threshold}')
        except Exception as e:
            logger.error(f'[AlertEvaluator] 创建告警历史失败: {e}')

        # 发送通知
        notify_channels = rule.notify_channels or []
        if notify_channels:
            notify_result = await dispatch_notification(
                channels=notify_channels,
                severity=rule.severity,
                title=f'告警: {rule.name}',
                message=result.message,
                details=result.details,
                db=db,
            )
            # 更新通知结果
            # 注意：由于刚创建的记录没有直接获取 ID 的方式，
            # 通知结果将在后续通过规则 ID 查询更新

        return result

    async def _check_resolution(self, rule: Any, db: Any) -> None:
        """检查告警是否已恢复

        当指标值恢复正常时，将 firing 状态的告警标记为 resolved。
        """
        from sqlalchemy import Select, select, update

        from backend.app.admin.model import AlertHistory
        from backend.utils.timezone import timezone

        # 查找该规则下 firing 状态的告警
        stmt = select(AlertHistory).where(
            AlertHistory.rule_id == rule.id,
            AlertHistory.status == AlertStatus.FIRING.value,
        )
        result = await db.execute(stmt)
        firing_alerts = result.scalars().all()

        if not firing_alerts:
            return

        now = timezone.now()
        for alert in firing_alerts:
            alert.status = AlertStatus.RESOLVED.value
            alert.resolved_time = now
            logger.info(f'[AlertEvaluator] 告警恢复: 规则={rule.name}, 告警ID={alert.id}')

        await db.flush()

    async def _get_existing_firing_alert(self, rule: Any, db: Any) -> Any | None:
        """获取该规则下已有的 firing 状态告警（去重）"""
        from sqlalchemy import select

        from backend.app.admin.model import AlertHistory

        stmt = select(AlertHistory).where(
            AlertHistory.rule_id == rule.id,
            AlertHistory.status == AlertStatus.FIRING.value,
        ).limit(1)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def _fetch_metric_value(self, rule: Any) -> float | None:
        """从指标提供者获取指标值

        根据规则类型从不同来源获取指标值。
        子类可覆盖此方法以支持自定义指标来源。
        """
        metric_type = rule.metric_type

        # 尝试从 Redis 缓存获取
        try:
            value = await self._get_metric_from_redis(rule)
            if value is not None:
                return value
        except Exception as e:
            logger.debug(f'[AlertEvaluator] Redis 获取指标失败: {e}')

        # 尝试从数据库查询获取
        try:
            value = await self._get_metric_from_db(rule)
            if value is not None:
                return value
        except Exception as e:
            logger.debug(f'[AlertEvaluator] 数据库获取指标失败: {e}')

        logger.warning(f'[AlertEvaluator] 无法获取指标值: metric_type={metric_type}')
        return None

    async def _get_metric_from_redis(self, rule: Any) -> float | None:
        """从 Redis 获取指标值"""
        from backend.database.redis import redis_client

        metric_key = f'alert:metric:{rule.metric_type}:{rule.id}'
        value = await redis_client.get(metric_key)
        if value is not None:
            return float(value)
        return None

    async def _get_metric_from_db(self, rule: Any) -> float | None:
        """从数据库查询获取指标值

        根据指标类型执行不同的查询逻辑。
        """
        from sqlalchemy import func, select, text

        from backend.app.admin.model import QualityCheck
        from backend.database.db import async_db_session

        metric_type = rule.metric_type

        if metric_type == AlertMetricType.DATA_QUALITY.value:
            # 数据质量指标：获取最近一次质量检查的评分
            async with async_db_session() as session:
                stmt = (
                    select(QualityCheck.score)
                    .where(QualityCheck.rule_id == rule.id if hasattr(rule, 'quality_rule_id') else True)
                    .order_by(QualityCheck.created_time.desc())
                    .limit(1)
                )
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
                return float(row) if row is not None else None

        elif metric_type == AlertMetricType.TASK_SUCCESS.value:
            # 任务成功率指标
            async with async_db_session() as session:
                # 查询最近任务的成功率
                result = await session.execute(
                    text('SELECT AVG(CASE WHEN status = :success THEN 1.0 ELSE 0.0 END) * 100 '
                         'FROM sys_crawl_task WHERE created_time > DATE_SUB(NOW(), INTERVAL 1 HOUR)'),
                    {'success': 'success'},
                )
                row = result.scalar_one_or_none()
                return float(row) if row is not None else None

        # 其他指标类型暂不支持自动获取
        return None

    @staticmethod
    def _evaluate_condition(value: float, condition: str, threshold: float) -> bool:
        """评估条件是否满足

        Args:
            value: 当前指标值
            condition: 条件类型 (gt/lt/eq/gte/lte)
            threshold: 阈值

        Returns:
            是否触发告警
        """
        try:
            condition_enum = AlertCondition(condition)
        except ValueError:
            logger.warning(f'[AlertEvaluator] 未知条件类型: {condition}')
            return False

        if condition_enum == AlertCondition.GT:
            return value > threshold
        elif condition_enum == AlertCondition.LT:
            return value < threshold
        elif condition_enum == AlertCondition.EQ:
            return value == threshold
        elif condition_enum == AlertCondition.GTE:
            return value >= threshold
        elif condition_enum == AlertCondition.LTE:
            return value <= threshold
        else:
            logger.warning(f'[AlertEvaluator] 未知条件类型: {condition}')
            return False

    @staticmethod
    def _build_message(rule: Any, metric_value: float, triggered: bool) -> str:
        """构建告警消息"""
        condition_map = {
            'gt': '大于',
            'lt': '小于',
            'eq': '等于',
            'gte': '大于等于',
            'lte': '小于等于',
        }
        condition_text = condition_map.get(rule.condition, rule.condition)

        if triggered:
            return (
                f'告警触发: [{rule.metric_type}] 指标值 {metric_value} {condition_text} 阈值 {rule.threshold}'
                f' (规则: {rule.name}, 级别: {rule.severity})'
            )
        else:
            return (
                f'指标正常: [{rule.metric_type}] 指标值 {metric_value}, 阈值 {rule.threshold}'
                f' (规则: {rule.name})'
            )


async def evaluate_alert_rule(rule: Any, db: Any, metric_value: float | None = None) -> AlertEvaluationResult:
    """评估告警规则并发送通知的便捷函数

    Args:
        rule: AlertRule ORM 对象
        db: 数据库会话
        metric_value: 可选的指标值，若不提供则自动获取

    Returns:
        AlertEvaluationResult 评估结果
    """
    evaluator = AlertEvaluator()
    return await evaluator.evaluate_and_notify(rule, db, metric_value=metric_value)