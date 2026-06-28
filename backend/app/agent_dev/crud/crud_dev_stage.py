"""Agent 开发任务阶段数据库操作"""

from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.agent_dev.enums import DevStageStatus, DevStageType
from backend.app.agent_dev.model import AgentDevStage
from backend.app.agent_dev.schema.dev_stage import CreateAgentDevStageParam, UpdateAgentDevStageParam


class CRUDAgentDevStage(CRUDPlus[AgentDevStage]):
    """任务阶段数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> AgentDevStage | None:
        return await self.select_model(db, pk)

    async def get_by_task(self, db: AsyncSession, task_id: int, order_by_seq: bool = True) -> Sequence[AgentDevStage]:
        """获取任务的所有阶段"""
        if order_by_seq:
            return await self.select_orders(db, ('sequence_order', 'asc'), task_id=task_id)
        return await self.select_models(db, task_id=task_id)

    async def get_by_task_and_type(
        self, db: AsyncSession, task_id: int, stage_type: DevStageType,
    ) -> AgentDevStage | None:
        """获取任务指定类型的阶段"""
        return await self.select_model_by_column(db, task_id=task_id, stage_type=stage_type)

    async def create(self, db: AsyncSession, obj: CreateAgentDevStageParam, task_id: int, created_by: int = 0) -> AgentDevStage:
        return await self.create_model(
            db, obj,
            task_id=task_id,
            created_by=created_by,
            flush=True,
        )

    async def update(self, db: AsyncSession, pk: int, obj: UpdateAgentDevStageParam) -> int:
        return await self.update_model(db, pk, obj)

    async def update_status(
        self, db: AsyncSession, pk: int, status: DevStageStatus,
        output_data: dict | None = None,
        error_message: str | None = None,
    ) -> int:
        updates = {'status': status}
        if output_data is not None:
            updates['output_data'] = output_data
        if error_message is not None:
            updates['error_message'] = error_message
        return await self.update_model(db, pk, updates)

    async def get_current_active_stage(self, db: AsyncSession, task_id: int) -> AgentDevStage | None:
        """获取当前进行中的阶段"""
        return await self.select_model_by_column(
            db, task_id=task_id, status=DevStageStatus.IN_PROGRESS,
        )

    async def get_next_pending_stage(self, db: AsyncSession, task_id: int) -> AgentDevStage | None:
        """获取下一个待处理的阶段"""
        from sqlalchemy import select, asc

        stmt = (
            select(self.model)
            .where(self.model.task_id == task_id)
            .where(self.model.status == DevStageStatus.PENDING)
            .order_by(asc(self.model.sequence_order))
            .limit(1)
        )
        results = await db.execute(stmt)
        return results.scalars().first()

    async def delete_by_task(self, db: AsyncSession, task_id: int) -> int:
        return await self.delete_model_by_column(db, task_id=task_id)


dev_stage_dao: CRUDAgentDevStage = CRUDAgentDevStage(AgentDevStage)
