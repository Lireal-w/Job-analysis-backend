"""查询引擎核心实现

负责连接数据源、执行 SQL 查询、返回结构化结果。

支持的数据库类型：
- MySQL (asyncmy)
- PostgreSQL (asyncpg)
- SQLite (aiosqlite)
- MSSQL (pyodbc)
- Oracle (oracledb)
- ClickHouse (http)
- Elasticsearch (http)

安全措施：
- 只允许 SELECT 语句，禁止 DDL/DML
- 查询超时控制（默认 30 秒）
- 结果行数限制（默认 10000 行）
- SQL 注入关键字检测
"""

from __future__ import annotations

import json
import re
import time
import traceback
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from backend.app.admin.service.datasource_service import _decrypt_password


# ── 常量 ──────────────────────────────────────────────────────

# 禁止的 SQL 关键字（防止 SQL 注入和危险操作）
FORBIDDEN_SQL_KEYWORDS = [
    'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
    'TRUNCATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE',
    'INTO', 'MERGE', 'CALL', 'LOCK', 'UNLOCK',
]

# 支持的数据库类型及其异步驱动
SUPPORTED_DB_DRIVERS = {
    'mysql': 'mysql+asyncmy',
    'postgresql': 'postgresql+asyncpg',
    'sqlite': 'sqlite+aiosqlite',
    'mssql': 'mssql+pyodbc',
    'oracle': 'oracle+oracledb',
    'clickhouse': 'clickhouse',
    'elasticsearch': 'elasticsearch',
}

# 默认查询超时（秒）
DEFAULT_QUERY_TIMEOUT = 30

# 默认结果行数限制
DEFAULT_RESULT_LIMIT = 10000

# 缓存 TTL（秒）
CACHE_TTL = 300  # 5 分钟


# ── 数据类 ────────────────────────────────────────────────────

@dataclass
class QueryResult:
    """查询结果"""

    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    total: int = 0
    duration: float = 0.0
    status: str = 'success'
    error_message: str | None = None
    datasource_name: str | None = None
    datasource_type: str | None = None
    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            'columns': self.columns,
            'rows': self.rows,
            'total': self.total,
            'duration': self.duration,
            'status': self.status,
            'error_message': self.error_message,
            'datasource_name': self.datasource_name,
            'datasource_type': self.datasource_type,
            'cached': self.cached,
        }


# ── SQL 安全检查 ──────────────────────────────────────────────

def validate_sql_safety(sql: str) -> tuple[bool, str]:
    """验证 SQL 安全性

    只允许 SELECT 语句，禁止所有 DDL/DML 操作。

    Args:
        sql: SQL 语句

    Returns:
        (is_safe, error_message) 元组
    """
    if not sql or not sql.strip():
        return False, 'SQL 语句不能为空'

    # 去除注释
    cleaned = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip()

    if not cleaned:
        return False, 'SQL 语句不能只包含注释'

    # 检查是否以 SELECT 开头
    first_word = cleaned.split()[0].upper() if cleaned.split() else ''
    if first_word != 'SELECT':
        return False, f'只允许 SELECT 查询，当前语句以 "{first_word}" 开头'

    # 检查是否包含禁止的关键字
    # 使用分号分割检查多条语句
    statements = [s.strip() for s in cleaned.split(';') if s.strip()]
    for stmt in statements:
        upper_stmt = stmt.upper()
        for keyword in FORBIDDEN_SQL_KEYWORDS:
            # 使用单词边界匹配，避免误判（如 SELECTED 包含 SELECT）
            pattern = rf'\b{keyword}\b'
            if re.search(pattern, upper_stmt):
                return False, f'SQL 语句包含禁止的关键字: {keyword}'

    # 检查是否包含子查询中的危险操作
    # 防止 SELECT ... ; DROP TABLE ... 形式的注入
    if ';' in sql.strip().rstrip(';'):
        # 多条语句，检查每条
        parts = sql.split(';')
        for part in parts:
            part = part.strip()
            if part and not part.upper().startswith('SELECT'):
                return False, '只允许 SELECT 查询，不允许执行多条语句'

    return True, ''


