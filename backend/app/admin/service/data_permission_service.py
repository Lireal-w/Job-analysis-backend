from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_data_permission import data_masking_rule_dao, resource_permission_dao
from backend.app.admin.model import DataMaskingRule, ResourcePermission
from backend.app.admin.schema.data_permission import (
    CreateDataMaskingRuleParam,
    CreateResourcePermissionParam,
    UpdateDataMaskingRuleParam,
    UpdateResourcePermissionParam,
)
from backend.common.exception import errors
from backend.common.pagination import paging_data


class ResourcePermissionService:
    """资源权限服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> ResourcePermission:
        permission = await resource_permission_dao.get(db, pk)
        if not permission:
            raise errors.NotFoundError(msg='资源权限不存在')
        return permission

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[ResourcePermission]:
        return await resource_permission_dao.get_all(db)

    @staticmethod
    async def get_list(
        *, db: AsyncSession, name: str | None = None, resource_type: str | None = None, role_id: int | None = None
    ) -> dict[str, Any]:
        select = await resource_permission_dao.get_select(name=name, resource_type=resource_type, role_id=role_id)
        return await paging_data(db, select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateResourcePermissionParam) -> None:
        existing = await resource_permission_dao.get_by_name(db, obj.name)
        if existing:
            raise errors.ConflictError(msg='资源权限名称已存在')
        await resource_permission_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateResourcePermissionParam) -> int:
        permission = await resource_permission_dao.get(db, pk)
        if not permission:
            raise errors.NotFoundError(msg='资源权限不存在')
        return await resource_permission_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        return await resource_permission_dao.delete(db, pks)


class DataMaskingRuleService:
    """数据脱敏规则服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> DataMaskingRule:
        rule = await data_masking_rule_dao.get(db, pk)
        if not rule:
            raise errors.NotFoundError(msg='数据脱敏规则不存在')
        return rule

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[DataMaskingRule]:
        return await data_masking_rule_dao.get_all(db)

    @staticmethod
    async def get_list(
        *, db: AsyncSession, name: str | None = None, mask_type: str | None = None
    ) -> dict[str, Any]:
        select = await data_masking_rule_dao.get_select(name=name, mask_type=mask_type)
        return await paging_data(db, select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateDataMaskingRuleParam) -> None:
        existing = await data_masking_rule_dao.get_by_name(db, obj.name)
        if existing:
            raise errors.ConflictError(msg='数据脱敏规则名称已存在')
        await data_masking_rule_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateDataMaskingRuleParam) -> int:
        rule = await data_masking_rule_dao.get(db, pk)
        if not rule:
            raise errors.NotFoundError(msg='数据脱敏规则不存在')
        return await data_masking_rule_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        return await data_masking_rule_dao.delete(db, pks)


resource_permission_service: ResourcePermissionService = ResourcePermissionService()
data_masking_rule_service: DataMaskingRuleService = DataMaskingRuleService()
