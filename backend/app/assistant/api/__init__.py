"""AI 助手 API 路由"""

from fastapi import APIRouter

from backend.app.assistant.api.v1.ai_config import router as ai_config_router
from backend.core.conf import settings

router = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)
router.include_router(ai_config_router, tags=['AI 助手'])
