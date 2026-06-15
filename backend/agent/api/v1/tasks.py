"""Worker Node API - 接收主节点下发的爬虫任务"""
from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from fastapi import APIRouter

from backend.agent.state import decrement_tasks, increment_tasks

router = APIRouter()


class TaskRequest:
    """任务请求模型"""

    def __init__(
        self,
        spider_name: str = 'xiaoyuan',
        keyword: str = '',
    ):
        self.spider_name = spider_name
        self.keyword = keyword


@router.post('/tasks', summary='接收并执行爬虫任务')
async def execute_task(task: TaskRequest) -> dict:
    """接收主节点分发的爬虫任务并执行"""
    increment_tasks()
    try:
        job_id = uuid.uuid4().hex
        output_dir = Path(__file__).resolve().parent.parent / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f'{task.spider_name}_{job_id}.json'

        command = [
            'scrapy', 'crawl', task.spider_name,
            '-o', str(output_file),
            '-t', 'json',
        ]
        if task.keyword:
            command.extend(['-a', f'keyword={task.keyword}'])

        print(f'[Worker] Starting crawler: {task.spider_name} (job={job_id})')

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            print(f'[Worker] Crawler finished: {output_file}')
            return {
                'job_id': job_id,
                'status': 'completed',
                'output_file': str(output_file),
                'spider': task.spider_name,
            }
        else:
            print(f'[Worker] Crawler failed: {result.stderr[:500]}')
            return {
                'job_id': job_id,
                'status': 'failed',
                'error': result.stderr[:500],
                'spider': task.spider_name,
            }
    except subprocess.TimeoutExpired:
        print(f'[Worker] Crawler timeout: {task.spider_name}')
        return {'status': 'failed', 'error': '爬虫执行超时'}
    except Exception as e:
        print(f'[Worker] Crawler error: {e}')
        return {'status': 'failed', 'error': str(e)}
    finally:
        decrement_tasks()


@router.get('/health', summary='Worker 健康检查')
async def health_check() -> dict:
    """返回 Worker 节点状态"""
    from backend.agent.state import get_globals

    import psutil

    return {
        'name': 'fba-worker',
        'status': 'healthy',
        'worker_id': get_globals().get('worker_id'),
        'running_tasks': get_globals().get('running_tasks', 0),
        'cpu_usage': psutil.cpu_percent(interval=0.5),
        'memory_usage': psutil.virtual_memory().percent,
    }
