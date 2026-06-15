from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import ServerSSH
from backend.app.admin.schema.ssh import CreateSSHParam, UpdateSSHParam


class CRUDSSH(CRUDPlus[ServerSSH]):
    """SSH 服务器数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> ServerSSH | None:
        """
        获取服务器详情

        :param db: 数据库会话
        :param pk: 服务器 ID
        :return:
        """
        return await self.select_model(db, pk)

    async def get_select(self, name: str | None) -> Select:
        """
        获取服务器列表查询表达式

        :param name: 服务器名称
        :return:
        """
        filters = {}

        if name is not None:
            filters['name__like'] = f'%{name}%'

        return await self.select_order('id', **filters)

    async def get_by_name(self, db: AsyncSession, name: str) -> ServerSSH | None:
        """
        通过名称获取服务器

        :param db: 数据库会话
        :param name: 服务器名称
        :return:
        """
        return await self.select_model_by_column(db, name=name)

    async def get_all(self, db: AsyncSession) -> Sequence[ServerSSH]:
        """
        获取所有服务器

        :param db: 数据库会话
        :return:
        """
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj: CreateSSHParam) -> None:
        """
        创建服务器

        :param db: 数据库会话
        :param obj: 创建服务器参数
        :return:
        """
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateSSHParam) -> int:
        """
        更新服务器

        :param db: 数据库会话
        :param pk: 服务器 ID
        :param obj: 更新服务器参数
        :return:
        """
        return await self.update_model(db, pk, obj)

    async def update_status(self, db: AsyncSession, pk: int, status: int) -> int:
        """
        更新服务器状态

        :param db: 数据库会话
        :param pk: 服务器 ID
        :param status: 状态
        :return:
        """
        return await self.update_model(db, pk, {'status': status})

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        """
        批量删除服务器

        :param db: 数据库会话
        :param pks: 服务器 ID 列表
        :return:
        """
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


ssh_dao: CRUDSSH = CRUDSSH(ServerSSH)
