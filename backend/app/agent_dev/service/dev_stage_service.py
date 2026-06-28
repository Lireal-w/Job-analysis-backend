"""Agent 开发任务阶段服务"""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agent_dev.crud.crud_dev_stage import dev_stage_dao
from backend.app.agent_dev.enums import DevStageStatus, DevStageType
from backend.app.agent_dev.model import AgentDevStage
from backend.app.agent_dev.schema.dev_stage import (
    CreateAgentDevStageParam,
    UpdateAgentDevStageParam,
    UpdateAgentDevStageStatusParam,
)
from backend.common.exception import errors


class AgentDevStageService:
    """任务阶段服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> AgentDevStage:
        stage = await dev_stage_dao.get(db, pk)
        if not stage:
            raise errors.NotFoundError(msg='任务阶段不存在')
        return stage

    @staticmethod
    async def get_by_task(
        *,
        db: AsyncSession,
        task_id: int,
    ) -> Sequence[AgentDevStage]:
        return await dev_stage_dao.get_by_task(db, task_id)

    @staticmethod
    async def create(
        *,
        db: AsyncSession,
        task_id: int,
        obj: CreateAgentDevStageParam,
        created_by: int = 0,
    ) -> AgentDevStage:
        return await dev_stage_dao.create(db, obj, task_id=task_id, created_by=created_by)

    @staticmethod
    async def update(
        *,
        db: AsyncSession,
        pk: int,
        obj: UpdateAgentDevStageParam,
    ) -> int:
        stage = await dev_stage_dao.get(db, pk)
        if not stage:
            raise errors.NotFoundError(msg='任务阶段不存在')
        return await dev_stage_dao.update(db, pk, obj)

    @staticmethod
    async def update_status(
        *,
        db: AsyncSession,
        pk: int,
        obj: UpdateAgentDevStageStatusParam,
    ) -> int:
        stage = await dev_stage_dao.get(db, pk)
        if not stage:
            raise errors.NotFoundError(msg='任务阶段不存在')
        return await dev_stage_dao.update_status(
            db, pk,
            status=obj.status,
            output_data=obj.output_data,
            error_message=obj.error_message,
        )

    @staticmethod
    async def batch_create_stages(
        *,
        db: AsyncSession,
        task_id: int,
        stages: list[CreateAgentDevStageParam],
        created_by: int = 0,
    ) -> list[AgentDevStage]:
        """批量创建阶段"""
        results = []
        for stage in stages:
            result = await dev_stage_dao.create(db, stage, task_id=task_id, created_by=created_by)
            results.append(result)
        return results


dev_stage_service: AgentDevStageService = AgentDevStageService()
