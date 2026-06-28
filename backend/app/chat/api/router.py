"""聊天 API"""
from fastapi import APIRouter

from backend.app.chat.api.v1.router import router as chat_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH, tags=['聊天'])

v1.include_router(chat_router, prefix='/chat')
