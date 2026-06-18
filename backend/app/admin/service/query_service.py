import time

from collections.abc import Sequence
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_query import query_history_dao, saved_query_dao
from backend.app.admin.model import QueryHistory, SavedQuery
from backend.app.admin.schema.query import (
    CreateSavedQueryParam,
    ExecuteQueryParam,
    QueryResultSchema,
    UpdateSavedQueryParam,
)
from backend.app.admin.service.query.engine import (
    DEFAULT_RESULT_LIMIT,
    DEFAULT_QUERY_TIMEOUT,
    QueryEngine,
    validate_sql_safety,
)
from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.database.db import async_db_session


class QueryService:
    """查询服务类"""

    @staticmethod
    async def execute_query(*, db: AsyncSession, obj: ExecuteQueryParam) -> QueryResultSchema:
        """执行查询

        根据数据源连接信息执行真实 SQL 查询，支持多种数据库类型。
        如果未指定数据源，则使用应用数据库执行查询。

        Args:
            db: 数据库会话
            obj: 查询参数

        Returns:
            QueryResultSchema 查询结果
        """
        start_time = time.time()
        result = QueryResultSchema()

        # 验证查询参数
        if obj.query_type == 'sql':
            if not obj.query_sql or not obj.query_sql.strip():
                result.status = 'failed'
                result.error_message = 'SQL 查询语句不能为空'
                result.duration = round(time.time() - start_time, 4)

                # 记录查询历史
                await query_history_dao.create_history(db, {
                    'name': '空查询',
                    'dataset_id': obj.dataset_id,
                    'query_type': obj.query_type,
                    'query_sql': obj.query_sql,
                    'query_config': obj.query_config,
                    'result_count': 0,
                    'duration': result.duration,
                    'status': result.status,
                    'error_message': result.error_message,
                })
                return result

            # SQL 安全检查
            is_safe, error_msg = validate_sql_safety(obj.query_sql)
            if not is_safe:
                result.status = 'failed'
                result.error_message = error_msg
                result.duration = round(time.time() - start_time, 4)

                await query_history_dao.create_history(db, {
                    'name': obj.query_sql[:64],
                    'dataset_id': obj.dataset_id,
                    'query_type': obj.query_type,
                    'query_sql': obj.query_sql,
                    'query_config': obj.query_config,
                    'result_count': 0,
                    'duration': result.duration,
                    'status': result.status,
                    'error_message': result.error_message,
                })
                return result

        elif obj.query_type == 'visual':
            if not obj.query_config:
                result.status = 'failed'
                result.error_message = '可视化查询配置不能为空'
                result.duration = round(time.time() - start_time, 4)

                await query_history_dao.create_history(db, {
                    'name': '可视化查询',
                    'dataset_id': obj.dataset_id,
                    'query_type': obj.query_type,
                    'query_sql': obj.query_sql,
                    'query_config': obj.query_config,
                    'result_count': 0,
                    'duration': result.duration,
                    'status': result.status,
                    'error_message': result.error_message,
                })
                return result

            # 将可视化配置转换为 SQL（简单实现）
            obj.query_sql = QueryService._visual_config_to_sql(obj.query_config)

        # 执行查询
        try:
            engine = QueryEngine()

            if obj.dataset_id:
                # 使用指定数据源
                from backend.app.admin.crud.crud_datasource import datasource_dao

                datasource = await datasource_dao.get(db, obj.dataset_id)
                if not datasource:
                    result.status = 'failed'
                    result.error_message = f'数据源 (ID={obj.dataset_id}) 不存在'
                    result.duration = round(time.time() - start_time, 4)

                    await query_history_dao.create_history(db, {
                        'name': obj.query_sql[:64] if obj.query_sql else '可视化查询',
                        'dataset_id': obj.dataset_id,
                        'query_type': obj.query_type,
                        'query_sql': obj.query_sql,
                        'query_config': obj.query_config,
                        'result_count': 0,
                        'duration': result.duration,
                        'status': result.status,
                        'error_message': result.error_message,
                    })
                    return result

                if datasource.status != 1:
                    result.status = 'failed'
                    result.error_message = f'数据源 "{datasource.name}" 已停用'
                    result.duration = round(time.time() - start_time, 4)

                    await query_history_dao.create_history(db, {
                        'name': obj.query_sql[:64] if obj.query_sql else '可视化查询',
                        'dataset_id': obj.dataset_id,
                        'query_type': obj.query_type,
                        'query_sql': obj.query_sql,
                        'query_config': obj.query_config,
                        'result_count': 0,
                        'duration': result.duration,
                        'status': result.status,
                        'error_message': result.error_message,
                    })
                    return result

                query_result = await engine.execute(
                    datasource=datasource,
                    sql=obj.query_sql,
                    limit=obj.limit,
                    timeout=DEFAULT_QUERY_TIMEOUT,
                )
            else:
                # 使用应用数据库
                query_result = await QueryService._execute_on_app_db(
                    sql=obj.query_sql,
                    limit=obj.limit,
                )

            # 转换结果
            result.columns = query_result.columns
            result.rows = query_result.rows
            result.total = query_result.total
            result.duration = query_result.duration
            result.status = query_result.status
            result.error_message = query_result.error_message

        except Exception as e:
            logger.error(f'[QueryService] 查询执行异常: {e}')
            result.status = 'failed'
            result.error_message = f'{type(e).__name__}: {e}'
            result.duration = round(time.time() - start_time, 4)

        # 记录查询历史
        await query_history_dao.create_history(db, {
            'name': obj.query_sql[:64] if obj.query_sql else '可视化查询',
            'dataset_id': obj.dataset_id,
            'query_type': obj.query_type,
            'query_sql': obj.query_sql,
            'query_config': obj.query_config,
            'result_count': result.total,
            'duration': result.duration,
            'status': result.status,
            'error_message': result.error_message,
        })

        return result

    @staticmethod
    async def _execute_on_app_db(
        sql: str,
        limit: int = DEFAULT_RESULT_LIMIT,
    ) -> 'QueryResult':
        """在应用数据库上执行查询

        Args:
            sql: SQL 查询语句
            limit: 结果行数限制

        Returns:
            QueryResult 查询结果
        """
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession

        from backend.app.admin.service.query.engine import QueryResult

        start_time = time.time()

        # 添加 LIMIT（如果 SQL 中没有 LIMIT）
        sql_upper = sql.upper().rstrip(';')
        if 'LIMIT' not in sql_upper:
            sql = f'{sql.rstrip(";")} LIMIT {limit}'

        try:
            async with async_db_session() as session:
                query_result = await session.execute(text(sql))
                columns = list(query_result.keys())
                rows = [list(row) for row in query_result.fetchall()]

                return QueryResult(
                    columns=columns,
                    rows=rows,
                    total=len(rows),
                    duration=round(time.time() - start_time, 4),
                    status='success',
                    datasource_name='应用数据库',
                    datasource_type='internal',
                )
        except Exception as e:
            return QueryResult(
                status='failed',
                error_message=f'{type(e).__name__}: {e}',
                duration=round(time.time() - start_time, 4),
            )

    @staticmethod
    def _visual_config_to_sql(config: dict) -> str:
        """将可视化查询配置转换为 SQL

        简单实现：支持基本的表选择和字段选择。

        Args:
            config: 可视化查询配置

        Returns:
            SQL 查询语句
        """
        table = config.get('table', '')
        fields = config.get('fields', ['*'])
        where = config.get('where', '')
        order_by = config.get('order_by', '')
        group_by = config.get('group_by', '')

        if not table:
            return ''

        # 构建字段列表
        if isinstance(fields, list) and fields:
            fields_str = ', '.join(fields)
        else:
            fields_str = '*'

        # 构建 SQL
        sql = f'SELECT {fields_str} FROM {table}'

        if where:
            sql += f' WHERE {where}'

        if group_by:
            sql += f' GROUP BY {group_by}'

        if order_by:
            sql += f' ORDER BY {order_by}'

        return sql

    @staticmethod
    async def get_history(*, db: AsyncSession) -> dict[str, Any]:
        """获取查询历史（分页）"""
        select = await query_history_dao.select_order('id')
        page_data = await paging_data(db, select)
        return page_data

    @staticmethod
    async def get_history_detail(*, db: AsyncSession, pk: int) -> QueryHistory:
        """获取查询历史详情"""
        history = await query_history_dao.get(db, pk)
        if not history:
            raise errors.NotFoundError(msg='查询历史不存在')
        return history

    @staticmethod
    async def save_query(*, db: AsyncSession, obj: CreateSavedQueryParam) -> SavedQuery:
        """保存查询"""
        existing = await saved_query_dao.get_by_name(db, obj.name)
        if existing:
            raise errors.ConflictError(msg='查询名称已存在')
        return await saved_query_dao.create(db, obj)

    @staticmethod
    async def get_saved_queries(
        *, db: AsyncSession, name: str | None = None, dataset_id: int | None = None
    ) -> dict[str, Any]:
        """获取保存的查询列表（分页）"""
        select = await saved_query_dao.get_select(name=name, dataset_id=dataset_id)
        page_data = await paging_data(db, select)
        return page_data

    @staticmethod
    async def get_saved_query(*, db: AsyncSession, pk: int) -> SavedQuery:
        """获取保存的查询详情"""
        saved_query = await saved_query_dao.get(db, pk)
        if not saved_query:
            raise errors.NotFoundError(msg='保存的查询不存在')
        return saved_query

    @staticmethod
    async def update_saved_query(*, db: AsyncSession, pk: int, obj: UpdateSavedQueryParam) -> int:
        """更新保存的查询"""
        saved_query = await saved_query_dao.get(db, pk)
        if not saved_query:
            raise errors.NotFoundError(msg='保存的查询不存在')
        if obj.name is not None:
            existing = await saved_query_dao.get_by_name(db, obj.name)
            if existing and existing.id != pk:
                raise errors.ConflictError(msg='查询名称已存在')
        return await saved_query_dao.update(db, pk, obj)

    @staticmethod
    async def delete_saved_query(*, db: AsyncSession, pks: list[int]) -> int:
        """删除保存的查询"""
        return await saved_query_dao.delete(db, pks)

    @staticmethod
    async def get_datasource_schema(*, db: AsyncSession, dataset_id: int) -> dict[str, Any]:
        """获取数据源的表结构信息

        Args:
            db: 数据库会话
            dataset_id: 数据源 ID

        Returns:
            包含表名和列信息的字典
        """
        from backend.app.admin.crud.crud_datasource import datasource_dao

        datasource = await datasource_dao.get(db, dataset_id)
        if not datasource:
            raise errors.NotFoundError(msg='数据源不存在')

        if datasource.status != 1:
            raise errors.RequestError(msg='数据源已停用')

        engine = QueryEngine()
        return await engine.get_datasource_schema(datasource)


query_service: QueryService = QueryService()
