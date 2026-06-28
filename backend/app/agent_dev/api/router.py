"""Agent 开发编排模块路由聚合"""

from fastapi import APIRouter

from backend.app.agent_dev.api.v1 import dev_task, dev_stage, dev_agent
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH, tags=['Agent 开发编排'])

# 移动端/管理端 - 开发任务
v1.include_router(dev_task.router, prefix='/agent-dev/tasks')

# 管理端 - 任务阶段
v1.include_router(dev_stage.router, prefix='/agent-dev/stages')

# 管理端 - Agent 节点
v1.include_router(dev_agent.router, prefix='/agent-dev/agents')
