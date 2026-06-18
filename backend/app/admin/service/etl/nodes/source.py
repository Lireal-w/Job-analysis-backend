"""数据源读取节点执行器

支持从各类数据源提取数据：
- database: 通过已配置的数据源执行 SQL 查询
- file_csv: 读取 CSV 文件
- file_excel: 读取 Excel 文件 (需安装 openpyxl)
- file_json: 读取 JSON 文件
- api: 调用 REST API 获取数据 (使用 httpx)
- file_text: 读取文本文件 (每行一条记录)
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any
from urllib.parse import urlencode

import httpx

from backend.app.admin.service.etl.context import ETLContext
from backend.app.admin.service.etl.exceptions import ETLConnectionError, ETLNodeError
from backend.app.admin.service.etl.nodes.base import BaseNodeExecutor


class DatabaseSourceExecutor(BaseNodeExecutor):
    """数据库源执行器"""

    node_type = 'source_database'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        datasource_id = self.config.get('datasource_id')
        query = self.config.get('query', '')
        if not datasource_id:
            self.raise_error('数据源 ID 不能为空')
        if not query:
            self.raise_error('SQL 查询语句不能为空')

        # 通过 datasource_service 获取数据源信息并查询
        from backend.app.admin.crud.crud_datasource import datasource_dao
        from backend.app.admin.model import Datasource
        from backend.app.admin.service.datasource_service import _decrypt_password
        from backend.database.db import async_db_session

        async with async_db_session() as session:
            datasource = await datasource_dao.get(session, datasource_id)
            if not datasource:
                raise ETLConnectionError(f'数据源 (ID={datasource_id}) 不存在')

            password = _decrypt_password(datasource.password)
            rows = await self._query_database(datasource, password, query)

        context.metrics[f'node_{self.node_id}_rows'] = len(rows)
        return rows

    async def _query_database(self, datasource: Any, password: str | None, query: str) -> list[dict[str, Any]]:
        """根据数据源类型执行 SQL 查询"""
        db_type = datasource.db_type
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        # 构建连接 URL
        if db_type == 'mysql':
            url = f'mysql+asyncmy://{datasource.username}:{password}@{datasource.host}:{datasource.port}/{datasource.database_name}'
        elif db_type == 'postgresql':
            url = f'postgresql+asyncpg://{datasource.username}:{password}@{datasource.host}:{datasource.port}/{datasource.database_name}'
        elif db_type == 'sqlite':
            url = f'sqlite+aiosqlite:///{datasource.database_name or ":memory:"}'
        else:
            raise ETLConnectionError(f'不支持的数据库类型: {db_type}')

        engine = create_async_engine(url, echo=False)
        try:
            async with AsyncSession(engine) as session:
                result = await session.execute(text(query))
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                return rows
        finally:
            await engine.dispose()


class FileCSVSourceExecutor(BaseNodeExecutor):
    """CSV 文件源执行器"""

    node_type = 'source_file_csv'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        file_path = self.config.get('file_path', '')
        delimiter = self.config.get('delimiter', ',')
        encoding = self.config.get('encoding', 'utf-8')
        has_header = self.config.get('has_header', True)

        if not file_path:
            self.raise_error('文件路径不能为空')

        try:
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter=delimiter) if has_header else csv.reader(f, delimiter=delimiter)
                if has_header:
                    rows = list(reader)
                else:
                    rows = [{'row': row} for row in reader]
        except FileNotFoundError:
            raise ETLNodeError(self.node_id, f'文件不存在: {file_path}')

        context.metrics[f'node_{self.node_id}_rows'] = len(rows)
        return rows


class FileExcelSourceExecutor(BaseNodeExecutor):
    """Excel 文件源执行器"""

    node_type = 'source_file_excel'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        try:
            import openpyxl
        except ImportError:
            self.raise_error('需要安装 openpyxl: pip install openpyxl')

        file_path = self.config.get('file_path', '')
        sheet_name = self.config.get('sheet_name', None)

        if not file_path:
            self.raise_error('文件路径不能为空')

        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            ws = wb[sheet_name] if sheet_name else wb.active
            rows_data = list(ws.iter_rows(values_only=True))
            wb.close()

            if not rows_data:
                return []

            headers = [str(h) if h is not None else f'col_{i}' for i, h in enumerate(rows_data[0])]
            rows = [dict(zip(headers, row)) for row in rows_data[1:]]
        except FileNotFoundError:
            raise ETLNodeError(self.node_id, f'文件不存在: {file_path}')

        context.metrics[f'node_{self.node_id}_rows'] = len(rows)
        return rows


class FileJSONSourceExecutor(BaseNodeExecutor):
    """JSON 文件源执行器"""

    node_type = 'source_file_json'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        file_path = self.config.get('file_path', '')
        root_path = self.config.get('root_path', None)

        if not file_path:
            self.raise_error('文件路径不能为空')

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if root_path:
                for key in root_path.split('.'):
                    if isinstance(data, dict):
                        data = data[key]
                    else:
                        self.raise_error(f'JSON 路径 {root_path} 无效')

            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict):
                rows = [data]
            else:
                rows = [{'value': data}]
        except FileNotFoundError:
            raise ETLNodeError(self.node_id, f'文件不存在: {file_path}')

        context.metrics[f'node_{self.node_id}_rows'] = len(rows)
        return rows


class APISourceExecutor(BaseNodeExecutor):
    """API 数据源执行器"""

    node_type = 'source_api'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        url = self.config.get('url', '')
        method = self.config.get('method', 'GET').upper()
        headers = self.config.get('headers', {})
        params = self.config.get('params', {})
        body = self.config.get('body', None)
        data_path = self.config.get('data_path', None)

        if not url:
            self.raise_error('API URL 不能为空')

        if params:
            url = f'{url}?{urlencode(params)}'

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                if method == 'GET':
                    resp = await client.get(url, headers=headers)
                elif method == 'POST':
                    resp = await client.post(url, headers=headers, json=body)
                else:
                    resp = await client.request(method, url, headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as e:
                raise ETLConnectionError(f'API 请求失败: {e}')

        if data_path:
            for key in data_path.split('.'):
                if isinstance(data, dict):
                    data = data.get(key, [])
                else:
                    data = []

        rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else [{'value': data}]
        context.metrics[f'node_{self.node_id}_rows'] = len(rows)
        return rows


class TextFileSourceExecutor(BaseNodeExecutor):
    """文本文件源执行器 (每行一条记录)"""

    node_type = 'source_file_text'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        file_path = self.config.get('file_path', '')
        encoding = self.config.get('encoding', 'utf-8')
        column_name = self.config.get('column_name', 'line')

        if not file_path:
            self.raise_error('文件路径不能为空')

        try:
            with open(file_path, 'r', encoding=encoding) as f:
                rows = [{column_name: line.rstrip('\n\r')} for line in f if line.strip()]
        except FileNotFoundError:
            raise ETLNodeError(self.node_id, f'文件不存在: {file_path}')

        context.metrics[f'node_{self.node_id}_rows'] = len(rows)
        return rows
