from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.job_crud import job_dao
from backend.app.admin.model.job import Job
from backend.app.admin.schema.job_schema import CreateJobParam, UpdateJobParam
from backend.common.exception import errors
from backend.common.pagination import paging_data
from sqlalchemy import Select


class JobService:
    """职位服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> Job:
        """
        获取职位详情

        :param db: 数据库会话
        :param pk: 职位 ID
        :return:
        """
        job = await job_dao.get(db, pk)
        if not job:
            raise errors.NotFoundError(msg='职位不存在')
        return job

    @staticmethod
    async def get_select(
        *,
        job_name: str | None = None,
        company_name: str | None = None,
        min_salary: float | None = None,
        max_salary: float | None = None,
        work_location: str | None = None,
        education: str | None = None,
    ) -> Select:
        """
        获取职位查询语句

        :param job_name: 职位名称
        :param company_name: 公司名称
        :param min_salary: 最低薪资
        :param max_salary: 最高薪资
        :param work_location: 工作地点
        :param education: 学历要求
        :return:
        """
        return await job_dao.get_select(
            job_name=job_name,
            company_name=company_name,
            min_salary=min_salary,
            max_salary=max_salary,
            work_location=work_location,
            education=education,
        )

    @staticmethod
    async def get_page_list(*, db: AsyncSession, select: Select) -> dict:
        """
        获取职位分页列表

        :param db: 数据库会话
        :param select: 查询语句
        :return:
        """
        return await paging_data(db, select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateJobParam) -> None:
        """
        创建职位

        :param db: 数据库会话
        :param obj: 创建职位参数
        :return:
        """
        existing = await job_dao.get_by_job_id(db, obj.job_id)
        if existing:
            raise errors.ConflictError(msg='职位已存在')
        await job_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateJobParam) -> int:
        """
        更新职位

        :param db: 数据库会话
        :param pk: 职位 ID
        :param obj: 更新职位参数
        :return:
        """
        job = await job_dao.get(db, pk)
        if not job:
            raise errors.NotFoundError(msg='职位不存在')
        count = await job_dao.update(db, pk, obj)
        return count

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int) -> int:
        """
        删除职位

        :param db: 数据库会话
        :param pk: 职位 ID
        :return:
        """
        job = await job_dao.get(db, pk)
        if not job:
            raise errors.NotFoundError(msg='职位不存在')
        count = await job_dao.delete(db, pk)
        return count


job_service: JobService = JobService()
