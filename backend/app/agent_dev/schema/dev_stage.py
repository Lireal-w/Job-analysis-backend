"""Agent 开发任务阶段 Schema"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field

from backend.app.agent_dev.enums import DevAgentType, DevStageStatus, DevStageType
from backend.common.schema import SchemaBase


class AgentDevStageSchemaBase(SchemaBase):
    """阶段基础模型"""

    stage_type: DevStageType = Field(description='阶段类型(plan/design/code/review/test/deploy)')
    agent_type: DevAgentType = Field(default=DevAgentType.CODER, description='执行Agent类型')
    sequence_order: int = Field(default=0, description='执行顺序')
    title: str = Field(max_length=256, description='阶段标题')
    description: str | None = Field(default=None, description='阶段描述')
    input_data: dict | None = Field(default=None, description='输入数据')
    max_retries: int = Field(default=3, description='最大重试次数')
    remark: str | None = Field(default=None, max_length=512, description='备注')


class CreateAgentDevStageParam(AgentDevStageSchemaBase):
    """创建阶段参数"""


class UpdateAgentDevStageParam(SchemaBase):
    """更新阶段参数"""

    title: str | None = Field(default=None, max_length=256, description='阶段标题')
    description: str | None = Field(default=None, description='阶段描述')
    status: DevStageStatus | None = Field(default=None, description='状态')
    input_data: dict | None = Field(default=None, description='输入数据')
    output_data: dict | None = Field(default=None, description='输出数据')
    agent_id: int | None = Field(default=None, description='指派 Agent ID')
    agent_name: str | None = Field(default=None, max_length=128, description='Agent 名称')
    error_message: str | None = Field(default=None, description='错误信息')
    remark: str | None = Field(default=None, max_length=512, description='备注')


class UpdateAgentDevStageStatusParam(SchemaBase):
    """更新阶段状态参数"""

    status: DevStageStatus = Field(description='状态(0等待中 1进行中 2已完成 3失败 4已跳过)')
    output_data: dict | None = Field(default=None, description='输出数据')
    error_message: str | None = Field(default=None, description='错误信息')


class GetAgentDevStageDetail(AgentDevStageSchemaBase):
    """阶段详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='阶段 ID')
    task_id: int = Field(description='所属任务 ID')
    status: DevStageStatus = Field(description='状态')
    output_data: dict | None = Field(None, description='输出数据')
    agent_id: int | None = Field(None, description='指派 Agent ID')
    agent_name: str | None = Field(None, description='Agent 名称')
    started_at: datetime | None = Field(None, description='开始时间')
    completed_at: datetime | None = Field(None, description='完成时间')
    duration_seconds: int | None = Field(None, description='耗时(秒)')
    error_message: str | None = Field(None, description='错误信息')
    retry_count: int = Field(description='重试次数')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class GetAgentDevTaskWithStagesDetail(SchemaBase):
    """开发任务详情(含阶段)"""

    model_config = ConfigDict(from_attributes=True)

    task: GetAgentDevTaskDetail
    stages: list[GetAgentDevStageDetail]
