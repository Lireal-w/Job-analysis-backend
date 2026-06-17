from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import DataMaskingRule, ResourcePermission
from backend.app.admin.schema.data_permission import (
    CreateDataMaskingRuleParam,
    CreateResourcePermissionParam,
    UpdateDataMaskingRuleParam,
    UpdateResourcePermissionParam,
)


class CRUDResourcePermission(CRUDPlus[ResourcePermission]):
    """资源权限数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> ResourcePermission | None:
        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> ResourcePermission | None:
        return await self.select_model_by_column(db, name=name)

    async def get_all(self, db: AsyncSession) -> Sequence[ResourcePermission]:
        return await self.select_models(db)

    async def get_select(
        self, name: str | None = None, resource_type: str | None = None, role_id: int | None = None
    ) -> Select:
        filters = {}
        if name is not None:
            filters['name__like'] = f'%{name}%'
        if resource_type is not None:
            filters['resource_type'] = resource_type
        if role_id is not None:
            filters['role_id'] = role_id
        return await self.select_order('id', **filters)

    async def create(self, db: AsyncSession, obj: CreateResourcePermissionParam) -> None:
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateResourcePermissionParam) -> int:
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


class CRUDDataMaskingRule(CRUDPlus[DataMaskingRule]):
    """数据脱敏规则数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> DataMaskingRule | None:
        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> DataMaskingRule | None:
        return await self.select_model_by_column(db, name=name)

    async def get_all(self, db: AsyncSession) -> Sequence[DataMaskingRule]:
        return await self.select_models(db)

    async def get_select(
        self, name: str | None = None, mask_type: str | None = None
    ) -> Select:
        filters = {}
        if name is not None:
            filters['name__like'] = f'%{name}%'
        if mask_type is not None:
            filters['mask_type'] = mask_type
        return await self.select_order('id', **filters)

    async def create(self, db: AsyncSession, obj: CreateDataMaskingRuleParam) -> None:
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateDataMaskingRuleParam) -> int:
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


resource_permission_dao: CRUDResourcePermission = CRUDResourcePermission(ResourcePermission)
data_masking_rule_dao: CRUDDataMaskingRule = CRUDDataMaskingRule(DataMaskingRule)
