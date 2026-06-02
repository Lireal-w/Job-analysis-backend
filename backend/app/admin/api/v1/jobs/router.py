from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.api import deps
from app.crud import job_crud
from app.schemas.job_schema import JobInDB, JobQueryParams
from app.tasks.job_crawler_tasks import run_job_crawler

router = APIRouter()

@router.get("/jobs", response_model=List[JobInDB])
def get_jobs(
    db: Session = Depends(deps.get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    job_name: Optional[str] = None,
    min_salary: Optional[float] = None,
    # ... 其他过滤条件
):
    """获取职位列表（支持分页、筛选）"""
    skip = (page - 1) * page_size
    jobs = job_crud.get_jobs(db, skip=skip, limit=page_size)
    return jobs

@router.get("/jobs/{job_id}", response_model=JobInDB)
def get_job(job_id: int, db: Session = Depends(deps.get_db)):
    """获取职位详情"""
    job = job_crud.get_job(db, job_id)
    return job

@router.post("/crawler/run")
def trigger_crawler():
    """手动触发爬虫任务"""
    task = run_job_crawler.delay()
    return {"task_id": task.id, "status": "started"}

@router.get("/crawler/status/{task_id}")
def get_crawler_status(task_id: str):
    """查询爬虫任务状态"""
    from app.tasks.celery_app import celery_app
    task = celery_app.AsyncResult(task_id)
    return {"task_id": task_id, "status": task.status, "result": task.result}