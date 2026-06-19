"""初始化数据脚本

从 init_test_data.sql 中读取 SQL 并执行，将初始化数据写入数据库。
用法: python scripts/init_data.py [--snowflake] [--db-type postgresql|mysql]

默认使用 PostgreSQL + autoincrement 模式的 SQL 文件。
每条 SQL 语句独立执行，避免事务中断影响后续语句。
"""

import argparse
import os
import re
import sys
from pathlib import Path

# 将项目根目录加入 sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# 加载 .env
from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / '.env')

# 获取数据库配置
DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'postgresql')
DATABASE_HOST = os.getenv('DATABASE_HOST', '127.0.0.1')
DATABASE_PORT = int(os.getenv('DATABASE_PORT', '5432'))
DATABASE_USER = os.getenv('DATABASE_USER', 'postgres')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD', '')
DATABASE_SCHEMA = os.getenv('DATABASE_SCHEMA', 'fba')


def _get_sql_file(db_type: str, snowflake: bool) -> Path:
    sql_dir = BACKEND_DIR / 'sql' / db_type
    if snowflake:
        return sql_dir / 'init_snowflake_test_data.sql'
    return sql_dir / 'init_test_data.sql'


def _split_sql_statements(sql_content: str) -> list[str]:
    """将 SQL 内容分割为独立的语句"""
    statements = []
    # 先去除单行注释
    content = re.sub(r'--.*$', '', sql_content, flags=re.MULTILINE)
    # 按分号分割
    for stmt in content.split(';'):
        stmt = stmt.strip()
        if stmt:
            statements.append(stmt)
    return statements


async def main():
    parser = argparse.ArgumentParser(description='初始化数据')
    parser.add_argument('--snowflake', action='store_true', help='使用雪花ID模式')
    parser.add_argument('--db-type', choices=['postgresql', 'mysql'], default=DATABASE_TYPE, help='数据库类型')
    args = parser.parse_args()

    db_type = args.db_type
    sql_file = _get_sql_file(db_type, args.snowflake)

    if not sql_file.exists():
        print(f'❌ SQL 文件不存在: {sql_file}')
        sys.exit(1)

    print(f'📄 SQL 文件: {sql_file}')
    print(f'🔗 数据库: {db_type}://{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_SCHEMA}')

    # 读取并分割 SQL
    sql_content = sql_file.read_text(encoding='utf-8')
    statements = _split_sql_statements(sql_content)
    total = len(statements)
    print(f'📝 共解析到 {total} 条 SQL 语句\n')

    if db_type == 'postgresql':
        await _run_postgresql(statements)
    else:
        await _run_mysql(statements)


async def _run_postgresql(statements: list[str]):
    """使用 asyncpg 逐条执行（每条独立事务）"""
    import asyncpg

    conn = await asyncpg.connect(
        host=DATABASE_HOST,
        port=DATABASE_PORT,
        user=DATABASE_USER,
        password=DATABASE_PASSWORD,
        database=DATABASE_SCHEMA,
    )

    total = len(statements)
    success = 0
    skipped = 0
    failed = 0

    try:
        for i, stmt in enumerate(statements, 1):
            # 跳过 setval 语句（序列可能已被删除或不存在）
            is_setval = stmt.upper().startswith('SELECT SETVAL')

            try:
                await conn.execute(stmt)
                success += 1
                if i <= 3 or i == total or i % 10 == 0:
                    _print_status(i, total, '✅', stmt)
                elif is_setval:
                    print(f'  🔄 更新序列 ({i}/{total})')
            except asyncpg.exceptions.UniqueViolationError:
                skipped += 1
                _print_status(i, total, '⏭️', stmt, '数据已存在')
            except asyncpg.exceptions.UndefinedTableError as e:
                failed += 1
                _print_status(i, total, '⚠️', stmt, f'表不存在: {e}')
            except asyncpg.exceptions.UndefinedColumnError as e:
                failed += 1
                _print_status(i, total, '⚠️', stmt, f'字段不存在: {e}')
            except Exception as e:
                err_msg = str(e).lower()
                if 'already exists' in err_msg or 'duplicate' in err_msg or 'unique' in err_msg:
                    skipped += 1
                    _print_status(i, total, '⏭️', stmt, '数据已存在')
                else:
                    failed += 1
                    _print_status(i, total, '❌', stmt, str(e)[:80])
    finally:
        await conn.close()

    print(f'\n{"="*50}')
    print(f'✅ 成功: {success} | ⏭️  跳过: {skipped} | ❌ 失败: {failed} | 总计: {total}')
    print(f'{"="*50}')


async def _run_mysql(statements: list[str]):
    """使用 aiomysql 逐条执行（每条独立事务）"""
    import aiomysql

    conn = await aiomysql.connect(
        host=DATABASE_HOST,
        port=DATABASE_PORT,
        user=DATABASE_USER,
        password=DATABASE_PASSWORD,
        db=DATABASE_SCHEMA,
        autocommit=True,
    )

    total = len(statements)
    success = 0
    skipped = 0
    failed = 0

    try:
        async with conn.cursor() as cur:
            for i, stmt in enumerate(statements, 1):
                try:
                    await cur.execute(stmt)
                    success += 1
                    if i <= 3 or i == total or i % 10 == 0:
                        _print_status(i, total, '✅', stmt)
                except Exception as e:
                    err_msg = str(e).lower()
                    if 'already exists' in err_msg or 'duplicate' in err_msg or 'unique' in err_msg or '1062' in str(e):
                        skipped += 1
                        _print_status(i, total, '⏭️', stmt, '数据已存在')
                    elif '1146' in str(e):
                        failed += 1
                        _print_status(i, total, '⚠️', stmt, f'表不存在')
                    else:
                        failed += 1
                        _print_status(i, total, '❌', stmt, str(e)[:80])
    finally:
        conn.close()

    print(f'\n{"="*50}')
    print(f'✅ 成功: {success} | ⏭️  跳过: {skipped} | ❌ 失败: {failed} | 总计: {total}')
    print(f'{"="*50}')


def _print_status(i: int, total: int, icon: str, stmt: str, detail: str = ''):
    """打印执行状态"""
    # 提取 SQL 类型和表名
    first_line = stmt.split('\n')[0].strip()
    prefix = detail and f' — {detail}' or ''
    print(f'  {icon} ({i}/{total}) {first_line[:70]}{prefix}')


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
