"""为采集任务注册 Celery Beat 调度（task_scheduler 表）

修复：采集任务的 schedule 只写入了 beat_schedule 字典，
而 DatabaseScheduler 实际读取的是 task_scheduler 表。
"""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path('backend/.env'))
os.environ['ENVIRONMENT'] = 'dev'


async def main():
    from sqlalchemy import select
    from backend.database.db import async_db_session
    from backend.app.admin.crud.crud_crawl_task import crawl_task_dao
    from backend.app.task.model.scheduler import TaskScheduler
    from backend.app.task.enums import TaskSchedulerType, PeriodType

    async with async_db_session() as db:
        tasks = await crawl_task_dao.get_all(db)
        crawl_tasks = [t for t in tasks if t.schedule_type and t.schedule_type != 'none']

        if not crawl_tasks:
            print('没有需要注册调度的采集任务')
            return

        print(f'找到 {len(crawl_tasks)} 个需注册调度的采集任务:\n')

        for ct in crawl_tasks:
            schedule_name = f'crawl_task_{ct.id}'

            # 检查是否已注册
            stmt = select(TaskScheduler).where(TaskScheduler.name == schedule_name)
            result = await db.execute(stmt)
            existing = result.scalars().first()

            if existing:
                print(f'  ⏭️  [{ct.id}] {ct.name} → 调度 "{schedule_name}" 已存在 (ID={existing.id})')
                continue

            # 注意：TaskScheduler 有名为 kwargs 的字段，不能用 **dict 传参
            if ct.schedule_type == 'interval' and ct.interval_seconds:
                scheduler = TaskScheduler(
                    name=schedule_name,
                    task='crawl_task_scheduled',
                    args=json.dumps([ct.id]),
                    kwargs=None,
                    queue=None,
                    exchange=None,
                    routing_key=None,
                    start_time=None,
                    expire_time=None,
                    expire_seconds=None,
                    type=TaskSchedulerType.INTERVAL.value,
                    interval_every=ct.interval_seconds,
                    interval_period=PeriodType.SECONDS.value,
                    crontab='* * * * *',
                    one_off=False,
                    enabled=True,
                    remark=f'采集任务[{ct.id}] {ct.name} 每{ct.interval_seconds}秒',
                )
                print(f'  ✅ [{ct.id}] {ct.name}')
                print(f'     调度名: {schedule_name}')
                print(f'     任务: crawl_task_scheduled({ct.id})  ⏱ {ct.interval_seconds}秒/次')

            elif ct.schedule_type == 'cron' and ct.cron_expr:
                scheduler = TaskScheduler(
                    name=schedule_name,
                    task='crawl_task_scheduled',
                    args=json.dumps([ct.id]),
                    kwargs=None,
                    queue=None,
                    exchange=None,
                    routing_key=None,
                    start_time=None,
                    expire_time=None,
                    expire_seconds=None,
                    type=TaskSchedulerType.CRONTAB.value,
                    interval_every=None,
                    interval_period=None,
                    crontab=ct.cron_expr,
                    one_off=False,
                    enabled=True,
                    remark=f'采集任务[{ct.id}] {ct.name} cron={ct.cron_expr}',
                )
                print(f'  ✅ [{ct.id}] {ct.name}')
                print(f'     调度名: {schedule_name}')
                print(f'     任务: crawl_task_scheduled({ct.id})  cron={ct.cron_expr}')
            else:
                print(f'  ⚠️  [{ct.id}] {ct.name} → 调度配置不完整，跳过')
                continue

            db.add(scheduler)

        await db.commit()
        print(f'\n✅ 完成! 请重启 Celery Beat 使调度生效')


asyncio.run(main())