# ── 数据库 URL 构建 ────────────────────────────────────────────

def build_db_url(datasource: Any, password: str | None) -> str:
    """构建数据库连接 URL

    Args:
        datasource: 数据源 ORM 对象
        password: 解密后的密码

    Returns:
        SQLAlchemy 异步连接 URL
    """
    db_type = datasource.db_type

    if db_type == 'mysql':
        return (
            f'mysql+asyncmy://{datasource.username}:{password}'
            f'@{datasource.host}:{datasource.port}/{datasource.database_name}'
        )
    elif db_type == 'postgresql':
        return (
            f'postgresql+asyncpg://{datasource.username}:{password}'
            f'@{datasource.host}:{datasource.port}/{datasource.database_name}'
        )
    elif db_type == 'sqlite':
        db_path = datasource.database_name or ':memory:'
        return f'sqlite+aiosqlite:///{db_path}'
    elif db_type == 'mssql':
        return (
            f'mssql+pyodbc://{datasource.username}:{password}'
            f'@{datasource.host}:{datasource.port}/{datasource.database_name}'
            f'?driver=ODBC+Driver+17+for+SQL+Server'
        )
    elif db_type == 'oracle':
        return (
            f'oracle+oracledb://{datasource.username}:{password}'
            f'@{datasource.host}:{datasource.port}/{datasource.database_name}'
        )
    else:
        raise ValueError(f'不支持的数据库类型: {db_type}')


# ── 查询引擎 ──────────────────────────────────────────────────

