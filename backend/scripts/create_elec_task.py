"""创建宿舍电费采集任务"""
import asyncio, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path('backend/.env'))
os.environ['ENVIRONMENT'] = 'dev'

async def main():
    from backend.database.db import create_tables, async_db_session
    from backend.app.admin.schema.crawl_task import CreateCrawlTaskParam
    from backend.app.admin.crud.crud_crawl_task import crawl_task_dao
    from backend.common.enums import CrawlMode, CrawlScheduleType

    # 1. 确保数据库表存在
    print('1. 创建数据库表...')
    await create_tables()
    print('   ✅ 表已创建')

    # 2. 检查是否已存在同名任务
    async with async_db_session() as db:
        existing = await crawl_task_dao.get_by_name(db, '宿舍电费采集')
        if existing:
            print(f'2. ⏭️  任务已存在 (ID={existing.id})，跳过创建')
            print(f'   当前配置: schedule={existing.schedule_type}, interval={existing.interval_seconds}s')
            return

        # 3. 创建采集任务
        obj = CreateCrawlTaskParam(
            name='宿舍电费采集',
            description='定时采集宿舍电费数据，每3分钟一次，来源自校园API',
            source_datasource_id=None,
            source_config={
                'type': 'api',
                'url': 'http://ybhqcz.fjny.edu.cn/campus/webchat/dormEmRealRead/getEmRealRead',
                'method': 'POST',
                'content_type': 'form',
                'cookies': 'JSESSIONID=A09B8750A199528160B1C58D27991CAF',
                'headers': {
                    'Accept': '*/*',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Origin': 'http://ybhqcz.fjny.edu.cn',
                    'Referer': 'http://ybhqcz.fjny.edu.cn/campus/webchat/dormEmRealRead/finduser?openid=oNRuR0RIW7UEiCL7ZMGgwZcByhic',
                },
                'body': {
                    'roomId': '7726521d-db3b-41b3-a2f8-c72fa9d6b768',
                },
                'data_path': '',
            },
            target_storage='local_database',
            target_datasource_id=None,
            target_config={
                'table': 'crawl_elec_record',
                'mode': 'insert',
                'batch_size': 1,
            },
            crawl_mode=CrawlMode.FULL,
            schedule_type=CrawlScheduleType.INTERVAL,
            interval_seconds=180,
            concurrency=1,
            batch_size=1,
            retry_enabled=True,
            max_retries=3,
            retry_delay=30,
            priority=2,
            tags='电费,校园,定时',
        )

        task = await crawl_task_dao.create(db, obj)
        await db.commit()
        print(f'2. ✅ 采集任务已创建 (ID={task.id})')
        print(f'   名称: 宿舍电费采集')
        print(f'   目标: http://ybhqcz.fjny.edu.cn...')
        print(f'   目标表: crawl_elec_record')
        print(f'   调度: 每180秒 (3分钟)')
        print(f'   状态: {task.status}')
        print()
        print('3. 启动服务后，任务会在 Celery Beat 中自动调度')

asyncio.run(main())
