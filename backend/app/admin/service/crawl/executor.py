"""采集任务执行引擎

负责：
1. 从源数据源读取数据
2. 应用增量过滤（增量模式）
3. 数据转换/映射（可选）
4. 写入目标存储
5. 批量处理与并发控制
6. 速率限制
7. 重试机制
8. 收集执行统计
"""

from __future__ import annotations

import asyncio
import traceback
from typing import Any

from loguru import logger

from backend.app.admin.service.crawl.context import CrawlContext
from backend.app.admin.service.crawl.exceptions import CrawlError
from backend.app.admin.service.crawl.progress import CrawlProgressTracker
from backend.app.admin.service.crawl.readers import BaseSourceReader, get_source_reader
from backend.app.admin.service.crawl.writers import BaseTargetWriter, get_target_writer
from backend.utils.timezone import timezone


class CrawlExecutor:
    """采集任务执行引擎"""

    def __init__(
        self,
        task_id: int,
        run_id: str,
        source_config: dict[str, Any],
        target_storage: str,
        target_config: dict[str, Any],
        crawl_mode: str = 'full',
        incremental_key: str | None = None,
        incremental_start: str | None = None,
        concurrency: int = 1,
        batch_size: int = 100,
        rate_limit: int = 0,
        retry_enabled: bool = True,
        max_retries: int = 3,
        retry_delay: int = 60,
        retry_backoff: bool = True,
        source_datasource_id: int | None = None,
        target_datasource_id: int | None = None,
    ) -> None:
        self.task_id = task_id
        self.run_id = run_id
        self.crawl_mode = crawl_mode
        self.concurrency = concurrency
        self.batch_size = batch_size
        self.rate_limit = rate_limit
        self.retry_enabled = retry_enabled
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_backoff = retry_backoff

        # 构建上下文
        self.context = CrawlContext(
            task_id=task_id,
            run_id=run_id,
            crawl_mode=crawl_mode,
            incremental_key=incremental_key,
            incremental_start=incremental_start,
        )

        # 确定源类型
        source_type = source_config.get('type', 'database')
        if source_datasource_id and source_type == 'database':
            source_config.setdefault('datasource_id', source_datasource_id)

        # 确定目标类型
        target_type = target_storage
        if target_datasource_id and target_type in ('database', 'mongodb'):
            target_config.setdefault('datasource_id', target_datasource_id)

        # 创建读取器和写入器
        self.source_reader: BaseSourceReader = get_source_reader(source_type, source_config)
        self.target_writer: BaseTargetWriter = get_target_writer(target_type, target_config)

        # 进度追踪器
        self.progress = CrawlProgressTracker(task_id=task_id, run_id=run_id)

    async def execute(self) -> CrawlContext:
        """执行采集任务

        Returns:
            采集执行上下文 (包含统计信息)
        """
        self.context.start_time = timezone.now()
        logger.info(
            f'[Crawl] 开始执行采集任务 task_id={self.task_id}, '
            f'run_id={self.run_id}, mode={self.crawl_mode}'
        )

        try:
            # 1. 从源读取数据
            await self.progress.update_progress('reading', 0, 0, {'message': '正在读取数据源'})
            data = await self._read_with_retry()

            self.context.total_found = len(data)
            logger.info(f'[Crawl] 从源读取到 {len(data)} 条记录')

            # 检查取消信号
            if await self.progress.is_cancelled():
                logger.info(f'[Crawl] 任务被取消 task_id={self.task_id}')
                self.context.error_message = '任务被用户取消'
                await self.progress.clear_cancel_signal()
                return self.context

            # 2. 增量过滤
            if self.crawl_mode == 'incremental' and self.context.incremental_key:
                await self.progress.update_progress('filtering', 0, len(data), {'message': '增量过滤中'})
                data = self._apply_incremental_filter(data)
                logger.info(f'[Crawl] 增量过滤后剩余 {len(data)} 条记录')

            # 3. 数据转换（可选，通过 source_config.transform 配置）
            await self.progress.update_progress('transforming', 0, len(data), {'message': '数据转换中'})
            data = self._apply_transform(data)

            # 检查取消信号
            if await self.progress.is_cancelled():
                logger.info(f'[Crawl] 任务被取消 task_id={self.task_id}')
                self.context.error_message = '任务被用户取消'
                await self.progress.clear_cancel_signal()
                return self.context

            # 4. 批量写入目标
            await self.progress.update_progress('writing', 0, len(data), {'message': '写入目标存储'})
            written = await self._write_with_retry(data)

            # 5. 更新统计
            self.context.total_scraped = len(data)
            self.context.total_succeeded = written
            self.context.total_failed = len(data) - written
            self.context.total_skipped = self.context.total_found - len(data)

            # 6. 计算性能指标
            self._calculate_metrics()

            logger.info(
                f'[Crawl] 采集任务完成 task_id={self.task_id}, '
                f'found={self.context.total_found}, scraped={self.context.total_scraped}, '
                f'succeeded={self.context.total_succeeded}, failed={self.context.total_failed}'
            )

        except Exception as e:
            logger.error(f'[Crawl] 采集任务执行失败 task_id={self.task_id}: {e}')
            logger.error(traceback.format_exc())
            self.context.error_message = f'{type(e).__name__}: {e}'
            self.context.error_traceback = traceback.format_exc()
            self.context.total_failed = self.context.total_scraped
            raise

        finally:
            self.context.end_time = timezone.now()

        return self.context

    async def _read_with_retry(self) -> list[dict[str, Any]]:
        """带重试的数据读取"""
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                data = await self.source_reader.read(self.context)
                return data
            except Exception as e:
                last_error = e
                if not self.retry_enabled or attempt >= self.max_retries:
                    raise

                delay = self._calculate_retry_delay(attempt)
                logger.warning(
                    f'[Crawl] 数据读取失败 (尝试 {attempt}/{self.max_retries}), '
                    f'{delay}秒后重试: {e}'
                )
                await asyncio.sleep(delay)

        # 理论上不会到达这里，但类型检查需要
        raise last_error  # type: ignore[misc]

    async def _write_with_retry(self, data: list[dict[str, Any]]) -> int:
        """带重试的批量数据写入"""
        if not data:
            return 0

        # 文件类目标一次性写入所有数据（避免分批覆盖）
        file_target_types = {'file_csv', 'file_json', 'file_excel'}
        if self.target_writer.target_type in file_target_types:
            return await self._write_single_with_retry(data)

        total_written = 0
        last_error: Exception | None = None

        # 分批写入
        for batch_start in range(0, len(data), self.batch_size):
            batch = data[batch_start:batch_start + self.batch_size]
            batch_written = 0

            # 检查取消信号
            if await self.progress.is_cancelled():
                logger.info(f'[Crawl] 任务被取消 task_id={self.task_id}，停止写入')
                self.context.error_message = '任务被用户取消'
                await self.progress.clear_cancel_signal()
                break

            for attempt in range(1, self.max_retries + 1):
                try:
                    written = await self.target_writer.write(batch, self.context)
                    batch_written = written
                    total_written += written
                    # 更新写入进度
                    await self.progress.update_progress(
                        'writing',
                        batch_start + len(batch),
                        len(data),
                        {'message': f'已写入 {total_written} 条'},
                    )
                    break
                except Exception as e:
                    last_error = e
                    if not self.retry_enabled or attempt >= self.max_retries:
                        logger.error(
                            f'[Crawl] 批次写入失败 (batch_start={batch_start}, '
                            f'attempt={attempt}): {e}'
                        )
                        # 记录失败但继续处理下一批
                        self.context.total_failed += len(batch)
                        break

                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        f'[Crawl] 批次写入失败 (尝试 {attempt}/{self.max_retries}), '
                        f'{delay}秒后重试: {e}'
                    )
                    await asyncio.sleep(delay)

            # 速率限制
            if self.rate_limit > 0:
                delay = len(batch) / self.rate_limit
                if delay > 0:
                    await asyncio.sleep(delay)

        return total_written

    async def _write_single_with_retry(self, data: list[dict[str, Any]]) -> int:
        """一次性写入所有数据（用于文件类目标，避免分批覆盖）"""
        for attempt in range(1, self.max_retries + 1):
            try:
                written = await self.target_writer.write(data, self.context)
                return written
            except Exception as e:
                if not self.retry_enabled or attempt >= self.max_retries:
                    self.context.total_failed += len(data)
                    raise

                delay = self._calculate_retry_delay(attempt)
                logger.warning(
                    f'[Crawl] 写入失败 (尝试 {attempt}/{self.max_retries}), '
                    f'{delay}秒后重试: {e}'
                )
                await asyncio.sleep(delay)

        return 0

    def _apply_incremental_filter(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """应用增量过滤

        根据 incremental_key 和 incremental_start 过滤数据，
        只保留增量键值大于上次采集最大值的数据。
        """
        key = self.context.incremental_key
        start_value = self.context.incremental_start

        if not key or not data:
            return data

        filtered = []
        max_value = start_value

        for row in data:
            value = row.get(key)
            if value is None:
                # 没有增量键的记录直接跳过
                self.context.total_skipped += 1
                continue

            # 比较增量值：尝试数值比较，失败则回退到字符串比较
            if start_value is not None:
                try:
                    if float(value) <= float(start_value):
                        self.context.total_skipped += 1
                        continue
                except (ValueError, TypeError):
                    if str(value) <= str(start_value):
                        self.context.total_skipped += 1
                        continue

            filtered.append(row)

            # 更新最大值
            if max_value is None:
                max_value = str(value)
            else:
                try:
                    if float(value) > float(max_value):
                        max_value = str(value)
                except (ValueError, TypeError):
                    if str(value) > str(max_value):
                        max_value = str(value)

        # 保存增量结束值
        self.context.incremental_end = max_value
        self.context.metrics['incremental_start'] = start_value
        self.context.metrics['incremental_end'] = max_value
        self.context.metrics['incremental_filtered'] = len(data) - len(filtered)

        return filtered

    def _apply_transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """应用数据转换

        支持通过 source_config.transform 配置简单的字段映射和过滤。
        transform 配置:
            - field_mapping: 字段映射 {old_name: new_name}
            - select_fields: 只保留指定字段
            - filter_fields: 移除指定字段
        """
        transform = self.source_reader.config.get('transform', {})
        if not transform or not data:
            return data

        # 字段映射
        field_mapping = transform.get('field_mapping', {})
        if field_mapping:
            mapped_data = []
            for row in data:
                new_row = {}
                for key, value in row.items():
                    new_key = field_mapping.get(key, key)
                    new_row[new_key] = value
                mapped_data.append(new_row)
            data = mapped_data

        # 选择字段
        select_fields = transform.get('select_fields', [])
        if select_fields:
            data = [{k: v for k, v in row.items() if k in select_fields} for row in data]

        # 过滤字段
        filter_fields = transform.get('filter_fields', [])
        if filter_fields:
            data = [{k: v for k, v in row.items() if k not in filter_fields} for row in data]

        return data

    def _calculate_retry_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        if self.retry_backoff:
            # 指数退避: delay * 2^(attempt-1)
            return self.retry_delay * (2 ** (attempt - 1))
        return float(self.retry_delay)

    def _calculate_metrics(self) -> None:
        """计算性能指标"""
        duration = self.context.duration
        if duration > 0:
            self.context.throughput = self.context.total_succeeded / duration

        # 计算平均响应时间（基于总耗时和记录数）
        if self.context.total_scraped > 0 and duration > 0:
            self.context.avg_response_time = (duration * 1000) / self.context.total_scraped

        # 内存和 CPU 使用（简化估算）
        try:
            import os
            import platform

            process = None
            if platform.system() != 'Windows':
                try:
                    import resource
                    process = resource.getrusage(resource.RUSAGE_SELF)
                    self.context.memory_usage = process.ru_maxrss / 1024  # KB -> MB
                except (ImportError, AttributeError):
                    pass

            if process is None:
                try:
                    import psutil
                    p = psutil.Process(os.getpid())
                    self.context.memory_usage = p.memory_info().rss / (1024 * 1024)
                    self.context.cpu_usage = p.cpu_percent()
                except ImportError:
                    pass
        except Exception:
            pass