from fastapi import APIRouter

from backend.app.admin.api.router import v1 as admin_v1
from backend.app.assistant.api import router as assistant_v1
from backend.app.mobile.api.router import v1 as mobile_v1
from backend.app.task.api.router import v1 as task_v1
from backend.app.todo.api.router import v1 as todo_v1

router = APIRouter()

router.include_router(admin_v1)
router.include_router(assistant_v1)
router.include_router(mobile_v1)
router.include_router(task_v1)
router.include_router(todo_v1)
