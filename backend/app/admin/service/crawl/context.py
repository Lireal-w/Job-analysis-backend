"""采集执行上下文

在采集执行过程中传递数据与状态。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CrawlContext:
    """采集执行上下文"""

    task_id: int = 0
    """采集任务 ID"""

    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    """运行批次 ID"""

    start_time: datetime = field(default_factory=datetime.now)
    """开始时间"""

    end_time: datetime | None = None
    """结束时间"""

    crawl_mode: str = 'full'
    """采集模式 (full/incremental)"""

    # ── 数据统计 ──────────────────────────────────────────
    total_found: int = 0
    """发现记录数"""

    total_scraped: int = 0
    """采集记录数"""

    total_succeeded: int = 0
    """成功数"""

    total_failed: int = 0
    """失败数"""

    total_skipped: int = 0
    """跳过数"""

    # ── 性能指标 ──────────────────────────────────────────
    avg_response_time: float = 0.0
    """平均响应时间(ms)"""

    throughput: float = 0.0
    """吞吐量(条/秒)"""

    memory_usage: float = 0.0
    """内存使用(MB)"""

    cpu_usage: float = 0.0
    """CPU 使用率(%)"""

    # ── 增量状态 ──────────────────────────────────────────
    incremental_key: str | None = None
    """增量字段名"""

    incremental_start: str | None = None
    """增量起始值"""

    incremental_end: str | None = None
    """增量结束值 (本次采集到的最大值)"""

    # ── 错误信息 ──────────────────────────────────────────
    error_message: str | None = None
    """错误信息"""

    error_traceback: str | None = None
    """错误堆栈"""

    # ── 扩展信息 ──────────────────────────────────────────
    extra: dict[str, Any] = field(default_factory=dict)
    """扩展信息"""

    metrics: dict[str, Any] = field(default_factory=dict)
    """运行指标"""

    @property
    def duration(self) -> float:
        """运行耗时(秒)"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def to_log_dict(self) -> dict[str, Any]:
        """转换为日志记录字典"""
        return {
            'task_id': self.task_id,
            'run_id': self.run_id,
            'status': 'success' if not self.error_message else 'failed',
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'total_found': self.total_found,
            'total_scraped': self.total_scraped,
            'total_succeeded': self.total_succeeded,
            'total_failed': self.total_failed,
            'total_skipped': self.total_skipped,
            'avg_response_time': self.avg_response_time,
            'throughput': self.throughput,
            'memory_usage': self.memory_usage,
            'cpu_usage': self.cpu_usage,
            'error_message': self.error_message,
            'error_traceback': self.error_traceback,
            'log_detail': {
                'crawl_mode': self.crawl_mode,
                'incremental_key': self.incremental_key,
                'incremental_start': self.incremental_start,
                'incremental_end': self.incremental_end,
                **self.metrics,
            },
        }