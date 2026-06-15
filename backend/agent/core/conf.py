"""
Worker Node Configuration
"""
from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录
BASE_PATH = Path(__file__).resolve().parent.parent
ENV_FILE_PATH = BASE_PATH / '.env'


class WorkerSettings(BaseSettings):
    """Worker 节点配置"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding='utf-8',
        extra='allow',
        case_sensitive=True,
    )

    # 节点身份
    NODE_NAME: str = Field(default='worker-1', description='节点名称')
    NODE_HOST: str = Field(default='0.0.0.0', description='绑定地址')
    NODE_PORT: int = Field(default=8001, description='节点 API 端口')
    NODE_MAX_TASKS: int = Field(default=5, description='最大并行任务数')
    NODE_TAGS: str = Field(default='', description='节点标签(逗号分隔)')

    # Master 节点配置
    MASTER_URL: str = Field(default='http://127.0.0.1:8000', description='主节点地址')
    MASTER_API_KEY: str = Field(default='', description='主节点 API 密钥(预共享)')

    # 心跳间隔（秒）
    HEARTBEAT_INTERVAL: int = Field(default=30, description='心跳上报间隔(秒)')
    REGISTER_ON_START: bool = Field(default=True, description='启动时自动注册')

    # FastAPI
    FASTAPI_API_V1_PATH: str = '/api/v1'
    FASTAPI_TITLE: str = 'FBA Worker Node'
    FASTAPI_DESCRIPTION: str = 'FastAPI Best Architecture Worker Node'
    FASTAPI_DOCS_URL: str = '/docs'

    # 爬虫配置
    CRAWLER_TIMEOUT: int = Field(default=300, description='爬虫超时时间(秒)')
    CRAWLER_OUTPUT_DIR: str = Field(default='output', description='爬虫输出目录')


@cache
def get_worker_settings() -> WorkerSettings:
    """获取 Worker 配置单例"""
    return WorkerSettings()


settings = get_worker_settings()
