from fastapi import APIRouter

from backend.app.mobile.api.v1.app_version import router as app_version_router
from backend.app.mobile.api.v1.auth import router as auth_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH, tags=['移动端'])

v1.include_router(app_version_router, prefix='/mobile/versions')
v1.include_router(auth_router)
