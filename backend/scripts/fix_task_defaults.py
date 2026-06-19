"""修复已有采集任务的NULL字段"""
import asyncio, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path('backend/.env'))

import asyncpg

async def main():
    conn = await asyncpg.connect(
        host=os.getenv('DATABASE_HOST'), port=int(os.getenv('DATABASE_PORT')),
        user=os.getenv('DATABASE_USER'), password=os.getenv('DATABASE_PASSWORD'),
        database=os.getenv('DATABASE_SCHEMA', 'fba'),
    )
    rows = await conn.fetch('SELECT id, name, schedule_type, rate_limit, total_run_count, total_records FROM sys_crawl_task')
    print('Before fix:')
    for r in rows:
        print(f'  [{r["id"]}] {r["name"]} | schedule={r["schedule_type"]} | rate={r["rate_limit"]} | runs={r["total_run_count"]} | recs={r["total_records"]}')

    await conn.execute('''
        UPDATE sys_crawl_task SET
            schedule_type = COALESCE(schedule_type, 'none'),
            rate_limit = COALESCE(rate_limit, 0),
            total_run_count = COALESCE(total_run_count, 0),
            total_records = COALESCE(total_records, 0),
            concurrency = COALESCE(concurrency, 1),
            batch_size = COALESCE(batch_size, 100),
            retry_enabled = COALESCE(retry_enabled, true),
            max_retries = COALESCE(max_retries, 3),
            retry_delay = COALESCE(retry_delay, 60),
            retry_backoff = COALESCE(retry_backoff, true),
            priority = COALESCE(priority, 2)
        WHERE id = 2 OR schedule_type IS NULL
    ''')

    rows = await conn.fetch('SELECT id, name, schedule_type, rate_limit, total_run_count, total_records FROM sys_crawl_task')
    print('After fix:')
    for r in rows:
        print(f'  [{r["id"]}] {r["name"]} | schedule={r["schedule_type"]} | rate={r["rate_limit"]} | runs={r["total_run_count"]} | recs={r["total_records"]}')
    await conn.close()

asyncio.run(main())
