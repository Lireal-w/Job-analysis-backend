import uuid

from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_data_quality import quality_check_dao, quality_rule_dao
from backend.app.admin.model import QualityCheck, QualityRule
from backend.app.admin.schema.data_quality import CreateQualityRuleParam, UpdateQualityRuleParam
from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.utils.timezone import timezone


class QualityRuleService:
    """数据质量规则服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> QualityRule:
        rule = await quality_rule_dao.get(db, pk)
        if not rule:
            raise errors.NotFoundError(msg='质量规则不存在')
        return rule

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[QualityRule]:
        return await quality_rule_dao.get_all(db)

    @staticmethod
    async def get_list(
        *,
        db: AsyncSession,
        name: str | None = None,
        rule_type: str | None = None,
        severity: str | None = None,
        enabled: bool | None = None,
    ) -> dict[str, Any]:
        select = await quality_rule_dao.get_select(
            name=name,
            rule_type=rule_type,
            severity=severity,
            enabled=enabled,
        )
        return await paging_data(db, select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateQualityRuleParam) -> None:
        existing = await quality_rule_dao.get_by_name(db, obj.name)
        if existing:
            raise errors.ConflictError(msg='质量规则名称已存在')
        await quality_rule_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateQualityRuleParam) -> int:
        rule = await quality_rule_dao.get(db, pk)
        if not rule:
            raise errors.NotFoundError(msg='质量规则不存在')
        return await quality_rule_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        return await quality_rule_dao.delete(db, pks)

    @staticmethod
    async def run_check(*, db: AsyncSession, pk: int) -> dict[str, Any]:
        """运行质量检查"""
        rule = await quality_rule_dao.get(db, pk)
        if not rule:
            raise errors.NotFoundError(msg='质量规则不存在')

        run_id = str(uuid.uuid4())
        now = timezone.now()

        check_data = {
            'rule_id': pk,
            'run_id': run_id,
            'status': 'running',
            'start_time': now,
            'total_checked': 0,
            'total_passed': 0,
            'total_failed': 0,
        }

        check = await quality_check_dao.create_check(db, check_data)

        try:
            # 模拟执行检查逻辑
            import random

            total = random.randint(100, 10000)
            passed = random.randint(int(total * 0.8), total)
            failed = total - passed
            score = round((passed / total) * 100, 2) if total > 0 else 0.0
            end_time = timezone.now()
            duration = (end_time - now).total_seconds()

            update_data = {
                'status': 'success',
                'end_time': end_time,
                'duration': duration,
                'total_checked': total,
                'total_passed': passed,
                'total_failed': failed,
                'score': score,
            }
            await quality_check_dao.update_check(db, check.id, update_data)

            return {
                'check_id': check.id,
                'run_id': run_id,
                'status': 'success',
                'score': score,
                'total_checked': total,
                'total_passed': passed,
                'total_failed': failed,
                'duration': duration,
            }
        except Exception as e:
            update_data = {
                'status': 'failed',
                'end_time': timezone.now(),
                'error_message': str(e),
            }
            await quality_check_dao.update_check(db, check.id, update_data)
            return {
                'check_id': check.id,
                'run_id': run_id,
                'status': 'failed',
                'error_message': str(e),
            }

    @staticmethod
    async def get_checks(*, db: AsyncSession, pk: int) -> Sequence[QualityCheck]:
        """获取规则的所有检查记录"""
        rule = await quality_rule_dao.get(db, pk)
        if not rule:
            raise errors.NotFoundError(msg='质量规则不存在')
        return await quality_check_dao.get_by_rule(db, pk)

    @staticmethod
    async def get_check_detail(*, db: AsyncSession, check_id: int) -> QualityCheck:
        """获取检查记录详情"""
        check = await quality_check_dao.get(db, check_id)
        if not check:
            raise errors.NotFoundError(msg='质量检查记录不存在')
        return check


quality_rule_service: QualityRuleService = QualityRuleService()
