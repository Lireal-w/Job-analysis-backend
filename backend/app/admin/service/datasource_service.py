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
from backend.core.conf import settings
from backend.utils.encrypt import AESCipher

# 初始化 AES 加密器，使用 TOKEN_SECRET_KEY 派生密钥
_aes_key = settings.TOKEN_SECRET_KEY.encode('utf-8').ljust(32, b'\0')[:32]
_aes_cipher = AESCipher(_aes_key)


def _encrypt_password(password: str | None) -> str | None:
    """加密密码"""
    if not password:
        return password
    return _aes_cipher.encrypt(password).hex()


def _decrypt_password(password: str | None) -> str | None:
    """解密密码"""
    if not password:
        return password
    try:
        return _aes_cipher.decrypt(bytes.fromhex(password))
    except Exception:
        return password


def _decrypt_datasource_password(datasource: Datasource) -> None:
    """原地解密数据源对象的密码字段"""
    if datasource.password:
        datasource.password = _decrypt_password(datasource.password)


class DatasourceService:
    """数据源服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int, dept_id: int | None = None) -> Datasource:
        datasource = await datasource_dao.get(db, pk, dept_id=dept_id)
        if not datasource:
            raise errors.NotFoundError(msg='数据源不存在')
        _decrypt_datasource_password(datasource)
        return datasource

    @staticmethod
    async def get_all(*, db: AsyncSession, dept_id: int | None = None) -> Sequence[Datasource]:
        datasources = await datasource_dao.get_all(db, dept_id=dept_id)
        for ds in datasources:
            _decrypt_datasource_password(ds)
        return datasources

    @staticmethod
    async def get_list(
        *, db: AsyncSession, name: str | None = None, db_type: str | None = None, dept_id: int | None = None
    ) -> dict[str, Any]:
        select = await datasource_dao.get_select(name=name, db_type=db_type, dept_id=dept_id)
        page_data = await paging_data(db, select)
        # 解密返回数据中的密码
        items = page_data.get('items', [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and item.get('password'):
                    item['password'] = _decrypt_password(item['password'])
                elif hasattr(item, 'password') and item.password:
                    item.password = _decrypt_password(item.password)
        return page_data

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateDatasourceParam) -> None:
        existing = await datasource_dao.get_by_name(db, obj.name)
        if existing:
            raise errors.ConflictError(msg='数据源名称已存在')
        # 加密密码
        if obj.password:
            obj.password = _encrypt_password(obj.password)
        await datasource_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateDatasourceParam) -> int:
        datasource = await datasource_dao.get(db, pk)
        if not datasource:
            raise errors.NotFoundError(msg='数据源不存在')
        # 加密密码（如果有提供）
        if obj.password is not None:
            obj.password = _encrypt_password(obj.password)
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
            DatasourceType.API_REST: _test_api_rest,
            DatasourceType.FILE_CSV: _test_file_csv,
            DatasourceType.FILE_EXCEL: _test_file_excel,
            DatasourceType.FILE_JSON: _test_file_json,
            DatasourceType.KAFKA: _test_kafka,
            DatasourceType.S3: _test_s3,
            DatasourceType.ELASTICSEARCH: _test_elasticsearch,
            DatasourceType.CLICKHOUSE: _test_clickhouse,
            DatasourceType.FTP: _test_ftp,
            DatasourceType.SFTP: _test_sftp,
            DatasourceType.HTTP_WEBHOOK: _test_http_webhook,
            DatasourceType.RABBITMQ: _test_rabbitmq,
            DatasourceType.HIVE: _test_hive,
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


def _test_api_rest(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 REST API 连接"""
    try:
        import httpx

        url = obj.host
        if obj.extra_params:
            try:
                params = json.loads(obj.extra_params)
                if isinstance(params, dict):
                    from urllib.parse import urlencode
                    url = url.rstrip('?') + '?' + urlencode(params)
            except (json.JSONDecodeError, TypeError):
                pass

        with httpx.Client(timeout=10) as client:
            response = client.get(url)
            if response.status_code < 500:
                return {'success': True, 'message': f'API 连接成功 (HTTP {response.status_code})', 'data': {'status_code': response.status_code}}
            return {'success': False, 'message': f'API 返回错误状态码: {response.status_code}'}
    except ImportError:
        try:
            import requests

            url = obj.host
            response = requests.get(url, timeout=10)
            if response.status_code < 500:
                return {'success': True, 'message': f'API 连接成功 (HTTP {response.status_code})', 'data': {'status_code': response.status_code}}
            return {'success': False, 'message': f'API 返回错误状态码: {response.status_code}'}
        except ImportError:
            return {'success': False, 'message': '请安装 httpx 或 requests 库: pip install httpx'}
        except Exception as e:
            return {'success': False, 'message': f'API 连接失败: {str(e)}'}
    except Exception as e:
        return {'success': False, 'message': f'API 连接失败: {str(e)}'}


