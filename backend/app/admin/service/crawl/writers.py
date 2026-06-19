"""目标存储写入器

支持写入目标：
- database: 写入关系型数据库（需通过数据源配置连接）
- local_database: 写入当前项目自身数据库（无需额外配置）
- file_csv: 写入 CSV 文件
- file_json: 写入 JSON 文件
- file_excel: 写入 Excel 文件
- mongodb: 写入 MongoDB
"""

from __future__ import annotations

import csv
import json
from typing import Any

from loguru import logger

from backend.app.admin.service.crawl.context import CrawlContext
from backend.app.admin.service.crawl.exceptions import CrawlConnectionError, CrawlTargetError

from __future__ import annotations

import csv
import json
from typing import Any

from loguru import logger

from backend.app.admin.service.crawl.context import CrawlContext
from backend.app.admin.service.crawl.exceptions import CrawlConnectionError, CrawlTargetError


class BaseTargetWriter:
    """目标存储写入器基类"""

    target_type: str = ''

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    async def write(self, data: list[dict[str, Any]], context: CrawlContext) -> int:
        """写入数据

        Args:
            data: 待写入的数据行列表
            context: 采集执行上下文

        Returns:
            写入的记录数
        """
        raise NotImplementedError


class DatabaseTargetWriter(BaseTargetWriter):
    """数据库目标写入器

    配置参数:
        datasource_id: 目标数据源 ID
        table: 目标表名
        mode: 写入模式 (insert/upsert/truncate_insert)
        batch_size: 批量写入大小 (默认 1000)
        on_conflict: 冲突处理字段 (upsert 模式必填)
    """

    target_type = 'database'

    async def write(self, data: list[dict[str, Any]], context: CrawlContext) -> int:
        if not data:
            return 0

        datasource_id = self.config.get('datasource_id')
        table = self.config.get('table', '')
        mode = self.config.get('mode', 'insert')
        batch_size = self.config.get('batch_size', 1000)
        on_conflict = self.config.get('on_conflict', None)

        if not datasource_id:
            raise CrawlTargetError('目标数据源 ID 不能为空', self.target_type)
        if not table:
            raise CrawlTargetError('目标表名不能为空', self.target_type)

        from backend.app.admin.crud.crud_datasource import datasource_dao
        from backend.app.admin.service.datasource_service import _decrypt_password
        from backend.database.db import async_db_session

        async with async_db_session() as session:
            datasource = await datasource_dao.get(session, datasource_id)
            if not datasource:
                raise CrawlConnectionError(f'目标数据源 (ID={datasource_id}) 不存在')

            password = _decrypt_password(datasource.password)
            written = await self._write_to_database(datasource, password, table, data, mode, batch_size, on_conflict)

        context.metrics['target_type'] = 'database'
        context.metrics['target_datasource_id'] = datasource_id
        context.metrics['target_table'] = table
        return written

    async def _write_to_database(
        self,
        datasource: Any,
        password: str | None,
        table: str,
        data: list[dict[str, Any]],
        mode: str,
        batch_size: int,
        on_conflict: str | None,
    ) -> int:
        """写入数据库"""
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        db_type = datasource.db_type
        url = DatabaseSourceReader._build_db_url(datasource, password, db_type)

        engine = create_async_engine(url, echo=False)
        try:
            async with AsyncSession(engine) as session:
                # 清空表模式
                if mode == 'truncate_insert':
                    await session.execute(text(f'TRUNCATE TABLE {table}'))

                if not data:
                    await session.commit()
                    return 0

                columns = list(data[0].keys())
                col_names = ', '.join(columns)
                placeholders = ', '.join([f':{c}' for c in columns])

                total = 0
                for i in range(0, len(data), batch_size):
                    batch = data[i:i + batch_size]

                    if mode == 'upsert' and on_conflict:
                        # 构建冲突更新语句
                        conflict_cols = on_conflict.split(',')
                        update_cols = [c for c in columns if c not in conflict_cols]
                        if db_type == 'mysql':
                            update_clause = ', '.join([f'{c}=VALUES({c})' for c in update_cols])
                            stmt = text(
                                f'INSERT INTO {table} ({col_names}) VALUES ({placeholders}) '
                                f'ON DUPLICATE KEY UPDATE {update_clause}'
                            )
                        elif db_type == 'postgresql':
                            conflict_clause = ', '.join(conflict_cols)
                            update_clause = ', '.join([f'{c}=EXCLUDED.{c}' for c in update_cols])
                            stmt = text(
                                f'INSERT INTO {table} ({col_names}) VALUES ({placeholders}) '
                                f'ON CONFLICT ({conflict_clause}) DO UPDATE SET {update_clause}'
                            )
                        else:
                            # 不支持 upsert 的数据库回退到 insert
                            stmt = text(f'INSERT INTO {table} ({col_names}) VALUES ({placeholders})')
                    else:
                        stmt = text(f'INSERT INTO {table} ({col_names}) VALUES ({placeholders})')

                    for row in batch:
                        # 确保所有列都存在
                        row_data = {c: row.get(c) for c in columns}
                        await session.execute(stmt, row_data)
                        total += 1

                await session.commit()
                return total
        finally:
            await engine.dispose()


