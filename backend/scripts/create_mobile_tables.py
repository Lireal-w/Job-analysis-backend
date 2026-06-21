"""创建 mobile_app_version 表"""
import asyncio
from sqlalchemy import text
from backend.database.db import async_engine


async def create_table():
    async with async_engine.connect() as conn:
        # Check if table exists
        result = await conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_name='mobile_app_version'")
        )
        if not result.fetchone():
            # Create the table via SQL directly
            await conn.execute(text("""
                CREATE TABLE mobile_app_version (
                    id BIGSERIAL PRIMARY KEY,
                    app_name VARCHAR(64),
                    bundle_id VARCHAR(128) DEFAULT NULL,
                    platform SMALLINT DEFAULT 0,
                    version_name VARCHAR(32),
                    version_code INTEGER,
                    changelog TEXT DEFAULT NULL,
                    download_url VARCHAR(512) DEFAULT NULL,
                    apk_file_path VARCHAR(512) DEFAULT NULL,
                    apk_file_size BIGINT DEFAULT 0,
                    apk_md5 VARCHAR(64) DEFAULT NULL,
                    min_version_code INTEGER DEFAULT 0,
                    force_update BOOLEAN DEFAULT FALSE,
                    download_count INTEGER DEFAULT 0,
                    status INTEGER DEFAULT 1,
                    publish_status SMALLINT DEFAULT 0,
                    remark VARCHAR(256) DEFAULT NULL,
                    created_by BIGINT DEFAULT NULL,
                    updated_by BIGINT DEFAULT NULL,
                    created_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_time TIMESTAMP WITH TIME ZONE DEFAULT NULL
                );
                COMMENT ON TABLE mobile_app_version IS '移动端应用版本表';
                COMMENT ON COLUMN mobile_app_version.platform IS '平台(0安卓 1iOS 2鸿蒙)';
                COMMENT ON COLUMN mobile_app_version.publish_status IS '发布状态(0草稿 1已发布 2已归档)';
            """))
            await conn.commit()
            print('✅ Created table mobile_app_version')
        else:
            print('Table mobile_app_version already exists')

asyncio.run(create_table())
