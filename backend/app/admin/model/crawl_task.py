import sqlalchemy as sa

from datetime import datetime

from backend.common.model import MappedBase, TimeZone, UniversalText
from backend.utils.timezone import timezone


class CrawlTask(MappedBase):
    """采集任务配置表"""

    __tablename__ = 'sys_crawl_task'
    __table_args__ = {'comment': '采集任务配置表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(128), unique=True, comment='任务名称')
    description = sa.Column(sa.String(512), default=None, comment='任务描述')

    # 数据源与目标
    source_datasource_id = sa.Column(sa.BigInteger, comment='源数据源 ID')
    source_config = sa.Column(sa.JSON, default=None, comment='源采集配置(JSON:{table,query,collection,fields...})')
    target_storage = sa.Column(sa.String(32), comment='目标存储类型(datasource/local/file/mongodb)')
    target_datasource_id = sa.Column(sa.BigInteger, default=None, comment='目标数据源 ID')
    target_config = sa.Column(sa.JSON, default=None, comment='目标存储配置(JSON)')

    # 采集模式
    crawl_mode = sa.Column(sa.String(16), default='full', comment='采集模式(full/incremental)')
    incremental_key = sa.Column(sa.String(128), default=None, comment='增量字段(如:updated_time)')
    incremental_start = sa.Column(sa.String(64), default=None, comment='增量起始值')

    # 调度策略
    schedule_type = sa.Column(sa.String(16), default='none', comment='调度类型(none/cron/interval)')
    cron_expr = sa.Column(sa.String(64), default=None, comment='Cron 表达式')
    interval_seconds = sa.Column(sa.Integer, default=None, comment='间隔秒数')

    # 并发控制
    concurrency = sa.Column(sa.Integer, default=1, comment='并发数')
    batch_size = sa.Column(sa.Integer, default=100, comment='每批处理条数')
    rate_limit = sa.Column(sa.Integer, default=0, comment='速率限制(请求/秒,0不限)')

    # 失败重试
    retry_enabled = sa.Column(sa.Boolean, default=True, comment='是否启用重试')
    max_retries = sa.Column(sa.Integer, default=3, comment='最大重试次数')
    retry_delay = sa.Column(sa.Integer, default=60, comment='重试间隔(秒)')
    retry_backoff = sa.Column(sa.Boolean, default=True, comment='是否启用退避策略')

    # 状态
    status = sa.Column(sa.String(16), default='stopped', comment='状态(stopped/running/paused/error)')
    priority = sa.Column(sa.Integer, default=2, comment='优先级(0-4)')
    enabled = sa.Column(sa.Boolean, default=True, comment='是否启用')

    # 运行统计
    total_run_count = sa.Column(sa.Integer, default=0, comment='总运行次数')
    total_records = sa.Column(sa.Integer, default=0, comment='总采集记录数')
    last_run_time = sa.Column(TimeZone, default=None, comment='最后运行时间')
    last_duration = sa.Column(sa.Float, default=None, comment='最后运行耗时(秒)')
    last_status = sa.Column(sa.String(16), default=None, comment='最后运行状态(success/failed)')

    # 元数据
    tags = sa.Column(sa.String(256), default=None, comment='标签(逗号分隔)')
    created_by = sa.Column(sa.BigInteger, default=None, comment='创建者')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')


class CrawlTaskLog(MappedBase):
    """采集任务执行日志表"""

    __tablename__ = 'sys_crawl_task_log'
    __table_args__ = {'comment': '采集任务执行日志表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    task_id = sa.Column(sa.BigInteger, index=True, comment='任务 ID')
    run_id = sa.Column(sa.String(64), comment='运行批次 ID')
    status = sa.Column(sa.String(16), comment='状态(running/success/failed)')

    # 执行信息
    start_time = sa.Column(TimeZone, comment='开始时间')
    end_time = sa.Column(TimeZone, default=None, comment='结束时间')
    duration = sa.Column(sa.Float, default=None, comment='耗时(秒)')

    # 数据统计
    total_found = sa.Column(sa.Integer, default=0, comment='发现记录数')
    total_scraped = sa.Column(sa.Integer, default=0, comment='采集记录数')
    total_succeeded = sa.Column(sa.Integer, default=0, comment='成功数')
    total_failed = sa.Column(sa.Integer, default=0, comment='失败数')
    total_skipped = sa.Column(sa.Integer, default=0, comment='跳过数')

    # 性能指标
    avg_response_time = sa.Column(sa.Float, default=None, comment='平均响应时间(ms)')
    throughput = sa.Column(sa.Float, default=None, comment='吞吐量(条/秒)')
    memory_usage = sa.Column(sa.Float, default=None, comment='内存使用(MB)')
    cpu_usage = sa.Column(sa.Float, default=None, comment='CPU 使用率(%)')

    # 错误信息
    error_message = sa.Column(UniversalText, default=None, comment='错误信息')
    error_traceback = sa.Column(UniversalText, default=None, comment='错误堆栈')

    # 详情
    log_detail = sa.Column(sa.JSON, default=None, comment='日志详情(JSON)')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
