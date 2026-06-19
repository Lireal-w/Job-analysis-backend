from collections.abc import Sequence

from sqlalchemy import Select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import CrawlTask, CrawlTaskLog
from backend.app.admin.schema.crawl_task import CreateCrawlTaskParam, UpdateCrawlTaskParam


class CRUDCrawlTask(CRUDPlus[CrawlTask]):
    """采集任务数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> CrawlTask | None:
        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> CrawlTask | None:
        return await self.select_model_by_column(db, name=name)

    async def get_all(self, db: AsyncSession) -> Sequence[CrawlTask]:
        return await self.select_models(db)

    async def get_select(
        self,
        name: str | None = None,
        status: str | None = None,
        crawl_mode: str | None = None,
        schedule_type: str | None = None,
        source_datasource_id: int | None = None,
    ) -> Select:
        filters = {}
        if name is not None:
            filters['name__like'] = f'%{name}%'
        if status is not None:
            filters['status'] = status
        if crawl_mode is not None:
            filters['crawl_mode'] = crawl_mode
        if schedule_type is not None:
            filters['schedule_type'] = schedule_type
        if source_datasource_id is not None:
            filters['source_datasource_id'] = source_datasource_id
        return await self.select_order(['priority', 'id'], ['desc', 'desc'], **filters)

    async def create(self, db: AsyncSession, obj: CreateCrawlTaskParam) -> CrawlTask:
        return await self.create_model(db, obj, flush=True)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateCrawlTaskParam) -> int:
        return await self.update_model(db, pk, obj)

    async def update_status(self, db: AsyncSession, pk: int, status: str) -> int:
        return await self.update_model(db, pk, {'status': status})

    async def update_stats(
        self, db: AsyncSession, pk: int, stats: dict
    ) -> int:
        return await self.update_model(db, pk, stats)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


class CRUDCrawlTaskLog(CRUDPlus[CrawlTaskLog]):
    """采集任务日志数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> CrawlTaskLog | None:
        return await self.select_model(db, pk)

    async def get_by_task(
        self, db: AsyncSession, task_id: int, limit: int = 50
    ) -> Sequence[CrawlTaskLog]:
        stmt = await self.select_order('id', 'desc', task_id=task_id)
        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_run_id(
        self, db: AsyncSession, run_id: str
    ) -> CrawlTaskLog | None:
        return await self.select_model_by_column(db, run_id=run_id)

    async def create_log(self, db: AsyncSession, data: dict) -> CrawlTaskLog:
        obj = CrawlTaskLog(**data)
        db.add(obj)
        await db.flush()
        return obj

    async def update_log(self, db: AsyncSession, pk: int, data: dict) -> int:
        return await self.update_model(db, pk, data)

    async def delete_by_task(self, db: AsyncSession, task_id: int) -> int:
        return await self.delete_model_by_column(db, task_id=task_id)


crawl_task_dao: CRUDCrawlTask = CRUDCrawlTask(CrawlTask)
crawl_task_log_dao: CRUDCrawlTaskLog = CRUDCrawlTaskLog(CrawlTaskLog)