class FileCSVTargetWriter(BaseTargetWriter):
    """CSV 文件目标写入器

    配置参数:
        file_path: 文件路径
        encoding: 编码 (默认 utf-8-sig)
        mode: 写入模式 (write/append)
    """

    target_type = 'file_csv'

    async def write(self, data: list[dict[str, Any]], context: CrawlContext) -> int:
        if not data:
            return 0

        file_path = self.config.get('file_path', '')
        encoding = self.config.get('encoding', 'utf-8-sig')
        mode = self.config.get('mode', 'write')

        if not file_path:
            raise CrawlTargetError('文件路径不能为空', self.target_type)

        is_append = mode == 'append'

        with open(file_path, 'a' if is_append else 'w', newline='', encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            if not is_append:
                writer.writeheader()
            writer.writerows(data)

        context.metrics['target_type'] = 'file_csv'
        context.metrics['target_file'] = file_path
        return len(data)


class FileJSONTargetWriter(BaseTargetWriter):
    """JSON 文件目标写入器

    配置参数:
        file_path: 文件路径
        indent: 缩进 (默认 2)
        mode: 写入模式 (write/append)
    """

    target_type = 'file_json'

    async def write(self, data: list[dict[str, Any]], context: CrawlContext) -> int:
        file_path = self.config.get('file_path', '')
        indent = self.config.get('indent', 2)
        mode = self.config.get('mode', 'write')

        if not file_path:
            raise CrawlTargetError('文件路径不能为空', self.target_type)

        if mode == 'append':
            # 追加模式：读取已有数据并合并
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                if isinstance(existing, list):
                    existing.extend(data)
                else:
                    existing = [existing, *data]
                data = existing
            except FileNotFoundError:
                pass

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent, default=str)

        context.metrics['target_type'] = 'file_json'
        context.metrics['target_file'] = file_path
        return len(data)


class FileExcelTargetWriter(BaseTargetWriter):
    """Excel 文件目标写入器

    配置参数:
        file_path: 文件路径
        sheet_name: 工作表名 (默认 Sheet1)
    """

    target_type = 'file_excel'

    async def write(self, data: list[dict[str, Any]], context: CrawlContext) -> int:
        if not data:
            return 0

        file_path = self.config.get('file_path', '')
        sheet_name = self.config.get('sheet_name', 'Sheet1')

        if not file_path:
            raise CrawlTargetError('文件路径不能为空', self.target_type)

        try:
            import openpyxl
        except ImportError:
            raise CrawlTargetError('需要安装 openpyxl: pip install openpyxl', self.target_type)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_name

        headers = list(data[0].keys())
        ws.append(headers)
        for row in data:
            ws.append([row.get(h, '') for h in headers])

        wb.save(file_path)
        wb.close()

        context.metrics['target_type'] = 'file_excel'
        context.metrics['target_file'] = file_path
        return len(data)


