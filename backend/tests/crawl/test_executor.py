"""采集执行引擎集成测试"""

import json
import os
import tempfile

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.admin.service.crawl.context import CrawlContext
from backend.app.admin.service.crawl.executor import CrawlExecutor
from backend.app.admin.service.crawl.exceptions import CrawlSourceError, CrawlTargetError


class TestCrawlExecutorInit:
    """CrawlExecutor 初始化测试"""

    def test_init_with_database_source(self):
        executor = CrawlExecutor(
            task_id=1,
            run_id='run123',
            source_config={'type': 'database', 'datasource_id': 1, 'query': 'SELECT 1'},
            target_storage='database',
            target_config={'datasource_id': 2, 'table': 'target'},
        )
        assert executor.task_id == 1
        assert executor.run_id == 'run123'
        assert executor.crawl_mode == 'full'
        assert executor.context.task_id == 1

    def test_init_with_file_source(self):
        executor = CrawlExecutor(
            task_id=2,
            run_id='run456',
            source_config={'type': 'file_csv', 'file_path': '/tmp/test.csv'},
            target_storage='file_json',
            target_config={'file_path': '/tmp/output.json'},
        )
        assert executor.crawl_mode == 'full'

    def test_init_incremental_mode(self):
        executor = CrawlExecutor(
            task_id=3,
            run_id='run789',
            source_config={'type': 'database', 'datasource_id': 1, 'query': 'SELECT 1'},
            target_storage='database',
            target_config={'datasource_id': 2, 'table': 'target'},
            crawl_mode='incremental',
            incremental_key='updated_at',
            incremental_start='2024-01-01',
        )
        assert executor.crawl_mode == 'incremental'
        assert executor.context.incremental_key == 'updated_at'
        assert executor.context.incremental_start == '2024-01-01'

    def test_init_with_datasource_ids(self):
        executor = CrawlExecutor(
            task_id=1,
            run_id='run001',
            source_config={'type': 'database', 'query': 'SELECT 1'},
            target_storage='database',
            target_config={'table': 'target'},
            source_datasource_id=10,
            target_datasource_id=20,
        )
        # datasource_id 应该被自动填入
        assert executor.source_reader.config.get('datasource_id') == 10
        assert executor.target_writer.config.get('datasource_id') == 20


class TestCrawlExecutorIncrementalFilter:
    """增量过滤测试"""

    def test_incremental_filter_with_string_values(self):
        executor = CrawlExecutor(
            task_id=1,
            run_id='run001',
            source_config={'type': 'file_csv', 'file_path': '/tmp/test.csv'},
            target_storage='file_json',
            target_config={'file_path': '/tmp/output.json'},
            crawl_mode='incremental',
            incremental_key='updated_at',
            incremental_start='2024-01-01',
        )

        data = [
            {'id': 1, 'name': 'A', 'updated_at': '2023-12-01'},
            {'id': 2, 'name': 'B', 'updated_at': '2024-01-01'},
            {'id': 3, 'name': 'C', 'updated_at': '2024-02-01'},
            {'id': 4, 'name': 'D', 'updated_at': '2024-03-01'},
        ]

        filtered = executor._apply_incremental_filter(data)
        # 应该过滤掉 <= 2024-01-01 的记录
        assert len(filtered) == 2
        assert filtered[0]['id'] == 3
        assert filtered[1]['id'] == 4
        assert executor.context.incremental_end == '2024-03-01'

    def test_incremental_filter_with_numeric_values(self):
        executor = CrawlExecutor(
            task_id=1,
            run_id='run002',
            source_config={'type': 'file_csv', 'file_path': '/tmp/test.csv'},
            target_storage='file_json',
            target_config={'file_path': '/tmp/output.json'},
            crawl_mode='incremental',
            incremental_key='id',
            incremental_start='100',
        )

        data = [
            {'id': 50, 'name': 'A'},
            {'id': 100, 'name': 'B'},
            {'id': 150, 'name': 'C'},
            {'id': 200, 'name': 'D'},
        ]

        filtered = executor._apply_incremental_filter(data)
        assert len(filtered) == 2
        assert filtered[0]['id'] == 150
        assert filtered[1]['id'] == 200

    def test_incremental_filter_no_key(self):
        executor = CrawlExecutor(
            task_id=1,
            run_id='run003',
            source_config={'type': 'file_csv', 'file_path': '/tmp/test.csv'},
            target_storage='file_json',
            target_config={'file_path': '/tmp/output.json'},
            crawl_mode='incremental',
            incremental_key=None,
        )

        data = [{'id': 1}, {'id': 2}]
        # 没有增量键时，应返回全部数据
        filtered = executor._apply_incremental_filter(data)
        assert len(filtered) == 2

    def test_incremental_filter_empty_data(self):
        executor = CrawlExecutor(
            task_id=1,
            run_id='run004',
            source_config={'type': 'file_csv', 'file_path': '/tmp/test.csv'},
            target_storage='file_json',
            target_config={'file_path': '/tmp/output.json'},
            crawl_mode='incremental',
            incremental_key='id',
            incremental_start='0',
        )

        filtered = executor._apply_incremental_filter([])
        assert len(filtered) == 0

    def test_incremental_filter_missing_key_in_row(self):
        executor = CrawlExecutor(
            task_id=1,
            run_id='run005',
            source_config={'type': 'file_csv', 'file_path': '/tmp/test.csv'},
            target_storage='file_json',
            target_config={'file_path': '/tmp/output.json'},
            crawl_mode='incremental',
            incremental_key='updated_at',
            incremental_start='2024-01-01',
        )

        data = [
            {'id': 1, 'name': 'A'},  # 缺少 updated_at
            {'id': 2, 'name': 'B', 'updated_at': '2024-02-01'},
        ]

        filtered = executor._apply_incremental_filter(data)
        assert len(filtered) == 1
        assert filtered[0]['id'] == 2


