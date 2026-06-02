from fastapi import APIRouter

from backend.app.admin.api.v1.jobs.mongo_router import router as mongo_router
from backend.app.admin.api.v1.jobs.router import router as job_router

router = APIRouter(prefix='/jobs')

router.include_router(job_router, prefix='/pg', tags=['职位管理'])
router.include_router(mongo_router, prefix='/mongo', tags=['MongoDB 职位数据'])
