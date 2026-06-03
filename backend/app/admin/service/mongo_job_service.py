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


class MongoDashboardService:
    """MongoDB 仪表盘服务类"""

    @staticmethod
    async def get_overview(*, db: AsyncIOMotorDatabase) -> "OverviewStats":
        """
        获取概览统计

        :param db: MongoDB 数据库实例
        :return: 概览统计数据
        """
        from backend.app.admin.schema.mongo_job_schema import OverviewStats

        job_col = db[settings.MONGODB_JOB_COLLECTION]
        company_col = db[settings.MONGODB_COMPANY_COLLECTION]

        total_jobs = await job_col.count_documents({})
        total_companies = await company_col.count_documents({})

        # 今日新增：crawl_time 在今天范围内的文档数
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_new = await job_col.count_documents({
            'crawl_time': {'$gte': today_start.strftime('%Y-%m-%d %H:%M:%S')},
        })

        # 平均薪资：基于 salary_min 和 salary_max 的中间值
        avg_salary_result = await job_col.aggregate([
            {'$match': {'salary_min': {'$ne': None}, 'salary_max': {'$ne': None}}},
            {'$group': {
                '_id': None,
                'avgSalary': {'$avg': {'$add': ['$salary_min', {'$divide': [{'$subtract': ['$salary_max', '$salary_min']}, 2]}]}},
            }},
        ]).to_list(length=1)
        avg_salary = round(avg_salary_result[0]['avgSalary'], 2) if avg_salary_result else 0

        return OverviewStats(
            totalJobs=total_jobs,
            todayNew=today_new,
            avgSalary=avg_salary,
            totalCompanies=total_companies,
        )

    @staticmethod
    async def get_trend(*, db: AsyncIOMotorDatabase) -> list["TrendItem"]:
        """
        获取岗位数量趋势（按月统计）

        :param db: MongoDB 数据库实例
        :return: 趋势数据列表
        """
        from backend.app.admin.schema.mongo_job_schema import TrendItem

        job_col = db[settings.MONGODB_JOB_COLLECTION]
        pipeline = [
            {'$match': {'crawl_time': {'$ne': None}}},
            {'$addFields': {
                'parsedDate': {'$dateFromString': {
                    'dateString': '$crawl_time',
                    'format': '%Y-%m-%d %H:%M:%S',
                    'onError': None,
                }},
            }},
            {'$match': {'parsedDate': {'$ne': None}}},
            {'$group': {
                '_id': {'$dateToString': {'date': '$parsedDate', 'format': '%Y-%m'}},
                'count': {'$sum': 1},
                'avgSalary': {'$avg': {'$add': [
                    {'$ifNull': ['$salary_min', 0]},
                    {'$divide': [{'$subtract': [
                        {'$ifNull': ['$salary_max', 0]},
                        {'$ifNull': ['$salary_min', 0]},
                    ]}, 2]},
                ]}},
            }},
            {'$sort': {'_id': 1}},
        ]
        results = await job_col.aggregate(pipeline).to_list(length=100)
        return [
            TrendItem(
                month=r['_id'],
                count=r['count'],
                avgSalary=round(r.get('avgSalary', 0) or 0, 2),
            )
            for r in results
            if r['_id']
        ]

    @staticmethod
    async def get_industry(*, db: AsyncIOMotorDatabase) -> list["IndustryItem"]:
        """
        获取行业岗位分布

        :param db: MongoDB 数据库实例
        :return: 行业分布数据列表
        """
        from backend.app.admin.schema.mongo_job_schema import IndustryItem

        job_col = db[settings.MONGODB_JOB_COLLECTION]
        total = await job_col.count_documents({'company_industry': {'$ne': None, '$ne': ''}})
        pipeline = [
            {'$match': {'company_industry': {'$ne': None, '$ne': ''}}},
            {'$group': {
                '_id': '$company_industry',
                'value': {'$sum': 1},
            }},
            {'$sort': {'value': -1}},
            {'$limit': 20},
        ]
        results = await job_col.aggregate(pipeline).to_list(length=20)
        return [
            IndustryItem(
                industry=r['_id'],
                value=r['value'],
                percent=round(r['value'] / total * 100, 2) if total > 0 else 0,
            )
            for r in results
        ]

    @staticmethod
    async def get_education(*, db: AsyncIOMotorDatabase) -> list["EducationItem"]:
        """
        获取学历要求分布

        :param db: MongoDB 数据库实例
        :return: 学历分布数据列表
        """
        from backend.app.admin.schema.mongo_job_schema import EducationItem

        job_col = db[settings.MONGODB_JOB_COLLECTION]
        pipeline = [
            {'$match': {'education': {'$ne': None, '$ne': ''}}},
            {'$group': {
                '_id': '$education',
                'value': {'$sum': 1},
            }},
            {'$sort': {'value': -1}},
        ]
        results = await job_col.aggregate(pipeline).to_list(length=50)
        return [
            EducationItem(education=r['_id'], value=r['value'])
            for r in results
        ]

    @staticmethod
    async def get_hot_jobs(*, db: AsyncIOMotorDatabase) -> list["HotJobItem"]:
        """
        获取热门岗位 TOP10

        :param db: MongoDB 数据库实例
        :return: 热门岗位数据列表
        """
        from backend.app.admin.schema.mongo_job_schema import HotJobItem

        job_col = db[settings.MONGODB_JOB_COLLECTION]
        pipeline = [
            {'$match': {'job_title': {'$ne': None, '$ne': ''}}},
            {'$group': {
                '_id': '$job_title',
                'count': {'$sum': 1},
                'minSalary': {'$min': {'$ifNull': ['$salary_min', None]}},
                'maxSalary': {'$max': {'$ifNull': ['$salary_max', None]}},
            }},
            {'$sort': {'count': -1}},
            {'$limit': 10},
        ]
        results = await job_col.aggregate(pipeline).to_list(length=10)
        items = []
        for r in results:
            min_s = r.get('minSalary')
            max_s = r.get('maxSalary')
            if min_s and max_s:
                salary = f'{int(min_s)}-{int(max_s)}'
            elif min_s:
                salary = f'{int(min_s)}+'
            elif max_s:
                salary = f'≤{int(max_s)}'
            else:
                salary = '面议'
            items.append(HotJobItem(name=r['_id'], count=r['count'], salary=salary))
        return items

    @staticmethod
    async def get_city(*, db: AsyncIOMotorDatabase) -> list["CityItem"]:
        """
        获取城市岗位分布

        :param db: MongoDB 数据库实例
        :return: 城市分布数据列表
        """
        from backend.app.admin.schema.mongo_job_schema import CityItem

        job_col = db[settings.MONGODB_JOB_COLLECTION]
        pipeline = [
            {'$match': {'work_city': {'$ne': None, '$ne': ''}}},
            {'$group': {
                '_id': '$work_city',
                'count': {'$sum': 1},
                'avgSalary': {'$avg': {'$add': [
                    {'$ifNull': ['$salary_min', 0]},
                    {'$divide': [{'$subtract': [
                        {'$ifNull': ['$salary_max', 0]},
                        {'$ifNull': ['$salary_min', 0]},
                    ]}, 2]},
                ]}},
            }},
            {'$sort': {'count': -1}},
            {'$limit': 30},
        ]
        results = await job_col.aggregate(pipeline).to_list(length=30)
        return [
            CityItem(
                city=r['_id'],
                count=r['count'],
                avgSalary=round(r.get('avgSalary', 0) or 0, 2),
            )
            for r in results
        ]

    @staticmethod
    async def get_experience(*, db: AsyncIOMotorDatabase) -> list["ExperienceItem"]:
        """
        获取工作经验要求分布

        :param db: MongoDB 数据库实例
        :return: 经验分布数据列表
        """
        from backend.app.admin.schema.mongo_job_schema import ExperienceItem

        job_col = db[settings.MONGODB_JOB_COLLECTION]
        pipeline = [
            {'$match': {'experience': {'$ne': None, '$ne': ''}}},
            {'$group': {
                '_id': '$experience',
                'value': {'$sum': 1},
            }},
            {'$sort': {'value': -1}},
        ]
        results = await job_col.aggregate(pipeline).to_list(length=50)
        return [
            ExperienceItem(experience=r['_id'], value=r['value'])
            for r in results
        ]

    @staticmethod
    async def get_salary_range(*, db: AsyncIOMotorDatabase) -> list["SalaryRangeItem"]:
        """
        获取薪资区间分布

        :param db: MongoDB 数据库实例
        :return: 薪资区间数据列表
        """
        from backend.app.admin.schema.mongo_job_schema import SalaryRangeItem

        job_col = db[settings.MONGODB_JOB_COLLECTION]

        # 定义薪资区间桶
        buckets = [
            ('3K以下', 0, 3000),
            ('3K-5K', 3000, 5000),
            ('5K-8K', 5000, 8000),
            ('8K-12K', 8000, 12000),
            ('12K-20K', 12000, 20000),
            ('20K-30K', 20000, 30000),
            ('30K-50K', 30000, 50000),
            ('50K以上', 50000, None),
        ]

        items = []
        for label, low, high in buckets:
            if high is not None:
                query = {'salary_min': {'$gte': low}, '$or': [
                    {'salary_max': {'$lt': high}},
                    {'salary_min': {'$lt': high}},
                ]}
            else:
                query = {'salary_min': {'$gte': low}}

            count = await job_col.count_documents(query)
            items.append(SalaryRangeItem(range=label, value=count))

        return items

    @staticmethod
    async def get_job_type(*, db: AsyncIOMotorDatabase) -> list["JobTypeItem"]:
        """
        获取岗位类型分布

        :param db: MongoDB 数据库实例
        :return: 岗位类型数据列表
        """
        from backend.app.admin.schema.mongo_job_schema import JobTypeItem

        job_col = db[settings.MONGODB_JOB_COLLECTION]
        pipeline = [
            {'$match': {'job_type': {'$ne': None, '$ne': ''}}},
            {'$group': {
                '_id': '$job_type',
                'value': {'$sum': 1},
            }},
            {'$sort': {'value': -1}},
        ]
        results = await job_col.aggregate(pipeline).to_list(length=20)
        return [
            JobTypeItem(type=r['_id'], value=r['value'])
            for r in results
        ]


mongo_dashboard_service: MongoDashboardService = MongoDashboardService()


mongo_job_service: MongoJobService = MongoJobService()