class MongoDBTargetWriter(BaseTargetWriter):
    """MongoDB 目标写入器

    配置参数:
        datasource_id: 目标数据源 ID
        collection: 集合名
        mode: 写入模式 (insert/upsert)
        upsert_key: upsert 模式的唯一键 (可选)
        batch_size: 批量写入大小 (默认 1000)
    """

    target_type = 'mongodb'

    async def write(self, data: list[dict[str, Any]], context: CrawlContext) -> int:
        if not data:
            return 0

        datasource_id = self.config.get('datasource_id')
        collection_name = self.config.get('collection', '')
        mode = self.config.get('mode', 'insert')
        upsert_key = self.config.get('upsert_key', None)
        batch_size = self.config.get('batch_size', 1000)

        if not datasource_id:
            raise CrawlTargetError('目标数据源 ID 不能为空', self.target_type)
        if not collection_name:
            raise CrawlTargetError('集合名不能为空', self.target_type)

        from backend.app.admin.crud.crud_datasource import datasource_dao
        from backend.app.admin.service.datasource_service import _decrypt_password
        from backend.database.db import async_db_session

        async with async_db_session() as session:
            datasource = await datasource_dao.get(session, datasource_id)
            if not datasource:
                raise CrawlConnectionError(f'目标数据源 (ID={datasource_id}) 不存在')

            password = _decrypt_password(datasource.password)
            written = await self._write_to_mongodb(
                datasource, password, collection_name, data, mode, upsert_key, batch_size
            )

        context.metrics['target_type'] = 'mongodb'
        context.metrics['target_datasource_id'] = datasource_id
        return written

    async def _write_to_mongodb(
        self,
        datasource: Any,
        password: str | None,
        collection_name: str,
        data: list[dict[str, Any]],
        mode: str,
        upsert_key: str | None,
        batch_size: int,
    ) -> int:
        """写入 MongoDB"""
        try:
            from pymongo import MongoClient
        except ImportError:
            raise CrawlTargetError('需要安装 pymongo', self.target_type)

        url = f'mongodb://{datasource.username}:{password}@{datasource.host}:{datasource.port}/'
        if datasource.database_name:
            url += datasource.database_name

        client = MongoClient(url)
        try:
            db = client[datasource.database_name]
            collection = db[collection_name]

            total = 0
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]

                if mode == 'upsert' and upsert_key:
                    for doc in batch:
                        filter_doc = {upsert_key: doc.get(upsert_key)}
                        collection.update_one(filter_doc, {'$set': doc}, upsert=True)
                        total += 1
                else:
                    result = collection.insert_many(batch)
                    total += len(result.inserted_ids)

            return total
        finally:
            client.close()


class LocalDatabaseTargetWriter(BaseTargetWriter):
    """本地数据库目标写入器

    直接写入当前项目自身的数据库，无需额外数据源配置。

    配置参数:
        table: 目标表名
        mode: 写入模式 (insert/upsert/truncate_insert)
        batch_size: 批量写入大小 (默认 1000)
        on_conflict: 冲突处理字段 (upsert 模式必填)
    """

    target_type = 'local_database'

    async def write(self, data: list[dict[str, Any]], context: CrawlContext) -> int:
        if not data:
            return 0

        table = self.config.get('table', '')
        mode = self.config.get('mode', 'insert')
        batch_size = self.config.get('batch_size', 1000)
        on_conflict = self.config.get('on_conflict', None)

        if not table:
            raise CrawlTargetError('目标表名不能为空', self.target_type)

        from sqlalchemy import text
        from backend.database.db import async_db_session

        async with async_db_session() as session:
            written = await self._write_to_local(session, table, data, mode, batch_size, on_conflict)

        context.metrics['target_type'] = 'local_database'
        context.metrics['target_table'] = table
        return written

    async def _write_to_local(
        self,
        session,
        table: str,
        data: list[dict[str, Any]],
        mode: str,
        batch_size: int,
        on_conflict: str | None,
    ) -> int:
        """写入本地数据库"""
        if mode == 'truncate_insert':
            await session.execute(text(f'TRUNCATE TABLE {table}'))

        if not data:
            await session.commit()
            return 0

        columns = list(data[0].keys())
        col_names = ', '.join(columns)
        placeholders = ', '.join([f':{c}' for c in columns])

        total = 0
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            stmt = text(f'INSERT INTO {table} ({col_names}) VALUES ({placeholders})')
            for row in batch:
                row_data = {c: row.get(c) for c in columns}
                await session.execute(stmt, row_data)
                total += 1

        await session.commit()
        return total


# ── 写入器注册表 ──────────────────────────────────────────

_TARGET_WRITERS: dict[str, type[BaseTargetWriter]] = {
    'database': DatabaseTargetWriter,
    'local_database': LocalDatabaseTargetWriter,
    'file_csv': FileCSVTargetWriter,
    'file_json': FileJSONTargetWriter,
    'file_excel': FileExcelTargetWriter,
    'mongodb': MongoDBTargetWriter,
}


def get_target_writer(target_type: str, config: dict[str, Any]) -> BaseTargetWriter:
    """获取目标存储写入器实例"""
    writer_cls = _TARGET_WRITERS.get(target_type)
    if writer_cls is None:
        raise CrawlTargetError(f'不支持的目标存储类型: {target_type}')
    return writer_cls(config)


# 避免循环导入，延迟引用 DatabaseSourceReader
from backend.app.admin.service.crawl.readers import DatabaseSourceReader  # noqa: E402