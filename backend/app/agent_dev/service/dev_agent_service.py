"""Agent 开发节点服务"""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agent_dev.crud.crud_dev_agent import dev_agent_dao
from backend.app.agent_dev.enums import DevAgentStatus, DevAgentType
from backend.app.agent_dev.model import AgentDevAgent
from backend.app.agent_dev.schema.dev_agent import (
    CreateAgentDevAgentParam,
    UpdateAgentDevAgentParam,
    UpdateAgentDevAgentHeartbeatParam,
)
from backend.common.exception import errors


class AgentDevAgentService:
    """Agent 节点服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> AgentDevAgent:
        agent = await dev_agent_dao.get(db, pk)
        if not agent:
            raise errors.NotFoundError(msg='Agent 节点不存在')
        return agent

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[AgentDevAgent]:
        return await dev_agent_dao.get_all(db)

    @staticmethod
    async def get_by_type(*, db: AsyncSession, agent_type: DevAgentType) -> Sequence[AgentDevAgent]:
        return await dev_agent_dao.get_by_type(db, agent_type)

    @staticmethod
    async def get_available(
        *,
        db: AsyncSession,
        agent_type: DevAgentType | None = None,
    ) -> Sequence[AgentDevAgent]:
        return await dev_agent_dao.get_available(db, agent_type)

    @staticmethod
    async def pick_available(
        *,
        db: AsyncSession,
        agent_type: DevAgentType,
    ) -> AgentDevAgent | None:
        """选取一个可用的 Agent（按完成任务数排序）"""
        from sqlalchemy import select, desc

        agents = await dev_agent_dao.get_available(db, agent_type)
        if not agents:
            return None
        # 选取完成任务最多的空闲 Agent
        return max(agents, key=lambda a: a.total_tasks_completed)

    @staticmethod
    async def create(
        *,
        db: AsyncSession,
        obj: CreateAgentDevAgentParam,
    ) -> AgentDevAgent:
        existing = await dev_agent_dao.select_model_by_column(db, name=obj.name)
        if existing:
            raise errors.ConflictError(msg=f'Agent 名称 "{obj.name}" 已存在')
        return await dev_agent_dao.create(db, obj)

    @staticmethod
    async def update(
        *,
        db: AsyncSession,
        pk: int,
        obj: UpdateAgentDevAgentParam,
    ) -> int:
        agent = await dev_agent_dao.get(db, pk)
        if not agent:
            raise errors.NotFoundError(msg='Agent 节点不存在')
        return await dev_agent_dao.update(db, pk, obj)

    @staticmethod
    async def heartbeat(
        *,
        db: AsyncSession,
        pk: int,
        obj: UpdateAgentDevAgentHeartbeatParam,
    ) -> int:
        agent = await dev_agent_dao.get(db, pk)
        if not agent:
            raise errors.NotFoundError(msg='Agent 节点不存在')
        return await dev_agent_dao.heartbeat(db, pk, obj)

    @staticmethod
    async def delete(
        *,
        db: AsyncSession,
        pks: list[int],
    ) -> int:
        return await dev_agent_dao.delete(db, pks)


dev_agent_service: AgentDevAgentService = AgentDevAgentService()
