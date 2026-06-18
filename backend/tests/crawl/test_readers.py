"""数据源读取器测试"""

import json
import os
import tempfile

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.admin.service.crawl.context import CrawlContext
from backend.app.admin.service.crawl.exceptions import CrawlSourceError, CrawlConnectionError
from backend.app.admin.service.crawl.readers import (
    APISourceReader,
    DatabaseSourceReader,
    FileCSVSourceReader,
    FileExcelSourceReader,
    FileJSONSourceReader,
    MongoDBSourceReader,
    get_source_reader,
)


class TestGetSourceReader:
    """读取器注册表测试"""

    def test_get_database_reader(self):
        reader = get_source_reader('database', {'datasource_id': 1, 'query': 'SELECT 1'})
        assert isinstance(reader, DatabaseSourceReader)

    def test_get_api_reader(self):
        reader = get_source_reader('api', {'url': 'https://example.com'})
        assert isinstance(reader, APISourceReader)

    def test_get_csv_reader(self):
        reader = get_source_reader('file_csv', {'file_path': '/tmp/test.csv'})
        assert isinstance(reader, FileCSVSourceReader)

    def test_get_json_reader(self):
        reader = get_source_reader('file_json', {'file_path': '/tmp/test.json'})
        assert isinstance(reader, FileJSONSourceReader)

    def test_get_excel_reader(self):
        reader = get_source_reader('file_excel', {'file_path': '/tmp/test.xlsx'})
        assert isinstance(reader, FileExcelSourceReader)

    def test_get_mongodb_reader(self):
        reader = get_source_reader('mongodb', {'datasource_id': 1, 'collection': 'test'})
        assert isinstance(reader, MongoDBSourceReader)

    def test_unsupported_type(self):
        with pytest.raises(CrawlSourceError, match='不支持的数据源类型'):
            get_source_reader('unknown_type', {})


class TestFileCSVSourceReader:
    """CSV 文件读取器测试"""

    @pytest.fixture
    def csv_file(self, tmp_path):
        file_path = tmp_path / 'test.csv'
        file_path.write_text('id,name,email\n1,Alice,alice@example.com\n2,Bob,bob@example.com\n')
        return str(file_path)

    @pytest.mark.asyncio
    async def test_read_csv(self, csv_file):
        reader = FileCSVSourceReader({'file_path': csv_file})
        ctx = CrawlContext()
        rows = await reader.read(ctx)
        assert len(rows) == 2
        assert rows[0]['id'] == '1'
        assert rows[0]['name'] == 'Alice'

    @pytest.mark.asyncio
    async def test_read_csv_with_delimiter(self, tmp_path):
        file_path = tmp_path / 'test.csv'
        file_path.write_text('id;name;email\n1;Alice;alice@example.com\n')
        reader = FileCSVSourceReader({'file_path': str(file_path), 'delimiter': ';'})
        ctx = CrawlContext()
        rows = await reader.read(ctx)
        assert len(rows) == 1
        assert rows[0]['id'] == '1'

    @pytest.mark.asyncio
    async def test_read_csv_no_header(self, tmp_path):
        file_path = tmp_path / 'test.csv'
        file_path.write_text('1,Alice,alice@example.com\n2,Bob,bob@example.com\n')
        reader = FileCSVSourceReader({'file_path': str(file_path), 'has_header': False})
        ctx = CrawlContext()
        rows = await reader.read(ctx)
        assert len(rows) == 2
        assert 'row' in rows[0]

    @pytest.mark.asyncio
    async def test_read_csv_file_not_found(self):
        reader = FileCSVSourceReader({'file_path': '/nonexistent/file.csv'})
        ctx = CrawlContext()
        with pytest.raises(CrawlSourceError, match='文件不存在'):
            await reader.read(ctx)

    @pytest.mark.asyncio
    async def test_read_csv_no_path(self):
        reader = FileCSVSourceReader({})
        ctx = CrawlContext()
        with pytest.raises(CrawlSourceError, match='文件路径不能为空'):
            await reader.read(ctx)


