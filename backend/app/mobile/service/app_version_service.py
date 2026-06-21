"""移动端版本管理服务"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.mobile.crud.crud_app_version import app_version_dao
from backend.app.mobile.model import AppVersion
from backend.app.mobile.schema.app_version import CreateAppVersionParam, UpdateAppVersionParam
from backend.common.exception import errors
from backend.common.pagination import paging_data


class AppVersionService:
    """版本管理服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> AppVersion:
        version = await app_version_dao.get(db, pk)
        if not version:
            raise errors.NotFoundError(msg='版本不存在')
        return version

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[AppVersion]:
        return await app_version_dao.get_all(db)

    @staticmethod
    async def get_list(
        *,
        db: AsyncSession,
        app_name: str | None = None,
        platform: int | None = None,
        status: int | None = None,
        publish_status: int | None = None,
    ) -> dict[str, Any]:
        select = await app_version_dao.get_select(
            app_name=app_name, platform=platform,
            status=status, publish_status=publish_status,
        )
        page_data = await paging_data(db, select)
        return page_data

    @staticmethod
    async def get_latest(*, db: AsyncSession, platform: int) -> AppVersion | None:
        """获取指定平台的最新版本"""
        return await app_version_dao.get_latest_by_platform(db, platform)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateAppVersionParam, created_by: int | None = None) -> AppVersion:
        # 检查相同 version_code 是否已存在
        existing = await app_version_dao.select_model_by_column(
            db, version_code=obj.version_code, platform=obj.platform,
        )
        if existing:
            raise errors.ConflictError(msg=f'该平台下版本号 {obj.version_code} 已存在')
        return await app_version_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateAppVersionParam) -> int:
        version = await app_version_dao.get(db, pk)
        if not version:
            raise errors.NotFoundError(msg='版本不存在')
        return await app_version_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        return await app_version_dao.delete(db, pks)

    @staticmethod
    async def record_download(*, db: AsyncSession, pk: int) -> AppVersion:
        """记录下载次数"""
        version = await app_version_dao.get(db, pk)
        if not version:
            raise errors.NotFoundError(msg='版本不存在')
        await app_version_dao.increment_download(db, pk)
        await db.refresh(version)
        return version


app_version_service: AppVersionService = AppVersionService()
