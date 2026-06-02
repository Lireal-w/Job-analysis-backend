from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.job import Job
from backend.app.admin.schema.job_schema import CreateJobParam, UpdateJobParam


class CRUDJob(CRUDPlus[Job]):
    """职位数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> Job | None:
        """
        获取职位详情

        :param db: 数据库会话
        :param pk: 职位 ID
        :return:
        """
        return await self.select_model_by_column(db, id=pk)

    async def get_by_job_id(self, db: AsyncSession, job_id: str) -> Job | None:
        """
        通过唯一职位 ID 获取职位

        :param db: 数据库会话
        :param job_id: 职位唯一 ID
        :return:
        """
        return await self.select_model_by_column(db, job_id=job_id)

    async def get_select(
        self,
        *,
        job_name: str | None = None,
        company_name: str | None = None,
        min_salary: float | None = None,
        max_salary: float | None = None,
        work_location: str | None = None,
        education: str | None = None,
    ) -> Select:
        """
        获取职位查询语句（支持筛选）

        :param job_name: 职位名称
        :param company_name: 公司名称
        :param min_salary: 最低薪资
        :param max_salary: 最高薪资
        :param work_location: 工作地点
        :param education: 学历要求
        :return:
        """
        stmt = select(self.model)
        if job_name is not None:
            stmt = stmt.where(self.model.job_name.like(f'%{job_name}%'))
        if company_name is not None:
            stmt = stmt.where(self.model.company_name.like(f'%{company_name}%'))
        if min_salary is not None:
            stmt = stmt.where(self.model.salary_min >= min_salary)
        if max_salary is not None:
            stmt = stmt.where(self.model.salary_max <= max_salary)
        if work_location is not None:
            stmt = stmt.where(self.model.work_location.like(f'%{work_location}%'))
        if education is not None:
            stmt = stmt.where(self.model.education == education)
        stmt = stmt.order_by(self.model.created_at.desc())
        return stmt

    async def create(self, db: AsyncSession, obj: CreateJobParam) -> None:
        """
        创建职位

        :param db: 数据库会话
        :param obj: 创建职位参数
        :return:
        """
        await self.create_model(db, obj)

    async def create_or_update(self, db: AsyncSession, job_data: dict[str, Any]) -> Job:
        """
        根据job_id判断是新增还是更新

        :param db: 数据库会话
        :param job_data: 职位数据字典
        :return:
        """
        existing = await self.get_by_job_id(db, job_data.get("job_id"))
        if existing:
            for key, value in job_data.items():
                setattr(existing, key, value)
            await db.flush()
            return existing
        else:
            await self.create_model(db, CreateJobParam(**job_data))
            return await self.get_by_job_id(db, job_data.get("job_id"))

    async def update(self, db: AsyncSession, pk: int, obj: UpdateJobParam) -> int:
        """
        更新职位

        :param db: 数据库会话
        :param pk: 职位 ID
        :param obj: 更新职位参数
        :return:
        """
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pk: int) -> int:
        """
        删除职位

        :param db: 数据库会话
        :param pk: 职位 ID
        :return:
        """
        return await self.delete_model(db, pk)


job_dao: CRUDJob = CRUDJob(Job)
