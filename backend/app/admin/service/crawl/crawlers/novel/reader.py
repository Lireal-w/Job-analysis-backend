"""天涯书库小说爬虫

采集天涯书库 (https://tianyashuku.net/) 的小说数据，
支持批量采集章节列表和章节内容。

配置示例 (source_config):
    {
        "type": "novel_spider",
        "novel_url": "https://tianyashuku.net/wangluo/1615/",
        "start_chapter": 0,
        "max_chapters": 50,
        "request_interval": 1.5,
        "store_content": true
    }
"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger

from backend.app.admin.service.crawl.context import CrawlContext
from backend.app.admin.service.crawl.crawlers.base import BaseCrawler
from backend.app.admin.service.crawl.exceptions import CrawlSourceError


class TianyaNovelCrawler(BaseCrawler):
    """天涯书库小说爬虫"""

    source_type = 'novel_spider'
    platform = '天涯书库'
    crawler_version = '1.0.0'

    supported_configs = {
        'novel_url': '小说目录页 URL (必需)',
        'start_chapter': '起始章节索引 (从 0 开始, 默认 0)',
        'max_chapters': '最大采集章节数 (默认全部)',
        'request_interval': '请求间隔秒数 (默认 1.5)',
        'store_content': '是否存储章节内容 (默认 true, 否则仅采集元数据)',
    }

    NOVEL_URL_PATTERN = re.compile(r'https?://tianyashuku\.net/[^/]+/\d+/')

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.novel_url = config.get('novel_url', '')
        if not self.novel_url or not self.NOVEL_URL_PATTERN.match(self.novel_url):
            raise CrawlSourceError('无效的天涯书库小说 URL', self.source_type)

        self.novel_url = self.novel_url.rstrip('/') + '/'
        self.start_chapter = int(config.get('start_chapter', 0))
        self.max_chapters = int(config.get('max_chapters', 0)) or None
        self.store_content = bool(config.get('store_content', True))

    async def read(self, context: CrawlContext) -> list[dict[str, Any]]:
        """采集小说数据

        Returns:
            章节列表，每章包含:
            - chapter_index: 章节序号
            - title: 章节标题
            - url: 章节 URL
            - content: 章节正文 (如果 store_content=True)
            - novel_title: 小说名称
            - novel_author: 作者
            - novel_category: 分类
            - novel_cover: 封面图片
        """
        logger.info(f'[天涯书库] 开始采集小说: {self.novel_url}')

        # 1. 抓取目录页
        novel_info = await self._fetch_novel_info()
        chapters = novel_info.pop('chapters', [])

        if not chapters:
            raise CrawlSourceError('未找到章节列表', self.source_type)

        logger.info(f'[天涯书库] 发现 {len(chapters)} 章, novel={novel_info.get("novel_title")}')

        # 2. 按范围截取
        start = self.start_chapter
        end = (start + self.max_chapters) if self.max_chapters else len(chapters)
        target_chapters = chapters[start:end]

        logger.info(f'[天涯书库] 计划采集 {len(target_chapters)} 章 (第{start+1}-{end}章)')

        # 3. 采集每章内容
        results = []
        for i, ch in enumerate(target_chapters):
            try:
                chapter_data = {**novel_info, **ch}

                if self.store_content:
                    content = await self._fetch_chapter_content(ch['url'])
                    chapter_data['content'] = content

                results.append(chapter_data)
                logger.debug(f'[天涯书库] 第{start+i+1}/{end}章: {ch["title"]}')

            except Exception as e:
                logger.warning(f'[天涯书库] 第{ch["title"]}章采集失败: {e}')
                continue

        context.metrics['novel_title'] = novel_info.get('novel_title', '')
        context.metrics['total_chapters'] = len(chapters)
        context.metrics['crawled_chapters'] = len(results)

        logger.info(f'[天涯书库] 采集完成, 共 {len(results)} 章')
        return results

    async def _fetch_novel_info(self) -> dict[str, Any]:
        """获取小说元信息和章节列表"""
        html = await self.async_fetch(self.novel_url)
        info: dict[str, Any] = {}

        # 从 OG meta 标签提取信息
        info['novel_title'] = self._extract_meta(html, 'og:novel:book_name')
        info['novel_author'] = self._extract_meta(html, 'og:novel:author')
        info['novel_category'] = self._extract_meta(html, 'og:novel:category')
        info['novel_status'] = self._extract_meta(html, 'og:novel:status')
        info['novel_cover'] = self._extract_meta(html, 'og:image')
        info['novel_desc'] = self._extract_meta(html, 'og:description')

        # 提取章节列表
        chapters = []
        list_match = re.search(r'<div id="list">(.*?)</div>', html, re.DOTALL)
        if list_match:
            links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', list_match.group(1))
            for idx, (url, title) in enumerate(links):
                # 补全相对 URL
                if url.startswith('/'):
                    url = f'https://tianyashuku.net{url}'
                elif not url.startswith('http'):
                    url = f'{self.novel_url}{url}'

                chapters.append({
                    'chapter_index': idx,
                    'title': title.strip(),
                    'url': url,
                })

        info['chapters'] = chapters
        return info

    async def _fetch_chapter_content(self, url: str) -> str:
        """获取单章正文内容"""
        html = await self.async_fetch(url)

        # 提取 content-body 或 m-article-text
        content = ''
        for pattern in [
            r'<div[^>]*class="content-body[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="m-article-text"[^>]*>(.*?)</div>',
        ]:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                content = match.group(1)
                break

        if not content:
            logger.warning(f'未找到正文内容: {url}')
            return ''

        # 清理 HTML
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<[^>]+>', '\n', content)
        # 清理空白
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        # 过滤广告行（常见广告关键词）
        ad_keywords = ['推荐票', '月票', '收藏', '加入书签', '投推荐票', '手机阅读', '本章未完']
        clean_lines = [
            l for l in lines
            if not any(kw in l for kw in ad_keywords)
        ]
        return '\n'.join(clean_lines)

    @staticmethod
    def _extract_meta(html: str, property_name: str) -> str:
        """提取 meta 标签内容"""
        match = re.search(
            rf'<meta[^>]+(?:property|name)=["\']{property_name}["\'][^>]*content=["\']([^"\']*)["\']',
            html,
        )
        if match:
            return match.group(1).strip()
        # 尝试顺序交换
        match = re.search(
            rf'<meta[^>]+content=["\']([^"\']*)["\'](?:.*?(?:property|name)=["\']{property_name}["\'])',
            html,
        )
        return match.group(1).strip() if match else ''
