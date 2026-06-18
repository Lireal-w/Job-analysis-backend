import uuid

from collections.abc import Sequence
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_data_quality import quality_check_dao, quality_rule_dao
from backend.app.admin.model import QualityCheck, QualityRule
from backend.app.admin.schema.data_quality import CreateQualityRuleParam, UpdateQualityRuleParam
from backend.app.admin.service.data_quality import execute_quality_check
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
        """运行质量检查

        使用真实的规则执行引擎进行检查，支持以下规则类型：
        - not_null: 检查字段是否为空
        - unique: 检查字段值是否唯一
        - range: 检查字段值是否在指定范围内
        - regex: 检查字段值是否匹配正则表达式
        - custom_sql: 执行自定义 SQL 并根据结果判断
        """
        rule = await quality_rule_dao.get(db, pk)
        if not rule:
            raise errors.NotFoundError(msg='质量规则不存在')

        if not rule.enabled:
            raise errors.RequestError(msg='规则已禁用，无法执行检查')

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
            # 使用真实的规则执行引擎
            result = await execute_quality_check(rule)

            end_time = timezone.now()
            duration = (end_time - now).total_seconds()

            if result.is_success:
                update_data = {
                    'status': 'success',
                    'end_time': end_time,
                    'duration': duration,
                    'total_checked': result.total_checked,
                    'total_passed': result.total_passed,
                    'total_failed': result.total_failed,
                    'score': result.score,
                }
            else:
                update_data = {
                    'status': 'failed',
                    'end_time': end_time,
                    'duration': duration,
                    'total_checked': result.total_checked,
                    'total_passed': result.total_passed,
                    'total_failed': result.total_failed,
                    'score': result.score,
                    'error_message': result.error_message,
                }

            await quality_check_dao.update_check(db, check.id, update_data)

            # 触发数据质量告警
            try:
                await trigger_quality_alert(rule, result, db)
            except Exception as e:
                logger.warning(f'[QualityCheck] 触发告警失败（不影响检查结果）: {e}')

            return {
                'check_id': check.id,
                'run_id': run_id,
                'status': update_data['status'],
                'score': result.score,
                'total_checked': result.total_checked,
                'total_passed': result.total_passed,
                'total_failed': result.total_failed,
                'duration': duration,
                'details': result.details,
                'error_message': result.error_message,
            }
        except Exception as e:
            logger.error(f'[QualityCheck] 规则 {pk} 执行失败: {e}')
            end_time = timezone.now()
            duration = (end_time - now).total_seconds()

            update_data = {
                'status': 'failed',
                'end_time': end_time,
                'duration': duration,
                'error_message': f'{type(e).__name__}: {e}',
            }
            await quality_check_dao.update_check(db, check.id, update_data)

            return {
                'check_id': check.id,
                'run_id': run_id,
                'status': 'failed',
                'error_message': f'{type(e).__name__}: {e}',
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


async def trigger_quality_alert(
    rule: QualityRule,
    result: Any,
    db: AsyncSession,
) -> None:
    """质量检查完成后触发告警

    当质量评分低于阈值时，查找匹配的告警规则并触发告警。

    Args:
        rule: 质量规则 ORM 对象
        result: QualityCheckResult 检查结果
        db: 数据库会话
    """
    from backend.app.admin.crud.crud_alert import alert_rule_dao
    from backend.app.admin.service.alert.evaluator import evaluate_alert_rule

    # 查找 data_quality 类型的告警规则
    alert_rules = await alert_rule_dao.get_all(db)
    quality_alert_rules = [
        r for r in alert_rules
        if r.metric_type == 'data_quality' and r.enabled
    ]

    if not quality_alert_rules:
        return

    for alert_rule in quality_alert_rules:
        try:
            # 使用质量评分作为指标值
            await evaluate_alert_rule(alert_rule, db, metric_value=result.score)
        except Exception as e:
            logger.error(f'[QualityAlert] 触发告警规则 {alert_rule.name} 失败: {e}')
