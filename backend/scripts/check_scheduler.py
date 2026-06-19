"""检查 task_scheduler 表数据"""
import asyncio, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path('backend/.env'))

async def main():
    import asyncpg
    conn = await asyncpg.connect(
        host=os.getenv('DATABASE_HOST'), port=int(os.getenv('DATABASE_PORT')),
        user=os.getenv('DATABASE_USER'), password=os.getenv('DATABASE_PASSWORD'),
        database=os.getenv('DATABASE_SCHEMA'),
    )
    rows = await conn.fetch('SELECT name, task, enabled, interval_every, interval_period, crontab FROM task_scheduler')
    print(f'task_scheduler 条目数: {len(rows)}')
    for r in rows:
        print(f'  name={r["name"]}, task={r["task"]}, enabled={r["enabled"]}, every={r["interval_every"]} {r["interval_period"] or ""} cron={r["crontab"] or ""} ')
    await conn.close()

asyncio.run(main())
