"""爬虫插件基类

基于 Scrapling 引擎，提供：
- AsyncFetcher: 异步 HTTP 请求（自动 TLS 指纹、请求头伪装）
- StealthyFetcher: 隐形浏览器模式（可处理 JS 渲染页面）
- Selector: 强大的 HTML/XML 解析器（scrapy 风格 CSS/XPath）
- 内置反爬策略（频率限制、指数退避重试、UA 轮换）
"""

from __future__ import annotations

import asyncio
import random
import time
from abc import abstractmethod
from typing import Any

from loguru import logger

from scrapling import AsyncFetcher, Selector, StealthyFetcher

from backend.app.admin.service.crawl.context import CrawlContext
from backend.app.admin.service.crawl.exceptions import (
    CrawlConfigError,
    CrawlError,
    CrawlSourceError,
)
from backend.app.admin.service.crawl.readers import BaseSourceReader


class BaseCrawler(BaseSourceReader):
    """爬虫插件基类

    所有平台爬虫的基类，封装了 Scrapling 引擎和通用反爬策略。

    子类需要:
    1. 设置类属性: source_type, platform
    2. 实现 read() 方法

    配置参数（通用，所有爬虫可用）:
        request_interval: 请求间隔秒数 (默认 1.0)
        use_stealth: 是否使用 StealthyFetcher (默认 False，用于 JS 渲染页面)
        max_retries_per_request: 单次请求最大重试 (默认 3)
        timeout: 请求超时秒数 (默认 30)
    """

    # ── 子类必须设置的元信息 ──
    source_type: str = ''
    """源类型标识，如 'mihoyo_post'、'bilibili_video' """

    platform: str = ''
    """平台显示名称，如 '米游社'、'Bilibili' """

    crawler_version: str = '1.0.0'
    """爬虫版本号 """

    supported_configs: dict[str, str] = {}
    """支持的配置项说明，用于前端动态渲染配置表单

    示例:
        {'cookies': '登录 Cookie (必需)', 'max_pages': '最大翻页数 (默认 10)'}
    """

    # ── 内部状态 ──
    _fetcher: AsyncFetcher | None = None
    """Scrapling 异步 HTTP 客户端 """

    _last_request_time: float = 0.0
    """上次请求时间，用于频率限制 """

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.request_interval = float(config.get('request_interval', 1.0))
        self.use_stealth = bool(config.get('use_stealth', False))
        self.max_retries = int(config.get('max_retries_per_request', 3))
        self.timeout = int(config.get('timeout', 30))
        self.validate_config()

    # ── 抽象方法 ──

    @abstractmethod
    async def read(self, context: CrawlContext) -> list[dict[str, Any]]:
        """执行采集，返回数据行列表

        Args:
            context: 采集执行上下文

        Returns:
            数据行列表，每行为一个 dict
        """
        ...

    # ── 模板方法 ──

    async def execute_read(self, context: CrawlContext) -> list[dict[str, Any]]:
        """read() 的包装方法，统一处理日志和指标记录

        子类应实现 read() 而非此方法。
        """
        logger.info(f'[{self.platform}] 开始采集, source_type={self.source_type}')
        result = await self.read(context)
        context.metrics['source_type'] = self.source_type
        context.metrics['platform'] = self.platform
        context.metrics['crawler_version'] = self.crawler_version
        context.metrics['records_count'] = len(result)
        logger.info(f'[{self.platform}] 采集完成, 共 {len(result)} 条')
        return result

    # ── Scrapling 引擎 ──

    @property
    def fetcher(self) -> AsyncFetcher:
        """获取 Scrapling Fetcher（懒加载）

        根据 use_stealth 配置决定使用:
        - AsyncFetcher: 普通异步请求，自动伪装 TLS 指纹
        - StealthyFetcher: 隐形模式，可渲染 JS（需要 playwright）
        """
        if self._fetcher is None:
            if self.use_stealth:
                self._fetcher = StealthyFetcher()
            else:
                self._fetcher = AsyncFetcher()
        return self._fetcher

    async def async_fetch(
        self,
        url: str,
        *,
        method: str = 'GET',
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        follow_redirects: bool = True,
    ) -> str:
        """发送 HTTP 请求，返回原始响应文本

        自动处理:
        - 频率限制 (request_interval)
        - 请求重试 (指数退避)
        - 响应状态码检查

        Returns:
            响应文本 (HTML/JSON string)

        Raises:
            CrawlSourceError: HTTP 错误或重试耗尽
        """
        # 频率限制
        await self._rate_limit()

        merged_headers = self._default_headers()
        if headers:
            merged_headers.update(headers)

        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                if self.use_stealth:
                    # StealthyFetcher 使用 fetch 方法
                    response = await self.fetcher.fetch(
                        url,
                        method=method,
                        headers=merged_headers,
                        cookies=cookies,
                        params=params,
                        body=json_body,
                    )
                    text = response.text
                else:
                    # AsyncFetcher
                    fetcher = self.fetcher
                    response = await getattr(fetcher, method.lower())(
                        url,
                        headers=merged_headers,
                        cookies=cookies,
                        params=params,
                        json=json_body,
                        follow_redirects=follow_redirects,
                    )
                    text = response.text

                if response.status >= 400:
                    raise CrawlSourceError(
                        f'HTTP {response.status}: {url[:100]}',
                        self.source_type,
                    )
                return text

            except Exception as e:
                last_error = e
                logger.warning(
                    f'[{self.platform}] 请求失败 (尝试 {attempt}/{self.max_retries}): {e}'
                )
                if attempt < self.max_retries:
                    delay = self._backoff_delay(attempt)
                    await asyncio.sleep(delay)

        raise CrawlSourceError(
            f'请求重试耗尽: {last_error}',
            self.source_type,
        )

    async def fetch_json(
        self,
        url: str,
        *,
        method: str = 'GET',
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """发送 HTTP 请求并自动解析 JSON 响应"""
        import json

        text = await self.async_fetch(
            url,
            method=method,
            headers=headers,
            cookies=cookies,
            params=params,
            json_body=json_body,
        )
        return json.loads(text)

    async def fetch_html(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Selector:
        """发送 HTTP 请求并返回 Scrapling Selector（可直接用 CSS/XPath 提取数据）"""
        text = await self.async_fetch(
            url,
            method='GET',
            headers=headers,
            cookies=cookies,
            params=params,
        )
        return Selector(text=text)

    # ── 内部辅助 ──

    async def _rate_limit(self) -> None:
        """请求频率限制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_interval:
            delay = self.request_interval - elapsed
            await asyncio.sleep(delay)
        self._last_request_time = time.time()

    def _backoff_delay(self, attempt: int) -> float:
        """指数退避延迟计算"""
        base = self.config.get('retry_delay', 2.0)
        delay = base * (2 ** (attempt - 1))
        # 添加随机抖动 ±25%
        jitter = random.uniform(-delay * 0.25, delay * 0.25)
        return max(0.5, delay + jitter)

    def _default_headers(self) -> dict[str, str]:
        """默认请求头"""
        return {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/json,*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
        }

    @classmethod
    def validate_config(cls) -> None:
        """校验配置是否完备，子类可覆盖

        在 __init__ 末尾自动调用。
        """
        if not cls.source_type:
            raise CrawlConfigError(f'{cls.__name__} 必须设置 source_type')
        if not cls.platform:
            raise CrawlConfigError(f'{cls.__name__} 必须设置 platform')

    # ── 资源清理 ──

    async def close(self) -> None:
        """释放 Scrapling Fetcher 资源"""
        try:
            fetcher = self._fetcher
            if fetcher is not None:
                if hasattr(fetcher, 'close'):
                    await fetcher.close()
                elif hasattr(fetcher, 'aclose'):
                    await fetcher.aclose()
        except Exception:
            pass
        finally:
            self._fetcher = None
