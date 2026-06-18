"""数据写入节点执行器

支持写入目标：
- database: 写入关系型数据库
- file_csv: 写入 CSV 文件
- file_json: 写入 JSON 文件
- file_excel: 写入 Excel 文件
- log: 仅日志输出 (调试用)
"""

from __future__ import annotations

import csv
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.admin.service.etl.context import ETLContext
from backend.app.admin.service.etl.exceptions import ETLConnectionError, ETLNodeError
from backend.app.admin.service.etl.nodes.base import BaseNodeExecutor


class DatabaseLoadExecutor(BaseNodeExecutor):
    """数据库写入执行器"""

    node_type = 'load_database'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        if not inputs or not inputs[0]:
            return []

        data = inputs[0]
        datasource_id = self.config.get('datasource_id')
        table = self.config.get('table', '')
        mode = self.config.get('mode', 'insert')  # insert / replace / truncate_insert
        batch_size = self.config.get('batch_size', 1000)

        if not datasource_id:
            self.raise_error('数据源 ID 不能为空')
        if not table:
            self.raise_error('目标表名不能为空')

        from backend.app.admin.crud.crud_datasource import datasource_dao
        from backend.app.admin.service.datasource_service import _decrypt_password
        from backend.database.db import async_db_session

        async with async_db_session() as session:
            datasource = await datasource_dao.get(session, datasource_id)
            if not datasource:
                raise ETLConnectionError(f'数据源 (ID={datasource_id}) 不存在')
            password = _decrypt_password(datasource.password)

            affected = await self._write_to_database(datasource, password, table, data, mode, batch_size)

        context.metrics[f'node_{self.node_id}_written'] = affected
        return data

    async def _write_to_database(
        self,
        datasource: Any,
        password: str | None,
        table: str,
        data: list[dict[str, Any]],
        mode: str,
        batch_size: int,
    ) -> int:
        db_type = datasource.db_type

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
                if mode == 'truncate_insert':
                    await session.execute(text(f'TRUNCATE TABLE {table}'))

                if not data:
                    return 0

                columns = list(data[0].keys())
                col_names = ', '.join(columns)
                placeholders = ', '.join([f':{c}' for c in columns])

                total = 0
                for i in range(0, len(data), batch_size):
                    batch = data[i:i + batch_size]
                    stmt = text(f'INSERT INTO {table} ({col_names}) VALUES ({placeholders})')
                    for row in batch:
                        await session.execute(stmt, row)
                        total += 1

                await session.commit()
                return total
        finally:
            await engine.dispose()


class FileCSVLoadExecutor(BaseNodeExecutor):
    """CSV 文件写入"""

    node_type = 'load_file_csv'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        if not inputs or not inputs[0]:
            return []

        data = inputs[0]
        file_path = self.config.get('file_path', '')
        encoding = self.config.get('encoding', 'utf-8-sig')

        if not file_path:
            self.raise_error('文件路径不能为空')

        if not data:
            return data

        with open(file_path, 'w', newline='', encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            writer.writeheader()
            writer.writerows(data)

        context.metrics[f'node_{self.node_id}_written'] = len(data)
        return data


class FileJSONLoadExecutor(BaseNodeExecutor):
    """JSON 文件写入"""

    node_type = 'load_file_json'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        data = inputs[0] if inputs and inputs[0] else []
        file_path = self.config.get('file_path', '')
        indent = self.config.get('indent', 2)
        orient = self.config.get('orient', 'records')  # records / array

        if not file_path:
            self.raise_error('文件路径不能为空')

        with open(file_path, 'w', encoding='utf-8') as f:
            if orient == 'records':
                json.dump(data, f, ensure_ascii=False, indent=indent, default=str)
            else:
                json.dump(data, f, ensure_ascii=False, indent=indent, default=str)

        context.metrics[f'node_{self.node_id}_written'] = len(data)
        return data


class FileExcelLoadExecutor(BaseNodeExecutor):
    """Excel 文件写入"""

    node_type = 'load_file_excel'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        if not inputs or not inputs[0]:
            return []

        data = inputs[0]
        file_path = self.config.get('file_path', '')
        sheet_name = self.config.get('sheet_name', 'Sheet1')

        if not file_path:
            self.raise_error('文件路径不能为空')

        try:
            import openpyxl
        except ImportError:
            self.raise_error('需要安装 openpyxl: pip install openpyxl')

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_name

        if data:
            headers = list(data[0].keys())
            ws.append(headers)
            for row in data:
                ws.append([row.get(h, '') for h in headers])

        wb.save(file_path)
        wb.close()

        context.metrics[f'node_{self.node_id}_written'] = len(data)
        return data


class LogLoadExecutor(BaseNodeExecutor):
    """日志输出 (调试用)"""

    node_type = 'load_log'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        if not inputs or not inputs[0]:
            return []

        data = inputs[0]
        limit = self.config.get('preview_limit', 5)

        from loguru import logger

        logger.info(f'[ETL Node {self.node_id}] 收到 {len(data)} 行数据')
        for i, row in enumerate(data[:limit]):
            logger.debug(f'[ETL Node {self.node_id}] Row {i}: {json.dumps(row, ensure_ascii=False, default=str)}')

        if len(data) > limit:
            logger.info(f'[ETL Node {self.node_id}] ... 还有 {len(data) - limit} 行未显示')

        return data