class TestCrawlExecutorTransform:
    """数据转换测试"""

    def test_field_mapping(self):
        executor = CrawlExecutor(
            task_id=1,
            run_id='run001',
            source_config={
                'type': 'file_csv',
                'file_path': '/tmp/test.csv',
                'transform': {
                    'field_mapping': {'old_name': 'new_name', 'old_email': 'new_email'},
                },
            },
            target_storage='file_json',
            target_config={'file_path': '/tmp/output.json'},
        )

        data = [
            {'old_name': 'Alice', 'old_email': 'alice@test.com', 'age': 25},
        ]
        result = executor._apply_transform(data)
        assert 'new_name' in result[0]
        assert 'new_email' in result[0]
        assert 'age' in result[0]  # 未映射的字段保留

    def test_select_fields(self):
        executor = CrawlExecutor(
            task_id=1,
            run_id='run002',
            source_config={
                'type': 'file_csv',
                'file_path': '/tmp/test.csv',
                'transform': {
                    'select_fields': ['id', 'name'],
                },
            },
            target_storage='file_json',
            target_config={'file_path': '/tmp/output.json'},
        )

        data = [{'id': 1, 'name': 'Alice', 'email': 'alice@test.com', 'password': 'secret'}]
        result = executor._apply_transform(data)
        assert 'id' in result[0]
        assert 'name' in result[0]
        assert 'email' not in result[0]
        assert 'password' not in result[0]

    def test_filter_fields(self):
        executor = CrawlExecutor(
            task_id=1,
            run_id='run003',
            source_config={
                'type': 'file_csv',
                'file_path': '/tmp/test.csv',
                'transform': {
                    'filter_fields': ['password', 'secret'],
                },
            },
            target_storage='file_json',
            target_config={'file_path': '/tmp/output.json'},
        )

        data = [{'id': 1, 'name': 'Alice', 'password': 'secret', 'secret': 'value'}]
        result = executor._apply_transform(data)
        assert 'id' in result[0]
        assert 'name' in result[0]
        assert 'password' not in result[0]
        assert 'secret' not in result[0]

    def test_no_transform(self):
        executor = CrawlExecutor(
            task_id=1,
            run_id='run004',
            source_config={'type': 'file_csv', 'file_path': '/tmp/test.csv'},
            target_storage='file_json',
            target_config={'file_path': '/tmp/output.json'},
        )

        data = [{'id': 1, 'name': 'Alice'}]
        result = executor._apply_transform(data)
        assert result == data

    def test_empty_data_transform(self):
        executor = CrawlExecutor(
            task_id=1,
            run_id='run005',
            source_config={
                'type': 'file_csv',
                'file_path': '/tmp/test.csv',
                'transform': {'field_mapping': {'a': 'b'}},
            },
            target_storage='file_json',
            target_config={'file_path': '/tmp/output.json'},
        )

        result = executor._apply_transform([])
        assert result == []


class TestCrawlExecutorRetryDelay:
    """重试延迟计算测试"""

    def test_fixed_delay(self):
        executor = CrawlExecutor(
            task_id=1,
            run_id='run001',
            source_config={'type': 'file_csv', 'file_path': '/tmp/test.csv'},
            target_storage='file_json',
            target_config={'file_path': '/tmp/output.json'},
            retry_backoff=False,
            retry_delay=60,
        )
        assert executor._calculate_retry_delay(1) == 60.0
        assert executor._calculate_retry_delay(2) == 60.0
        assert executor._calculate_retry_delay(3) == 60.0

    def test_exponential_backoff(self):
        executor = CrawlExecutor(
            task_id=1,
            run_id='run002',
            source_config={'type': 'file_csv', 'file_path': '/tmp/test.csv'},
            target_storage='file_json',
            target_config={'file_path': '/tmp/output.json'},
            retry_backoff=True,
            retry_delay=30,
        )
        assert executor._calculate_retry_delay(1) == 30.0   # 30 * 2^0
        assert executor._calculate_retry_delay(2) == 60.0   # 30 * 2^1
        assert executor._calculate_retry_delay(3) == 120.0  # 30 * 2^2


