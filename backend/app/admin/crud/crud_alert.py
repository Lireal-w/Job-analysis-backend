from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import AlertHistory, AlertRule
from backend.app.admin.schema.alert import CreateAlertHistoryParam, CreateAlertRuleParam, UpdateAlertRuleParam


class CRUDAlertRule(CRUDPlus[AlertRule]):
    """告警规则数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> AlertRule | None:
        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> AlertRule | None:
        return await self.select_model_by_column(db, name=name)

    async def get_all(self, db: AsyncSession) -> Sequence[AlertRule]:
        return await self.select_models(db)

    async def get_select(
        self,
        name: str | None = None,
        metric_type: str | None = None,
        severity: str | None = None,
        enabled: bool | None = None,
    ) -> Select:
        filters = {}
        if name is not None:
            filters['name__like'] = f'%{name}%'
        if metric_type is not None:
            filters['metric_type'] = metric_type
        if severity is not None:
            filters['severity'] = severity
        if enabled is not None:
            filters['enabled'] = enabled
        return await self.select_order('id', **filters)

    async def create(self, db: AsyncSession, obj: CreateAlertRuleParam) -> None:
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateAlertRuleParam) -> int:
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


class CRUDAlertHistory(CRUDPlus[AlertHistory]):
    """告警历史数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> AlertHistory | None:
        return await self.select_model(db, pk)

    async def get_select(
        self,
        rule_id: int | None = None,
        severity: str | None = None,
        status: str | None = None,
    ) -> Select:
        filters = {}
        if rule_id is not None:
            filters['rule_id'] = rule_id
        if severity is not None:
            filters['severity'] = severity
        if status is not None:
            filters['status'] = status
        return await self.select_order('created_time', 'desc', **filters)

    async def create(self, db: AsyncSession, obj: CreateAlertHistoryParam) -> None:
        await self.create_model(db, obj)


alert_rule_dao: CRUDAlertRule = CRUDAlertRule(AlertRule)
alert_history_dao: CRUDAlertHistory = CRUDAlertHistory(AlertHistory)
