"""数据写入节点执行器单元测试"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.admin.service.etl.context import ETLContext
from backend.app.admin.service.etl.exceptions import ETLNodeError
from backend.app.admin.service.etl.nodes.load import (
    FileCSVLoadExecutor,
    FileJSONLoadExecutor,
    LogLoadExecutor,
)


@pytest.mark.asyncio
class TestFileCSVLoad:
    """CSV 文件写入测试"""

    async def test_write_csv(self, sample_data, temp_output_path) -> None:
        executor = FileCSVLoadExecutor('csv_w1', {
            'file_path': temp_output_path,
        })
        ctx = ETLContext()
        await executor.execute(ctx, sample_data)

        # 验证文件存在且内容正确
        assert Path(temp_output_path).exists()
        with open(temp_output_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        assert 'Alice' in content
        assert 'Beijing' in content
        assert content.startswith('id,name,age,city,salary')

    async def test_write_empty_data(self, temp_output_path) -> None:
        executor = FileCSVLoadExecutor('csv_w2', {
            'file_path': temp_output_path,
        })
        ctx = ETLContext()
        await executor.execute(ctx, [])
        # 空数据也应该创建空文件
        assert Path(temp_output_path).exists()

    async def test_missing_file_path(self, sample_data) -> None:
        executor = FileCSVLoadExecutor('csv_w3', {'file_path': ''})
        ctx = ETLContext()
        with pytest.raises(ETLNodeError, match='文件路径不能为空'):
            await executor.execute(ctx, sample_data)


@pytest.mark.asyncio
class TestFileJSONLoad:
    """JSON 文件写入测试"""

    async def test_write_json(self, sample_data, temp_output_path) -> None:
        json_path = temp_output_path.replace('.csv', '.json')
        executor = FileJSONLoadExecutor('json_w1', {'file_path': json_path})
        ctx = ETLContext()
        await executor.execute(ctx, sample_data)

        assert Path(json_path).exists()
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert len(data) == 6
        assert data[0]['name'] == 'Alice'
        Path(json_path).unlink(missing_ok=True)

    async def test_write_empty_data(self, temp_output_path) -> None:
        json_path = temp_output_path.replace('.csv', '.json')
        executor = FileJSONLoadExecutor('json_w2', {'file_path': json_path})
        ctx = ETLContext()
        await executor.execute(ctx, [])
        assert Path(json_path).exists()
        Path(json_path).unlink(missing_ok=True)

    async def test_missing_file_path(self, sample_data) -> None:
        executor = FileJSONLoadExecutor('json_w3', {'file_path': ''})
        ctx = ETLContext()
        with pytest.raises(ETLNodeError, match='文件路径不能为空'):
            await executor.execute(ctx, sample_data)


@pytest.mark.asyncio
class TestLogLoad:
    """日志输出测试 (仅验证不崩溃)"""

    async def test_log_output(self, sample_data) -> None:
        executor = LogLoadExecutor('log1', {})
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 6
        assert result == sample_data

    async def test_log_empty(self) -> None:
        executor = LogLoadExecutor('log2', {})
        ctx = ETLContext()
        result = await executor.execute(ctx, [])
        assert result == []

    async def test_log_with_preview_limit(self, sample_data) -> None:
        executor = LogLoadExecutor('log3', {'preview_limit': 3})
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 6  # 数据完整返回
