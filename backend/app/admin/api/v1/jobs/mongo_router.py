from typing import Annotated

from fastapi import APIRouter, Path, Query

from backend.app.admin.schema.mongo_job_schema import (
    MongoCompanyPageData,
    MongoJobPageData,
    GetMongoJobDetail,
    GetMongoCompanyDetail,
)
from backend.app.admin.service.mongo_job_service import mongo_job_service
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
