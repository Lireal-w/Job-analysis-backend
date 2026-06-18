"""采集执行引擎测试配置"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def sample_source_config_db():
    """数据库源配置"""
    return {
        'type': 'database',
        'datasource_id': 1,
        'query': 'SELECT * FROM users',
    }


@pytest.fixture
def sample_source_config_api():
    """API 源配置"""
    return {
        'type': 'api',
        'url': 'https://api.example.com/data',
        'method': 'GET',
        'data_path': 'data.items',
    }


@pytest.fixture
def sample_source_config_csv():
    """CSV 源配置"""
    return {
        'type': 'file_csv',
        'file_path': '/tmp/test.csv',
        'delimiter': ',',
        'encoding': 'utf-8',
    }


@pytest.fixture
def sample_target_config_db():
    """数据库目标配置"""
    return {
        'datasource_id': 2,
        'table': 'target_table',
        'mode': 'insert',
        'batch_size': 100,
    }


@pytest.fixture
def sample_target_config_csv():
    """CSV 目标配置"""
    return {
        'file_path': '/tmp/output.csv',
        'encoding': 'utf-8-sig',
    }


@pytest.fixture
def sample_target_config_json():
    """JSON 目标配置"""
    return {
        'file_path': '/tmp/output.json',
        'indent': 2,
    }


@pytest.fixture
def sample_data():
    """示例数据"""
    return [
        {'id': 1, 'name': 'Alice', 'email': 'alice@example.com', 'updated_at': '2024-01-01'},
        {'id': 2, 'name': 'Bob', 'email': 'bob@example.com', 'updated_at': '2024-02-01'},
        {'id': 3, 'name': 'Charlie', 'email': 'charlie@example.com', 'updated_at': '2024-03-01'},
        {'id': 4, 'name': 'Diana', 'email': 'diana@example.com', 'updated_at': '2024-04-01'},
        {'id': 5, 'name': 'Eve', 'email': 'eve@example.com', 'updated_at': '2024-05-01'},
    ]


@pytest.fixture
def mock_datasource():
    """模拟数据源对象"""
    ds = MagicMock()
    ds.id = 1
    ds.name = 'test_datasource'
    ds.db_type = 'postgresql'
    ds.host = 'localhost'
    ds.port = 5432
    ds.database_name = 'testdb'
    ds.username = 'testuser'
    ds.password = 'encrypted_password'
    return ds