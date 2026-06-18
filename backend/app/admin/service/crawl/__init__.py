"""采集任务执行引擎

提供完整的数据采集执行能力，支持：
- 多种数据源读取 (MySQL/PostgreSQL/SQLite/MongoDB/API/CSV/Excel/JSON)
- 多种目标存储写入 (数据库/文件)
- 全量/增量采集模式
- 批量处理与并发控制
- 速率限制与重试机制
- 详细的执行统计与日志
"""

from backend.app.admin.service.crawl.executor import CrawlExecutor

__all__ = ['CrawlExecutor']