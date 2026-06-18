"""数据质量规则执行引擎

支持五种规则类型的真实检查：
- not_null: 检查字段是否为空
- unique: 检查字段值是否唯一
- range: 检查字段值是否在指定范围内
- regex: 检查字段值是否匹配正则表达式
- custom_sql: 执行自定义 SQL 并根据结果判断

执行流程：
1. 根据规则类型选择对应的执行器
2. 连接目标数据源执行检查 SQL
3. 计算质量评分和通过/失败数
4. 返回检查结果
"""

from __future__ import annotations

import re
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from loguru import logger

from backend.app.admin.service.datasource_service import _decrypt_password
from backend.database.db import async_db_session


class QualityCheckResult:
    """质量检查结果"""

    def __init__(
        self,
        total_checked: int = 0,
        total_passed: int = 0,
        total_failed: int = 0,
        score: float = 0.0,
        details: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> None:
        self.total_checked = total_checked
        self.total_passed = total_passed
        self.total_failed = total_failed
        self.score = score
        self.details = details or {}
        self.error_message = error_message

    @property
    def is_success(self) -> bool:
        return self.error_message is None

    def to_dict(self) -> dict[str, Any]:
        return {
            'total_checked': self.total_checked,
            'total_passed': self.total_passed,
            'total_failed': self.total_failed,
            'score': self.score,
            'details': self.details,
            'error_message': self.error_message,
        }


class BaseRuleExecutor(ABC):
    """规则执行器基类"""

    rule_type: str = ''

    def __init__(self, rule: Any) -> None:
        self.rule = rule
        self.rule_config = rule.rule_config or {}

    @abstractmethod
    async def execute(self, datasource: Any, password: str | None) -> QualityCheckResult:
        """执行规则检查

        Args:
            datasource: 数据源对象
            password: 解密后的密码

        Returns:
            检查结果
        """
        ...

    async def _execute_query(
        self,
        datasource: Any,
        password: str | None,
        query: str,
    ) -> list[dict[str, Any]]:
        """在数据源上执行 SQL 查询

        Args:
            datasource: 数据源对象
            password: 解密后的密码
            query: SQL 查询语句

        Returns:
            查询结果行列表
        """
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        db_type = datasource.db_type
        url = self._build_db_url(datasource, password, db_type)

        engine = create_async_engine(url, echo=False)
        try:
            async with AsyncSession(engine) as session:
                result = await session.execute(text(query))
                columns = list(result.keys())
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                return rows
        finally:
            await engine.dispose()

    @staticmethod
    def _build_db_url(datasource: Any, password: str | None, db_type: str) -> str:
        """构建数据库连接 URL"""
        if db_type == 'mysql':
            return f'mysql+asyncmy://{datasource.username}:{password}@{datasource.host}:{datasource.port}/{datasource.database_name}'
        elif db_type == 'postgresql':
            return f'postgresql+asyncpg://{datasource.username}:{password}@{datasource.host}:{datasource.port}/{datasource.database_name}'
        elif db_type == 'sqlite':
            return f'sqlite+aiosqlite:///{datasource.database_name or ":memory:"}'
        elif db_type == 'mssql':
            return f'mssql+pyodbc://{datasource.username}:{password}@{datasource.host}:{datasource.port}/{datasource.database_name}?driver=ODBC+Driver+17+for+SQL+Server'
        elif db_type == 'oracle':
            return f'oracle+oracledb://{datasource.username}:{password}@{datasource.host}:{datasource.port}/{datasource.database_name}'
        else:
            raise ValueError(f'不支持的数据库类型: {db_type}')


class NotNullRuleExecutor(BaseRuleExecutor):
    """非空检查规则执行器

    检查目标字段是否为 NULL，统计 NULL 值数量和比例。

    rule_config:
        datasource_id: 数据源 ID（可选，若不指定则使用应用数据库）
        database_name: 数据库名（可选，覆盖数据源配置）
    """

    rule_type = 'not_null'

    async def execute(self, datasource: Any, password: str | None) -> QualityCheckResult:
        table = self.rule.target_table
        field = self.rule.target_field

        if not table or not field:
            return QualityCheckResult(error_message='目标表名和字段名不能为空')

        # 统计总行数
        count_sql = f'SELECT COUNT(*) AS total FROM {table}'
        # 统计 NULL 值行数
        null_sql = f'SELECT COUNT(*) AS null_count FROM {table} WHERE {field} IS NULL'

        try:
            if datasource:
                count_rows = await self._execute_query(datasource, password, count_sql)
                null_rows = await self._execute_query(datasource, password, null_sql)
            else:
                count_rows = await self._execute_app_db(count_sql)
                null_rows = await self._execute_app_db(null_sql)

            total = count_rows[0]['total'] if count_rows else 0
            null_count = null_rows[0]['null_count'] if null_rows else 0
            passed = total - null_count
            score = round((passed / total) * 100, 2) if total > 0 else 100.0

            return QualityCheckResult(
                total_checked=total,
                total_passed=passed,
                total_failed=null_count,
                score=score,
                details={
                    'table': table,
                    'field': field,
                    'null_count': null_count,
                    'null_ratio': round(null_count / total, 4) if total > 0 else 0,
                },
            )
        except Exception as e:
            logger.error(f'[QualityCheck] not_null 规则执行失败: {e}')
            return QualityCheckResult(error_message=f'{type(e).__name__}: {e}')

    @staticmethod
    async def _execute_app_db(query: str) -> list[dict[str, Any]]:
        """在应用数据库上执行查询"""
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession

        from backend.database.db import async_db_session

        async with async_db_session() as session:
            result = await session.execute(text(query))
            columns = list(result.keys())
            return [dict(zip(columns, row)) for row in result.fetchall()]


class UniqueRuleExecutor(BaseRuleExecutor):
    """唯一性检查规则执行器

    检查目标字段值是否唯一，统计重复值数量。

    rule_config:
        datasource_id: 数据源 ID（可选）
    """

    rule_type = 'unique'

    async def execute(self, datasource: Any, password: str | None) -> QualityCheckResult:
        table = self.rule.target_table
        field = self.rule.target_field

        if not table or not field:
            return QualityCheckResult(error_message='目标表名和字段名不能为空')

        # 统计总行数
        count_sql = f'SELECT COUNT(*) AS total FROM {table}'
        # 统计重复值（出现次数 > 1 的值）
        dup_sql = f'SELECT COUNT(*) AS dup_count FROM (SELECT {field} FROM {table} GROUP BY {field} HAVING COUNT(*) > 1) AS t'

        try:
            if datasource:
                count_rows = await self._execute_query(datasource, password, count_sql)
                dup_rows = await self._execute_query(datasource, password, dup_sql)
            else:
                count_rows = await NotNullRuleExecutor._execute_app_db(count_sql)
                dup_rows = await NotNullRuleExecutor._execute_app_db(dup_sql)

            total = count_rows[0]['total'] if count_rows else 0
            dup_value_count = dup_rows[0]['dup_count'] if dup_rows else 0

            # 计算受影响的行数（重复值导致的额外行数）
            if datasource:
                affected_sql = f'SELECT SUM(cnt - 1) AS affected FROM (SELECT COUNT(*) AS cnt FROM {table} GROUP BY {field} HAVING COUNT(*) > 1) AS t'
                affected_rows = await self._execute_query(datasource, password, affected_sql)
            else:
                affected_sql = f'SELECT SUM(cnt - 1) AS affected FROM (SELECT COUNT(*) AS cnt FROM {table} GROUP BY {field} HAVING COUNT(*) > 1) AS t'
                affected_rows = await NotNullRuleExecutor._execute_app_db(affected_sql)

            affected = affected_rows[0]['affected'] if affected_rows and affected_rows[0]['affected'] else 0
            affected = int(affected) if affected else 0

            passed = total - affected
            score = round((passed / total) * 100, 2) if total > 0 else 100.0

            return QualityCheckResult(
                total_checked=total,
                total_passed=passed,
                total_failed=affected,
                score=score,
                details={
                    'table': table,
                    'field': field,
                    'duplicate_values': dup_value_count,
                    'affected_rows': affected,
                },
            )
        except Exception as e:
            logger.error(f'[QualityCheck] unique 规则执行失败: {e}')
            return QualityCheckResult(error_message=f'{type(e).__name__}: {e}')


class RangeRuleExecutor(BaseRuleExecutor):
    """范围检查规则执行器

    检查目标字段值是否在指定范围内。

    rule_config:
        min_value: 最小值（可选）
        max_value: 最大值（可选）
        datasource_id: 数据源 ID（可选）
    """

    rule_type = 'range'

    async def execute(self, datasource: Any, password: str | None) -> QualityCheckResult:
        table = self.rule.target_table
        field = self.rule.target_field
        config = self.rule_config

        if not table or not field:
            return QualityCheckResult(error_message='目标表名和字段名不能为空')

        min_value = config.get('min_value')
        max_value = config.get('max_value')

        if min_value is None and max_value is None:
            return QualityCheckResult(error_message='范围检查至少需要指定 min_value 或 max_value')

        # 构建条件
        conditions = []
        if min_value is not None:
            conditions.append(f'{field} < {min_value}')
        if max_value is not None:
            conditions.append(f'{field} > {max_value}')

        out_of_range_condition = ' OR '.join(conditions)

        # 统计总行数
        count_sql = f'SELECT COUNT(*) AS total FROM {table}'
        # 统计超出范围的行数
        fail_sql = f'SELECT COUNT(*) AS fail_count FROM {table} WHERE {out_of_range_condition}'

        try:
            if datasource:
                count_rows = await self._execute_query(datasource, password, count_sql)
                fail_rows = await self._execute_query(datasource, password, fail_sql)
            else:
                count_rows = await NotNullRuleExecutor._execute_app_db(count_sql)
                fail_rows = await NotNullRuleExecutor._execute_app_db(fail_sql)

            total = count_rows[0]['total'] if count_rows else 0
            fail_count = fail_rows[0]['fail_count'] if fail_rows else 0
            passed = total - fail_count
            score = round((passed / total) * 100, 2) if total > 0 else 100.0

            return QualityCheckResult(
                total_checked=total,
                total_passed=passed,
                total_failed=fail_count,
                score=score,
                details={
                    'table': table,
                    'field': field,
                    'min_value': min_value,
                    'max_value': max_value,
                    'out_of_range_count': fail_count,
                },
            )
        except Exception as e:
            logger.error(f'[QualityCheck] range 规则执行失败: {e}')
            return QualityCheckResult(error_message=f'{type(e).__name__}: {e}')


class RegexRuleExecutor(BaseRuleExecutor):
    """正则表达式检查规则执行器

    检查目标字段值是否匹配指定正则表达式。

    rule_config:
        pattern: 正则表达式模式
        datasource_id: 数据源 ID（可选）
    """

    rule_type = 'regex'

    async def execute(self, datasource: Any, password: str | None) -> QualityCheckResult:
        table = self.rule.target_table
        field = self.rule.target_field
        config = self.rule_config

        if not table or not field:
            return QualityCheckResult(error_message='目标表名和字段名不能为空')

        pattern = config.get('pattern', '')
        if not pattern:
            return QualityCheckResult(error_message='正则表达式模式不能为空')

        # 验证正则表达式是否有效
        try:
            compiled = re.compile(pattern)
        except re.error as e:
            return QualityCheckResult(error_message=f'无效的正则表达式: {e}')

        # 获取所有值进行正则匹配
        values_sql = f'SELECT {field} FROM {table}'

        try:
            if datasource:
                rows = await self._execute_query(datasource, password, values_sql)
            else:
                rows = await NotNullRuleExecutor._execute_app_db(values_sql)

            total = len(rows)
            failed = 0
            for row in rows:
                value = row.get(field)
                if value is None:
                    # NULL 值视为不匹配（除非模式允许空）
                    failed += 1
                    continue
                if not compiled.match(str(value)):
                    failed += 1

            passed = total - failed
            score = round((passed / total) * 100, 2) if total > 0 else 100.0

            return QualityCheckResult(
                total_checked=total,
                total_passed=passed,
                total_failed=failed,
                score=score,
                details={
                    'table': table,
                    'field': field,
                    'pattern': pattern,
                    'mismatch_count': failed,
                },
            )
        except Exception as e:
            logger.error(f'[QualityCheck] regex 规则执行失败: {e}')
            return QualityCheckResult(error_message=f'{type(e).__name__}: {e}')


class CustomSQLRuleExecutor(BaseRuleExecutor):
    """自定义 SQL 检查规则执行器

    执行用户自定义 SQL，根据返回结果判断数据质量。

    rule_config:
        sql: 自定义 SQL 查询语句
        pass_condition: 通过条件 (empty/zero/less_than/equals)
        threshold: 阈值（用于 less_than/equals 条件）
        datasource_id: 数据源 ID（可选）
    """

    rule_type = 'custom_sql'

    async def execute(self, datasource: Any, password: str | None) -> QualityCheckResult:
        config = self.rule_config
        sql = config.get('sql', '')
        pass_condition = config.get('pass_condition', 'empty')
        threshold = config.get('threshold', 0)

        if not sql:
            return QualityCheckResult(error_message='自定义 SQL 不能为空')

        # 安全检查：只允许 SELECT 语句
        normalized_sql = sql.strip().upper()
        forbidden_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'GRANT', 'REVOKE']
        for keyword in forbidden_keywords:
            if normalized_sql.startswith(keyword):
                return QualityCheckResult(error_message=f'安全限制：不允许执行 {keyword} 语句')

        try:
            if datasource:
                rows = await self._execute_query(datasource, password, sql)
            else:
                rows = await NotNullRuleExecutor._execute_app_db(sql)

            # 根据通过条件判断结果
            total_checked = 1  # 自定义 SQL 视为一次检查
            result_value = 0

            if pass_condition == 'empty':
                # 结果为空则通过
                passed = 1 if len(rows) == 0 else 0
                failed = 1 - passed
                result_value = len(rows)
            elif pass_condition == 'zero':
                # 第一行第一列值为 0 则通过
                if rows and len(rows) > 0:
                    first_value = list(rows[0].values())[0] if rows[0] else 0
                    result_value = float(first_value) if first_value is not None else 0
                    passed = 1 if result_value == 0 else 0
                else:
                    passed = 1
                failed = 1 - passed
            elif pass_condition == 'less_than':
                # 第一行第一列值小于阈值则通过
                if rows and len(rows) > 0:
                    first_value = list(rows[0].values())[0] if rows[0] else 0
                    result_value = float(first_value) if first_value is not None else 0
                    passed = 1 if result_value < threshold else 0
                else:
                    passed = 1
                failed = 1 - passed
            elif pass_condition == 'equals':
                # 第一行第一列值等于阈值则通过
                if rows and len(rows) > 0:
                    first_value = list(rows[0].values())[0] if rows[0] else 0
                    result_value = float(first_value) if first_value is not None else 0
                    passed = 1 if result_value == threshold else 0
                else:
                    passed = 1 if threshold == 0 else 0
                failed = 1 - passed
            else:
                # 默认：结果为空则通过
                passed = 1 if len(rows) == 0 else 0
                failed = 1 - passed

            score = round((passed / total_checked) * 100, 2) if total_checked > 0 else 100.0

            return QualityCheckResult(
                total_checked=total_checked,
                total_passed=passed,
                total_failed=failed,
                score=score,
                details={
                    'sql': sql[:200],  # 截断避免过长
                    'pass_condition': pass_condition,
                    'threshold': threshold,
                    'result_value': result_value,
                    'result_rows': len(rows),
                },
            )
        except Exception as e:
            logger.error(f'[QualityCheck] custom_sql 规则执行失败: {e}')
            return QualityCheckResult(error_message=f'{type(e).__name__}: {e}')


