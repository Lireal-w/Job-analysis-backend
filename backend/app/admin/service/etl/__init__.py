"""ETL 执行引擎

提供完整的 ETL 数据流执行能力，支持：
- DAG 拓扑排序与并行执行
- 多种数据源读取 (MySQL/PostgreSQL/CSV/Excel/JSON/API)
- 丰富的数据转换 (过滤/映射/聚合/排序/Join/Union 等)
- 多种目标写入 (数据库/文件)
- Celery 异步执行
"""

from backend.app.admin.service.etl.engine import ETLPipeline

__all__ = ['ETLPipeline']
