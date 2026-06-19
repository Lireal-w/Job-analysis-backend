"""验证 AI 数据库表"""
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
    rows = await conn.fetch(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name LIKE 'sys_ai_%'"
    )
    print('AI module tables:')
    for r in rows:
        print(f'  - {r["table_name"]}')
    await conn.close()

asyncio.run(main())
