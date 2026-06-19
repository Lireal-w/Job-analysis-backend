"""验证采集任务 Schema 序列化 (通过 ORM)"""
import asyncio, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path('backend/.env'))
os.environ['ENVIRONMENT'] = 'dev'

async def main():
    from sqlalchemy import select
    from backend.database.db import async_db_session
    from backend.app.admin.model import CrawlTask
    from backend.app.admin.schema.crawl_task import GetCrawlTaskDetail

    async with async_db_session() as session:
        result = await session.execute(select(CrawlTask).order_by(CrawlTask.id))
        rows = result.scalars().all()
        print(f'ORM records: {len(rows)}')
        for r in rows:
            try:
                schema = GetCrawlTaskDetail.model_validate(r)
                data = schema.model_dump(mode='json')
                print(f'  Task [{r.id}] {r.name}: VALID')
                sc = type(data.get('source_config')).__name__
                tc = type(data.get('target_config')).__name__
                print(f'    source_config={sc}, target_config={tc}')
                for f in ['schedule_type','source_datasource_id','concurrency','rate_limit','total_run_count','total_records']:
                    print(f'    {f}={data.get(f)}')
            except Exception as e:
                print(f'  Task [{r.id}] {r.name}: INVALID - {e}')

    print('Done')

asyncio.run(main())

