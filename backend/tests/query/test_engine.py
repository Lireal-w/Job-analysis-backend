"""查询引擎测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.admin.service.query.engine import (
    DEFAULT_QUERY_TIMEOUT,
    DEFAULT_RESULT_LIMIT,
    CACHE_TTL,
    FORBIDDEN_SQL_KEYWORDS,
    SUPPORTED_DB_DRIVERS,
    QueryEngine,
    QueryResult,
    build_db_url,
    execute_query_on_datasource,
    validate_sql_safety,
)


class TestConstants:
    """常量测试"""

    def test_forbidden_keywords(self):
        assert 'INSERT' in FORBIDDEN_SQL_KEYWORDS
        assert 'UPDATE' in FORBIDDEN_SQL_KEYWORDS
        assert 'DELETE' in FORBIDDEN_SQL_KEYWORDS
        assert 'DROP' in FORBIDDEN_SQL_KEYWORDS
        assert 'CREATE' in FORBIDDEN_SQL_KEYWORDS
        assert 'ALTER' in FORBIDDEN_SQL_KEYWORDS
        assert 'TRUNCATE' in FORBIDDEN_SQL_KEYWORDS
        assert 'SELECT' not in FORBIDDEN_SQL_KEYWORDS

    def test_supported_drivers(self):
        assert 'mysql' in SUPPORTED_DB_DRIVERS
        assert 'postgresql' in SUPPORTED_DB_DRIVERS
        assert 'sqlite' in SUPPORTED_DB_DRIVERS
        assert 'mssql' in SUPPORTED_DB_DRIVERS
        assert 'oracle' in SUPPORTED_DB_DRIVERS

    def test_defaults(self):
        assert DEFAULT_QUERY_TIMEOUT == 30
        assert DEFAULT_RESULT_LIMIT == 10000
        assert CACHE_TTL == 300


class TestQueryResult:
    """QueryResult 测试"""

    def test_default_values(self):
        result = QueryResult()
        assert result.columns == []
        assert result.rows == []
        assert result.total == 0
        assert result.duration == 0.0
        assert result.status == 'success'
        assert result.error_message is None
        assert result.datasource_name is None
        assert result.datasource_type is None
        assert result.cached is False

    def test_custom_values(self):
        result = QueryResult(
            columns=['id', 'name'],
            rows=[[1, 'Alice'], [2, 'Bob']],
            total=2,
            duration=0.5,
            status='success',
            datasource_name='MySQL Prod',
            datasource_type='mysql',
        )
        assert result.columns == ['id', 'name']
        assert result.total == 2
        assert result.datasource_name == 'MySQL Prod'

    def test_error_result(self):
        result = QueryResult(
            status='failed',
            error_message='Connection refused',
        )
        assert result.status == 'failed'
        assert result.error_message == 'Connection refused'

    def test_to_dict(self):
        result = QueryResult(
            columns=['id', 'name'],
            rows=[[1, 'Alice']],
            total=1,
            duration=0.1,
            status='success',
            datasource_name='TestDB',
            datasource_type='mysql',
            cached=True,
        )
        d = result.to_dict()
        assert d['columns'] == ['id', 'name']
        assert d['total'] == 1
        assert d['cached'] is True
        assert d['datasource_name'] == 'TestDB'


class TestValidateSqlSafety:
    """SQL 安全检查测试"""

    def test_valid_select(self):
        is_safe, msg = validate_sql_safety('SELECT * FROM users')
        assert is_safe is True
        assert msg == ''

    def test_valid_select_with_where(self):
        is_safe, msg = validate_sql_safety('SELECT id, name FROM users WHERE age > 18')
        assert is_safe is True

    def test_valid_select_with_join(self):
        is_safe, msg = validate_sql_safety('SELECT u.id, u.name FROM users u JOIN orders o ON u.id = o.user_id')
        assert is_safe is True

    def test_valid_select_with_subquery(self):
        is_safe, msg = validate_sql_safety('SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)')
        assert is_safe is True

    def test_empty_sql(self):
        is_safe, msg = validate_sql_safety('')
        assert is_safe is False
        assert '不能为空' in msg

    def test_whitespace_only(self):
        is_safe, msg = validate_sql_safety('   ')
        assert is_safe is False

    def test_insert_blocked(self):
        is_safe, msg = validate_sql_safety('INSERT INTO users VALUES (1, "hack")')
        assert is_safe is False
        assert 'SELECT' in msg or 'INSERT' in msg

    def test_update_blocked(self):
        is_safe, msg = validate_sql_safety('UPDATE users SET name = "hack"')
        assert is_safe is False

    def test_delete_blocked(self):
        is_safe, msg = validate_sql_safety('DELETE FROM users')
        assert is_safe is False

    def test_drop_blocked(self):
        is_safe, msg = validate_sql_safety('DROP TABLE users')
        assert is_safe is False

    def test_create_blocked(self):
        is_safe, msg = validate_sql_safety('CREATE TABLE evil (id INT)')
        assert is_safe is False

    def test_alter_blocked(self):
        is_safe, msg = validate_sql_safety('ALTER TABLE users ADD COLUMN evil TEXT')
        assert is_safe is False

    def test_truncate_blocked(self):
        is_safe, msg = validate_sql_safety('TRUNCATE TABLE users')
        assert is_safe is False

    def test_grant_blocked(self):
        is_safe, msg = validate_sql_safety('GRANT ALL ON users TO public')
        assert is_safe is False

    def test_select_with_insert_subquery_blocked(self):
        """SELECT 中包含 INSERT 子查询应被阻止"""
        is_safe, msg = validate_sql_safety('SELECT * FROM (INSERT INTO users VALUES (1, "hack"))')
        assert is_safe is False
        assert 'INSERT' in msg

    def test_comment_only(self):
        is_safe, msg = validate_sql_safety('-- just a comment')
        assert is_safe is False
        assert '注释' in msg

    def test_select_with_comment(self):
        is_safe, msg = validate_sql_safety('SELECT * FROM users -- get all users')
        assert is_safe is True

    def test_multi_statement_injection(self):
        """多条语句注入应被阻止"""
        is_safe, msg = validate_sql_safety('SELECT * FROM users; DROP TABLE users')
        assert is_safe is False

    def test_select_count(self):
        is_safe, msg = validate_sql_safety('SELECT COUNT(*) FROM users')
        assert is_safe is True

    def test_select_with_group_by(self):
        is_safe, msg = validate_sql_safety('SELECT department, COUNT(*) FROM employees GROUP BY department')
        assert is_safe is True

    def test_select_with_order_by(self):
        is_safe, msg = validate_sql_safety('SELECT * FROM users ORDER BY created_time DESC')
        assert is_safe is True

    def test_select_with_limit(self):
        is_safe, msg = validate_sql_safety('SELECT * FROM users LIMIT 10')
        assert is_safe is True


class TestBuildDbUrl:
    """数据库 URL 构建测试"""

    def test_mysql_url(self):
        ds = MagicMock(
            db_type='mysql',
            username='root',
            password='encrypted_pass',
            host='localhost',
            port=3306,
            database_name='testdb',
        )
        url = build_db_url(ds, 'decrypted_pass')
        assert 'mysql+asyncmy' in url
        assert 'root:decrypted_pass' in url
        assert 'localhost:3306' in url
        assert 'testdb' in url

    def test_postgresql_url(self):
        ds = MagicMock(
            db_type='postgresql',
            username='postgres',
            password='encrypted',
            host='db.example.com',
            port=5432,
            database_name='mydb',
        )
        url = build_db_url(ds, 'mypassword')
        assert 'postgresql+asyncpg' in url
        assert 'postgres:mypassword' in url
        assert 'db.example.com:5432' in url

    def test_sqlite_url(self):
        ds = MagicMock(
            db_type='sqlite',
            database_name='/data/test.db',
        )
        url = build_db_url(ds, None)
        assert 'sqlite+aiosqlite' in url
        assert '/data/test.db' in url

    def test_sqlite_memory_url(self):
        ds = MagicMock(
            db_type='sqlite',
            database_name=None,
        )
        url = build_db_url(ds, None)
        assert 'sqlite+aiosqlite' in url
        assert ':memory:' in url

    def test_mssql_url(self):
        ds = MagicMock(
            db_type='mssql',
            username='sa',
            password='encrypted',
            host='mssql.example.com',
            port=1433,
            database_name='master',
        )
        url = build_db_url(ds, 'StrongPass123')
        assert 'mssql+pyodbc' in url
        assert 'ODBC+Driver+17' in url

    def test_oracle_url(self):
        ds = MagicMock(
            db_type='oracle',
            username='system',
            password='encrypted',
            host='oracle.example.com',
            port=1521,
            database_name='orcl',
        )
        url = build_db_url(ds, 'oracle_pass')
        assert 'oracle+oracledb' in url

    def test_unsupported_db_type(self):
        ds = MagicMock(db_type='unknown_db')
        with pytest.raises(ValueError, match='不支持的数据库类型'):
            build_db_url(ds, 'pass')


class TestQueryEngine:
    """查询引擎测试"""

    @pytest.fixture
    def mock_datasource(self):
        ds = MagicMock()
        ds.id = 1
        ds.name = 'Test MySQL'
        ds.db_type = 'mysql'
        ds.host = 'localhost'
        ds.port = 3306
        ds.database_name = 'testdb'
        ds.username = 'root'
        ds.password = 'encrypted_password'
        ds.extra_params = None
        ds.status = 1
        return ds

    @pytest.mark.asyncio
    async def test_execute_empty_sql(self, mock_datasource):
        engine = QueryEngine()
        result = await engine.execute(mock_datasource, '')
        assert result.status == 'failed'
        assert '不能为空' in result.error_message

    @pytest.mark.asyncio
    async def test_execute_dangerous_sql(self, mock_datasource):
        engine = QueryEngine()
        result = await engine.execute(mock_datasource, 'DROP TABLE users')
        assert result.status == 'failed'
        assert 'SELECT' in result.error_message or 'DROP' in result.error_message

    @pytest.mark.asyncio
    async def test_execute_unsupported_db(self):
        ds = MagicMock()
        ds.id = 1
        ds.name = 'Test Redis'
        ds.db_type = 'redis'
        ds.status = 1
        engine = QueryEngine()
        result = await engine.execute(ds, 'SELECT * FROM users')
        assert result.status == 'failed'
        assert '不支持' in result.error_message

    @pytest.mark.asyncio
    async def test_execute_with_cache_miss(self, mock_datasource):
        """测试缓存未命中时正常执行"""
        with patch.object(QueryEngine, '_get_cache', new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = None
            with patch.object(QueryEngine, '_execute_sql_query', new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = (
                    [[1, 'Alice'], [2, 'Bob']],
                    ['id', 'name'],
                )
                with patch.object(QueryEngine, '_set_cache', new_callable=AsyncMock):
                    engine = QueryEngine()
                    result = await engine.execute(mock_datasource, 'SELECT * FROM users')

                    assert result.status == 'success'
                    assert result.columns == ['id', 'name']
                    assert result.total == 2

    @pytest.mark.asyncio
    async def test_execute_with_cache_hit(self, mock_datasource):
        """测试缓存命中"""
        cached_result = QueryResult(
            columns=['id'],
            rows=[[1]],
            total=1,
            duration=0.01,
            status='success',
        )
        with patch.object(QueryEngine, '_get_cache', new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = cached_result
            engine = QueryEngine()
            result = await engine.execute(mock_datasource, 'SELECT * FROM users')

            assert result.status == 'success'
            assert result.cached is True
            assert result.columns == ['id']

    @pytest.mark.asyncio
    async def test_execute_no_cache(self, mock_datasource):
        """测试禁用缓存"""
        with patch.object(QueryEngine, '_execute_sql_query', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = (
                [[1, 'Alice']],
                ['id', 'name'],
            )
            engine = QueryEngine()
            result = await engine.execute(mock_datasource, 'SELECT * FROM users', use_cache=False)

            assert result.status == 'success'
            assert result.cached is False

    @pytest.mark.asyncio
    async def test_get_datasource_schema(self, mock_datasource):
        """测试获取数据源表结构"""
        with patch.object(QueryEngine, 'execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = QueryResult(
                columns=['table_name'],
                rows=[['users'], ['orders']],
                total=2,
                status='success',
            )
            engine = QueryEngine()
            schema = await engine.get_datasource_schema(mock_datasource)

            assert 'tables' in schema
            assert 'users' in schema['tables']
            assert 'orders' in schema['tables']


class TestExecuteQueryOnDatasource:
    """便捷函数测试"""

    @pytest.mark.asyncio
    async def test_execute_query_on_datasource(self):
        ds = MagicMock()
        ds.id = 1
        ds.name = 'TestDB'
        ds.db_type = 'mysql'
        ds.status = 1

        with patch.object(QueryEngine, 'execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = QueryResult(
                columns=['id'],
                rows=[[1]],
                total=1,
                status='success',
            )
            result = await execute_query_on_datasource(ds, 'SELECT 1')
            assert result.status == 'success'