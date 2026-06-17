from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import QualityCheck, QualityRule
from backend.app.admin.schema.data_quality import CreateQualityRuleParam, UpdateQualityRuleParam


class CRUDQualityRule(CRUDPlus[QualityRule]):
    """数据质量规则数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> QualityRule | None:
        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> QualityRule | None:
        return await self.select_model_by_column(db, name=name)

    async def get_all(self, db: AsyncSession) -> Sequence[QualityRule]:
        return await self.select_models(db)

    async def get_select(
        self,
        name: str | None = None,
        rule_type: str | None = None,
        severity: str | None = None,
        enabled: bool | None = None,
    ) -> Select:
        filters = {}
        if name is not None:
            filters['name__like'] = f'%{name}%'
        if rule_type is not None:
            filters['rule_type'] = rule_type
        if severity is not None:
            filters['severity'] = severity
        if enabled is not None:
            filters['enabled'] = enabled
        return await self.select_order('id', **filters)

    async def create(self, db: AsyncSession, obj: CreateQualityRuleParam) -> None:
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateQualityRuleParam) -> int:
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


class CRUDQualityCheck(CRUDPlus[QualityCheck]):
    """数据质量检查记录数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> QualityCheck | None:
        return await self.select_model(db, pk)

    async def get_by_rule(self, db: AsyncSession, rule_id: int) -> Sequence[QualityCheck]:
        return await self.select_models_by_column(db, rule_id=rule_id)

    async def get_by_run_id(self, db: AsyncSession, run_id: str) -> QualityCheck | None:
        return await self.select_model_by_column(db, run_id=run_id)

    async def create_check(self, db: AsyncSession, obj: dict) -> QualityCheck:
        return await self.create_model(db, obj)

    async def update_check(self, db: AsyncSession, pk: int, obj: dict) -> int:
        return await self.update_model(db, pk, obj)


quality_rule_dao: CRUDQualityRule = CRUDQualityRule(QualityRule)
quality_check_dao: CRUDQualityCheck = CRUDQualityCheck(QualityCheck)
