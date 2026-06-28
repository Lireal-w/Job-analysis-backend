"""Agent 开发任务 Schema"""

from datetime import datetime

from pydantic import ConfigDict, Field

from backend.app.agent_dev.enums import DevTaskPriority, DevTaskSource, DevTaskStatus, DevTaskType
from backend.common.schema import SchemaBase


class AgentDevTaskSchemaBase(SchemaBase):
    """开发任务基础模型"""

    title: str = Field(max_length=256, description='任务标题')
    description: str | None = Field(default=None, description='详细需求描述')
    task_type: DevTaskType = Field(default=DevTaskType.FEATURE, description='任务类型(0功能 1Bug 2重构 3优化 4集成 5配置)')
    priority: DevTaskPriority = Field(default=DevTaskPriority.MEDIUM, description='优先级(0低 1中 2高 3紧急)')
    source: DevTaskSource = Field(default=DevTaskSource.MOBILE, description='来源(0移动端 1管理后台 2API 3自动)')
    project_name: str | None = Field(default=None, max_length=128, description='项目名称')
    language: str | None = Field(default=None, max_length=64, description='编程语言')
    framework: str | None = Field(default=None, max_length=128, description='框架')
    related_paths: list[str] | None = Field(default=None, description='关联文件路径')
    requirement_doc: str | None = Field(default=None, description='需求文档/PRD')
    acceptance_criteria: dict | None = Field(default=None, description='验收标准')


class CreateAgentDevTaskParam(AgentDevTaskSchemaBase):
    """移动端创建开发任务参数"""


class CreateAgentDevTaskByAdminParam(AgentDevTaskSchemaBase):
    """管理端创建开发任务参数"""


class UpdateAgentDevTaskParam(SchemaBase):
    """更新开发任务参数"""

    title: str | None = Field(default=None, max_length=256, description='任务标题')
    description: str | None = Field(default=None, description='详细需求描述')
    task_type: DevTaskType | None = Field(default=None, description='任务类型')
    priority: DevTaskPriority | None = Field(default=None, description='优先级')
    project_name: str | None = Field(default=None, max_length=128, description='项目名称')
    language: str | None = Field(default=None, max_length=64, description='编程语言')
    framework: str | None = Field(default=None, max_length=128, description='框架')
    related_paths: list[str] | None = Field(default=None, description='关联文件路径')
    requirement_doc: str | None = Field(default=None, description='需求文档')
    acceptance_criteria: dict | None = Field(default=None, description='验收标准')


class UpdateAgentDevTaskStatusParam(SchemaBase):
    """更新开发任务状态参数"""

    status: DevTaskStatus = Field(description='状态(0待处理 1规划中 2进行中 3评审中 4已完成 5失败 6已取消)')


class GetAgentDevTaskDetail(AgentDevTaskSchemaBase):
    """开发任务详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='任务 ID')
    status: DevTaskStatus = Field(description='状态')
    progress: int = Field(description='整体进度(0-100)')
    current_stage: str | None = Field(None, description='当前阶段')
    orchestration_plan: dict | None = Field(None, description='编排计划')
    result_summary: str | None = Field(None, description='执行结果摘要')
    error_message: str | None = Field(None, description='错误信息')
    output_data: dict | None = Field(None, description='产出物信息')
    started_at: datetime | None = Field(None, description='开始时间')
    completed_at: datetime | None = Field(None, description='完成时间')
    created_by: int = Field(description='创建者')
    updated_by: int | None = Field(None, description='修改者')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class StartAgentDevTaskParam(SchemaBase):
    """启动编排参数"""

    agent_id: int | None = Field(default=None, description='指定编排 Agent ID')
