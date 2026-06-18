"""数据源节点执行器单元测试"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.app.admin.service.etl.context import ETLContext
from backend.app.admin.service.etl.exceptions import ETLNodeError
from backend.app.admin.service.etl.nodes.source import (
    APISourceExecutor,
    DatabaseSourceExecutor,
    FileCSVSourceExecutor,
    FileJSONSourceExecutor,
    TextFileSourceExecutor,
)


@pytest.mark.asyncio
class TestFileCSVSource:
    """CSV 文件源测试"""

    async def test_read_csv_with_header(self, temp_csv_file: str) -> None:
        executor = FileCSVSourceExecutor('csv1', {
            'file_path': temp_csv_file,
            'has_header': True,
        })
        ctx = ETLContext()
        result = await executor.execute(ctx)
        assert len(result) == 3
        assert result[0]['name'] == 'Alice'
        assert result[1]['city'] == 'Shanghai'

    async def test_read_csv_with_delimiter(self) -> None:
        import tempfile
        from pathlib import Path

        content = 'id|name|age\n1|Alice|30\n2|Bob|25\n'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(content)
            path = f.name
        try:
            executor = FileCSVSourceExecutor('csv2', {
                'file_path': path,
                'delimiter': '|',
            })
            ctx = ETLContext()
            result = await executor.execute(ctx)
            assert len(result) == 2
            assert result[0]['name'] == 'Alice'
        finally:
            Path(path).unlink(missing_ok=True)

    async def test_missing_file(self) -> None:
        executor = FileCSVSourceExecutor('csv3', {
            'file_path': '/nonexistent/file.csv',
        })
        ctx = ETLContext()
        with pytest.raises(ETLNodeError, match='文件不存在'):
            await executor.execute(ctx)

    async def test_empty_file_path(self) -> None:
        executor = FileCSVSourceExecutor('csv4', {'file_path': ''})
        ctx = ETLContext()
        with pytest.raises(ETLNodeError, match='文件路径不能为空'):
            await executor.execute(ctx)


@pytest.mark.asyncio
class TestFileJSONSource:
    """JSON 文件源测试"""

    async def test_read_json_array(self, temp_json_file: str) -> None:
        executor = FileJSONSourceExecutor('json1', {'file_path': temp_json_file})
        ctx = ETLContext()
        result = await executor.execute(ctx)
        assert len(result) == 3
        assert result[0]['name'] == 'Alice'
        assert result[1]['score'] == 87

    async def test_read_json_with_root_path(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        data = {'data': {'items': [{'x': 1}, {'x': 2}]}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(data, f)
            path = f.name
        try:
            executor = FileJSONSourceExecutor('json2', {
                'file_path': path,
                'root_path': 'data.items',
            })
            ctx = ETLContext()
            result = await executor.execute(ctx)
            assert len(result) == 2
            assert result[0]['x'] == 1
        finally:
            Path(path).unlink(missing_ok=True)

    async def test_missing_file(self) -> None:
        executor = FileJSONSourceExecutor('json3', {'file_path': '/nonexistent.json'})
        ctx = ETLContext()
        with pytest.raises(ETLNodeError, match='文件不存在'):
            await executor.execute(ctx)

    async def test_empty_file_path(self) -> None:
        executor = FileJSONSourceExecutor('json4', {'file_path': ''})
        ctx = ETLContext()
        with pytest.raises(ETLNodeError, match='文件路径不能为空'):
            await executor.execute(ctx)


@pytest.mark.asyncio
class TestTextFileSource:
    """文本文件源测试"""

    async def test_read_text_file(self, temp_text_file: str) -> None:
        executor = TextFileSourceExecutor('txt1', {'file_path': temp_text_file})
        ctx = ETLContext()
        result = await executor.execute(ctx)
        assert len(result) == 4
        assert result[0]['line'] == 'line1'
        assert result[2]['line'] == 'line3'

    async def test_custom_column_name(self, temp_text_file: str) -> None:
        executor = TextFileSourceExecutor('txt2', {
            'file_path': temp_text_file,
            'column_name': 'content',
        })
        ctx = ETLContext()
        result = await executor.execute(ctx)
        assert result[0]['content'] == 'line1'

    async def test_missing_file(self) -> None:
        executor = TextFileSourceExecutor('txt3', {'file_path': '/nonexistent.txt'})
        ctx = ETLContext()
        with pytest.raises(ETLNodeError, match='文件不存在'):
            await executor.execute(ctx)


@pytest.mark.asyncio
class TestAPISource:
    """API 数据源测试 (mock httpx)"""

    def _make_json_response(self, data):
        """创建 mock httpx.Response"""
        from unittest.mock import MagicMock

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = data
        resp.raise_for_status.return_value = None
        return resp

    @staticmethod
    def _mock_async_client(**methods):
        """创建异步上下文管理器版本的 mock httpx.AsyncClient"""
        from unittest.mock import AsyncMock

        class _MockClient:
            def __init__(self):
                for name, ret in methods.items():
                    setattr(self, name, AsyncMock(return_value=ret))

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        return _MockClient()

    async def test_get_request(self) -> None:
        resp = self._make_json_response([{'id': 1, 'name': 'Alice'}])
        mc = self._mock_async_client(get=resp)

        with patch('httpx.AsyncClient', return_value=mc):
            executor = APISourceExecutor('api1', {
                'url': 'https://api.test.com/users',
                'method': 'GET',
            })
            ctx = ETLContext()
            result = await executor.execute(ctx)
            assert len(result) == 1
            assert result[0]['name'] == 'Alice'

    async def test_post_request(self) -> None:
        resp = self._make_json_response({'result': 'ok'})
        mc = self._mock_async_client(post=resp)

        with patch('httpx.AsyncClient', return_value=mc):
            executor = APISourceExecutor('api2', {
                'url': 'https://api.test.com/query',
                'method': 'POST',
                'body': {'q': 'test'},
            })
            ctx = ETLContext()
            result = await executor.execute(ctx)
            assert result[0]['result'] == 'ok'

    async def test_data_path_extraction(self) -> None:
        resp = self._make_json_response({
            'status': 'ok',
            'data': {'users': [{'name': 'A'}, {'name': 'B'}]},
        })
        mc = self._mock_async_client(get=resp)

        with patch('httpx.AsyncClient', return_value=mc):
            executor = APISourceExecutor('api3', {
                'url': 'https://api.test.com/users',
                'data_path': 'data.users',
            })
            ctx = ETLContext()
            result = await executor.execute(ctx)
            assert len(result) == 2
            assert result[0]['name'] == 'A'

    async def test_http_error(self) -> None:
        import httpx

        class _ErrorClient:
            get = AsyncMock(side_effect=httpx.HTTPError('Connection failed'))

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        with patch('httpx.AsyncClient', return_value=_ErrorClient()):
            executor = APISourceExecutor('api4', {
                'url': 'https://api.test.com/error',
            })
            ctx = ETLContext()
            with pytest.raises(Exception, match='API 请求失败'):
                await executor.execute(ctx)

    async def test_empty_url(self) -> None:
        executor = APISourceExecutor('api5', {'url': ''})
        ctx = ETLContext()
        with pytest.raises(ETLNodeError, match='API URL 不能为空'):
            await executor.execute(ctx)


@pytest.mark.asyncio
class TestDatabaseSource:
    """数据库源测试 (mock _query_database)"""

    async def test_execute_query(self) -> None:
        executor = DatabaseSourceExecutor('db1', {
            'datasource_id': 1,
            'query': 'SELECT * FROM users',
        })
        executor._query_database = AsyncMock(return_value=[
            {'id': 1, 'name': 'Alice'},
            {'id': 2, 'name': 'Bob'},
        ])
        ctx = ETLContext()
        result = await executor.execute(ctx)
        assert len(result) == 2
        assert result[0]['name'] == 'Alice'

    async def test_missing_datasource_id(self) -> None:
        executor = DatabaseSourceExecutor('db2', {
            'query': 'SELECT 1',
        })
        ctx = ETLContext()
        with pytest.raises(ETLNodeError, match='数据源 ID 不能为空'):
            await executor.execute(ctx)

    async def test_missing_query(self) -> None:
        executor = DatabaseSourceExecutor('db3', {
            'datasource_id': 1,
        })
        ctx = ETLContext()
        with pytest.raises(ETLNodeError, match='SQL 查询语句不能为空'):
            await executor.execute(ctx)

    async def test_metrics_tracking(self) -> None:
        executor = DatabaseSourceExecutor('db4', {
            'datasource_id': 1,
            'query': 'SELECT 1',
        })
        executor._query_database = AsyncMock(return_value=[{'a': 1}, {'a': 2}, {'a': 3}])
        # mock datasource 查询和密码解密，避免真实数据库连接
        with (
            patch('backend.app.admin.crud.crud_datasource.datasource_dao.get', new_callable=AsyncMock) as mock_get,
            patch('backend.app.admin.service.datasource_service._decrypt_password', return_value='pwd'),
        ):
            mock_ds = AsyncMock()
            mock_ds.db_type = 'postgresql'
            mock_ds.host = 'localhost'
            mock_ds.port = 5432
            mock_ds.username = 'test'
            mock_ds.password = 'encrypted'
            mock_ds.database_name = 'testdb'
            mock_get.return_value = mock_ds

            ctx = ETLContext()
            await executor.execute(ctx)

        assert ctx.metrics['node_db4_rows'] == 3
