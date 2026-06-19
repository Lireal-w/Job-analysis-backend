"""采集任务管理工具 - AI 可调用的采集任务操作"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from backend.app.admin.crud.crud_crawl_task import crawl_task_dao
from backend.app.admin.schema.crawl_task import CreateCrawlTaskParam
from backend.app.assistant.tools import ai_tool
from backend.common.enums import CrawlMode, CrawlScheduleType
from backend.database.db import async_db_session


@ai_tool(
    name='create_crawl_task',
    description='创建数据采集任务。支持从 database/api/mihoyo_post/等源采集数据到目标存储。'
               'source_config 的 type 字段指定源类型，target_config 指定写入目标。',
    parameters={
        'name': {
            'type': 'string',
            'description': '任务名称，必须唯一',
        },
        'description': {
            'type': 'string',
            'description': '任务描述',
        },
        'source_type': {
            'type': 'string',
            'description': '源数据类型。可选: database(数据库), api(REST API), '
                           'mihoyo_post(米游社帖子), file_csv(CSV文件), '
                           'file_excel(Excel文件), file_json(JSON文件), mongodb',
        },
        'source_config_json': {
            'type': 'string',
            'description': '源采集配置 JSON 字符串。不同type不同:\n'
                           '- database: {"query":"SELECT * FROM table"}\n'
                           '- api: {"url":"https://...","method":"GET","data_path":"data.items"}\n'
                           '- mihoyo_post: {"cookies":"...","game_id":2,"max_pages":5}',
        },
        'target_storage': {
            'type': 'string',
            'description': '目标存储类型: database(数据库), file_csv(CSV文件), '
                           'file_json(JSON文件), file_excel(Excel文件), mongodb',
        },
        'target_config_json': {
            'type': 'string',
            'description': '目标存储配置 JSON 字符串。\n'
                           '- database: {"table":"target_table","mode":"insert"}\n'
                           '- file_csv: {"file_path":"/data/output.csv"}',
        },
        'crawl_mode': {
            'type': 'string',
            'description': '采集模式: full(全量), incremental(增量)',
            'enum': ['full', 'incremental'],
        },
        'incremental_key': {
            'type': 'string',
            'description': '增量字段名，crawl_mode=incremental时必填，如 updated_time',
        },
        'schedule_type': {
            'type': 'string',
            'description': '调度类型: none(不调度), cron(Cron表达式), interval(间隔)',
            'enum': ['none', 'cron', 'interval'],
        },
        'cron_expr': {
            'type': 'string',
            'description': 'Cron 表达式，schedule_type=cron 时必填，如 "0 */6 * * *"',
        },
        'interval_seconds': {
            'type': 'integer',
            'description': '间隔秒数，schedule_type=interval 时必填，>=10',
        },
    },
    required=['name', 'source_type', 'source_config_json', 'target_storage', 'target_config_json', 'crawl_mode'],
)
async def create_crawl_task(
    name: str,
    source_type: str,
    source_config_json: str,
    target_storage: str,
    target_config_json: str,
    crawl_mode: str = 'full',
    description: str = '',
    incremental_key: str | None = None,
    schedule_type: str = 'none',
    cron_expr: str | None = None,
    interval_seconds: int | None = None,
) -> str:
    """创建采集任务"""
    try:
        source_config = json.loads(source_config_json)
        source_config['type'] = source_type
        target_config = json.loads(target_config_json)

        # 从配置中提取是否使用数据源
        source_datasource_id = source_config.pop('datasource_id', None)
        target_datasource_id = target_config.pop('datasource_id', None)

        obj = CreateCrawlTaskParam(
            name=name,
            description=description or f'AI 自动创建的{source_type}采集任务',
            source_datasource_id=source_datasource_id,
            source_config=source_config,
            target_storage=target_storage,
            target_datasource_id=target_datasource_id,
            target_config=target_config,
            crawl_mode=CrawlMode(crawl_mode),
            incremental_key=incremental_key,
            schedule_type=CrawlScheduleType(schedule_type),
            cron_expr=cron_expr,
            interval_seconds=interval_seconds,
        )

        async with async_db_session() as db:
            existing = await crawl_task_dao.get_by_name(db, name)
            if existing:
                return f'任务名 "{name}" 已存在 (ID={existing.id})，请换一个名称'

            task = await crawl_task_dao.create(db, obj)
            await db.commit()

        return (
            f'✅ 采集任务创建成功！\n'
            f'   ID: {task.id}\n'
            f'   名称: {name}\n'
            f'   源类型: {source_type}\n'
            f'   目标存储: {target_storage}\n'
            f'   采集模式: {crawl_mode}\n'
            f'   调度: {schedule_type}\n'
            f'   可在"数据管理 → 采集任务"中查看和管理'
        )
    except json.JSONDecodeError as e:
        return f'❌ JSON 格式错误: {e}'
    except Exception as e:
        logger.error(f'[AITool] 创建采集任务失败: {e}')
        return f'❌ 创建失败: {type(e).__name__}: {e}'


@ai_tool(
    name='list_crawl_tasks',
    description='查询采集任务列表。可按名称/状态/源类型过滤。',
    parameters={
        'status': {
            'type': 'string',
            'description': '过滤状态: stopped(已停止), running(运行中), paused(已暂停), error(错误)',
            'enum': ['stopped', 'running', 'paused', 'error'],
        },
        'source_type': {
            'type': 'string',
            'description': '过滤源类型: database, api, mihoyo_post 等',
        },
        'limit': {
            'type': 'integer',
            'description': '返回条数限制 (默认 10)',
        },
    },
)
async def list_crawl_tasks(status: str | None = None, source_type: str | None = None, limit: int = 10) -> str:
    """查询采集任务列表"""
    async with async_db_session() as db:
        tasks = await crawl_task_dao.get_all(db)

    filtered = tasks
    if status:
        filtered = [t for t in filtered if t.status == status]
    if source_type:
        filtered = [t for t in filtered if t.source_config and t.source_config.get('type') == source_type]

    if not filtered:
        return '暂无符合条件的采集任务'

    lines = [f'共 {len(filtered)} 个采集任务:']
    for t in filtered[:limit]:
        src_type = (t.source_config or {}).get('type', '?')
        lines.append(
            f'  [{t.id}] {t.name}\n'
            f'       源={src_type} 目标={t.target_storage} '
            f'模式={t.crawl_mode} 状态={t.status}'
        )

    if len(filtered) > limit:
        lines.append(f'  ... 还有 {len(filtered) - limit} 条未显示')

    return '\n'.join(lines)


@ai_tool(
    name='start_crawl_task',
    description='启动一个已停止的采集任务',
    parameters={
        'task_id': {
            'type': 'integer',
            'description': '要启动的任务 ID',
        },
    },
    required=['task_id'],
)
async def start_crawl_task(task_id: int) -> str:
    """启动采集任务"""
    from backend.app.admin.service.crawl_task_service import crawl_task_service

    async with async_db_session() as db:
        task = await crawl_task_dao.get(db, task_id)
        if not task:
            return f'❌ 任务 ID={task_id} 不存在'

        if task.status == 'running':
            return f'⏳ 任务 "{task.name}" 已在运行中'

        await crawl_task_service.start(db=db, pk=task_id)
        await db.commit()

    return f'✅ 任务 "{task.name}" (ID={task_id}) 已启动！可在采集日志中查看执行进度'


@ai_tool(
    name='stop_crawl_task',
    description='停止一个运行中的采集任务',
    parameters={
        'task_id': {
            'type': 'integer',
            'description': '要停止的任务 ID',
        },
    },
    required=['task_id'],
)
async def stop_crawl_task(task_id: int) -> str:
    """停止采集任务"""
    from backend.app.admin.service.crawl_task_service import crawl_task_service

    async with async_db_session() as db:
        task = await crawl_task_dao.get(db, task_id)
        if not task:
            return f'❌ 任务 ID={task_id} 不存在'

        if task.status != 'running':
            return f'⏹️ 任务 "{task.name}" 当前未运行'

        await crawl_task_service.stop(db=db, pk=task_id)
        await db.commit()

    return f'⏹️ 任务 "{task.name}" (ID={task_id}) 已停止'
