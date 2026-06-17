import time

from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_query import query_history_dao, saved_query_dao
from backend.app.admin.model import QueryHistory, SavedQuery
from backend.app.admin.schema.query import (
    CreateSavedQueryParam,
    ExecuteQueryParam,
    QueryResultSchema,
    UpdateSavedQueryParam,
)
from backend.common.exception import errors
from backend.common.pagination import paging_data


class QueryService:
    """查询服务类"""

    @staticmethod
    async def execute_query(*, db: AsyncSession, obj: ExecuteQueryParam) -> QueryResultSchema:
        """
        执行查询

        注意: 当前为占位实现，返回模拟数据。
        实际 SQL 执行将在后续迭代中对接具体数据源。
        """
        start_time = time.time()
        duration = 0.0
        result = QueryResultSchema()

        try:
            # 占位: 模拟查询执行
            # TODO: 实际执行 SQL 查询逻辑
            if obj.query_type == 'sql' and obj.query_sql:
                # 模拟 SQL 查询结果
                result.columns = ['id', 'name', 'value']
                result.rows = [
                    [1, '示例数据A', 100],
                    [2, '示例数据B', 200],
                    [3, '示例数据C', 300],
                ]
                result.total = len(result.rows)
                result.status = 'success'
            elif obj.query_type == 'visual' and obj.query_config:
                # 模拟可视化查询结果
                result.columns = ['category', 'count']
                result.rows = [
                    ['分类1', 150],
                    ['分类2', 230],
                    ['分类3', 180],
                ]
                result.total = len(result.rows)
                result.status = 'success'
            else:
                result.status = 'failed'
                result.error_message = '查询 SQL 或查询配置不能为空'

        except Exception as e:
            result.status = 'failed'
            result.error_message = str(e)

        duration = time.time() - start_time
        result.duration = round(duration, 4)

        # 记录查询历史
        await query_history_dao.create_history(
            db,
            {
                'name': obj.query_sql[:64] if obj.query_sql else '可视化查询',
                'dataset_id': obj.dataset_id,
                'query_type': obj.query_type,
                'query_sql': obj.query_sql,
                'query_config': obj.query_config,
                'result_count': result.total,
                'duration': result.duration,
                'status': result.status,
                'error_message': result.error_message,
            },
        )

        return result

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


query_service: QueryService = QueryService()
