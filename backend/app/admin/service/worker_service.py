import secrets

from collections.abc import Sequence
from datetime import timedelta
from typing import Any

import httpx

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_worker import worker_dao
from backend.app.admin.model import WorkerNode
from backend.app.admin.schema.worker import (
    CreateWorkerParam,
    UpdateWorkerParam,
    WorkerDispatchParam,
    WorkerHeartbeatParam,
    WorkerRegisterParam,
)
from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.utils.timezone import timezone


class WorkerService:
    """Worker 节点服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> WorkerNode:
        worker = await worker_dao.get(db, pk)
        if not worker:
            raise errors.NotFoundError(msg='Worker 节点不存在')
        return worker

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[WorkerNode]:
        return await worker_dao.get_all(db)

    @staticmethod
    async def get_online(*, db: AsyncSession) -> Sequence[WorkerNode]:
        return await worker_dao.get_online(db)

    @staticmethod
    async def get_list(
        *, db: AsyncSession, name: str | None = None, status: str | None = None
    ) -> dict[str, Any]:
        select = await worker_dao.get_select(name=name, status=status)
        return await paging_data(db, select)

    @staticmethod
    async def register(*, db: AsyncSession, obj: WorkerRegisterParam) -> WorkerNode:
        """Worker 注册（从节点调用）"""
        existing = await worker_dao.get_by_name(db, obj.name)
        if existing:
            # 已存在则更新注册信息
            update_data = {
                'host': obj.host,
                'port': obj.port,
                'version': obj.version,
                'max_tasks': obj.max_tasks,
                'tags': obj.tags,
                'status': 'online',
                'last_heartbeat': timezone.now(),
            }
            await worker_dao.update_heartbeat(db, existing.id, update_data)
            return await worker_dao.get(db, existing.id)

        # 生成 API 密钥
        api_key = secrets.token_hex(32)

        create = CreateWorkerParam(
            name=obj.name,
            host=obj.host,
            port=obj.port,
            tags=obj.tags,
            description=f'Auto-registered worker: {obj.name}',
            max_tasks=obj.max_tasks,
        )
        await worker_dao.create(db, create)
        worker = await worker_dao.get_by_name(db, obj.name)
        # 更新 api_key
        await worker_dao.update_heartbeat(db, worker.id, {
            'api_key': api_key,
            'status': 'online',
            'last_heartbeat': timezone.now(),
            'version': obj.version,
        })
        return await worker_dao.get(db, worker.id)

    @staticmethod
    async def heartbeat(
        *, db: AsyncSession, pk: int, obj: WorkerHeartbeatParam
    ) -> None:
        """Worker 心跳更新（从节点定时调用）"""
        worker = await worker_dao.get(db, pk)
        if not worker:
            raise errors.NotFoundError(msg='Worker 节点不存在')

        data = {
            'status': obj.status,
            'last_heartbeat': timezone.now(),
        }
        if obj.cpu_usage is not None:
            data['cpu_usage'] = obj.cpu_usage
        if obj.memory_usage is not None:
            data['memory_usage'] = obj.memory_usage
        if obj.task_count is not None:
            data['task_count'] = obj.task_count

        await worker_dao.update_heartbeat(db, pk, data)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateWorkerParam) -> None:
        existing = await worker_dao.get_by_name(db, obj.name)
        if existing:
            raise errors.ConflictError(msg='Worker 节点名称已存在')
        await worker_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateWorkerParam) -> int:
        worker = await worker_dao.get(db, pk)
        if not worker:
            raise errors.NotFoundError(msg='Worker 节点不存在')
        return await worker_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        return await worker_dao.delete(db, pks)

    @staticmethod
    async def dispatch_offline_check(*, db: AsyncSession, minutes: int = 5) -> int:
        """标记超时未心跳的 Worker 为 offline"""
        cutoff = timezone.now() - timedelta(minutes=minutes)

        stmt = (
            update(WorkerNode)
            .where(WorkerNode.last_heartbeat < cutoff, WorkerNode.status.in_(['online', 'busy']))
            .values(status='offline')
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @staticmethod
    async def dispatch_task(*, db: AsyncSession, obj: WorkerDispatchParam) -> dict[str, Any]:
        """分发爬虫任务到 Worker

        向指定 Worker 发送 HTTP 请求触发爬虫任务
        """
        if obj.worker_id:
            worker = await worker_dao.get(db, obj.worker_id)
            if not worker:
                raise errors.NotFoundError(msg='Worker 节点不存在')
            if worker.status == 'offline':
                raise errors.RequestError(msg='Worker 节点离线')
            workers = [worker]
        else:
            # 自动选择在线且负载最低的 Worker
            workers = await worker_dao.get_online(db)
            if not workers:
                raise errors.RequestError(msg='没有可用的 Worker 节点')
            workers = sorted(workers, key=lambda w: w.task_count or 0)

        worker = workers[0]
        url = f'http://{worker.host}:{worker.port}/api/v1/worker/tasks'

        headers = {'Authorization': f'Bearer {worker.api_key}'}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    json={
                        'spider_name': obj.spider_name,
                        'keyword': obj.keyword or '',
                    },
                    headers=headers,
                )
                resp.raise_for_status()
                result = resp.json()

            # 更新 Worker 任务计数
            await worker_dao.update_heartbeat(db, worker.id, {
                'task_count': (worker.task_count or 0) + 1,
            })

            return {
                'success': True,
                'worker': worker.name,
                'worker_id': worker.id,
                'result': result,
            }
        except httpx.RequestError as e:
            return {'success': False, 'worker': worker.name, 'error': f'请求失败: {str(e)}'}


worker_service: WorkerService = WorkerService()
