"""AI 助手 Schema 定义"""

from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


# ── AI 配置 ──────────────────────────────────────────

class AiConfigSchemaBase(SchemaBase):
    """AI 配置基础模型"""

    name: str = Field(max_length=64, description='配置名称')
    provider: str = Field(default='openai', max_length=32, description='提供商')
    api_base: str = Field(default='https://api.openai.com/v1', max_length=512, description='API 地址')
    api_key: str = Field(max_length=512, description='API Key')
    model: str = Field(default='gpt-4o-mini', max_length=128, description='模型名称')
    max_tokens: int = Field(default=4096, ge=1, le=128000, description='最大输出 Token')
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description='温度参数')
    system_prompt: str | None = Field(default=None, description='自定义系统提示词')
    enabled: bool = Field(default=True, description='是否启用')
    remark: str | None = Field(default=None, max_length=256, description='备注')


class CreateAiConfigParam(AiConfigSchemaBase):
    """创建 AI 配置参数"""


class UpdateAiConfigParam(SchemaBase):
    """更新 AI 配置参数"""

    name: str | None = Field(default=None, max_length=64, description='配置名称')
    provider: str | None = Field(default=None, max_length=32, description='提供商')
    api_base: str | None = Field(default=None, max_length=512, description='API 地址')
    api_key: str | None = Field(default=None, max_length=512, description='API Key')
    model: str | None = Field(default=None, max_length=128, description='模型名称')
    max_tokens: int | None = Field(default=None, ge=1, le=128000, description='最大输出 Token')
    temperature: float | None = Field(default=None, ge=0.0, le=2.0, description='温度参数')
    system_prompt: str | None = Field(default=None, description='自定义系统提示词')
    enabled: bool | None = Field(default=None, description='是否启用')
    remark: str | None = Field(default=None, max_length=256, description='备注')


class GetAiConfigDetail(AiConfigSchemaBase):
    """AI 配置详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='配置 ID')
    api_key: str = Field(description='API Key (密文)')
    is_active: bool = Field(description='是否当前激活')
    status: int = Field(description='状态')
    created_by: int | None = Field(None, description='创建者')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class SetActiveAiConfigParam(SchemaBase):
    """设置激活配置参数"""

    id: int = Field(description='配置 ID')


# ── 对话 ─────────────────────────────────────────────

class ChatMessage(SchemaBase):
    """WebSocket 聊天消息"""

    session_id: str = Field(description='会话 ID')
    content: str = Field(description='消息内容')
    stream: bool = Field(default=True, description='是否流式输出')


class ChatResponse(SchemaBase):
    """WebSocket 聊天响应"""

    session_id: str = Field(description='会话 ID')
    type: str = Field(description='消息类型: message/error/tool_call/done')
    content: str = Field(default='', description='消息内容')
    tool_name: str | None = Field(default=None, description='工具名称')
    tool_args: dict | None = Field(default=None, description='工具参数')
    tool_result: str | None = Field(default=None, description='工具执行结果')
    tokens_used: int | None = Field(default=None, description='消耗 Token 数')
