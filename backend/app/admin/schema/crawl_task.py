from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.enums import CrawlMode, CrawlPriority, CrawlScheduleType, CrawlStatus
from backend.common.schema import SchemaBase


class CrawlTaskSchemaBase(SchemaBase):
    """采集任务基础模型"""

    name: str = Field(max_length=128, description='任务名称')
    description: str | None = Field(default=None, max_length=512, description='任务描述')
    source_datasource_id: int | None = Field(default=None, description='源数据源 ID（API/文件类型源可为空）')
    source_config: dict = Field(default_factory=dict, description='源采集配置')
    target_storage: str = Field(max_length=32, description='目标存储类型(datasource/local/file/mongodb)')
    target_datasource_id: int | None = Field(default=None, description='目标数据源 ID')
    target_config: dict | None = Field(default=None, description='目标存储配置')
    crawl_mode: CrawlMode = Field(default=CrawlMode.FULL, description='采集模式')
    incremental_key: str | None = Field(default=None, max_length=128, description='增量字段')
    incremental_start: str | None = Field(default=None, max_length=64, description='增量起始值')
    schedule_type: CrawlScheduleType | None = Field(default=CrawlScheduleType.NONE, description='调度类型')
    cron_expr: str | None = Field(default=None, max_length=64, description='Cron 表达式')
    interval_seconds: int | None = Field(default=None, ge=10, description='间隔秒数(>=10)')
    concurrency: int | None = Field(default=1, ge=1, le=100, description='并发数')
    batch_size: int | None = Field(default=100, ge=1, le=10000, description='每批处理条数')
    rate_limit: int | None = Field(default=0, ge=0, description='速率限制(请求/秒)')
    retry_enabled: bool | None = Field(default=True, description='是否启用重试')
    max_retries: int | None = Field(default=3, ge=0, le=20, description='最大重试次数')
    retry_delay: int | None = Field(default=60, ge=1, description='重试间隔(秒)')
    retry_backoff: bool | None = Field(default=True, description='是否启用退避策略')
    priority: CrawlPriority | None = Field(default=CrawlPriority.MEDIUM, description='优先级')
    tags: str | None = Field(default=None, max_length=256, description='标签(逗号分隔)')


class CreateCrawlTaskParam(CrawlTaskSchemaBase):
    """创建采集任务参数"""


class UpdateCrawlTaskParam(SchemaBase):
    """更新采集任务参数"""
    name: str | None = Field(default=None, max_length=128, description='任务名称')
    description: str | None = Field(default=None, max_length=512, description='任务描述')
    source_datasource_id: int | None = Field(default=None, description='源数据源 ID')
    source_config: dict | None = Field(default=None, description='源采集配置')
    target_storage: str | None = Field(default=None, max_length=32, description='目标存储类型')
    target_datasource_id: int | None = Field(default=None, description='目标数据源 ID')
    target_config: dict | None = Field(default=None, description='目标存储配置')
    crawl_mode: CrawlMode | None = Field(default=None, description='采集模式')
    incremental_key: str | None = Field(default=None, max_length=128, description='增量字段')
    incremental_start: str | None = Field(default=None, max_length=64, description='增量起始值')
    schedule_type: CrawlScheduleType | None = Field(default=None, description='调度类型')
    cron_expr: str | None = Field(default=None, max_length=64, description='Cron 表达式')
    interval_seconds: int | None = Field(default=None, ge=10, description='间隔秒数(>=10)')
    concurrency: int | None = Field(default=None, ge=1, le=100, description='并发数')
    batch_size: int | None = Field(default=None, ge=1, le=10000, description='每批处理条数')
    rate_limit: int | None = Field(default=None, ge=0, description='速率限制(请求/秒)')
    retry_enabled: bool | None = Field(default=None, description='是否启用重试')
    max_retries: int | None = Field(default=None, ge=0, le=20, description='最大重试次数')
    retry_delay: int | None = Field(default=None, ge=1, description='重试间隔(秒)')
    retry_backoff: bool | None = Field(default=None, description='是否启用退避策略')
    priority: CrawlPriority | None = Field(default=None, description='优先级')
    tags: str | None = Field(default=None, max_length=256, description='标签(逗号分隔)')


class GetCrawlTaskDetail(CrawlTaskSchemaBase):
    """采集任务详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='任务 ID')
    status: CrawlStatus = Field(description='任务状态')
    enabled: bool = Field(description='是否启用')
    total_run_count: int | None = Field(default=0, description='总运行次数')
    total_records: int | None = Field(default=0, description='总采集记录数')
    last_run_time: datetime | None = Field(None, description='最后运行时间')
    last_duration: float | None = Field(None, description='最后运行耗时(秒)')
    last_status: str | None = Field(None, description='最后运行状态')
    created_by: int | None = Field(None, description='创建者')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class UpdateCrawlTaskStatusParam(SchemaBase):
    """更新采集任务状态参数"""

    status: CrawlStatus = Field(description='任务状态(stopped/running/paused)')


class GetCrawlTaskLogDetail(SchemaBase):
    """采集任务日志详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='日志 ID')
    task_id: int = Field(description='任务 ID')
    run_id: str = Field(description='运行批次 ID')
    status: str = Field(description='状态(running/success/failed)')
    start_time: datetime = Field(description='开始时间')
    end_time: datetime | None = Field(None, description='结束时间')
    duration: float | None = Field(None, description='耗时(秒)')
    total_found: int = Field(description='发现记录数')
    total_scraped: int = Field(description='采集记录数')
    total_succeeded: int = Field(description='成功数')
    total_failed: int = Field(description='失败数')
    total_skipped: int = Field(description='跳过数')
    avg_response_time: float | None = Field(None, description='平均响应时间(ms)')
    throughput: float | None = Field(None, description='吞吐量(条/秒)')
    memory_usage: float | None = Field(None, description='内存使用(MB)')
    cpu_usage: float | None = Field(None, description='CPU 使用率(%)')
    error_message: str | None = Field(None, description='错误信息')
    created_time: datetime = Field(description='创建时间')
