"""AI 助手工具系统

AI 可通过工具调用执行系统操作，如创建采集任务、查询数据等。
每个工具是一个函数，使用 `@ai_tool` 注册。

添加新工具的步骤:
    1. 在此目录下创建新的工具模块
    2. 定义函数并使用 @ai_tool 装饰器注册
    3. 函数需返回描述性字符串
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger


# ── 工具注册表 ──────────────────────────────────────

_TOOL_REGISTRY: dict[str, dict[str, Any]] = {}


def ai_tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
    required: list[str] | None = None,
) -> Any:
    """注册 AI 可调用工具的装饰器

    Args:
        name: 工具名称 (AI 会以此名调用)
        description: 工具功能描述 (AI 理解用)
        parameters: JSON Schema 格式的参数定义
        required: 必需参数列表
    """
    def decorator(func: Any) -> Any:
        _TOOL_REGISTRY[name] = {
            'function': func,
            'definition': {
                'type': 'function',
                'function': {
                    'name': name,
                    'description': description,
                    'parameters': {
                        'type': 'object',
                        'properties': parameters,
                    },
                },
            },
        }
        if required:
            _TOOL_REGISTRY[name]['definition']['function']['parameters']['required'] = required
        logger.debug(f'[AITool] 注册工具: {name} - {description}')
        return func
    return decorator


def get_tool_definitions() -> list[dict[str, Any]]:
    """获取所有工具的 OpenAI Tool 格式定义"""
    return [reg['definition'] for reg in _TOOL_REGISTRY.values()]


async def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """执行 AI 工具调用

    Args:
        name: 工具名称
        arguments: 工具参数

    Returns:
        工具执行结果文本
    """
    registry = _TOOL_REGISTRY.get(name)
    if not registry:
        return f'错误: 未找到工具 "{name}"'

    try:
        logger.info(f'[AITool] 执行工具: {name}, 参数: {json.dumps(arguments, ensure_ascii=False)}')
        result = await registry['function'](**arguments)
        result_str = str(result) if result is not None else '执行成功（无返回）'
        logger.info(f'[AITool] 工具完成: {name} → {result_str[:200]}')
        return result_str
    except Exception as e:
        logger.error(f'[AITool] 工具执行失败: {name} - {e}')
        return f'执行失败: {type(e).__name__}: {e}'
