from typing import Annotated

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from backend.core.conf import settings

# 全局 MongoDB 客户端
_mongo_client: AsyncIOMotorClient | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    """获取 MongoDB 客户端（单例）"""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=5000,
        )
    return _mongo_client


async def get_mongo_db() -> AsyncIOMotorDatabase:
    """获取 MongoDB 数据库实例"""
    client = get_mongo_client()
    return client[settings.MONGODB_DATABASE]


async def close_mongo_client() -> None:
    """关闭 MongoDB 客户端连接"""
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None


# FastAPI 依赖注入类型别名
CurrentMongoDB = Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)]