class TestFileJSONSourceReader:
    """JSON 文件读取器测试"""

    @pytest.mark.asyncio
    async def test_read_json_array(self, tmp_path):
        file_path = tmp_path / 'test.json'
        data = [{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}]
        file_path.write_text(json.dumps(data))

        reader = FileJSONSourceReader({'file_path': str(file_path)})
        ctx = CrawlContext()
        rows = await reader.read(ctx)
        assert len(rows) == 2
        assert rows[0]['id'] == 1

    @pytest.mark.asyncio
    async def test_read_json_object(self, tmp_path):
        file_path = tmp_path / 'test.json'
        data = {'id': 1, 'name': 'Alice'}
        file_path.write_text(json.dumps(data))

        reader = FileJSONSourceReader({'file_path': str(file_path)})
        ctx = CrawlContext()
        rows = await reader.read(ctx)
        assert len(rows) == 1
        assert rows[0]['id'] == 1

    @pytest.mark.asyncio
    async def test_read_json_with_root_path(self, tmp_path):
        file_path = tmp_path / 'test.json'
        data = {'data': {'items': [{'id': 1}, {'id': 2}]}}
        file_path.write_text(json.dumps(data))

        reader = FileJSONSourceReader({'file_path': str(file_path), 'root_path': 'data.items'})
        ctx = CrawlContext()
        rows = await reader.read(ctx)
        assert len(rows) == 2

    @pytest.mark.asyncio
    async def test_read_json_file_not_found(self):
        reader = FileJSONSourceReader({'file_path': '/nonexistent/file.json'})
        ctx = CrawlContext()
        with pytest.raises(CrawlSourceError, match='文件不存在'):
            await reader.read(ctx)

    @pytest.mark.asyncio
    async def test_read_json_invalid_path(self, tmp_path):
        file_path = tmp_path / 'test.json'
        file_path.write_text(json.dumps({'data': {'id': 1}}))

        reader = FileJSONSourceReader({'file_path': str(file_path), 'root_path': 'nonexistent.path'})
        ctx = CrawlContext()
        with pytest.raises(CrawlSourceError, match='JSON 路径'):
            await reader.read(ctx)


class TestAPISourceReader:
    """API 数据源读取器测试"""

    @pytest.mark.asyncio
    async def test_read_api_single_page(self):
        reader = APISourceReader({
            'url': 'https://api.example.com/data',
            'method': 'GET',
            'data_path': 'items',
        })
        ctx = CrawlContext()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'items': [{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}],
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            rows = await reader.read(ctx)
            assert len(rows) == 2
            assert rows[0]['id'] == 1

    @pytest.mark.asyncio
    async def test_read_api_no_url(self):
        reader = APISourceReader({})
        ctx = CrawlContext()
        with pytest.raises(CrawlSourceError, match='API URL 不能为空'):
            await reader.read(ctx)

    def test_extract_data_list(self):
        data = [{'id': 1}, {'id': 2}]
        result = APISourceReader._extract_data(data, None)
        assert len(result) == 2

    def test_extract_data_dict(self):
        data = {'id': 1, 'name': 'test'}
        result = APISourceReader._extract_data(data, None)
        assert len(result) == 1
        assert result[0]['id'] == 1

    def test_extract_data_with_path(self):
        data = {'response': {'items': [{'id': 1}]}}
        result = APISourceReader._extract_data(data, 'response.items')
        assert len(result) == 1

    def test_get_nested_value(self):
        data = {'a': {'b': {'c': 'value'}}}
        assert APISourceReader._get_nested_value(data, 'a.b.c') == 'value'
        assert APISourceReader._get_nested_value(data, 'a.b') == {'c': 'value'}
        assert APISourceReader._get_nested_value(data, 'x.y') is None


class TestDatabaseSourceReader:
    """数据库源读取器测试"""

    def test_build_db_url_mysql(self, mock_datasource):
        url = DatabaseSourceReader._build_db_url(mock_datasource, 'password', 'mysql')
        assert 'mysql+asyncmy' in url
        assert 'testuser' in url
        assert '5432' in url

    def test_build_db_url_postgresql(self, mock_datasource):
        url = DatabaseSourceReader._build_db_url(mock_datasource, 'password', 'postgresql')
        assert 'postgresql+asyncpg' in url

    def test_build_db_url_sqlite(self, mock_datasource):
        url = DatabaseSourceReader._build_db_url(mock_datasource, None, 'sqlite')
        assert 'sqlite+aiosqlite' in url

    def test_build_db_url_unsupported(self, mock_datasource):
        with pytest.raises(CrawlConnectionError, match='不支持的数据库类型'):
            DatabaseSourceReader._build_db_url(mock_datasource, 'password', 'unknown_db')

    @pytest.mark.asyncio
    async def test_read_no_datasource_id(self):
        reader = DatabaseSourceReader({'query': 'SELECT 1'})
        ctx = CrawlContext()
        with pytest.raises(CrawlSourceError, match='数据源 ID 不能为空'):
            await reader.read(ctx)

    @pytest.mark.asyncio
    async def test_read_no_query(self):
        reader = DatabaseSourceReader({'datasource_id': 1})
        ctx = CrawlContext()
        with pytest.raises(CrawlSourceError, match='SQL 查询语句不能为空'):
            await reader.read(ctx)


class TestMongoDBSourceReader:
    """MongoDB 读取器测试"""

    @pytest.mark.asyncio
    async def test_read_no_datasource_id(self):
        reader = MongoDBSourceReader({'collection': 'test'})
        ctx = CrawlContext()
        with pytest.raises(CrawlSourceError, match='数据源 ID 不能为空'):
            await reader.read(ctx)

    @pytest.mark.asyncio
    async def test_read_no_collection(self):
        reader = MongoDBSourceReader({'datasource_id': 1})
        ctx = CrawlContext()
        with pytest.raises(CrawlSourceError, match='集合名不能为空'):
            await reader.read(ctx)