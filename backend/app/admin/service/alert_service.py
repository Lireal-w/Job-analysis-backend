from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_alert import alert_history_dao, alert_rule_dao
from backend.app.admin.model import AlertHistory, AlertRule
from backend.app.admin.schema.alert import CreateAlertRuleParam, UpdateAlertRuleParam
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
        existing = await alert_rule_dao.get_by_name(db, obj.name)
        if existing:
            raise errors.ConflictError(msg='告警规则名称已存在')
        await alert_rule_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateAlertRuleParam) -> int:
        rule = await alert_rule_dao.get(db, pk)
        if not rule:
            raise errors.NotFoundError(msg='告警规则不存在')
        return await alert_rule_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        return await alert_rule_dao.delete(db, pks)


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
