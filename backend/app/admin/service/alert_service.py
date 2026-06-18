from collections.abc import Sequence
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_alert import alert_history_dao, alert_rule_dao
from backend.app.admin.model import AlertHistory, AlertRule
from backend.app.admin.schema.alert import CreateAlertRuleParam, UpdateAlertRuleParam
from backend.app.admin.service.alert.evaluator import AlertEvaluator, evaluate_alert_rule
from backend.app.admin.service.alert.enums import AlertCondition, AlertMetricType, AlertSeverity
from backend.common.exception import errors
from backend.common.pagination import paging_data


class AlertRuleService:
    """告警规则服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> AlertRule:
        rule = await alert_rule_dao.get(db, pk)
        if not rule:
            raise errors.NotFoundError(msg='告警规则不存在')
        return rule

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[AlertRule]:
        return await alert_rule_dao.get_all(db)

    @staticmethod
    async def get_list(
        *,
        db: AsyncSession,
        name: str | None = None,
        metric_type: str | None = None,
        severity: str | None = None,
        enabled: bool | None = None,
    ) -> dict[str, Any]:
        select = await alert_rule_dao.get_select(
            name=name, metric_type=metric_type, severity=severity, enabled=enabled,
        )
        return await paging_data(db, select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateAlertRuleParam) -> None:
        # 验证枚举值
        if obj.metric_type and obj.metric_type not in [e.value for e in AlertMetricType]:
            raise errors.RequestError(msg=f'不支持的指标类型: {obj.metric_type}')
        if obj.condition and obj.condition not in [e.value for e in AlertCondition]:
            raise errors.RequestError(msg=f'不支持的条件类型: {obj.condition}')
        if obj.severity and obj.severity not in [e.value for e in AlertSeverity]:
            raise errors.RequestError(msg=f'不支持的严重级别: {obj.severity}')

        existing = await alert_rule_dao.get_by_name(db, obj.name)
        if existing:
            raise errors.ConflictError(msg='告警规则名称已存在')
        await alert_rule_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateAlertRuleParam) -> int:
        rule = await alert_rule_dao.get(db, pk)
        if not rule:
            raise errors.NotFoundError(msg='告警规则不存在')

        # 验证枚举值
        if obj.metric_type is not None and obj.metric_type not in [e.value for e in AlertMetricType]:
            raise errors.RequestError(msg=f'不支持的指标类型: {obj.metric_type}')
        if obj.condition is not None and obj.condition not in [e.value for e in AlertCondition]:
            raise errors.RequestError(msg=f'不支持的条件类型: {obj.condition}')
        if obj.severity is not None and obj.severity not in [e.value for e in AlertSeverity]:
            raise errors.RequestError(msg=f'不支持的严重级别: {obj.severity}')

        return await alert_rule_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        return await alert_rule_dao.delete(db, pks)

    @staticmethod
    async def evaluate(*, db: AsyncSession, pk: int, metric_value: float | None = None) -> dict[str, Any]:
        """手动触发告警规则评估

        Args:
            db: 数据库会话
            pk: 规则 ID
            metric_value: 可选的指标值，若不提供则自动获取

        Returns:
            评估结果
        """
        rule = await alert_rule_dao.get(db, pk)
        if not rule:
            raise errors.NotFoundError(msg='告警规则不存在')

        if not rule.enabled:
            raise errors.RequestError(msg='规则已禁用，无法评估')

        result = await evaluate_alert_rule(rule, db, metric_value=metric_value)

        return {
            'rule_id': rule.id,
            'rule_name': rule.name,
            'triggered': result.triggered,
            'metric_value': result.metric_value,
            'threshold': result.threshold,
            'condition': result.condition,
            'severity': result.severity,
            'message': result.message,
            'details': result.details,
        }

    @staticmethod
    async def evaluate_all(*, db: AsyncSession, metric_type: str | None = None) -> list[dict[str, Any]]:
        """评估所有启用的告警规则

        Args:
            db: 数据库会话
            metric_type: 可选，只评估指定指标类型的规则

        Returns:
            评估结果列表
        """
        rules = await alert_rule_dao.get_all(db)
        results = []

        for rule in rules:
            if not rule.enabled:
                continue
            if metric_type and rule.metric_type != metric_type:
                continue

            try:
                result = await evaluate_alert_rule(rule, db)
                results.append({
                    'rule_id': rule.id,
                    'rule_name': rule.name,
                    'triggered': result.triggered,
                    'metric_value': result.metric_value,
                    'threshold': result.threshold,
                    'condition': result.condition,
                    'severity': result.severity,
                    'message': result.message,
                })
            except Exception as e:
                logger.error(f'[AlertRuleService] 评估规则 {rule.id} 失败: {e}')
                results.append({
                    'rule_id': rule.id,
                    'rule_name': rule.name,
                    'triggered': False,
                    'error': f'{type(e).__name__}: {e}',
                })

        return results


class AlertHistoryService:
    """告警历史服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> AlertHistory:
        history = await alert_history_dao.get(db, pk)
        if not history:
            raise errors.NotFoundError(msg='告警历史不存在')
        return history

    @staticmethod
    async def get_list(
        *,
        db: AsyncSession,
        rule_id: int | None = None,
        severity: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        select = await alert_history_dao.get_select(rule_id=rule_id, severity=severity, status=status)
        return await paging_data(db, select)


alert_rule_service: AlertRuleService = AlertRuleService()
alert_history_service: AlertHistoryService = AlertHistoryService()