# ── 规则执行器注册表 ──────────────────────────────────────────

_RULE_EXECUTORS: dict[str, type[BaseRuleExecutor]] = {
    'not_null': NotNullRuleExecutor,
    'unique': UniqueRuleExecutor,
    'range': RangeRuleExecutor,
    'regex': RegexRuleExecutor,
    'custom_sql': CustomSQLRuleExecutor,
}


def get_rule_executor(rule_type: str, rule: Any) -> BaseRuleExecutor:
    """获取规则执行器实例"""
    executor_cls = _RULE_EXECUTORS.get(rule_type)
    if executor_cls is None:
        raise ValueError(f'不支持的规则类型: {rule_type}')
    return executor_cls(rule)


async def execute_quality_check(rule: Any) -> QualityCheckResult:
    """执行质量检查的入口函数

    根据规则配置获取数据源连接，选择对应的执行器，执行检查。

    Args:
        rule: QualityRule ORM 对象

    Returns:
        QualityCheckResult 检查结果
    """
    rule_type = rule.rule_type
    rule_config = rule.rule_config or {}

    # 获取执行器
    try:
        executor = get_rule_executor(rule_type, rule)
    except ValueError as e:
        return QualityCheckResult(error_message=str(e))

    # 获取数据源（如果配置了）
    datasource = None
    password = None
    datasource_id = rule_config.get('datasource_id')

    if datasource_id:
        from backend.app.admin.crud.crud_datasource import datasource_dao

        async with async_db_session() as session:
            datasource = await datasource_dao.get(session, datasource_id)
            if not datasource:
                return QualityCheckResult(error_message=f'数据源 (ID={datasource_id}) 不存在')
            password = _decrypt_password(datasource.password)

    # 执行检查
    try:
        result = await executor.execute(datasource, password)
        return result
    except Exception as e:
        logger.error(f'[QualityCheck] 规则 {rule.id} 执行异常: {e}')
        logger.error(traceback.format_exc())
        return QualityCheckResult(error_message=f'{type(e).__name__}: {e}')