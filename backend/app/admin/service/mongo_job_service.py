from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.app.admin.schema.mongo_job_schema import (
    GetMongoCompanyDetail,
    GetMongoCompanyListDetail,
    GetMongoJobDetail,
    GetMongoJobListDetail,
    MongoCompanyPageData,
    MongoJobPageData,
)
from backend.common.exception import errors
from backend.core.conf import settings


class MongoJobService:
    """MongoDB 职位服务类"""

    @staticmethod
    async def get_job(*, db: AsyncIOMotorDatabase, job_id: str) -> GetMongoJobDetail:
        """
        获取 MongoDB 职位详情

        :param db: MongoDB 数据库实例
        :param job_id: 职位唯一 ID
        :return:
        """
        collection = db[settings.MONGODB_JOB_COLLECTION]
        doc = await collection.find_one({'job_id': job_id})
        if not doc:
            raise errors.NotFoundError(msg='职位不存在')
        return _parse_job_detail(doc)

    @staticmethod
    async def get_job_list(
        *,
        db: AsyncIOMotorDatabase,
        page: int = 1,
        size: int = 20,
        job_name: str | None = None,
        company_name: str | None = None,
        work_location: str | None = None,
        education: str | None = None,
    ) -> MongoJobPageData:
        """
        分页获取 MongoDB 职位列表

        :param db: MongoDB 数据库实例
        :param page: 页码
        :param size: 每页数量
        :param job_name: 职位名称（模糊搜索）
        :param company_name: 公司名称（模糊搜索）
        :param work_location: 工作地点（模糊搜索）
        :param education: 学历要求
        :return:
        """
        collection = db[settings.MONGODB_JOB_COLLECTION]
        query: dict[str, Any] = {}
        if job_name:
            query['job_name'] = {'$regex': job_name, '$options': 'i'}
        if company_name:
            query['company_name'] = {'$regex': company_name, '$options': 'i'}
        if work_location:
            query['work_location'] = {'$regex': work_location, '$options': 'i'}
        if education:
            query['education'] = education

        total = await collection.count_documents(query)
        skip = (page - 1) * size
        cursor = collection.find(query).sort('crawl_time', -1).skip(skip).limit(size)
        docs = await cursor.to_list(length=size)

        items = [_parse_job_list_item(doc) for doc in docs]
        return MongoJobPageData(items=items, total=total, page=page, size=size)

    @staticmethod
    async def get_company(*, db: AsyncIOMotorDatabase, company_id: str) -> GetMongoCompanyDetail:
        """
        获取 MongoDB 公司详情

        :param db: MongoDB 数据库实例
        :param company_id: 公司唯一 ID
        :return:
        """
        collection = db[settings.MONGODB_COMPANY_COLLECTION]
        doc = await collection.find_one({'company_id': company_id})
        if not doc:
            raise errors.NotFoundError(msg='公司不存在')
        return _parse_company_detail(doc)

    @staticmethod
    async def get_company_list(
        *,
        db: AsyncIOMotorDatabase,
        page: int = 1,
        size: int = 20,
        company_name: str | None = None,
        industry: str | None = None,
    ) -> MongoCompanyPageData:
        """
        分页获取 MongoDB 公司列表

        :param db: MongoDB 数据库实例
        :param page: 页码
        :param size: 每页数量
        :param company_name: 公司名称（模糊搜索）
        :param industry: 所属行业（模糊搜索）
        :return:
        """
        collection = db[settings.MONGODB_COMPANY_COLLECTION]
        query: dict[str, Any] = {}
        if company_name:
            query['company_name'] = {'$regex': company_name, '$options': 'i'}
        if industry:
            query['industry'] = {'$regex': industry, '$options': 'i'}

        total = await collection.count_documents(query)
        skip = (page - 1) * size
        cursor = collection.find(query).skip(skip).limit(size)
        docs = await cursor.to_list(length=size)

        items = [_parse_company_list_item(doc) for doc in docs]
        return MongoCompanyPageData(items=items, total=total, page=page, size=size)


def _parse_job_detail(doc: dict[str, Any]) -> GetMongoJobDetail:
    """解析 MongoDB 文档为职位详情 Schema"""
    return GetMongoJobDetail(
        mongo_id=str(doc['_id']),
        job_id=doc.get('job_id', ''),
        job_name=doc.get('job_name', ''),
        company_name=doc.get('company_name', ''),
        salary_text=doc.get('salary_text'),
        work_location=doc.get('work_location'),
        education=doc.get('education'),
        experience=doc.get('experience'),
        job_tags=doc.get('job_tags'),
        skills=doc.get('skills'),
        description=doc.get('description'),
        source_url=doc.get('source_url'),
        publish_date=doc.get('publish_date'),
        crawl_time=doc.get('crawl_time'),
    )


def _parse_job_list_item(doc: dict[str, Any]) -> GetMongoJobListDetail:
    """解析 MongoDB 文档为职位列表项 Schema"""
    return GetMongoJobListDetail(
        mongo_id=str(doc['_id']),
        job_id=doc.get('job_id', ''),
        job_name=doc.get('job_name', ''),
        company_name=doc.get('company_name', ''),
        salary_text=doc.get('salary_text'),
        work_location=doc.get('work_location'),
        education=doc.get('education'),
        experience=doc.get('experience'),
        crawl_time=doc.get('crawl_time'),
    )


def _parse_company_detail(doc: dict[str, Any]) -> GetMongoCompanyDetail:
    """解析 MongoDB 文档为公司详情 Schema"""
    return GetMongoCompanyDetail(
        mongo_id=str(doc['_id']),
        company_id=doc.get('company_id', ''),
        company_name=doc.get('company_name', ''),
        company_size=doc.get('company_size'),
        industry=doc.get('industry'),
        company_url=doc.get('company_url'),
    )


def _parse_company_list_item(doc: dict[str, Any]) -> GetMongoCompanyListDetail:
    """解析 MongoDB 文档为公司列表项 Schema"""
    return GetMongoCompanyListDetail(
        mongo_id=str(doc['_id']),
        company_id=doc.get('company_id', ''),
        company_name=doc.get('company_name', ''),
        company_size=doc.get('company_size'),
        industry=doc.get('industry'),
    )


mongo_job_service: MongoJobService = MongoJobService()
