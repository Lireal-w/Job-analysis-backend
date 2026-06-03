from typing import Annotated

from fastapi import APIRouter, Path, Query

from backend.app.admin.schema.mongo_job_schema import (
    MongoCompanyPageData,
    MongoJobPageData,
    GetMongoJobDetail,
    GetMongoCompanyDetail,
    OverviewStats,
    TrendItem,
    IndustryItem,
    EducationItem,
    HotJobItem,
    CityItem,
    ExperienceItem,
    SalaryRangeItem,
    JobTypeItem,
)
from backend.app.admin.service.mongo_job_service import mongo_job_service, mongo_dashboard_service
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.mongo_db import CurrentMongoDB

router = APIRouter()


@router.get(
    '/jobs',
    summary='分页获取 MongoDB 职位列表',
    dependencies=[DependsJwtAuth],
)
async def get_mongo_jobs_paginated(
    db: CurrentMongoDB,
    page: Annotated[int, Query(ge=1, description='页码')] = 1,
    size: Annotated[int, Query(gt=0, le=200, description='每页数量')] = 20,
    job_name: Annotated[str | None, Query(description='职位名称')] = None,
    company_name: Annotated[str | None, Query(description='公司名称')] = None,
    work_location: Annotated[str | None, Query(description='工作地点')] = None,
    education: Annotated[str | None, Query(description='学历要求')] = None,
) -> ResponseSchemaModel[MongoJobPageData]:
    """分页获取 MongoDB 职位列表（支持筛选）"""
    data = await mongo_job_service.get_job_list(
        db=db,
        page=page,
        size=size,
        job_name=job_name,
        company_name=company_name,
        work_location=work_location,
        education=education,
    )
    return response_base.success(data=data)


@router.get(
    '/jobs/{job_id}',
    summary='获取 MongoDB 职位详情',
    dependencies=[DependsJwtAuth],
)
async def get_mongo_job(
    db: CurrentMongoDB,
    job_id: Annotated[str, Path(description='职位唯一 ID')],
) -> ResponseSchemaModel[GetMongoJobDetail]:
    """获取 MongoDB 职位详情"""
    job = await mongo_job_service.get_job(db=db, job_id=job_id)
    return response_base.success(data=job)


@router.get(
    '/companies',
    summary='分页获取 MongoDB 公司列表',
    dependencies=[DependsJwtAuth],
)
async def get_mongo_companies_paginated(
    db: CurrentMongoDB,
    page: Annotated[int, Query(ge=1, description='页码')] = 1,
    size: Annotated[int, Query(gt=0, le=200, description='每页数量')] = 20,
    company_name: Annotated[str | None, Query(description='公司名称')] = None,
    industry: Annotated[str | None, Query(description='所属行业')] = None,
) -> ResponseSchemaModel[MongoCompanyPageData]:
    """分页获取 MongoDB 公司列表（支持筛选）"""
    data = await mongo_job_service.get_company_list(
        db=db,
        page=page,
        size=size,
        company_name=company_name,
        industry=industry,
    )
    return response_base.success(data=data)


@router.get(
    '/companies/{company_id}',
    summary='获取 MongoDB 公司详情',
    dependencies=[DependsJwtAuth],
)
async def get_mongo_company(
    db: CurrentMongoDB,
    company_id: Annotated[str, Path(description='公司唯一 ID')],
) -> ResponseSchemaModel[GetMongoCompanyDetail]:
    """获取 MongoDB 公司详情"""
    company = await mongo_job_service.get_company(db=db, company_id=company_id)
    return response_base.success(data=company)


# ==================== Dashboard 接口 ====================


@router.get(
    '/job-dashboard/overview',
    summary='获取岗位概览统计',
    dependencies=[DependsJwtAuth],
)
async def get_dashboard_overview(
    db: CurrentMongoDB,
) -> ResponseSchemaModel[OverviewStats]:
    """获取岗位概览统计：总岗位数、今日新增、平均薪资、公司总数"""
    data = await mongo_dashboard_service.get_overview(db=db)
    return response_base.success(data=data)


@router.get(
    '/job-dashboard/trend',
    summary='获取岗位数量趋势',
    dependencies=[DependsJwtAuth],
)
async def get_dashboard_trend(
    db: CurrentMongoDB,
) -> ResponseSchemaModel[list[TrendItem]]:
    """获取岗位数量趋势（按月统计岗位数量及平均薪资）"""
    data = await mongo_dashboard_service.get_trend(db=db)
    return response_base.success(data=data)


@router.get(
    '/job-dashboard/industry',
    summary='获取行业岗位分布',
    dependencies=[DependsJwtAuth],
)
async def get_dashboard_industry(
    db: CurrentMongoDB,
) -> ResponseSchemaModel[list[IndustryItem]]:
    """获取行业岗位分布：各行业的岗位数量及占比"""
    data = await mongo_dashboard_service.get_industry(db=db)
    return response_base.success(data=data)


@router.get(
    '/job-dashboard/education',
    summary='获取学历要求分布',
    dependencies=[DependsJwtAuth],
)
async def get_dashboard_education(
    db: CurrentMongoDB,
) -> ResponseSchemaModel[list[EducationItem]]:
    """获取学历要求分布：不同学历要求的岗位数量"""
    data = await mongo_dashboard_service.get_education(db=db)
    return response_base.success(data=data)


@router.get(
    '/job-dashboard/hot-jobs',
    summary='获取热门岗位 TOP10',
    dependencies=[DependsJwtAuth],
)
async def get_dashboard_hot_jobs(
    db: CurrentMongoDB,
) -> ResponseSchemaModel[list[HotJobItem]]:
    """获取热门岗位 TOP10：热门职位名称、数量及薪资区间"""
    data = await mongo_dashboard_service.get_hot_jobs(db=db)
    return response_base.success(data=data)


@router.get(
    '/job-dashboard/city',
    summary='获取城市岗位分布',
    dependencies=[DependsJwtAuth],
)
async def get_dashboard_city(
    db: CurrentMongoDB,
) -> ResponseSchemaModel[list[CityItem]]:
    """获取城市岗位分布：各城市的岗位数量及平均薪资"""
    data = await mongo_dashboard_service.get_city(db=db)
    return response_base.success(data=data)


@router.get(
    '/job-dashboard/experience',
    summary='获取工作经验要求分布',
    dependencies=[DependsJwtAuth],
)
async def get_dashboard_experience(
    db: CurrentMongoDB,
) -> ResponseSchemaModel[list[ExperienceItem]]:
    """获取工作经验要求分布：不同工作经验要求的岗位数量"""
    data = await mongo_dashboard_service.get_experience(db=db)
    return response_base.success(data=data)


@router.get(
    '/job-dashboard/salary-range',
    summary='获取薪资区间分布',
    dependencies=[DependsJwtAuth],
)
async def get_dashboard_salary_range(
    db: CurrentMongoDB,
) -> ResponseSchemaModel[list[SalaryRangeItem]]:
    """获取薪资区间分布：各薪资段的岗位数量"""
    data = await mongo_dashboard_service.get_salary_range(db=db)
    return response_base.success(data=data)


@router.get(
    '/job-dashboard/job-type',
    summary='获取岗位类型分布',
    dependencies=[DependsJwtAuth],
)
async def get_dashboard_job_type(
    db: CurrentMongoDB,
) -> ResponseSchemaModel[list[JobTypeItem]]:
    """获取岗位类型分布：全职、兼职、实习、远程等类型的数量"""
    data = await mongo_dashboard_service.get_job_type(db=db)
    return response_base.success(data=data)
