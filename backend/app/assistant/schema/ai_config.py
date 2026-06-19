"""AI 配置 Schema"""

from backend.app.assistant.schema import (
    AiConfigSchemaBase,
    ChatMessage,
    ChatResponse,
    CreateAiConfigParam,
    GetAiConfigDetail,
    SetActiveAiConfigParam,
    UpdateAiConfigParam,
)

__all__ = [
    'AiConfigSchemaBase',
    'CreateAiConfigParam',
    'UpdateAiConfigParam',
    'GetAiConfigDetail',
    'SetActiveAiConfigParam',
    'ChatMessage',
    'ChatResponse',
]
