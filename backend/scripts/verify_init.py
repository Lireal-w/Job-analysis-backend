"""验证初始化数据"""
import asyncio
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / '.env')

import asyncpg


async def main():
    conn = await asyncpg.connect(
        host=os.getenv('DATABASE_HOST', '127.0.0.1'),
        port=int(os.getenv('DATABASE_PORT', '5432')),
        user=os.getenv('DATABASE_USER', 'postgres'),
        password=os.getenv('DATABASE_PASSWORD', ''),
        database=os.getenv('DATABASE_SCHEMA', 'fba'),
    )

    tables = [
        ('sys_datasource', '数据源'),
        ('sys_crawl_task', '采集任务'),
        ('sys_quality_rule', '数据质量规则'),
        ('sys_alert_rule', '告警规则'),
        ('sys_resource_permission', '资源权限'),
    ]

    print('=' * 50)
    print('📊 初始化数据验证结果')
    print('=' * 50)
    for table, label in tables:
        cnt = await conn.fetchval(f'SELECT count(*) FROM {table}')
        print(f'  ✅ {label} ({table}): {cnt} 条')

    # 新菜单
    cnt = await conn.fetchval("SELECT count(*) FROM sys_menu WHERE id >= 51 AND id <= 67")
    print(f'  ✅ 新菜单 (sys_menu ID 51-67): {cnt} 条')

    # 新角色菜单映射
    cnt = await conn.fetchval('SELECT count(*) FROM sys_role_menu WHERE id >= 5')
    print(f'  ✅ 角色菜单分配: {cnt} 条')

    # 打印各表详细信息
    print('\n📋 采集任务列表:')
    rows = await conn.fetch('SELECT id, name, crawl_mode, status FROM sys_crawl_task')
    for r in rows:
        print(f'    [{r["id"]}] {r["name"]} (模式: {r["crawl_mode"]}, 状态: {r["status"]})')

    print('\n📋 数据质量规则:')
    rows = await conn.fetch('SELECT id, name, rule_type, severity FROM sys_quality_rule')
    for r in rows:
        print(f'    [{r["id"]}] {r["name"]} (类型: {r["rule_type"]}, 级别: {r["severity"]})')

    print('\n📋 告警规则:')
    rows = await conn.fetch('SELECT id, name, metric_type, threshold FROM sys_alert_rule')
    for r in rows:
        print(f'    [{r["id"]}] {r["name"]} (指标: {r["metric_type"]}, 阈值: {r["threshold"]})')

    print('\n📋 资源权限:')
    rows = await conn.fetch('SELECT id, name, resource_type, permission_type FROM sys_resource_permission')
    for r in rows:
        print(f'    [{r["id"]}] {r["name"]} (类型: {r["resource_type"]}, 权限: {r["permission_type"]})')

    await conn.close()
    print('\n✅ 验证完成')


if __name__ == '__main__':
    asyncio.run(main())
