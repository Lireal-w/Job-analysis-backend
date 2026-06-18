"""采集执行上下文测试"""

import pytest
from datetime import datetime

from backend.app.admin.service.crawl.context import CrawlContext


class TestCrawlContext:
    """CrawlContext 测试"""

    def test_default_values(self):
        ctx = CrawlContext()
        assert ctx.task_id == 0
        assert ctx.run_id is not None
        assert ctx.crawl_mode == 'full'
        assert ctx.total_found == 0
        assert ctx.total_scraped == 0
        assert ctx.total_succeeded == 0
        assert ctx.total_failed == 0
        assert ctx.total_skipped == 0
        assert ctx.error_message is None
        assert ctx.error_traceback is None

    def test_custom_values(self):
        ctx = CrawlContext(
            task_id=42,
            run_id='abc123',
            crawl_mode='incremental',
            incremental_key='updated_at',
            incremental_start='2024-01-01',
        )
        assert ctx.task_id == 42
        assert ctx.run_id == 'abc123'
        assert ctx.crawl_mode == 'incremental'
        assert ctx.incremental_key == 'updated_at'
        assert ctx.incremental_start == '2024-01-01'

    def test_duration(self):
        ctx = CrawlContext()
        # 未设置结束时间
        assert ctx.duration == 0.0

        # 设置结束时间
        ctx.start_time = datetime(2024, 1, 1, 10, 0, 0)
        ctx.end_time = datetime(2024, 1, 1, 10, 0, 30)
        assert ctx.duration == 30.0

    def test_to_log_dict_success(self):
        ctx = CrawlContext(
            task_id=1,
            run_id='run123',
            total_found=100,
            total_scraped=95,
            total_succeeded=95,
            total_failed=0,
            total_skipped=5,
        )
        ctx.start_time = datetime(2024, 1, 1, 10, 0, 0)
        ctx.end_time = datetime(2024, 1, 1, 10, 1, 0)

        log_dict = ctx.to_log_dict()
        assert log_dict['task_id'] == 1
        assert log_dict['run_id'] == 'run123'
        assert log_dict['status'] == 'success'
        assert log_dict['total_found'] == 100
        assert log_dict['total_scraped'] == 95
        assert log_dict['duration'] == 60.0

    def test_to_log_dict_failed(self):
        ctx = CrawlContext(
            task_id=1,
            run_id='run456',
            error_message='ConnectionError: timeout',
        )
        log_dict = ctx.to_log_dict()
        assert log_dict['status'] == 'failed'
        assert log_dict['error_message'] == 'ConnectionError: timeout'

    def test_metrics_and_extra(self):
        ctx = CrawlContext()
        ctx.metrics['source_type'] = 'database'
        ctx.metrics['rows_read'] = 100
        ctx.extra['custom_field'] = 'custom_value'

        assert ctx.metrics['source_type'] == 'database'
        assert ctx.extra['custom_field'] == 'custom_value'

    def test_incremental_state(self):
        ctx = CrawlContext(
            incremental_key='id',
            incremental_start='100',
        )
        ctx.incremental_end = '200'

        log_dict = ctx.to_log_dict()
        assert log_dict['log_detail']['incremental_key'] == 'id'
        assert log_dict['log_detail']['incremental_start'] == '100'
        assert log_dict['log_detail']['incremental_end'] == '200'