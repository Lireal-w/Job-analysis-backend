"""查询引擎模块

提供真实 SQL 查询执行能力，支持多种数据源类型。

核心功能：
- 从数据源获取连接参数并执行 SQL 查询
- SQL 注入防护（只允许 SELECT 语句）
- 查询超时控制
- 大结果集分页
- 查询结果缓存（Redis）
"""

from backend.app.admin.service.query.engine import QueryEngine, execute_query_on_datasource

__all__ = ['QueryEngine', 'execute_query_on_datasource']