class QueryEngine:
    """查询引擎

    负责连接数据源并执行 SQL 查询。

    用法：
        engine = QueryEngine()
        result = await engine.execute(
            datasource=datasource,
            sql='SELECT * FROM users LIMIT 10',
            limit=100,
            timeout=30,
        )
    """

    def __init__(self) -> None:
        self._engine_cache: dict[int, Any] = {}

    async def execute(
        self,
        datasource: Any,
        sql: str,
        limit: int = DEFAULT_RESULT_LIMIT,
        timeout: int = DEFAULT_QUERY_TIMEOUT,
        use_cache: bool = True,
    ) -> QueryResult:
        """执行 SQL 查询

        Args:
            datasource: 数据源 ORM 对象
            sql: SQL 查询语句
            limit: 结果行数限制
            timeout: 查询超时（秒）
            use_cache: 是否使用缓存

        Returns:
            QueryResult 查询结果
        """
        start_time = time.time()
        result = QueryResult(
            datasource_name=datasource.name,
            datasource_type=datasource.db_type,
        )

        # 1. 验证 SQL 安全性
        is_safe, error_msg = validate_sql_safety(sql)
        if not is_safe:
            result.status = 'failed'
            result.error_message = error_msg
            result.duration = round(time.time() - start_time, 4)
            return result

        # 2. 检查缓存
        if use_cache:
            cached_result = await self._get_cache(datasource.id, sql, limit)
            if cached_result is not None:
                cached_result.cached = True
                cached_result.duration = round(time.time() - start_time, 4)
                return cached_result

        # 3. 检查数据源类型是否支持
        db_type = datasource.db_type
        if db_type not in SUPPORTED_DB_DRIVERS and db_type not in ['clickhouse', 'elasticsearch']:
            result.status = 'failed'
            result.error_message = f'不支持的数据库类型: {db_type}，支持: {", ".join(SUPPORTED_DB_DRIVERS.keys())}'
            result.duration = round(time.time() - start_time, 4)
            return result

        # 4. 执行查询
        try:
            if db_type in ['clickhouse']:
                rows, columns = await self._execute_http_query(datasource, sql, limit, timeout)
            elif db_type in ['elasticsearch']:
                rows, columns = await self._execute_elasticsearch_query(datasource, sql, limit, timeout)
            else:
                rows, columns = await self._execute_sql_query(datasource, sql, limit, timeout)

            result.columns = columns
            result.rows = rows
            result.total = len(rows)
            result.status = 'success'

        except Exception as e:
            logger.error(f'[QueryEngine] 查询执行失败: {e}')
            logger.error(traceback.format_exc())
            result.status = 'failed'
            result.error_message = f'{type(e).__name__}: {e}'

        result.duration = round(time.time() - start_time, 4)

        # 5. 缓存结果
        if use_cache and result.status == 'success':
            await self._set_cache(datasource.id, sql, limit, result)

        return result

    async def _execute_sql_query(
        self,
        datasource: Any,
        sql: str,
        limit: int,
        timeout: int,
    ) -> tuple[list[list[Any]], list[str]]:
        """通过 SQLAlchemy 执行 SQL 查询

        Args:
            datasource: 数据源 ORM 对象
            sql: SQL 查询语句
            limit: 结果行数限制
            timeout: 查询超时（秒）

        Returns:
            (rows, columns) 元组
        """
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        password = _decrypt_password(datasource.password)
        url = build_db_url(datasource, password)

        # 添加额外参数
        if datasource.extra_params:
            try:
                extra = json.loads(datasource.extra_params) if isinstance(datasource.extra_params, str) else datasource.extra_params
                if isinstance(extra, dict):
                    # 构建查询参数
                    params = '&'.join(f'{k}={v}' for k, v in extra.items())
                    if '?' in url:
                        url = f'{url}&{params}'
                    else:
                        url = f'{url}?{params}'
            except (json.JSONDecodeError, TypeError):
                pass

        # 添加 LIMIT（如果 SQL 中没有 LIMIT）
        sql_upper = sql.upper().rstrip(';')
        if 'LIMIT' not in sql_upper:
            sql = f'{sql.rstrip(";")} LIMIT {limit}'

        engine = create_async_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )

        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                result = await session.execute(text(sql))
                columns = list(result.keys())
                rows = [list(row) for row in result.fetchall()]
                return rows, columns
        finally:
            await engine.dispose()

    async def _execute_http_query(
        self,
        datasource: Any,
        sql: str,
        limit: int,
        timeout: int,
    ) -> tuple[list[list[Any]], list[str]]:
        """通过 HTTP API 执行 ClickHouse 查询

        Args:
            datasource: 数据源 ORM 对象
            sql: SQL 查询语句
            limit: 结果行数限制
            timeout: 查询超时（秒）

        Returns:
            (rows, columns) 元组
        """
        import httpx

        password = _decrypt_password(datasource.password)
        url = f'http://{datasource.host}:{datasource.port}'

        params = {
            'query': f'{sql.rstrip(";")} LIMIT {limit}',
            'user': datasource.username,
            'password': password or '',
            'database': datasource.database_name or 'default',
        }

        headers = {'Content-Type': 'text/plain'}

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f'{url}/',
                params=params,
                headers=headers,
            )
            response.raise_for_status()

        # 解析 ClickHouse TabSeparated 格式
        lines = response.text.strip().split('\n')
        if not lines:
            return [], []

        # 第一行是列名（如果启用 headers）
        # ClickHouse 默认返回 TabSeparated 格式
        columns = []
        rows = []

        for i, line in enumerate(lines):
            values = line.split('\t')
            if i == 0:
                # 尝试从第一行获取列名
                # ClickHouse 默认不返回列名，使用列索引
                columns = [f'col_{j}' for j in range(len(values))]
                rows.append(values)
            else:
                rows.append(values)

        return rows, columns

    async def _execute_elasticsearch_query(
        self,
        datasource: Any,
        sql: str,
        limit: int,
        timeout: int,
    ) -> tuple[list[list[Any]], list[str]]:
        """通过 Elasticsearch SQL API 执行查询

        Args:
            datasource: 数据源 ORM 对象
            sql: SQL 查询语句
            limit: 结果行数限制
            timeout: 查询超时（秒）

        Returns:
            (rows, columns) 元组
        """
        import httpx

        password = _decrypt_password(datasource.password)
        url = f'http://{datasource.host}:{datasource.port}'

        auth = None
        if datasource.username and password:
            auth = (datasource.username, password)

        payload = {
            'query': sql,
            'fetch_size': limit,
        }

        headers = {'Content-Type': 'application/json'}

        async with httpx.AsyncClient(timeout=timeout, auth=auth) as client:
            response = await client.post(
                f'{url}/_sql',
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

        data = response.json()
        columns = [col.get('name', f'col_{i}') for i, col in enumerate(data.get('columns', []))]
        rows = data.get('rows', [])

        return rows, columns

    async def _get_cache(
        self,
        datasource_id: int,
        sql: str,
        limit: int,
    ) -> QueryResult | None:
        """从 Redis 获取缓存结果"""
        try:
            from backend.database.redis import redis_client
            import hashlib

            cache_key = f'query:cache:{datasource_id}:{hashlib.md5(f"{sql}:{limit}".encode()).hexdigest()}'
            cached = await redis_client.get(cache_key)
            if cached:
                data = json.loads(cached)
                return QueryResult(**data)
        except Exception as e:
            logger.debug(f'[QueryEngine] 缓存读取失败: {e}')
        return None

    async def _set_cache(
        self,
        datasource_id: int,
        sql: str,
        limit: int,
        result: QueryResult,
    ) -> None:
        """将查询结果写入 Redis 缓存"""
        try:
            from backend.database.redis import redis_client
            import hashlib

            cache_key = f'query:cache:{datasource_id}:{hashlib.md5(f"{sql}:{limit}".encode()).hexdigest()}'
            # 不缓存大结果集
            if result.total <= 1000:
                await redis_client.setex(cache_key, CACHE_TTL, json.dumps(result.to_dict(), default=str))
        except Exception as e:
            logger.debug(f'[QueryEngine] 缓存写入失败: {e}')

    async def get_datasource_schema(
        self,
        datasource: Any,
        schema_name: str | None = None,
    ) -> dict[str, Any]:
        """获取数据源的表结构信息

        Args:
            datasource: 数据源 ORM 对象
            schema_name: 数据库 schema 名称（可选）

        Returns:
            包含表名和列信息的字典
        """
        db_type = datasource.db_type

        if db_type == 'mysql':
            sql = 'SHOW TABLES'
        elif db_type == 'postgresql':
            sql = f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema_name or 'public'}'"
        elif db_type == 'mssql':
            sql = 'SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = \'BASE TABLE\''
        elif db_type == 'oracle':
            sql = 'SELECT table_name FROM user_tables'
        elif db_type == 'sqlite':
            sql = "SELECT name FROM sqlite_master WHERE type='table'"
        else:
            return {'error': f'不支持的数据库类型: {db_type}'}

        result = await self.execute(datasource, sql, limit=1000, use_cache=False)
        if result.status != 'success':
            return {'error': result.error_message}

        tables = [row[0] for row in result.rows]
        return {
            'datasource_id': datasource.id,
            'datasource_name': datasource.name,
            'db_type': db_type,
            'tables': tables,
        }


# ── 便捷函数 ──────────────────────────────────────────────────

async def execute_query_on_datasource(
    datasource: Any,
    sql: str,
    limit: int = DEFAULT_RESULT_LIMIT,
    timeout: int = DEFAULT_QUERY_TIMEOUT,
) -> QueryResult:
    """在数据源上执行 SQL 查询的便捷函数

    Args:
        datasource: 数据源 ORM 对象
        sql: SQL 查询语句
        limit: 结果行数限制
        timeout: 查询超时（秒）

    Returns:
        QueryResult 查询结果
    """
    engine = QueryEngine()
    return await engine.execute(datasource, sql, limit=limit, timeout=timeout)