"""AI 助手数据模型"""

import sqlalchemy as sa

from backend.common.model import MappedBase, TimeZone
from backend.utils.timezone import timezone


class AiConfig(MappedBase):
    """AI 助手配置表

    存储 AI 提供商的连接信息和模型参数。
    支持多个配置，用户可切换使用。
    """

    __tablename__ = 'sys_ai_config'
    __table_args__ = {'comment': 'AI 助手配置表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(64), unique=True, comment='配置名称 (如 "默认 OpenAI", "DeepSeek")')
    provider = sa.Column(sa.String(32), default='openai', comment='提供商 (openai/azure/deepseek/custom)')
    api_base = sa.Column(sa.String(512), default='https://api.openai.com/v1', comment='API 地址')
    api_key = sa.Column(sa.String(512), comment='API Key (加密存储)')
    model = sa.Column(sa.String(128), default='gpt-4o-mini', comment='模型名称')
    max_tokens = sa.Column(sa.Integer, default=4096, comment='最大输出 Token 数')
    temperature = sa.Column(sa.Float, default=0.7, comment='温度参数 (0.0-2.0)')
    system_prompt = sa.Column(sa.Text, default=None, comment='自定义系统提示词 (覆盖默认)')
    is_active = sa.Column(sa.Boolean, default=False, comment='是否为当前激活的配置')
    enabled = sa.Column(sa.Boolean, default=True, comment='是否启用')
    status = sa.Column(sa.Integer, default=1, comment='状态(0停用 1正常)')
    remark = sa.Column(sa.String(256), default=None, comment='备注')
    created_by = sa.Column(sa.BigInteger, default=None, comment='创建者')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')


class AiChatHistory(MappedBase):
    """AI 对话历史记录表"""

    __tablename__ = 'sys_ai_chat_history'
    __table_args__ = {'comment': 'AI 对话历史记录表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    session_id = sa.Column(sa.String(64), index=True, comment='会话 ID (UUID)')
    user_id = sa.Column(sa.BigInteger, comment='用户 ID')
    role = sa.Column(sa.String(16), comment='角色 (user/assistant/system)')
    content = sa.Column(sa.Text, comment='消息内容')
    tool_calls = sa.Column(sa.JSON, default=None, comment='工具调用记录')
    tokens_used = sa.Column(sa.Integer, default=0, comment='消耗 Token 数')
    model = sa.Column(sa.String(128), default=None, comment='使用的模型')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
