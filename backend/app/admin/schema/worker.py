from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class WorkerSchemaBase(SchemaBase):
    """Worker 基础模型"""

    name: str = Field(max_length=128, description='节点名称')
    host: str = Field(max_length=256, description='节点主机地址')
    port: int = Field(default=8001, description='节点 API 端口')
    tags: str | None = Field(default=None, max_length=512, description='节点标签(逗号分隔)')
    description: str | None = Field(default=None, max_length=256, description='描述')
    max_tasks: int = Field(default=5, description='最大并行任务数')


class CreateWorkerParam(WorkerSchemaBase):
    """创建 Worker 参数"""


class UpdateWorkerParam(WorkerSchemaBase):
    """更新 Worker 参数"""


class GetWorkerDetail(WorkerSchemaBase):
    """Worker 详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Worker ID')
    api_key: str | None = Field(None, description='节点 API 密钥')
    status: str = Field(description='状态(online/offline/busy)')
    version: str | None = Field(None, description='节点版本')
    cpu_usage: float | None = Field(None, description='CPU 使用率')
    memory_usage: float | None = Field(None, description='内存使用率')
    task_count: int = Field(description='当前运行任务数')
    last_heartbeat: datetime | None = Field(None, description='最后心跳时间')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class WorkerRegisterParam(SchemaBase):
    """Worker 注册参数"""

    name: str = Field(max_length=128, description='节点名称')
    host: str = Field(max_length=256, description='节点主机地址')
    port: int = Field(default=8001, description='节点 API 端口')
    version: str | None = Field(default=None, max_length=32, description='节点版本')
    max_tasks: int = Field(default=5, description='最大并行任务数')
    tags: str | None = Field(default=None, max_length=512, description='节点标签')


class WorkerHeartbeatParam(SchemaBase):
    """Worker 心跳参数"""

    status: str = Field(default='online', description='状态(online/busy)')
    cpu_usage: float | None = Field(default=None, description='CPU 使用率')
    memory_usage: float | None = Field(default=None, description='内存使用率')
    task_count: int | None = Field(default=None, description='当前运行任务数')


class WorkerDispatchParam(SchemaBase):
    """Worker 任务分发参数"""

    spider_name: str = Field(max_length=64, description='爬虫名称')
    keyword: str | None = Field(default=None, max_length=128, description='搜索关键词')
    worker_id: int | None = Field(default=None, description='指定 Worker ID(留空自动选择)')
