"""H5 路由"""

from fastapi import APIRouter

from backend.app.h5.api.v1.task import router as h5_task_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH, tags=['H5 移动端'])

v1.include_router(h5_task_router)
