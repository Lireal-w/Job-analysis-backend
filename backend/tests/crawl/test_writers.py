"""目标存储写入器测试"""

import json
import os
import tempfile

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.admin.service.crawl.context import CrawlContext
from backend.app.admin.service.crawl.exceptions import CrawlTargetError, CrawlConnectionError
from backend.app.admin.service.crawl.writers import (
    DatabaseTargetWriter,
    FileCSVTargetWriter,
    FileExcelTargetWriter,
    FileJSONTargetWriter,
    MongoDBTargetWriter,
    get_target_writer,
)


class TestGetTargetWriter:
    """写入器注册表测试"""

    def test_get_database_writer(self):
        writer = get_target_writer('database', {'datasource_id': 1, 'table': 'test'})
        assert isinstance(writer, DatabaseTargetWriter)

    def test_get_csv_writer(self):
        writer = get_target_writer('file_csv', {'file_path': '/tmp/output.csv'})
        assert isinstance(writer, FileCSVTargetWriter)

    def test_get_json_writer(self):
        writer = get_target_writer('file_json', {'file_path': '/tmp/output.json'})
        assert isinstance(writer, FileJSONTargetWriter)

    def test_get_excel_writer(self):
        writer = get_target_writer('file_excel', {'file_path': '/tmp/output.xlsx'})
        assert isinstance(writer, FileExcelTargetWriter)

    def test_get_mongodb_writer(self):
        writer = get_target_writer('mongodb', {'datasource_id': 1, 'collection': 'test'})
        assert isinstance(writer, MongoDBTargetWriter)

    def test_unsupported_type(self):
        with pytest.raises(CrawlTargetError, match='不支持的目标存储类型'):
            get_target_writer('unknown_type', {})


class TestFileCSVTargetWriter:
    """CSV 文件写入器测试"""

    @pytest.mark.asyncio
    async def test_write_csv(self, tmp_path, sample_data):
        file_path = str(tmp_path / 'output.csv')
        writer = FileCSVTargetWriter({'file_path': file_path})
        ctx = CrawlContext()
        written = await writer.write(sample_data, ctx)
        assert written == len(sample_data)
        assert os.path.exists(file_path)

        # 验证内容
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        assert 'id' in content
        assert 'Alice' in content

    @pytest.mark.asyncio
    async def test_write_csv_empty_data(self, tmp_path):
        file_path = str(tmp_path / 'output.csv')
        writer = FileCSVTargetWriter({'file_path': file_path})
        ctx = CrawlContext()
        written = await writer.write([], ctx)
        assert written == 0

    @pytest.mark.asyncio
    async def test_write_csv_no_path(self, sample_data):
        writer = FileCSVTargetWriter({})
        ctx = CrawlContext()
        with pytest.raises(CrawlTargetError, match='文件路径不能为空'):
            await writer.write(sample_data, ctx)

    @pytest.mark.asyncio
    async def test_write_csv_append_mode(self, tmp_path, sample_data):
        file_path = str(tmp_path / 'output.csv')
        writer = FileCSVTargetWriter({'file_path': file_path, 'mode': 'write'})
        ctx = CrawlContext()
        await writer.write(sample_data, ctx)

        # 追加模式
        writer_append = FileCSVTargetWriter({'file_path': file_path, 'mode': 'append'})
        more_data = [{'id': 6, 'name': 'Frank', 'email': 'frank@example.com', 'updated_at': '2024-06-01'}]
        written = await writer_append.write(more_data, ctx)
        assert written == 1


class TestFileJSONTargetWriter:
    """JSON 文件写入器测试"""

    @pytest.mark.asyncio
    async def test_write_json(self, tmp_path, sample_data):
        file_path = str(tmp_path / 'output.json')
        writer = FileJSONTargetWriter({'file_path': file_path})
        ctx = CrawlContext()
        written = await writer.write(sample_data, ctx)
        assert written == len(sample_data)

        # 验证内容
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert len(data) == len(sample_data)

    @pytest.mark.asyncio
    async def test_write_json_empty_data(self, tmp_path):
        file_path = str(tmp_path / 'output.json')
        writer = FileJSONTargetWriter({'file_path': file_path})
        ctx = CrawlContext()
        written = await writer.write([], ctx)
        assert written == 0

    @pytest.mark.asyncio
    async def test_write_json_append_mode(self, tmp_path, sample_data):
        file_path = str(tmp_path / 'output.json')
        writer = FileJSONTargetWriter({'file_path': file_path})
        ctx = CrawlContext()
        await writer.write(sample_data, ctx)

        # 追加模式
        writer_append = FileJSONTargetWriter({'file_path': file_path, 'mode': 'append'})
        more_data = [{'id': 6, 'name': 'Frank'}]
        written = await writer_append.write(more_data, ctx)
        assert written == len(sample_data) + 1   # 原有数据 + 新数据

    @pytest.mark.asyncio
    async def test_write_json_no_path(self, sample_data):
        writer = FileJSONTargetWriter({})
        ctx = CrawlContext()
        with pytest.raises(CrawlTargetError, match='文件路径不能为空'):
            await writer.write(sample_data, ctx)


class TestDatabaseTargetWriter:
    """数据库写入器测试"""

    @pytest.mark.asyncio
    async def test_write_no_datasource_id(self, sample_data):
        writer = DatabaseTargetWriter({'table': 'test'})
        ctx = CrawlContext()
        with pytest.raises(CrawlTargetError, match='目标数据源 ID 不能为空'):
            await writer.write(sample_data, ctx)

    @pytest.mark.asyncio
    async def test_write_no_table(self, sample_data):
        writer = DatabaseTargetWriter({'datasource_id': 1})
        ctx = CrawlContext()
        with pytest.raises(CrawlTargetError, match='目标表名不能为空'):
            await writer.write(sample_data, ctx)

    @pytest.mark.asyncio
    async def test_write_empty_data(self):
        writer = DatabaseTargetWriter({'datasource_id': 1, 'table': 'test'})
        ctx = CrawlContext()
        written = await writer.write([], ctx)
        assert written == 0


class TestMongoDBTargetWriter:
    """MongoDB 写入器测试"""

    @pytest.mark.asyncio
    async def test_write_no_datasource_id(self, sample_data):
        writer = MongoDBTargetWriter({'collection': 'test'})
        ctx = CrawlContext()
        with pytest.raises(CrawlTargetError, match='目标数据源 ID 不能为空'):
            await writer.write(sample_data, ctx)

    @pytest.mark.asyncio
    async def test_write_no_collection(self, sample_data):
        writer = MongoDBTargetWriter({'datasource_id': 1})
        ctx = CrawlContext()
        with pytest.raises(CrawlTargetError, match='集合名不能为空'):
            await writer.write(sample_data, ctx)

    @pytest.mark.asyncio
    async def test_write_empty_data(self):
        writer = MongoDBTargetWriter({'datasource_id': 1, 'collection': 'test'})
        ctx = CrawlContext()
        written = await writer.write([], ctx)
        assert written == 0