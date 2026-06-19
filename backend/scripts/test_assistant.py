"""验证 AI 助手模块完整性"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ['ENVIRONMENT'] = 'dev'

from dotenv import load_dotenv
load_dotenv(Path('backend/.env'))

# Test model import
from backend.app.assistant.model import AiConfig, AiChatHistory
print('1. Models OK:', [c.__name__ for c in [AiConfig, AiChatHistory]])

# Test schema
from backend.app.assistant.schema import CreateAiConfigParam, ChatMessage, ChatResponse
print('2. Schemas OK')

# Test CRUD
from backend.app.assistant.crud import ai_config_dao, ai_chat_history_dao
print('3. CRUD OK')

# Test tools
from backend.app.assistant.tools import get_tool_definitions
from backend.app.assistant.tools.crawl_tasks import create_crawl_task, list_crawl_tasks
defs = get_tool_definitions()
names = [d['function']['name'] for d in defs]
print(f'4. Tools registered: {names}')

# Test SocketIO handler
from backend.app.assistant.socketio import ASSISTANT_NAMESPACE
print(f'5. WS Namespace: {ASSISTANT_NAMESPACE}')

# Test router
from backend.app.assistant.api import router
routes = [r.path for r in router.routes]
print(f'6. API routes: {routes}')

# Test service
from backend.app.assistant.service.chat_service import ai_chat_service
print('7. Chat Service OK')

from backend.app.assistant.service.config_service import ai_config_service
print('8. Config Service OK')

# Test main app router
from backend.app.router import router as main_router
print(f'9. Main router paths: {[r.path for r in main_router.routes if "assistant" in str(r.path) or "ai" in str(r.path).lower()]}')

print()
print('AI Assistant Module fully loaded!')
