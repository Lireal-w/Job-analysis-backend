"""ETL 数据流异步执行任务"""
from __future__ import annotations

import traceback
from typing import Any

from loguru import logger

from backend.app.admin.crud.crud_data_flow import data_flow_dao, data_flow_run_dao
from backend.app.admin.service.etl.engine import ETLPipeline
from backend.app.task.celery import celery_app
from backend.app.task.tasks.base import TaskBase
from backend.database.db import async_db_session
from backend.utils.timezone import timezone


@celery_app.task(
    name='etl_run_flow',
    base=TaskBase,
    bind=True,
    track_started=True,
)
async def etl_run_flow(
    self,
    flow_id: int,
    run_record_id: int,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, str]],
) -> dict[str, Any]:
    """异步执行 ETL 数据流

    Args:
        flow_id: 数据流 ID
        run_record_id: 运行记录 ID
        nodes: 节点配置列表
        edges: 边配置列表

    Returns:
        执行结果摘要
    """
    pipeline = ETLPipeline(nodes, edges)
    pipeline.context.flow_id = flow_id
    pipeline.context.run_record_id = run_record_id

    summary: dict[str, Any] = {
        'flow_id': flow_id,
        'run_record_id': run_record_id,
        'status': 'success',
        'total_input': 0,
        'total_output': 0,
        'total_error': 0,
        'error_message': None,
    }

    try:
        ctx = await pipeline.execute()

        # 计算总输入行数
        total_input = 0
        for key, value in ctx.metrics.items():
            if key.startswith('node_') and key.endswith('_rows') and isinstance(value, (int, float)):
                total_input += int(value)

        summary['total_input'] = total_input
        summary['total_output'] = total_input

        # 更新运行记录为成功
        end_time = timezone.now()
        duration = (end_time - pipeline.context.start_time).total_seconds()
        await _update_run_record(
            run_record_id,
            status='success',
            end_time=end_time,
            duration=duration,
            total_input=summary['total_input'],
            total_output=summary['total_output'],
        )

    except Exception as e:
        logger.error(f'[ETL] 数据流 {flow_id} 执行失败: {e}')
        logger.error(traceback.format_exc())

        summary['status'] = 'failed'
        summary['total_error'] = 1
        summary['error_message'] = f'{type(e).__name__}: {e}'

        end_time = timezone.now()
        duration = (end_time - pipeline.context.start_time).total_seconds()
        await _update_run_record(
            run_record_id,
            status='failed',
            end_time=end_time,
            duration=duration,
            error_message=summary['error_message'],
            log_detail={'traceback': traceback.format_exc()},
        )

    logger.info(f'[ETL] 数据流 {flow_id} 执行完成, 状态: {summary["status"]}')
    return summary


async def _update_run_record(run_record_id: int, **kwargs: Any) -> None:
    """更新运行记录"""
    try:
        async with async_db_session.begin() as session:
            await data_flow_run_dao.update_run(session, run_record_id, kwargs)
    except Exception as e:
        logger.error(f'更新运行记录失败 (ID={run_record_id}): {e}')
