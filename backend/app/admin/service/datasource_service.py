import json

from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from backend.app.admin.crud.crud_datasource import datasource_dao
from backend.app.admin.model import Datasource
from backend.app.admin.schema.datasource import (
    CreateDatasourceParam,
    DatasourceTestParam,
    UpdateDatasourceParam,
)
from backend.common.enums import DatasourceType
from backend.common.exception import errors
from backend.common.pagination import paging_data


class DatasourceService:
    """数据源服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> Datasource:
        datasource = await datasource_dao.get(db, pk)
        if not datasource:
            raise errors.NotFoundError(msg='数据源不存在')
        return datasource

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[Datasource]:
        return await datasource_dao.get_all(db)

    @staticmethod
    async def get_list(
        *, db: AsyncSession, name: str | None = None, db_type: str | None = None
    ) -> dict[str, Any]:
        select = await datasource_dao.get_select(name=name, db_type=db_type)
        return await paging_data(db, select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateDatasourceParam) -> None:
        existing = await datasource_dao.get_by_name(db, obj.name)
        if existing:
            raise errors.ConflictError(msg='数据源名称已存在')
        await datasource_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateDatasourceParam) -> int:
        datasource = await datasource_dao.get(db, pk)
        if not datasource:
            raise errors.NotFoundError(msg='数据源不存在')
        return await datasource_dao.update(db, pk, obj)

    @staticmethod
    async def update_status(*, db: AsyncSession, pk: int, status: int) -> int:
        datasource = await datasource_dao.get(db, pk)
        if not datasource:
            raise errors.NotFoundError(msg='数据源不存在')
        return await datasource_dao.update_status(db, pk, status)

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        return await datasource_dao.delete(db, pks)

    @staticmethod
    async def test_connection(*, obj: DatasourceTestParam) -> dict[str, Any]:
        """
        测试数据源连接

        根据不同的数据库类型，采用对应的驱动进行连接测试
        """
        testers = {
            DatasourceType.MYSQL: _test_mysql,
            DatasourceType.POSTGRESQL: _test_postgresql,
            DatasourceType.SQLITE: _test_sqlite,
            DatasourceType.MONGODB: _test_mongodb,
            DatasourceType.REDIS: _test_redis,
            DatasourceType.MSSQL: _test_mssql,
            DatasourceType.ORACLE: _test_oracle,
        }

        tester = testers.get(obj.db_type)
        if not tester:
            return {'success': False, 'message': f'不支持的数据库类型: {obj.db_type}'}

        try:
            result = await run_in_threadpool(tester, obj)
            return result
        except Exception as e:
            return {'success': False, 'message': f'连接失败: {str(e)}'}


# ── 各数据库连接测试函数 ────────────────────────────────────────


def _build_extra_params(obj: DatasourceTestParam) -> dict:
    """解析额外连接参数"""
    if not obj.extra_params:
        return {}
    try:
        return json.loads(obj.extra_params)
    except json.JSONDecodeError:
        return {}


def _test_mysql(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 MySQL 连接"""
    import pymysql

    try:
        conn = pymysql.connect(
            host=obj.host,
            port=obj.port,
            user=obj.username or 'root',
            password=obj.password or '',
            database=obj.database_name or '',
            connect_timeout=10,
        )
        version = conn.get_server_info()
        conn.close()
        return {'success': True, 'message': 'MySQL 连接成功', 'data': {'version': version}}
    except pymysql.err.OperationalError as e:
        return {'success': False, 'message': f'MySQL 连接失败: {e.args[1]}' if len(e.args) > 1 else str(e)}
    except Exception as e:
        return {'success': False, 'message': f'MySQL 连接失败: {str(e)}'}


