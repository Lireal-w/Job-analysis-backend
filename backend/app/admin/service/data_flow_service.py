import uuid

from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_data_flow import data_flow_dao, data_flow_run_dao
from backend.app.admin.model import DataFlow
from backend.app.admin.schema.data_flow import CreateDataFlowParam, UpdateDataFlowParam
from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.utils.timezone import timezone


class DataFlowService:
    """数据流服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> DataFlow:
        data_flow = await data_flow_dao.get(db, pk)
        if not data_flow:
            raise errors.NotFoundError(msg='数据流不存在')
        return data_flow

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[DataFlow]:
        return await data_flow_dao.get_all(db)

    @staticmethod
    async def get_list(
        *, db: AsyncSession, name: str | None = None, status: str | None = None
    ) -> dict[str, Any]:
        select = await data_flow_dao.get_select(name=name, status=status)
        page_data = await paging_data(db, select)
        return page_data

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateDataFlowParam) -> None:
        existing = await data_flow_dao.get_by_name(db, obj.name)
        if existing:
            raise errors.ConflictError(msg='数据流名称已存在')
        await data_flow_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateDataFlowParam) -> int:
        data_flow = await data_flow_dao.get(db, pk)
        if not data_flow:
            raise errors.NotFoundError(msg='数据流不存在')
        return await data_flow_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        return await data_flow_dao.delete(db, pks)

    @staticmethod
    async def publish_flow(*, db: AsyncSession, pk: int) -> int:
        data_flow = await data_flow_dao.get(db, pk)
        if not data_flow:
            raise errors.NotFoundError(msg='数据流不存在')
        if data_flow.status != 'draft':
            raise errors.ForbiddenError(msg='仅草稿状态的数据流可以发布')
        return await data_flow_dao.update(db, pk, {'status': 'published', 'version': data_flow.version + 1})

    @staticmethod
    async def run_flow(*, db: AsyncSession, pk: int) -> dict[str, Any]:
        data_flow = await data_flow_dao.get(db, pk)
        if not data_flow:
            raise errors.NotFoundError(msg='数据流不存在')
        if data_flow.status != 'published':
            raise errors.ForbiddenError(msg='仅已发布的数据流可以运行')
        run_id = str(uuid.uuid4())
        run_record = {
            'flow_id': pk,
            'run_id': run_id,
            'status': 'running',
            'start_time': timezone.now(),
            'total_input': 0,
            'total_output': 0,
            'total_error': 0,
        }
        created = await data_flow_run_dao.create_run(db, run_record)
        return {
            'run_id': run_id,
            'flow_id': pk,
            'status': 'running',
            'record_id': created.id if hasattr(created, 'id') else None,
        }

    @staticmethod
    async def get_runs(*, db: AsyncSession, pk: int) -> Sequence[Any]:
        return await data_flow_run_dao.get_by_flow(db, pk)

    @staticmethod
    async def get_run_detail(*, db: AsyncSession, run_id: int) -> Any:
        run = await data_flow_run_dao.get(db, run_id)
        if not run:
            raise errors.NotFoundError(msg='运行记录不存在')
        return run


data_flow_service: DataFlowService = DataFlowService()
