from fastapi import APIRouter

from backend.app.admin.api.v1.sys.crawl_task import router as crawl_task_router
from backend.app.admin.api.v1.sys.data_flow import router as data_flow_router
from backend.app.admin.api.v1.sys.data_quality import router as data_quality_router
from backend.app.admin.api.v1.sys.data_rule import router as data_rule_router
from backend.app.admin.api.v1.sys.data_scope import router as data_scope_router
from backend.app.admin.api.v1.sys.data_storage import router as data_storage_router
from backend.app.admin.api.v1.sys.datasource import router as datasource_router
from backend.app.admin.api.v1.sys.dept import router as dept_router
from backend.app.admin.api.v1.sys.file import router as file_router
from backend.app.admin.api.v1.sys.menu import router as menu_router
from backend.app.admin.api.v1.sys.plugin import router as plugin_router
from backend.app.admin.api.v1.sys.role import router as role_router
from backend.app.admin.api.v1.sys.server import router as server_router
from backend.app.admin.api.v1.sys.user import router as user_router
from backend.app.admin.api.v1.sys.worker import router as worker_router

router = APIRouter(prefix='/sys')

router.include_router(crawl_task_router, prefix='/crawl-tasks', tags=['系统采集任务管理'])
router.include_router(dept_router, prefix='/depts', tags=['系统部门'])
router.include_router(menu_router, prefix='/menus', tags=['系统菜单'])
router.include_router(role_router, prefix='/roles', tags=['系统角色'])
router.include_router(user_router, prefix='/users', tags=['系统用户'])
router.include_router(data_quality_router, prefix='/data-quality', tags=['系统数据质量管理'])
router.include_router(data_rule_router, prefix='/data-rules', tags=['系统数据规则'])
router.include_router(data_scope_router, prefix='/data-scopes', tags=['系统数据范围'])
router.include_router(file_router, prefix='/files', tags=['系统文件'])
router.include_router(data_flow_router, prefix='/data-flows', tags=['系统数据流管理'])
router.include_router(data_storage_router, prefix='/data-storage', tags=['系统数据存储管理'])
router.include_router(datasource_router, prefix='/datasources', tags=['系统数据源管理'])
router.include_router(server_router, prefix='/servers', tags=['系统服务器管理'])
router.include_router(worker_router, prefix='/workers', tags=['系统 Worker 管理'])
router.include_router(plugin_router, prefix='/plugins', tags=['系统插件'])