def _test_postgresql(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 PostgreSQL 连接"""
    import psycopg

    try:
        conn_info = (
            f'host={obj.host} port={obj.port} '
            f'user={obj.username or "postgres"} password={obj.password or ""} '
            f'connect_timeout=10'
        )
        if obj.database_name:
            conn_info += f' dbname={obj.database_name}'

        conn = psycopg.connect(conn_info)
        cur = conn.cursor()
        cur.execute('SELECT version()')
        version = cur.fetchone()[0]
        cur.close()
        conn.close()
        return {'success': True, 'message': 'PostgreSQL 连接成功', 'data': {'version': version}}
    except Exception as e:
        return {'success': False, 'message': f'PostgreSQL 连接失败: {str(e)}'}


def _test_sqlite(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 SQLite 连接"""
    import sqlite3

    try:
        db_path = obj.database_name or ':memory:'
        conn = sqlite3.connect(db_path, timeout=10)
        cur = conn.cursor()
        cur.execute('SELECT sqlite_version()')
        version = cur.fetchone()[0]
        conn.close()
        return {'success': True, 'message': 'SQLite 连接成功', 'data': {'version': version, 'path': db_path}}
    except Exception as e:
        return {'success': False, 'message': f'SQLite 连接失败: {str(e)}'}


def _test_mongodb(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 MongoDB 连接"""
    from pymongo import MongoClient

    try:
        uri = f'mongodb://{obj.host}:{obj.port}'
        if obj.username and obj.password:
            from urllib.parse import quote

            uri = f'mongodb://{quote(obj.username)}:{quote(obj.password)}@{obj.host}:{obj.port}'

        client = MongoClient(uri, serverSelectionTimeoutMS=10000)
        info = client.server_info()
        version = info.get('version', '')
        client.close()
        return {'success': True, 'message': 'MongoDB 连接成功', 'data': {'version': version}}
    except Exception as e:
        return {'success': False, 'message': f'MongoDB 连接失败: {str(e)}'}


def _test_redis(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 Redis 连接"""
    import redis as redis_py

    try:
        r = redis_py.Redis(
            host=obj.host,
            port=obj.port,
            password=obj.password or None,
            db=0,
            socket_timeout=10,
            socket_connect_timeout=10,
        )
        info = r.info()
        version = info.get('redis_version', '')
        ping = r.ping()
        r.close()
        if ping:
            return {'success': True, 'message': 'Redis 连接成功', 'data': {'version': version}}
        return {'success': False, 'message': 'Redis Ping 失败'}
    except Exception as e:
        return {'success': False, 'message': f'Redis 连接失败: {str(e)}'}


def _test_mssql(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 SQL Server 连接"""
    try:
        import pymssql

        conn = pymssql.connect(
            server=obj.host,
            port=obj.port,
            user=obj.username or 'sa',
            password=obj.password or '',
            database=obj.database_name or '',
            timeout=10,
        )
        cur = conn.cursor()
        cur.execute('SELECT @@VERSION')
        version = cur.fetchone()[0][:100]
        cur.close()
        conn.close()
        return {'success': True, 'message': 'SQL Server 连接成功', 'data': {'version': version}}
    except ImportError:
        return {'success': False, 'message': '请安装 pymssql 驱动: pip install pymssql'}
    except Exception as e:
        return {'success': False, 'message': f'SQL Server 连接失败: {str(e)}'}


def _test_oracle(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 Oracle 连接"""
    try:
        import cx_Oracle

        dsn = cx_Oracle.makedsn(obj.host, obj.port, service_name=obj.database_name or 'XE')
        conn = cx_Oracle.connect(
            user=obj.username or 'system',
            password=obj.password or '',
            dsn=dsn,
            timeout=10,
        )
        cur = conn.cursor()
        cur.execute('SELECT version FROM v$instance')
        version = cur.fetchone()[0]
        cur.close()
        conn.close()
        return {'success': True, 'message': 'Oracle 连接成功', 'data': {'version': version}}
    except ImportError:
        return {'success': False, 'message': '请安装 cx_Oracle 驱动: pip install cx_Oracle'}
    except Exception as e:
        return {'success': False, 'message': f'Oracle 连接失败: {str(e)}'}


datasource_service: DatasourceService = DatasourceService()