class TestCrawlExecutorMetrics:
    """性能指标计算测试"""

    def test_calculate_metrics(self):
        executor = CrawlExecutor(
            task_id=1,
            run_id='run001',
            source_config={'type': 'file_csv', 'file_path': '/tmp/test.csv'},
            target_storage='file_json',
            target_config={'file_path': '/tmp/output.json'},
        )
        executor.context.total_succeeded = 100
        executor.context.total_scraped = 100
        executor.context.start_time = __import__('datetime').datetime(2024, 1, 1, 10, 0, 0)
        executor.context.end_time = __import__('datetime').datetime(2024, 1, 1, 10, 1, 40)

        executor._calculate_metrics()

        assert executor.context.throughput > 0
        assert executor.context.avg_response_time > 0


class TestCrawlExecutorFullPipeline:
    """完整管道集成测试 (使用文件源和文件目标)"""

    @pytest.mark.asyncio
    async def test_csv_to_json_pipeline(self, tmp_path, sample_data):
        """测试 CSV → JSON 完整管道"""
        # 创建源 CSV 文件
        csv_path = str(tmp_path / 'source.csv')
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write('id,name,email,updated_at\n')
            for row in sample_data:
                f.write(f"{row['id']},{row['name']},{row['email']},{row['updated_at']}\n")

        # 创建执行器
        json_path = str(tmp_path / 'output.json')
        executor = CrawlExecutor(
            task_id=1,
            run_id='pipeline001',
            source_config={'type': 'file_csv', 'file_path': csv_path},
            target_storage='file_json',
            target_config={'file_path': json_path},
            batch_size=2,
        )

        # 执行
        ctx = await executor.execute()

        # 验证结果
        assert ctx.total_found == 5
        assert ctx.total_succeeded == 5
        assert ctx.total_failed == 0
        assert ctx.error_message is None

        # 验证输出文件
        with open(json_path, 'r', encoding='utf-8') as f:
            output = json.load(f)
        assert len(output) == 5

    @pytest.mark.asyncio
    async def test_json_to_csv_pipeline(self, tmp_path, sample_data):
        """测试 JSON → CSV 完整管道"""
        # 创建源 JSON 文件
        json_path = str(tmp_path / 'source.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f)

        # 创建执行器
        csv_path = str(tmp_path / 'output.csv')
        executor = CrawlExecutor(
            task_id=2,
            run_id='pipeline002',
            source_config={'type': 'file_json', 'file_path': json_path},
            target_storage='file_csv',
            target_config={'file_path': csv_path},
        )

        # 执行
        ctx = await executor.execute()

        # 验证结果
        assert ctx.total_found == 5
        assert ctx.total_succeeded == 5
        assert ctx.error_message is None

        # 验证输出文件
        assert os.path.exists(csv_path)

    @pytest.mark.asyncio
    async def test_incremental_pipeline(self, tmp_path, sample_data):
        """测试增量采集管道"""
        # 创建源 JSON 文件
        json_path = str(tmp_path / 'source.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f)

        # 创建执行器 (增量模式)
        output_path = str(tmp_path / 'output.json')
        executor = CrawlExecutor(
            task_id=3,
            run_id='pipeline003',
            source_config={'type': 'file_json', 'file_path': json_path},
            target_storage='file_json',
            target_config={'file_path': output_path},
            crawl_mode='incremental',
            incremental_key='updated_at',
            incremental_start='2024-03-01',
        )

        # 执行
        ctx = await executor.execute()

        # 验证增量过滤结果
        assert ctx.total_found == 5
        assert ctx.total_scraped == 2  # 只有 2024-04-01 和 2024-05-01
        assert ctx.total_skipped == 3  # 2024-01-01, 2024-02-01, 2024-03-01
        assert ctx.incremental_end == '2024-05-01'

    @pytest.mark.asyncio
    async def test_pipeline_with_transform(self, tmp_path, sample_data):
        """测试带数据转换的管道"""
        # 创建源 JSON 文件
        json_path = str(tmp_path / 'source.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f)

        # 创建执行器 (带字段选择)
        output_path = str(tmp_path / 'output.json')
        executor = CrawlExecutor(
            task_id=4,
            run_id='pipeline004',
            source_config={
                'type': 'file_json',
                'file_path': json_path,
                'transform': {
                    'select_fields': ['id', 'name'],
                },
            },
            target_storage='file_json',
            target_config={'file_path': output_path},
        )

        # 执行
        ctx = await executor.execute()

        # 验证结果
        assert ctx.total_succeeded == 5

        # 验证输出只包含选择的字段
        with open(output_path, 'r', encoding='utf-8') as f:
            output = json.load(f)
        for row in output:
            assert 'id' in row
            assert 'name' in row
            assert 'email' not in row

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, tmp_path):
        """测试管道错误处理"""
        executor = CrawlExecutor(
            task_id=5,
            run_id='pipeline005',
            source_config={'type': 'file_csv', 'file_path': '/nonexistent/file.csv'},
            target_storage='file_json',
            target_config={'file_path': '/tmp/output.json'},
            retry_enabled=False,
        )

        # 执行应该抛出异常
        with pytest.raises(CrawlSourceError):
            await executor.execute()

        # 验证错误信息
        assert executor.context.error_message is not None