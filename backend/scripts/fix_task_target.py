"""更新宿舍电费任务: target_storage → local_database"""
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

    # 更新任务配置
    await conn.execute("""
        UPDATE sys_crawl_task
        SET target_storage = 'local_database',
            target_config = '{"table":"crawl_elec_record","mode":"insert","batch_size":1}',
            source_config = '{"type":"api","url":"http://ybhqcz.fjny.edu.cn/campus/webchat/dormEmRealRead/getEmRealRead","method":"POST","content_type":"form","cookies":"JSESSIONID=A09B8750A199528160B1C58D27991CAF","headers":{"Accept":"*/*","X-Requested-With":"XMLHttpRequest","Origin":"http://ybhqcz.fjny.edu.cn","Referer":"http://ybhqcz.fjny.edu.cn/campus/webchat/dormEmRealRead/finduser?openid=oNRuR0RIW7UEiCL7ZMGgwZcByhic"},"body":{"roomId":"7726521d-db3b-41b3-a2f8-c72fa9d6b768"},"data_path":"","transform":{"field_mapping":{"dt":"dt","useEq":"use_eq","TzEq":"tz_eq","remainEq":"remain_eq","freeEq":"free_eq","totalEq":"total_eq","rechargeEq":"recharge_eq","remainWqMoney":"remain_wq_money","status":"status"}}}',
            status = 'stopped'
        WHERE id = 4
    """)

    row = await conn.fetchrow('SELECT id, name, target_storage, status FROM sys_crawl_task WHERE id=4')
    if row:
        print(f'✅ 已更新: [{row["id"]}] {row["name"]}')
        print(f'   target_storage: {row["target_storage"]}')
        print(f'   status: {row["status"]}')

    await conn.close()
    print('请重启 Worker 使新配置生效')

asyncio.run(main())
