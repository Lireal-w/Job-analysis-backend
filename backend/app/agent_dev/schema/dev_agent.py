"""Agent 开发节点 Schema"""

from datetime import datetime

from pydantic import ConfigDict, Field

from backend.app.agent_dev.enums import DevAgentStatus, DevAgentType
from backend.common.schema import SchemaBase


class AgentDevAgentSchemaBase(SchemaBase):
    """Agent 节点基础模型"""

    name: str = Field(max_length=128, description='Agent 名称')
    agent_type: DevAgentType = Field(description='Agent 类型')
    description: str | None = Field(default=None, max_length=256, description='描述')
    capabilities: list[str] | None = Field(default=None, description='能力列表')
    config: dict | None = Field(default=None, description='Agent 配置')
    max_concurrent_tasks: int = Field(default=3, description='最大并发任务数')
    version: str | None = Field(default=None, max_length=32, description='Agent 版本')


class CreateAgentDevAgentParam(AgentDevAgentSchemaBase):
    """创建 Agent 节点参数"""


class UpdateAgentDevAgentParam(SchemaBase):
    """更新 Agent 节点参数"""

    name: str | None = Field(default=None, max_length=128, description='Agent 名称')
    description: str | None = Field(default=None, max_length=256, description='描述')
    capabilities: list[str] | None = Field(default=None, description='能力列表')
    config: dict | None = Field(default=None, description='Agent 配置')
    max_concurrent_tasks: int | None = Field(default=None, description='最大并发任务数')
    status: DevAgentStatus | None = Field(default=None, description='状态')
    version: str | None = Field(default=None, max_length=32, description='Agent 版本')


class UpdateAgentDevAgentHeartbeatParam(SchemaBase):
    """Agent 心跳上报参数"""

    status: DevAgentStatus = Field(default=DevAgentStatus.IDLE, description='状态')
    current_tasks: int = Field(default=0, description='当前任务数')
    total_tasks_completed: int = Field(default=0, description='累计完成任务数')
    total_tasks_failed: int = Field(default=0, description='累计失败任务数')


class GetAgentDevAgentDetail(AgentDevAgentSchemaBase):
    """Agent 节点详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Agent ID')
    worker_node_id: int | None = Field(None, description='关联 Worker 节点 ID')
    status: DevAgentStatus = Field(description='状态')
    current_tasks: int = Field(description='当前任务数')
    total_tasks_completed: int = Field(description='累计完成任务数')
    total_tasks_failed: int = Field(description='累计失败任务数')
    last_heartbeat: datetime | None = Field(None, description='最后心跳时间')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
