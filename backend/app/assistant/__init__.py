"""AI 助手模块

提供基于大语言模型的智能 AI 助手功能：
- WebSocket 实时对话
- 多模型支持 (OpenAI / DeepSeek / 任意 OpenAI 兼容 API)
- AI 可执行工具：创建采集任务、查询数据源、管理任务等
- 配置项通过 REST API 动态管理
"""

from backend.app.assistant.model import AiConfig as AiConfig

__all__ = ['AiConfig']
