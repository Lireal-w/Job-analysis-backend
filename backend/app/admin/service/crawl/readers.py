"""数据源读取器

支持从各类数据源提取数据：
- database: 通过已配置的数据源执行 SQL 查询
- api: 调用 REST API 获取数据
- file_csv: 读取 CSV 文件
- file_excel: 读取 Excel 文件
- file_json: 读取 JSON 文件
- mongodb: 从 MongoDB 读取数据
- mihoyo_post: 米游社帖子采集 (爬虫插件)

爬虫插件位于 `crawlers/` 目录，基于 Scrapling 引擎开发。
新增爬虫后在 `_SOURCE_READERS` 中注册即可在 UI 中使用。
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

import httpx
from loguru import logger

from backend.app.admin.service.crawl.context import CrawlContext
from backend.app.admin.service.crawl.exceptions import CrawlConnectionError, CrawlSourceError


class BaseSourceReader:
    """数据源读取器基类"""

    source_type: str = ''

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    async def read(self, context: CrawlContext) -> list[dict[str, Any]]:
        """读取数据

        Args:
            context: 采集执行上下文

        Returns:
            读取到的数据行列表
        """
        raise NotImplementedError


class DatabaseSourceReader(BaseSourceReader):
    """数据库源读取器

    配置参数:
        datasource_id: 数据源 ID
        query: SQL 查询语句
        query_params: 查询参数 (可选)
    """

    source_type = 'database'

    async def read(self, context: CrawlContext) -> list[dict[str, Any]]:
        datasource_id = self.config.get('datasource_id')
        query = self.config.get('query', '')
        query_params = self.config.get('query_params', {})

        if not datasource_id:
            raise CrawlSourceError('数据源 ID 不能为空', self.source_type)
        if not query:
            raise CrawlSourceError('SQL 查询语句不能为空', self.source_type)

        from backend.app.admin.crud.crud_datasource import datasource_dao
        from backend.app.admin.service.datasource_service import _decrypt_password
        from backend.database.db import async_db_session

        async with async_db_session() as session:
            datasource = await datasource_dao.get(session, datasource_id)
            if not datasource:
                raise CrawlConnectionError(f'数据源 (ID={datasource_id}) 不存在')

            password = _decrypt_password(datasource.password)
            rows = await self._query_database(datasource, password, query, query_params)

        context.metrics['source_type'] = 'database'
        context.metrics['source_datasource_id'] = datasource_id
        return rows

    async def _query_database(
        self,
        datasource: Any,
        password: str | None,
        query: str,
        query_params: dict | None = None,
    ) -> list[dict[str, Any]]:
        """根据数据源类型执行 SQL 查询"""
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        db_type = datasource.db_type
        url = self._build_db_url(datasource, password, db_type)

        engine = create_async_engine(url, echo=False)
        try:
            async with AsyncSession(engine) as session:
                result = await session.execute(text(query), query_params or {})
                columns = list(result.keys())
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                return rows
        finally:
            await engine.dispose()

    @staticmethod
    def _build_db_url(datasource: Any, password: str | None, db_type: str) -> str:
        """构建数据库连接 URL"""
        if db_type == 'mysql':
            return f'mysql+asyncmy://{datasource.username}:{password}@{datasource.host}:{datasource.port}/{datasource.database_name}'
        elif db_type == 'postgresql':
            return f'postgresql+asyncpg://{datasource.username}:{password}@{datasource.host}:{datasource.port}/{datasource.database_name}'
        elif db_type == 'sqlite':
            return f'sqlite+aiosqlite:///{datasource.database_name or ":memory:"}'
        elif db_type == 'mssql':
            return f'mssql+pyodbc://{datasource.username}:{password}@{datasource.host}:{datasource.port}/{datasource.database_name}?driver=ODBC+Driver+17+for+SQL+Server'
        elif db_type == 'oracle':
            return f'oracle+oracledb://{datasource.username}:{password}@{datasource.host}:{datasource.port}/{datasource.database_name}'
        else:
            raise CrawlConnectionError(f'不支持的数据库类型: {db_type}')


class APISourceReader(BaseSourceReader):
    """API 数据源读取器

    配置参数:
        url: API URL
        method: HTTP 方法 (GET/POST, 默认 GET)
        headers: 请求头 (可选)
        cookies: Cookie 字符串 (可选, 如 'key1=val1; key2=val2')
        params: 查询参数 (可选)
        body: 请求体 (可选，json 模式传 dict，form 模式传 dict 自动编码)
        content_type: 请求体类型 (json 或 form, 默认 json)
        data_path: 数据路径 (可选, 如 'data.items')
        pagination: 分页配置 (可选)
            - type: 分页类型 (offset/cursor/page)
            - page_param: 页码参数名
            - size_param: 每页大小参数名
            - total_path: 总数路径
            - data_path: 数据路径
            - cursor_path: 游标路径
            - max_pages: 最大页数 (默认 100)
    """

    source_type = 'api'

    async def read(self, context: CrawlContext) -> list[dict[str, Any]]:
        url = self.config.get('url', '')
        method = self.config.get('method', 'GET').upper()
        headers = self.config.get('headers', {})
        raw_cookies = self.config.get('cookies', None)
        params = self.config.get('params', {})
        body = self.config.get('body', None)
        content_type = self.config.get('content_type', 'json')
        data_path = self.config.get('data_path', None)
        pagination = self.config.get('pagination', None)

        # 解析 Cookie 字符串
        cookies = None
        if raw_cookies:
            from http.cookies import SimpleCookie
            c = SimpleCookie()
            c.load(raw_cookies)
            cookies = {k: v.value for k, v in c.items()}

        if not url:
            raise CrawlSourceError('API URL 不能为空', self.source_type)

        all_rows: list[dict[str, Any]] = []

        if pagination:
            all_rows = await self._read_paginated(url, method, headers, cookies, params, body, content_type, data_path, pagination)
        else:
            all_rows = await self._read_single(url, method, headers, cookies, params, body, content_type, data_path)

        if not url:
            raise CrawlSourceError('API URL 不能为空', self.source_type)

        all_rows: list[dict[str, Any]] = []

        if pagination:
            all_rows = await self._read_paginated(url, method, headers, params, body, data_path, pagination)
        else:
            all_rows = await self._read_single(url, method, headers, params, body, data_path)

        context.metrics['source_type'] = 'api'
        context.metrics['source_url'] = url
        return all_rows

    async def _read_single(
        self,
        url: str,
        method: str,
        headers: dict,
        cookies: dict | None,
        params: dict,
        body: dict | None,
        content_type: str,
        data_path: str | None,
    ) -> list[dict[str, Any]]:
        """读取单页数据"""
        request_kwargs = {'headers': headers, 'cookies': cookies, 'params': params}
        if body is not None:
            if content_type == 'form':
                request_kwargs['data'] = body
            else:
                request_kwargs['json'] = body

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(method, url, **request_kwargs)
            response.raise_for_status()
            data = response.json()

        return self._extract_data(data, data_path)

    async def _read_paginated(
        self,
        url: str,
        method: str,
        headers: dict,
        cookies: dict | None,
        params: dict,
        body: dict | None,
        content_type: str,
        data_path: str | None,
        pagination: dict,
    ) -> list[dict[str, Any]]:
        """分页读取数据"""
        page_type = pagination.get('type', 'offset')
        page_param = pagination.get('page_param', 'page')
        size_param = pagination.get('size_param', 'size')
        page_size = pagination.get('page_size', 100)
        total_path = pagination.get('total_path', 'total')
        page_data_path = pagination.get('data_path', data_path)
        cursor_path = pagination.get('cursor_path', 'next_cursor')
        max_pages = pagination.get('max_pages', 100)

        all_rows: list[dict[str, Any]] = []
        page = 1
        cursor = None

        async with httpx.AsyncClient(timeout=60.0) as client:
            while page <= max_pages:
                request_params = {**params}
                request_body = {**body} if body else {}

                if page_type == 'offset':
                    request_params[page_param] = page
                    request_params[size_param] = page_size
                elif page_type == 'page':
                    request_params[page_param] = page
                    request_params[size_param] = page_size
                elif page_type == 'cursor' and cursor:
                    request_params[cursor_path] = cursor

                request_kwargs = {'headers': headers, 'cookies': cookies, 'params': request_params}
                if request_body:
                    if content_type == 'form':
                        request_kwargs['data'] = request_body
                    else:
                        request_kwargs['json'] = request_body

                response = await client.request(method, url, **request_kwargs)
                response.raise_for_status()
                data = response.json()

                page_data = self._extract_data(data, page_data_path)
                if not page_data:
                    break

                all_rows.extend(page_data)

                # 检查是否还有更多数据
                if page_type == 'cursor':
                    cursor = self._get_nested_value(data, cursor_path)
                    if not cursor:
                        break
                else:
                    total = self._get_nested_value(data, total_path)
                    if total is not None and page * page_size >= total:
                        break

                page += 1

        return all_rows

    @staticmethod
    def _extract_data(data: Any, data_path: str | None) -> list[dict[str, Any]]:
        """从响应数据中提取数据列表"""
        if data_path:
            data = APISourceReader._get_nested_value(data, data_path)

        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        else:
            return [{'value': data}]

    @staticmethod
    def _get_nested_value(data: Any, path: str) -> Any:
        """从嵌套结构中获取值"""
        if not path:
            return data
        for key in path.split('.'):
            if isinstance(data, dict):
                data = data.get(key)
            elif isinstance(data, list) and key.isdigit():
                data = data[int(key)]
            else:
                return None
        return data


class FileCSVSourceReader(BaseSourceReader):
    """CSV 文件源读取器

    配置参数:
        file_path: 文件路径
        delimiter: 分隔符 (默认 ,)
        encoding: 编码 (默认 utf-8)
        has_header: 是否有表头 (默认 True)
    """

    source_type = 'file_csv'

    async def read(self, context: CrawlContext) -> list[dict[str, Any]]:
        file_path = self.config.get('file_path', '')
        delimiter = self.config.get('delimiter', ',')
        encoding = self.config.get('encoding', 'utf-8')
        has_header = self.config.get('has_header', True)

        if not file_path:
            raise CrawlSourceError('文件路径不能为空', self.source_type)

        try:
            with open(file_path, 'r', encoding=encoding) as f:
                if has_header:
                    reader = csv.DictReader(f, delimiter=delimiter)
                    rows = list(reader)
                else:
                    reader = csv.reader(f, delimiter=delimiter)
                    rows = [{'row': row} for row in reader]
        except FileNotFoundError:
            raise CrawlSourceError(f'文件不存在: {file_path}', self.source_type)
        except Exception as e:
            raise CrawlSourceError(f'读取 CSV 文件失败: {e}', self.source_type)

        context.metrics['source_type'] = 'file_csv'
        context.metrics['source_file'] = file_path
        return rows


class FileExcelSourceReader(BaseSourceReader):
    """Excel 文件源读取器

    配置参数:
        file_path: 文件路径
        sheet_name: 工作表名 (可选)
    """

    source_type = 'file_excel'

    async def read(self, context: CrawlContext) -> list[dict[str, Any]]:
        try:
            import openpyxl
        except ImportError:
            raise CrawlSourceError('需要安装 openpyxl: pip install openpyxl', self.source_type)

        file_path = self.config.get('file_path', '')
        sheet_name = self.config.get('sheet_name', None)

        if not file_path:
            raise CrawlSourceError('文件路径不能为空', self.source_type)

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
            raise CrawlSourceError(f'文件不存在: {file_path}', self.source_type)
        except Exception as e:
            raise CrawlSourceError(f'读取 Excel 文件失败: {e}', self.source_type)

        context.metrics['source_type'] = 'file_excel'
        context.metrics['source_file'] = file_path
        return rows


class FileJSONSourceReader(BaseSourceReader):
    """JSON 文件源读取器

    配置参数:
        file_path: 文件路径
        root_path: 数据根路径 (可选, 如 'data.items')
    """

    source_type = 'file_json'

    async def read(self, context: CrawlContext) -> list[dict[str, Any]]:
        file_path = self.config.get('file_path', '')
        root_path = self.config.get('root_path', None)

        if not file_path:
            raise CrawlSourceError('文件路径不能为空', self.source_type)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if root_path:
                for key in root_path.split('.'):
                    if isinstance(data, dict):
                        data = data[key]
                    else:
                        raise CrawlSourceError(f'JSON 路径 {root_path} 无效', self.source_type)

            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict):
                rows = [data]
            else:
                rows = [{'value': data}]
        except FileNotFoundError:
            raise CrawlSourceError(f'文件不存在: {file_path}', self.source_type)
        except KeyError as e:
            raise CrawlSourceError(f'JSON 路径不存在: {e}', self.source_type)
        except Exception as e:
            raise CrawlSourceError(f'读取 JSON 文件失败: {e}', self.source_type)

        context.metrics['source_type'] = 'file_json'
        context.metrics['source_file'] = file_path
        return rows


class MongoDBSourceReader(BaseSourceReader):
    """MongoDB 数据源读取器

    配置参数:
        datasource_id: 数据源 ID (用于获取连接信息)
        collection: 集合名
        filter: 查询条件 (可选)
        projection: 字段投影 (可选)
        sort: 排序条件 (可选)
        limit: 限制条数 (可选)
    """

    source_type = 'mongodb'

    async def read(self, context: CrawlContext) -> list[dict[str, Any]]:
        datasource_id = self.config.get('datasource_id')
        collection_name = self.config.get('collection', '')
        filter_query = self.config.get('filter', {})
        projection = self.config.get('projection', None)
        sort = self.config.get('sort', None)
        limit = self.config.get('limit', 0)

        if not datasource_id:
            raise CrawlSourceError('数据源 ID 不能为空', self.source_type)
        if not collection_name:
            raise CrawlSourceError('集合名不能为空', self.source_type)

        from backend.app.admin.crud.crud_datasource import datasource_dao
        from backend.app.admin.service.datasource_service import _decrypt_password
        from backend.database.db import async_db_session

        async with async_db_session() as session:
            datasource = await datasource_dao.get(session, datasource_id)
            if not datasource:
                raise CrawlConnectionError(f'数据源 (ID={datasource_id}) 不存在')

            password = _decrypt_password(datasource.password)
            rows = await self._query_mongodb(datasource, password, collection_name, filter_query, projection, sort, limit)

        context.metrics['source_type'] = 'mongodb'
        context.metrics['source_datasource_id'] = datasource_id
        return rows

    async def _query_mongodb(
        self,
        datasource: Any,
        password: str | None,
        collection_name: str,
        filter_query: dict,
        projection: dict | None,
        sort: list | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """从 MongoDB 读取数据"""
        try:
            from pymongo import MongoClient
        except ImportError:
            raise CrawlSourceError('需要安装 pymongo', self.source_type)

        url = f'mongodb://{datasource.username}:{password}@{datasource.host}:{datasource.port}/'
        if datasource.database_name:
            url += datasource.database_name

        client = MongoClient(url)
        try:
            db = client[datasource.database_name]
            collection = db[collection_name]

            cursor = collection.find(filter_query, projection)
            if sort:
                cursor = cursor.sort(sort)
            if limit > 0:
                cursor = cursor.limit(limit)

            rows = []
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                rows.append(doc)
            return rows
        finally:
            client.close()


# ── 读取器注册表 ──────────────────────────────────────────

def _get_source_readers() -> dict[str, type[BaseSourceReader]]:
    """获取读取器注册表（惰性加载，避免循环导入）"""
    from backend.app.admin.service.crawl.crawlers.mihoyo import MiHoYoPostCrawler

    return {
        'database': DatabaseSourceReader,
        'api': APISourceReader,
        'file_csv': FileCSVSourceReader,
        'file_excel': FileExcelSourceReader,
        'file_json': FileJSONSourceReader,
        'mongodb': MongoDBSourceReader,
        # ── 爬虫插件 ──
        'mihoyo_post': MiHoYoPostCrawler,
        # 后续扩展：
        # 'bilibili_video': BiliBiliVideoCrawler,
        # 'weibo_timeline': WeiboTimelineCrawler,
    }


def get_source_reader(source_type: str, config: dict[str, Any]) -> BaseSourceReader:
    """获取数据源读取器实例"""
    readers = _get_source_readers()
    reader_cls = readers.get(source_type)
    if reader_cls is None:
        raise CrawlSourceError(f'不支持的源类型: {source_type}')
    return reader_cls(config)