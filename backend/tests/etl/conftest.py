"""ETL 引擎测试共享 Fixtures"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def sample_data() -> list[dict[str, Any]]:
    """基础测试数据"""
    return [
        {'id': 1, 'name': 'Alice', 'age': 30, 'city': 'Beijing', 'salary': 12000},
        {'id': 2, 'name': 'Bob', 'age': 25, 'city': 'Shanghai', 'salary': 9000},
        {'id': 3, 'name': 'Charlie', 'age': 35, 'city': 'Beijing', 'salary': 15000},
        {'id': 4, 'name': 'Diana', 'age': 28, 'city': 'Guangzhou', 'salary': 11000},
        {'id': 5, 'name': 'Eve', 'age': 32, 'city': 'Shanghai', 'salary': 13000},
        {'id': 6, 'name': 'Frank', 'age': 40, 'city': 'Beijing', 'salary': None},
    ]


@pytest.fixture
def sample_orders() -> list[dict[str, Any]]:
    """订单测试数据"""
    return [
        {'order_id': 1, 'user_id': 1, 'amount': 100, 'status': 'completed'},
        {'order_id': 2, 'user_id': 2, 'amount': 200, 'status': 'pending'},
        {'order_id': 3, 'user_id': 1, 'amount': 150, 'status': 'completed'},
        {'order_id': 4, 'user_id': 3, 'amount': 300, 'status': 'cancelled'},
        {'order_id': 5, 'user_id': 2, 'amount': 50, 'status': 'pending'},
    ]


@pytest.fixture
def sample_users() -> list[dict[str, Any]]:
    """用户测试数据 (用于 join 测试)"""
    return [
        {'id': 1, 'name': 'Alice', 'email': 'alice@test.com'},
        {'id': 2, 'name': 'Bob', 'email': 'bob@test.com'},
        {'id': 3, 'name': 'Charlie', 'email': 'charlie@test.com'},
        {'id': 5, 'name': 'Eve', 'email': 'eve@test.com'},
    ]


@pytest.fixture
def temp_csv_file() -> str:
    """创建临时 CSV 文件"""
    content = 'id,name,age,city\n1,Alice,30,Beijing\n2,Bob,25,Shanghai\n3,Charlie,35,Beijing\n'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(content)
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def temp_json_file() -> str:
    """创建临时 JSON 文件"""
    data = [
        {'id': 1, 'name': 'Alice', 'score': 95},
        {'id': 2, 'name': 'Bob', 'score': 87},
        {'id': 3, 'name': 'Charlie', 'score': 92},
    ]
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(data, f)
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def temp_text_file() -> str:
    """创建临时文本文件"""
    content = 'line1\nline2\nline3\nline4\n'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def temp_output_path() -> str:
    """临时输出文件路径"""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)
