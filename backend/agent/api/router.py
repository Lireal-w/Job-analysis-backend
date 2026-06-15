"""Agent Router"""
from __future__ import annotations

from fastapi import APIRouter

from backend.agent.api.v1.tasks import router as tasks_router

router = APIRouter(prefix='/worker')

router.include_router(tasks_router, tags=['Worker 任务'])
