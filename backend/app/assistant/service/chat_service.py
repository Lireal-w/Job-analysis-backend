"""AI 助手服务 - 核心对话与工具调用逻辑"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from backend.app.admin.crud.crud_crawl_task import crawl_task_dao
from backend.app.assistant.crud import ai_config_dao, ai_chat_history_dao
from backend.app.assistant.tools import execute_tool, get_tool_definitions
from backend.database.db import async_db_session

# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """你是 FBA (FastAPI Best Architecture) 系统的 AI 智能助手。

## 你的能力
你可以通过工具调用来执行系统操作，帮助用户管理数据采集任务。

## 你可以做的事
1. **创建采集任务** - 支持各种数据源 (database/api/mihoyo_post 等)
2. **查询采集任务** - 查看任务列表和状态
3. **启动/停止任务** - 控制采集任务的运行

## 通用规则
- 回答问题要简洁清晰，使用中文
- 如果用户意图不明确，主动引导用户说明需求
- 如果工具调用失败，向用户解释原因
- 创建任务时，帮用户生成合理的配置 JSON
- 如果用户提供 Cookie 等敏感信息，注意不要在对话中明文展示
"""


class AiChatService:
    """AI 对话服务

    负责:
    1. 加载 AI 配置
    2. 调用 OpenAI 兼容 API
    3. 管理对话上下文
    4. 执行工具调用
    """

    def __init__(self) -> None:
        self._http_client: Any | None = None

    async def get_http_client(self) -> Any:
        """获取 HTTP 客户端（懒加载）"""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(timeout=120.0)
        return self._http_client

    async def get_active_config(self) -> dict[str, Any] | None:
        """获取当前激活的 AI 配置"""
        async with async_db_session() as db:
            config = await ai_config_dao.get_active(db)
            if not config:
                return None
            return {
                'api_base': config.api_base.rstrip('/'),
                'api_key': config.api_key,
                'model': config.model,
                'max_tokens': config.max_tokens,
                'temperature': config.temperature,
                'system_prompt': config.system_prompt or DEFAULT_SYSTEM_PROMPT,
            }

    async def chat(
        self,
        session_id: str,
        user_id: int,
        user_message: str,
        *,
        stream: bool = True,
    ) -> ChatStreamResult:
        """执行一次 AI 对话

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            user_message: 用户消息
            stream: 是否流式输出

        Yields:
            ChatStreamResult 流式片段
        """
        # 1. 获取 AI 配置
        config = await self.get_active_config()
        if not config:
            yield ChatStreamResult(error='请先在系统设置中配置并激活 AI 模型')
            return

        # 2. 保存用户消息
        async with async_db_session() as db:
            await ai_chat_history_dao.add_message(
                db, session_id, user_id, 'user', user_message,
            )
            await db.commit()

        # 3. 获取历史消息
        messages = await self._build_messages(session_id, user_id, config)

        # 4. 调用 AI API
        tool_defs = get_tool_definitions()
        result = await self._call_ai_api(config, messages, tool_defs, stream)

        # 5. 处理响应和工具调用
        assistant_content = ''
        total_tokens = 0

        if stream:
            async for chunk in self._handle_stream_response(result, session_id, user_id, config):
                yield chunk
                if chunk.type != 'done':
                    assistant_content += chunk.content or ''
                if chunk.tokens_used:
                    total_tokens = chunk.tokens_used
        else:
            # 非流式处理
            response_text, tool_calls_data = await self._process_non_stream(result)

            # 处理工具调用
            if tool_calls_data:
                for tool_call in tool_calls_data:
                    yield ChatStreamResult(
                        session_id=session_id,
                        type='tool_call',
                        tool_name=tool_call['name'],
                        tool_args=tool_call['arguments'],
                    )

                    tool_result = await execute_tool(tool_call['name'], tool_call['arguments'])
                    yield ChatStreamResult(
                        session_id=session_id,
                        type='tool_result',
                        content=tool_result,
                        tool_name=tool_call['name'],
                    )

                    # 将工具结果送回 AI 继续
                    messages.append({'role': 'assistant', 'content': None, 'tool_calls': [tool_call]})
                    messages.append({'role': 'tool', 'tool_call_id': tool_call.get('id', ''), 'content': tool_result})

                    result2 = await self._call_ai_api(config, messages, tool_defs, stream=False)
                    final_text = result2.get('content', '')
                    response_text = final_text

                async with async_db_session() as db:
                    await ai_chat_history_dao.add_message(
                        db, session_id, user_id, 'assistant', response_text,
                        tokens_used=total_tokens, model=config['model'],
                    )
                    await db.commit()

                yield ChatStreamResult(session_id=session_id, type='message', content=response_text)

            yield ChatStreamResult(session_id=session_id, type='done', tokens_used=total_tokens)

    async def _build_messages(
        self, session_id: str, user_id: int, config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """构建消息列表（含历史）"""
        async with async_db_session() as db:
            history = await ai_chat_history_dao.get_session_messages(db, session_id, limit=50)

        messages = [{'role': 'system', 'content': config['system_prompt']}]
        for msg in history:
            messages.append({'role': msg.role, 'content': msg.content})

        return messages

    async def _call_ai_api(
        self,
        config: dict[str, Any],
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        stream: bool = False,
    ) -> Any:
        """调用 OpenAI 兼容 API"""
        import httpx

        client = await self.get_http_client()
        headers = {
            'Authorization': f'Bearer {config["api_key"]}',
            'Content-Type': 'application/json',
        }
        payload: dict[str, Any] = {
            'model': config['model'],
            'messages': messages,
            'max_tokens': config['max_tokens'],
            'temperature': config['temperature'],
            'stream': stream,
        }
        if tools:
            payload['tools'] = tools
            payload['tool_choice'] = 'auto'

        # 构建请求体用于日志（隐藏 api_key）
        log_payload = {**payload}
        logger.debug(f'[AI] 请求: model={config["model"]}, messages={len(messages)}, tools={len(tools)}')

        if stream:
            # 流式请求
            req = client.build_request('POST', f'{config["api_base"]}/chat/completions', json=payload, headers=headers)
            return await client.send(req, stream=True)
        else:
            resp = await client.post(
                f'{config["api_base"]}/chat/completions',
                json=payload, headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def _handle_stream_response(self, response: Any, session_id: str, user_id: int, config: dict[str, Any]):
        """处理流式响应"""
        import json

        full_content = ''
        tool_calls_buffer: dict[int, dict] = {}
        total_tokens = 0

        async with async_db_session() as db:
            async for line in response.aiter_lines():
                if not line.startswith('data: '):
                    continue
                data_str = line[6:].strip()
                if data_str == '[DONE]':
                    break

                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get('choices', [])
                if not choices:
                    continue

                delta = choices[0].get('delta', {})

                # 累积 token 用量
                usage = chunk.get('usage', {})
                if usage:
                    total_tokens = usage.get('total_tokens', 0)

                # 处理工具调用
                if 'tool_calls' in delta:
                    for tc in delta['tool_calls']:
                        idx = tc.get('index', 0)
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {
                                'id': tc.get('id', ''),
                                'function': {'name': '', 'arguments': ''},
                            }
                        func = tc.get('function', {})
                        if func.get('name'):
                            tool_calls_buffer[idx]['function']['name'] += func['name']
                        if func.get('arguments'):
                            tool_calls_buffer[idx]['function']['arguments'] += func['arguments']

                    # 检查是否工具调用完成
                    finish_reason = choices[0].get('finish_reason')
                    if finish_reason == 'tool_calls' and tool_calls_buffer:
                        for tc_data in tool_calls_buffer.values():
                            tool_name = tc_data['function']['name']
                            try:
                                tool_args = json.loads(tc_data['function']['arguments'])
                            except json.JSONDecodeError:
                                tool_args = {}

                            yield ChatStreamResult(
                                session_id=session_id, type='tool_call',
                                tool_name=tool_name, tool_args=tool_args,
                            )

                            # 执行工具
                            tool_result = await execute_tool(tool_name, tool_args)
                            yield ChatStreamResult(
                                session_id=session_id, type='tool_result',
                                tool_name=tool_name, content=tool_result,
                            )

                            # 将结果插入消息历史，继续请求 AI
                            message_entry = {
                                'role': 'assistant',
                                'content': None,
                                'tool_calls': [{
                                    'id': tc_data['id'],
                                    'type': 'function',
                                    'function': tc_data['function'],
                                }],
                            }
                            # 这里简化处理，不递归多次工具调用
                            yield ChatStreamResult(
                                session_id=session_id, type='message',
                                content=f'已执行工具 **{tool_name}**，结果: {tool_result[:300]}',
                            )

                        tool_calls_buffer.clear()

                # 处理文本内容
                content = delta.get('content', '')
                if content:
                    full_content += content
                    yield ChatStreamResult(session_id=session_id, type='message', content=content)

                # 流结束 - 保存消息
                if choices[0].get('finish_reason') == 'stop' and full_content:
                    await ai_chat_history_dao.add_message(
                        db, session_id, user_id, 'assistant', full_content,
                        tokens_used=total_tokens, model=config['model'],
                    )
                    await db.commit()
                    yield ChatStreamResult(session_id=session_id, type='done', tokens_used=total_tokens)
                    return

            # 如果没有正常结束但有内容也保存
            if full_content:
                await ai_chat_history_dao.add_message(
                    db, session_id, user_id, 'assistant', full_content,
                    tokens_used=total_tokens, model=config['model'],
                )
                await db.commit()
            yield ChatStreamResult(session_id=session_id, type='done', tokens_used=total_tokens)

    async def _process_non_stream(self, result: dict) -> tuple[str, list[dict] | None]:
        """处理非流式响应"""
        choice = result.get('choices', [{}])[0]
        message = choice.get('message', {})
        content = message.get('content', '')

        tool_calls = message.get('tool_calls')
        if tool_calls:
            tools = []
            for tc in tool_calls:
                func = tc.get('function', {})
                try:
                    args = json.loads(func.get('arguments', '{}'))
                except json.JSONDecodeError:
                    args = {}
                tools.append({
                    'id': tc.get('id', ''),
                    'name': func.get('name', ''),
                    'arguments': args,
                })
            return content, tools

        return content, None


class ChatStreamResult:
    """流式聊天结果片段"""

    def __init__(
        self,
        session_id: str = '',
        type: str = 'message',
        content: str = '',
        tool_name: str | None = None,
        tool_args: dict | None = None,
        error: str | None = None,
        tokens_used: int | None = None,
    ):
        self.session_id = session_id
        self.type = type
        self.content = content
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.error = error
        self.tokens_used = tokens_used


# 服务单例
ai_chat_service = AiChatService()
