from fastapi import APIRouter

from backend.app.todo.api.v1.goal import router as todo_goal_router
from backend.app.todo.api.v1.task import router as todo_task_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH, tags=['待办事项'])

v1.include_router(todo_task_router, prefix='/todos')
v1.include_router(todo_goal_router, prefix='/todo-goals')
