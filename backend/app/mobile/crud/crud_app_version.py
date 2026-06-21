"""移动端版本管理数据库操作"""

from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.mobile.model import AppVersion
from backend.app.mobile.schema.app_version import CreateAppVersionParam, UpdateAppVersionParam


class CRUDAppVersion(CRUDPlus[AppVersion]):
    """版本管理数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> AppVersion | None:
        return await self.select_model(db, pk)

    async def get_all(self, db: AsyncSession) -> Sequence[AppVersion]:
        return await self.select_models(db)

    async def get_select(
        self,
        app_name: str | None = None,
        platform: int | None = None,
        status: int | None = None,
        publish_status: int | None = None,
    ) -> Select:
        filters = {}
        if app_name is not None:
            filters['app_name__like'] = f'%{app_name}%'
        if platform is not None:
            filters['platform'] = platform
        if status is not None:
            filters['status'] = status
        if publish_status is not None:
            filters['publish_status'] = publish_status
        return await self.select_order('created_time', 'desc', **filters)

    async def get_latest_by_platform(self, db: AsyncSession, platform: int) -> AppVersion | None:
        """获取指定平台的最新已发布版本"""
        from sqlalchemy import select, desc

        stmt = (
            select(self.model)
            .where(self.model.platform == platform)
            .where(self.model.publish_status == 1)
            .where(self.model.status == 1)
            .order_by(desc(self.model.version_code))
            .limit(1)
        )
        results = await db.execute(stmt)
        return results.scalars().first()

    async def create(self, db: AsyncSession, obj: CreateAppVersionParam) -> AppVersion:
        return await self.create_model(db, obj, flush=True)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateAppVersionParam) -> int:
        return await self.update_model(db, pk, obj)

    async def increment_download(self, db: AsyncSession, pk: int) -> int:
        """增加下载次数"""
        return await self.update_model(db, pk, {'download_count': AppVersion.download_count + 1})

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


app_version_dao: CRUDAppVersion = CRUDAppVersion(AppVersion)
