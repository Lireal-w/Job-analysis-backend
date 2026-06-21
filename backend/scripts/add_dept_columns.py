"""添加 dept_id 列到 sys_datasource 和 sys_dataset 表"""
import asyncio
from sqlalchemy import text
from backend.database.db import async_engine


async def add_columns():
    async with async_engine.connect() as conn:
        # Check if dept_id column exists in sys_datasource
        result = await conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name='sys_datasource' AND column_name='dept_id'")
        )
        if not result.fetchone():
            await conn.execute(text('ALTER TABLE sys_datasource ADD COLUMN dept_id BIGINT DEFAULT NULL'))
            print('Added dept_id to sys_datasource')
        else:
            print('dept_id already exists in sys_datasource')

        # Check if dept_id column exists in sys_dataset
        result = await conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name='sys_dataset' AND column_name='dept_id'")
        )
        if not result.fetchone():
            await conn.execute(text('ALTER TABLE sys_dataset ADD COLUMN dept_id BIGINT DEFAULT NULL'))
            print('Added dept_id to sys_dataset')
        else:
            print('dept_id already exists in sys_dataset')

        await conn.commit()
        print('Done!')


asyncio.run(add_columns())
