"""Agent 开发节点数据库操作"""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.agent_dev.enums import DevAgentStatus, DevAgentType
from backend.app.agent_dev.model import AgentDevAgent
from backend.app.agent_dev.schema.dev_agent import (
    CreateAgentDevAgentParam,
    UpdateAgentDevAgentParam,
    UpdateAgentDevAgentHeartbeatParam,
)


class CRUDAgentDevAgent(CRUDPlus[AgentDevAgent]):
    """Agent 节点数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> AgentDevAgent | None:
        return await self.select_model(db, pk)

    async def get_all(self, db: AsyncSession) -> Sequence[AgentDevAgent]:
        return await self.select_models(db)

    async def get_by_type(self, db: AsyncSession, agent_type: DevAgentType) -> Sequence[AgentDevAgent]:
        """按类型获取 Agent 列表"""
        return await self.select_models(db, agent_type=agent_type)

    async def get_available(self, db: AsyncSession, agent_type: DevAgentType | None = None) -> Sequence[AgentDevAgent]:
        """获取可用的 Agent（空闲状态）"""
        filters = {'status': DevAgentStatus.IDLE}
        if agent_type is not None:
            filters['agent_type'] = agent_type
        return await self.select_models(db, **filters)

    async def create(self, db: AsyncSession, obj: CreateAgentDevAgentParam) -> AgentDevAgent:
        return await self.create_model(db, obj, flush=True)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateAgentDevAgentParam) -> int:
        return await self.update_model(db, pk, obj)

    async def heartbeat(self, db: AsyncSession, pk: int, obj: UpdateAgentDevAgentHeartbeatParam) -> int:
        """Agent 心跳上报"""
        from backend.utils.timezone import timezone

        updates = {
            'status': obj.status,
            'current_tasks': obj.current_tasks,
            'total_tasks_completed': obj.total_tasks_completed,
            'total_tasks_failed': obj.total_tasks_failed,
            'last_heartbeat': timezone.now(),
        }
        return await self.update_model(db, pk, updates)

    async def assign_task(self, db: AsyncSession, pk: int) -> int:
        """分配任务：增加当前任务数"""
        return await self.update_model(db, pk, {'current_tasks': AgentDevAgent.current_tasks + 1})

    async def complete_task(self, db: AsyncSession, pk: int, success: bool = True) -> int:
        """完成任务：减少当前任务数，累计完成/失败计数"""
        updates = {
            'current_tasks': AgentDevAgent.current_tasks - 1,
        }
        if success:
            updates['total_tasks_completed'] = AgentDevAgent.total_tasks_completed + 1
        else:
            updates['total_tasks_failed'] = AgentDevAgent.total_tasks_failed + 1
        return await self.update_model(db, pk, updates)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


dev_agent_dao: CRUDAgentDevAgent = CRUDAgentDevAgent(AgentDevAgent)
