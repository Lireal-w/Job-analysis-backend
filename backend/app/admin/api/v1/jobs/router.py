from typing import Annotated

from fastapi import APIRouter, Path, Query

from backend.app.admin.schema.job_schema import CreateJobParam, GetJobDetail, GetJobListDetail, UpdateJobParam
from backend.app.admin.service.job_service import job_service
from backend.app.task.celery import celery_app
from backend.app.task.job_crawler_tasks import run_job_crawler
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get(
    '',
    summary='分页获取职位列表',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_jobs_paginated(
    db: CurrentSession,
    job_name: Annotated[str | None, Query(description='职位名称')] = None,
    company_name: Annotated[str | None, Query(description='公司名称')] = None,
    min_salary: Annotated[float | None, Query(description='最低薪资')] = None,
    max_salary: Annotated[float | None, Query(description='最高薪资')] = None,
    work_location: Annotated[str | None, Query(description='工作地点')] = None,
    education: Annotated[str | None, Query(description='学历要求')] = None,
) -> ResponseSchemaModel[PageData[GetJobListDetail]]:
    """分页获取职位列表（支持筛选）"""
    select = await job_service.get_select(
        job_name=job_name,
        company_name=company_name,
        min_salary=min_salary,
        max_salary=max_salary,
        work_location=work_location,
        education=education,
    )
    page_data = await job_service.get_page_list(db=db, select=select)
    return response_base.success(data=page_data)


@router.get('/{pk}', summary='获取职位详情', dependencies=[DependsJwtAuth])
async def get_job(
    db: CurrentSession,
    pk: Annotated[int, Path(description='职位 ID')],
) -> ResponseSchemaModel[GetJobDetail]:
    """获取职位详情"""
    job = await job_service.get(db=db, pk=pk)
    return response_base.success(data=job)


@router.post('', summary='创建职位', dependencies=[DependsJwtAuth])
async def create_job(
    db: CurrentSessionTransaction,
    obj: CreateJobParam,
) -> ResponseModel:
    """创建职位"""
    await job_service.create(db=db, obj=obj)
    return response_base.success()


@router.put('/{pk}', summary='更新职位', dependencies=[DependsJwtAuth])
async def update_job(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='职位 ID')],
    obj: UpdateJobParam,
) -> ResponseModel:
    """更新职位"""
    count = await job_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('/{pk}', summary='删除职位', dependencies=[DependsJwtAuth])
async def delete_job(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='职位 ID')],
) -> ResponseModel:
    """删除职位"""
    count = await job_service.delete(db=db, pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post('/crawler/run', summary='手动触发爬虫任务', dependencies=[DependsJwtAuth])
async def trigger_crawler() -> ResponseSchemaModel[dict]:
    """手动触发爬虫任务"""
    task = run_job_crawler.delay()
    return response_base.success(data={'task_id': task.id, 'status': 'started'})


@router.get('/crawler/status/{task_id}', summary='查询爬虫任务状态', dependencies=[DependsJwtAuth])
async def get_crawler_status(
    task_id: Annotated[str, Path(description='任务 ID')],
) -> ResponseSchemaModel[dict]:
    """查询爬虫任务状态"""
    task = celery_app.AsyncResult(task_id)
    return response_base.success(data={
        'task_id': task_id,
        'status': task.status,
        'result': task.result,
    })