def _test_file_csv(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 CSV 文件访问"""
    import os

    file_path = obj.host or obj.database_name or ''
    if not file_path:
        return {'success': False, 'message': '请提供文件路径'}
    if not os.path.exists(file_path):
        return {'success': False, 'message': f'文件不存在: {file_path}'}
    if not os.access(file_path, os.R_OK):
        return {'success': False, 'message': f'文件不可读: {file_path}'}
    try:
        import csv

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            row_count = sum(1 for _ in reader)
        return {'success': True, 'message': f'CSV 文件可访问', 'data': {'path': file_path, 'rows': row_count}}
    except Exception as e:
        return {'success': False, 'message': f'CSV 文件读取失败: {str(e)}'}


def _test_file_excel(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 Excel 文件访问"""
    import os

    file_path = obj.host or obj.database_name or ''
    if not file_path:
        return {'success': False, 'message': '请提供文件路径'}
    if not os.path.exists(file_path):
        return {'success': False, 'message': f'文件不存在: {file_path}'}
    if not os.access(file_path, os.R_OK):
        return {'success': False, 'message': f'文件不可读: {file_path}'}
    try:
        import openpyxl

        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheet_names = wb.sheetnames
        sheet_count = len(sheet_names)
        wb.close()
        return {'success': True, 'message': 'Excel 文件可访问', 'data': {'path': file_path, 'sheets': sheet_count, 'sheet_names': sheet_names}}
    except ImportError:
        return {'success': False, 'message': '请安装 openpyxl 库: pip install openpyxl'}
    except Exception as e:
        return {'success': False, 'message': f'Excel 文件读取失败: {str(e)}'}


def _test_file_json(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 JSON 文件访问"""
    import os

    file_path = obj.host or obj.database_name or ''
    if not file_path:
        return {'success': False, 'message': '请提供文件路径'}
    if not os.path.exists(file_path):
        return {'success': False, 'message': f'文件不存在: {file_path}'}
    if not os.access(file_path, os.R_OK):
        return {'success': False, 'message': f'文件不可读: {file_path}'}
    try:
        import json as json_lib

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json_lib.load(f)
        data_type = type(data).__name__
        size = len(data) if isinstance(data, (list, dict)) else 0
        return {'success': True, 'message': 'JSON 文件可访问', 'data': {'path': file_path, 'type': data_type, 'size': size}}
    except json.JSONDecodeError as e:
        return {'success': False, 'message': f'JSON 解析失败: {str(e)}'}
    except Exception as e:
        return {'success': False, 'message': f'JSON 文件读取失败: {str(e)}'}


def _test_kafka(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 Kafka 连接"""
    import socket

    host = obj.host or 'localhost'
    port = obj.port or 9092
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return {'success': True, 'message': f'Kafka Broker 可达 ({host}:{port})', 'data': {'host': host, 'port': port}}
        return {'success': False, 'message': f'Kafka Broker 不可达 ({host}:{port})'}
    except Exception as e:
        return {'success': False, 'message': f'Kafka 连接失败: {str(e)}'}


def _test_s3(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 S3/OSS 连接"""
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError

        bucket = obj.database_name or obj.host or ''
        endpoint_url = obj.extra_params if obj.extra_params else None
        try:
            extra = json.loads(obj.extra_params) if obj.extra_params else {}
        except (json.JSONDecodeError, TypeError):
            extra = {}

        client_kwargs = {}
        if endpoint_url:
            client_kwargs['endpoint_url'] = endpoint_url

        if obj.username and obj.password:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=obj.username,
                aws_secret_access_key=obj.password,
                **client_kwargs,
            )
        else:
            s3_client = boto3.client('s3', **client_kwargs)

        if bucket:
            response = s3_client.list_objects_v2(Bucket=bucket, MaxKeys=5)
            object_count = response.get('KeyCount', 0)
            return {'success': True, 'message': f'S3 连接成功，Bucket: {bucket}', 'data': {'bucket': bucket, 'object_count': object_count}}
        else:
            buckets = s3_client.list_buckets()
            bucket_list = [b['Name'] for b in buckets.get('Buckets', [])]
            return {'success': True, 'message': 'S3 连接成功', 'data': {'buckets': bucket_list}}
    except ImportError:
        return {'success': False, 'message': '请安装 boto3 库: pip install boto3'}
    except NoCredentialsError:
        return {'success': False, 'message': 'S3 凭证无效'}
    except ClientError as e:
        return {'success': False, 'message': f'S3 访问失败: {e.response["Error"]["Message"]}'}
    except Exception as e:
        return {'success': False, 'message': f'S3 连接失败: {str(e)}'}


def _test_elasticsearch(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 Elasticsearch 连接"""
    try:
        import httpx

        url = f'http://{obj.host}:{obj.port}'
        if obj.username and obj.password:
            from httpx import BasicAuth
            auth = BasicAuth(obj.username, obj.password)
            with httpx.Client(timeout=10, auth=auth) as client:
                response = client.get(url)
        else:
            with httpx.Client(timeout=10) as client:
                response = client.get(url)

        if response.status_code == 200:
            info = response.json()
            version = info.get('version', {}).get('number', '')
            return {'success': True, 'message': 'Elasticsearch 连接成功', 'data': {'version': version, 'cluster_name': info.get('cluster_name', '')}}
        return {'success': False, 'message': f'Elasticsearch 返回状态码: {response.status_code}'}
    except ImportError:
        return {'success': False, 'message': '请安装 httpx 库: pip install httpx'}
    except Exception as e:
        return {'success': False, 'message': f'Elasticsearch 连接失败: {str(e)}'}


def _test_clickhouse(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 ClickHouse 连接"""
    try:
        import httpx

        url = f'http://{obj.host}:{obj.port}'
        params = {}
        if obj.database_name:
            params['database'] = obj.database_name

        with httpx.Client(timeout=10) as client:
            if obj.username and obj.password:
                response = client.get(url, params=params, headers={'X-ClickHouse-User': obj.username, 'X-ClickHouse-Key': obj.password})
            else:
                response = client.get(url, params=params)

        if response.status_code == 200:
            return {'success': True, 'message': f'ClickHouse 连接成功 (HTTP {response.status_code})', 'data': {'host': obj.host, 'port': obj.port}}
        return {'success': False, 'message': f'ClickHouse 返回状态码: {response.status_code}'}
    except ImportError:
        return {'success': False, 'message': '请安装 httpx 库: pip install httpx'}
    except Exception as e:
        return {'success': False, 'message': f'ClickHouse 连接失败: {str(e)}'}


def _test_ftp(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 FTP 连接"""
    try:
        from ftplib import FTP

        ftp = FTP()
        ftp.connect(obj.host, obj.port or 21, timeout=10)
        ftp.login(obj.username or 'anonymous', obj.password or '')
        welcome = ftp.welcome
        dir_list = ftp.nlst()[:10] if ftp.nlst() else []
        ftp.quit()
        return {'success': True, 'message': 'FTP 连接成功', 'data': {'welcome': welcome, 'dir_list': dir_list}}
    except ImportError:
        return {'success': False, 'message': 'FTP 模块加载失败'}
    except Exception as e:
        return {'success': False, 'message': f'FTP 连接失败: {str(e)}'}


def _test_sftp(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 SFTP 连接"""
    try:
        import paramiko

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=obj.host,
            port=obj.port or 22,
            username=obj.username or 'root',
            password=obj.password or '',
            timeout=10,
        )
        sftp = ssh.open_sftp()
        dir_list = sftp.listdir('.')[:10]
        sftp.close()
        ssh.close()
        return {'success': True, 'message': 'SFTP 连接成功', 'data': {'dir_list': dir_list}}
    except ImportError:
        return {'success': False, 'message': '请安装 paramiko 库: pip install paramiko'}
    except Exception as e:
        return {'success': False, 'message': f'SFTP 连接失败: {str(e)}'}


def _test_http_webhook(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 HTTP Webhook 连接"""
    try:
        import httpx

        url = obj.host
        if not url.startswith(('http://', 'https://')):
            url = f'http://{url}'

        payload = {'test': True, 'timestamp': timezone.now().isoformat()}
        with httpx.Client(timeout=10) as client:
            response = client.post(url, json=payload)

        if response.status_code < 500:
            return {'success': True, 'message': f'Webhook 可达 (HTTP {response.status_code})', 'data': {'status_code': response.status_code}}
        return {'success': False, 'message': f'Webhook 返回错误状态码: {response.status_code}'}
    except ImportError:
        return {'success': False, 'message': '请安装 httpx 库: pip install httpx'}
    except Exception as e:
        return {'success': False, 'message': f'Webhook 连接失败: {str(e)}'}


def _test_rabbitmq(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 RabbitMQ 连接"""
    try:
        import httpx

        management_port = obj.port or 15672
        url = f'http://{obj.host}:{management_port}/api/overview'
        auth_username = obj.username or 'guest'
        auth_password = obj.password or 'guest'

        with httpx.Client(timeout=10, auth=(auth_username, auth_password)) as client:
            response = client.get(url)

        if response.status_code == 200:
            data = response.json()
            version = data.get('rabbitmq_version', '')
            cluster = data.get('cluster_name', '')
            return {'success': True, 'message': 'RabbitMQ 连接成功', 'data': {'version': version, 'cluster_name': cluster}}
        return {'success': False, 'message': f'RabbitMQ 返回状态码: {response.status_code}'}
    except ImportError:
        # Fallback: try socket connection
        import socket

        host = obj.host or 'localhost'
        port = obj.port or 5672
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return {'success': True, 'message': f'RabbitMQ AMQP 端口可达 ({host}:{port})', 'data': {'host': host, 'port': port}}
            return {'success': False, 'message': f'RabbitMQ AMQP 端口不可达 ({host}:{port})'}
        except Exception as e:
            return {'success': False, 'message': f'RabbitMQ 连接失败: {str(e)}'}
    except Exception as e:
        return {'success': False, 'message': f'RabbitMQ 连接失败: {str(e)}'}


def _test_hive(obj: DatasourceTestParam) -> dict[str, Any]:
    """测试 Hive 连接"""
    import socket

    host = obj.host or 'localhost'
    port = obj.port or 10000
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return {'success': True, 'message': f'Hive Server 可达 ({host}:{port})', 'data': {'host': host, 'port': port}}
        return {'success': False, 'message': f'Hive Server 不可达 ({host}:{port})'}
    except Exception as e:
        return {'success': False, 'message': f'Hive 连接失败: {str(e)}'}


datasource_service: DatasourceService = DatasourceService()
