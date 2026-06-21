from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import QueryHistory, SavedQuery
from backend.app.admin.schema.query import CreateSavedQueryParam, UpdateSavedQueryParam


class CRUDQueryHistory(CRUDPlus[QueryHistory]):
    """查询历史数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> QueryHistory | None:
        return await self.select_model(db, pk)

    async def get_by_user(self, db: AsyncSession, user_id: int) -> Sequence[QueryHistory]:
        from sqlalchemy import select as sa_select
        stmt = (
            sa_select(QueryHistory)
            .where(QueryHistory.created_by == user_id)
            .order_by(QueryHistory.created_time.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def create_history(self, db: AsyncSession, obj: dict) -> None:
        """创建查询历史记录

        Note: obj 为 dict 类型，不能直接使用 create_model（它需要 Pydantic 模型），
        因此直接构造 SQLAlchemy 模型实例后 add 到 session。
        """
        model = QueryHistory(**obj)
        db.add(model)
        await db.flush()


class CRUDSavedQuery(CRUDPlus[SavedQuery]):
    """保存的查询数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> SavedQuery | None:
        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> SavedQuery | None:
        return await self.select_model_by_column(db, name=name)

    async def get_all(self, db: AsyncSession) -> Sequence[SavedQuery]:
        return await self.select_models(db)

    async def get_select(
        self, name: str | None = None, dataset_id: int | None = None, is_public: bool | None = None
    ) -> Select:
        filters = {}
        if name is not None:
            filters['name__like'] = f'%{name}%'
        if dataset_id is not None:
            filters['dataset_id'] = dataset_id
        if is_public is not None:
            filters['is_public'] = is_public
        return await self.select_order('id', **filters)

    async def create(self, db: AsyncSession, obj: CreateSavedQueryParam) -> SavedQuery:
        return await self.create_model(db, obj, flush=True)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateSavedQueryParam) -> int:
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


query_history_dao: CRUDQueryHistory = CRUDQueryHistory(QueryHistory)
saved_query_dao: CRUDSavedQuery = CRUDSavedQuery(SavedQuery)
