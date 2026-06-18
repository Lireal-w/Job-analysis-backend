"""数据质量规则执行引擎测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.admin.service.data_quality import (
    CustomSQLRuleExecutor,
    NotNullRuleExecutor,
    QualityCheckResult,
    RangeRuleExecutor,
    RegexRuleExecutor,
    UniqueRuleExecutor,
    execute_quality_check,
    get_rule_executor,
)


class TestQualityCheckResult:
    """QualityCheckResult 测试"""

    def test_default_values(self):
        result = QualityCheckResult()
        assert result.total_checked == 0
        assert result.total_passed == 0
        assert result.total_failed == 0
        assert result.score == 0.0
        assert result.details == {}
        assert result.error_message is None
        assert result.is_success is True

    def test_custom_values(self):
        result = QualityCheckResult(
            total_checked=100,
            total_passed=95,
            total_failed=5,
            score=95.0,
            details={'table': 'users'},
        )
        assert result.total_checked == 100
        assert result.total_passed == 95
        assert result.total_failed == 5
        assert result.score == 95.0
        assert result.is_success is True

    def test_error_result(self):
        result = QualityCheckResult(error_message='Connection failed')
        assert result.is_success is False
        assert result.error_message == 'Connection failed'

    def test_to_dict(self):
        result = QualityCheckResult(
            total_checked=50,
            total_passed=48,
            total_failed=2,
            score=96.0,
            details={'field': 'email'},
        )
        d = result.to_dict()
        assert d['total_checked'] == 50
        assert d['total_passed'] == 48
        assert d['total_failed'] == 2
        assert d['score'] == 96.0
        assert d['details']['field'] == 'email'


class TestGetRuleExecutor:
    """规则执行器注册表测试"""

    def test_get_not_null_executor(self):
        rule = MagicMock(rule_type='not_null', rule_config={})
        executor = get_rule_executor('not_null', rule)
        assert isinstance(executor, NotNullRuleExecutor)

    def test_get_unique_executor(self):
        rule = MagicMock(rule_type='unique', rule_config={})
        executor = get_rule_executor('unique', rule)
        assert isinstance(executor, UniqueRuleExecutor)

    def test_get_range_executor(self):
        rule = MagicMock(rule_type='range', rule_config={})
        executor = get_rule_executor('range', rule)
        assert isinstance(executor, RangeRuleExecutor)

    def test_get_regex_executor(self):
        rule = MagicMock(rule_type='regex', rule_config={})
        executor = get_rule_executor('regex', rule)
        assert isinstance(executor, RegexRuleExecutor)

    def test_get_custom_sql_executor(self):
        rule = MagicMock(rule_type='custom_sql', rule_config={})
        executor = get_rule_executor('custom_sql', rule)
        assert isinstance(executor, CustomSQLRuleExecutor)

    def test_unsupported_type(self):
        with pytest.raises(ValueError, match='不支持的规则类型'):
            get_rule_executor('unknown_type', MagicMock())


class TestNotNullRuleExecutor:
    """非空检查规则执行器测试"""

    def test_missing_table(self):
        rule = MagicMock(target_table=None, target_field='name', rule_config={})
        executor = NotNullRuleExecutor(rule)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            executor.execute(None, None)
        )
        assert result.is_success is False
        assert '不能为空' in result.error_message

    def test_missing_field(self):
        rule = MagicMock(target_table='users', target_field=None, rule_config={})
        executor = NotNullRuleExecutor(rule)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            executor.execute(None, None)
        )
        assert result.is_success is False
        assert '不能为空' in result.error_message


class TestRangeRuleExecutor:
    """范围检查规则执行器测试"""

    def test_missing_range_values(self):
        rule = MagicMock(target_table='users', target_field='age', rule_config={})
        executor = RangeRuleExecutor(rule)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            executor.execute(None, None)
        )
        assert result.is_success is False
        assert '至少需要指定' in result.error_message

    def test_with_min_value(self):
        rule = MagicMock(target_table='users', target_field='age', rule_config={'min_value': 0})
        executor = RangeRuleExecutor(rule)
        assert executor.rule_config['min_value'] == 0

    def test_with_max_value(self):
        rule = MagicMock(target_table='users', target_field='age', rule_config={'max_value': 150})
        executor = RangeRuleExecutor(rule)
        assert executor.rule_config['max_value'] == 150


class TestRegexRuleExecutor:
    """正则表达式检查规则执行器测试"""

    def test_missing_pattern(self):
        rule = MagicMock(target_table='users', target_field='email', rule_config={})
        executor = RegexRuleExecutor(rule)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            executor.execute(None, None)
        )
        assert result.is_success is False
        assert '不能为空' in result.error_message

    def test_invalid_regex(self):
        rule = MagicMock(
            target_table='users',
            target_field='email',
            rule_config={'pattern': '[invalid'},
        )
        executor = RegexRuleExecutor(rule)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            executor.execute(None, None)
        )
        assert result.is_success is False
        assert '无效的正则表达式' in result.error_message

    def test_valid_regex_pattern(self):
        rule = MagicMock(
            target_table='users',
            target_field='email',
            rule_config={'pattern': r'^[\w.-]+@[\w.-]+\.\w+$'},
        )
        executor = RegexRuleExecutor(rule)
        import re
        # 验证正则可以编译
        assert re.compile(r'^[\w.-]+@[\w.-]+\.\w+$') is not None


class TestCustomSQLRuleExecutor:
    """自定义 SQL 检查规则执行器测试"""

    def test_missing_sql(self):
        rule = MagicMock(target_table=None, target_field=None, rule_config={})
        executor = CustomSQLRuleExecutor(rule)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            executor.execute(None, None)
        )
        assert result.is_success is False
        assert '不能为空' in result.error_message

    def test_forbidden_insert(self):
        rule = MagicMock(
            target_table=None,
            target_field=None,
            rule_config={'sql': 'INSERT INTO users VALUES (1, "hack")'},
        )
        executor = CustomSQLRuleExecutor(rule)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            executor.execute(None, None)
        )
        assert result.is_success is False
        assert '安全限制' in result.error_message

    def test_forbidden_delete(self):
        rule = MagicMock(
            target_table=None,
            target_field=None,
            rule_config={'sql': 'DELETE FROM users'},
        )
        executor = CustomSQLRuleExecutor(rule)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            executor.execute(None, None)
        )
        assert result.is_success is False

    def test_forbidden_drop(self):
        rule = MagicMock(
            target_table=None,
            target_field=None,
            rule_config={'sql': 'DROP TABLE users'},
        )
        executor = CustomSQLRuleExecutor(rule)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            executor.execute(None, None)
        )
        assert result.is_success is False

    def test_valid_select_sql(self):
        rule = MagicMock(
            target_table=None,
            target_field=None,
            rule_config={
                'sql': 'SELECT COUNT(*) FROM users WHERE status = "inactive"',
                'pass_condition': 'zero',
            },
        )
        executor = CustomSQLRuleExecutor(rule)
        assert executor.rule_config['sql'].startswith('SELECT')


class TestBuildDbUrl:
    """数据库 URL 构建测试"""

    def test_mysql_url(self):
        ds = MagicMock(
            db_type='mysql',
            username='root',
            password=None,
            host='localhost',
            port=3306,
            database_name='testdb',
        )
        url = NotNullRuleExecutor._build_db_url(ds, 'pass123', 'mysql')
        assert 'mysql+asyncmy' in url
        assert 'root:pass123' in url
        assert 'localhost:3306' in url
        assert 'testdb' in url

    def test_postgresql_url(self):
        ds = MagicMock(
            db_type='postgresql',
            username='postgres',
            password=None,
            host='localhost',
            port=5432,
            database_name='testdb',
        )
        url = NotNullRuleExecutor._build_db_url(ds, 'pass123', 'postgresql')
        assert 'postgresql+asyncpg' in url

    def test_sqlite_url(self):
        ds = MagicMock(
            db_type='sqlite',
            database_name='/data/test.db',
        )
        url = NotNullRuleExecutor._build_db_url(ds, None, 'sqlite')
        assert 'sqlite+aiosqlite' in url

    def test_unsupported_db_type(self):
        ds = MagicMock(db_type='unknown_db')
        with pytest.raises(ValueError, match='不支持的数据库类型'):
            NotNullRuleExecutor._build_db_url(ds, None, 'unknown_db')