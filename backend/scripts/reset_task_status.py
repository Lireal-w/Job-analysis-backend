"""重置采集任务状态"""
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
        database=os.getenv('DATABASE_SCHEMA', 'fba'),
    )

    # 查看任务状态
    rows = await conn.fetch('SELECT id, name, status FROM sys_crawl_task ORDER BY id')
    print('当前采集任务状态:')
    for r in rows:
        print(f'  [{r["id"]}] {r["name"]} → status={r["status"]}')

    # 重置卡在 running 的任务
    for r in rows:
        if r['status'] == 'running':
            await conn.execute('UPDATE sys_crawl_task SET status=$1 WHERE id=$2', 'stopped', r['id'])
            print(f'  ✅ 任务 [{r["id"]}] {r["name"]} 已重置为 stopped')

    # 查看 task_scheduler 表中的调度状态
    rows2 = await conn.fetch('SELECT id, name, enabled, total_run_count FROM task_scheduler ORDER BY id')
    print(f'\n调度器条目 ({len(rows2)}):')
    for r in rows2:
        print(f'  [{r["id"]}] {r["name"]} enabled={r["enabled"]} runs={r["total_run_count"]}')

    await conn.close()

asyncio.run(main())
