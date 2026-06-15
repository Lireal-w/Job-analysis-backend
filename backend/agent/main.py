"""Worker Node - 从节点 FastAPI 应用

可独立部署到其他服务器上，与主节点通信执行爬虫任务。

启动方式:
    # 在 agent 目录下
    pip install -r requirements.txt
    python -m backend.agent.main
    # 或
    granian backend.agent.main:app --host 0.0.0.0 --port 8001
"""
from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import psutil
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 将项目根目录加入 sys.path
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.agent.api.router import router as agent_router
from backend.agent.core.conf import settings
from backend.agent.state import (
    decrement_tasks,
    get_globals,
    increment_tasks,
    set_api_key,
    set_worker_id,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时注册到主节点
    if settings.REGISTER_ON_START:
        try:
            await _register_with_master()
        except Exception as e:
            print(f'[Worker] Master registration failed: {e}')

    # 启动心跳任务
    heartbeat_task = asyncio.create_task(_heartbeat_loop())

    yield

    # 清理
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass
    print('[Worker] Node shutdown complete')


async def _register_with_master():
    """向主节点注册"""
    url = f'{settings.MASTER_URL}{settings.FASTAPI_API_V1_PATH}/sys/workers/register'
    payload = {
        'name': settings.NODE_NAME,
        'host': settings.NODE_HOST if settings.NODE_HOST != '0.0.0.0' else _get_local_ip(),
        'port': settings.NODE_PORT,
        'version': '1.0.0',
        'max_tasks': settings.NODE_MAX_TASKS,
        'tags': settings.NODE_TAGS,
    }
    headers = {}
    if settings.MASTER_API_KEY:
        headers['Authorization'] = f'Bearer {settings.MASTER_API_KEY}'

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        result = resp.json()['data']
        print(f'[Worker] Registered with master: id={result["id"]}, api_key={result["api_key"][:8]}...')
        set_worker_id(result['id'])
        set_api_key(result['api_key'])


async def _heartbeat_loop():
    """定时心跳上报"""
    worker_id = get_worker_id()
    api_key = get_api_key()
    if not worker_id:
        print('[Worker] No worker_id, skipping heartbeat')
        return

    while True:
        try:
            url = f'{settings.MASTER_URL}{settings.FASTAPI_API_V1_PATH}/sys/workers/{worker_id}/heartbeat'
            payload = {
                'status': 'online',
                'cpu_usage': psutil.cpu_percent(interval=0.5),
                'memory_usage': psutil.virtual_memory().percent,
                'task_count': get_globals().get('running_tasks', 0),
            }
            headers = {}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'

            async with httpx.AsyncClient(timeout=5) as client:
                await client.put(url, json=payload, headers=headers)
        except Exception as e:
            print(f'[Worker] Heartbeat failed: {e}')

        await asyncio.sleep(settings.HEARTBEAT_INTERVAL)


def _get_local_ip() -> str:
    """获取本机 IP 地址"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.FASTAPI_TITLE,
    description=settings.FASTAPI_DESCRIPTION,
    docs_url=settings.FASTAPI_DOCS_URL,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# 注册路由
app.include_router(agent_router, prefix=settings.FASTAPI_API_V1_PATH)
