"""米游社帖子采集器

基于 BaseCrawler + Scrapling 引擎，采集米游社 BBS 帖子。

配置示例 (source_config):
    {
        "type": "mihoyo_post",
        "cookies": "login_ticket=xxx; stuid=xxx; ...",
        "game_id": 2,
        "forums": [
            {"forum_id": 49, "name": "原神·官方"},
            {"forum_id": 56, "name": "原神·同人"}
        ],
        "max_pages": 5,
        "page_size": 20,
        "sort_type": 1,
        "request_interval": 3.0,
        "transform": {
            "filter_fields": ["content"]
        }
    }
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from backend.app.admin.service.crawl.context import CrawlContext
from backend.app.admin.service.crawl.crawlers.base import BaseCrawler
from backend.app.admin.service.crawl.crawlers.mihoyo.api import (
    MiHoYoApiClient,
    MiHoYoApiError,
)
from backend.app.admin.service.crawl.exceptions import CrawlSourceError


class MiHoYoPostCrawler(BaseCrawler):
    """米游社帖子采集器

    采集米游社 BBS 各版块的帖子数据，支持多版块、多页采集。
    使用 Scrapling AsyncFetcher 进行 HTTP 请求，自动处理 DS 签名。

    前置条件:
        - cookies: 米游社登录 Cookie（必需，含 login_ticket 和 stuid）
                  从浏览器 F12 → Application → Cookies 复制
    """

    # ── 元信息 ──
    source_type = 'mihoyo_post'
    platform = '米游社'
    crawler_version = '1.0.0'

    supported_configs = {
        'cookies': '米游社登录 Cookie (必需，含 login_ticket + stuid + account_id)',
        'game_id': '游戏 ID (1=崩坏3, 2=原神, 6=星穹铁道, 8=绝区零)',
        'forums': '版块列表，格式 [{"forum_id": 49, "name": "原神·官方"}]，为空则采集综合',
        'max_pages': '每个版块最大翻页数 (默认 5)',
        'page_size': '每页条数 (默认 20, 最大 50)',
        'sort_type': '排序方式 (1=最新, 2=热门)',
        'request_interval': '请求间隔秒数 (默认 3.0, 建议 >= 2 秒)',
    }

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)

        # 校验必需配置
        cookies = config.get('cookies', '')
        if not cookies:
            raise CrawlSourceError('米游社 Cookie 不能为空，请填写 cookies', self.source_type)

        # 创建 API 客户端
        self.api_client = MiHoYoApiClient(
            cookies=cookies,
            game_id=int(config.get('game_id', 2)),
        )

        # 采集参数
        self.forums = config.get('forums', [])
        self.max_pages = int(config.get('max_pages', 5))
        self.page_size = min(int(config.get('page_size', 20)), 50)
        self.sort_type = int(config.get('sort_type', 1))

    async def read(self, context: CrawlContext) -> list[dict[str, Any]]:
        """执行米游社帖子采集"""
        all_posts: list[dict[str, Any]] = []
        forum_list = self.forums or [{'forum_id': 0, 'name': '综合'}]

        logger.info(
            f'[米游社] 开始采集 game_id={self.api_client.game_id}, '
            f'版块数={len(forum_list)}, 最多{self.max_pages}页'
        )

        for forum in forum_list:
            forum_id = int(forum.get('forum_id', 0))
            forum_name = forum.get('name', f'版块{forum_id}')

            for page in range(1, self.max_pages + 1):
                try:
                    posts = await self._fetch_page(forum_id, page)
                    if not posts:
                        logger.info(f'[米游社] {forum_name} 第{page}页无数据')
                        break

                    # 附加上下文信息
                    for p in posts:
                        p['_forum_name'] = forum_name
                        p['_forum_id'] = forum_id
                        p['_page'] = page

                    all_posts.extend(posts)
                    logger.info(
                        f'[米游社] {forum_name} 第{page}/{self.max_pages}页 '
                        f'→ {len(posts)}条 (累计{len(all_posts)}条)'
                    )

                except MiHoYoApiError as e:
                    logger.warning(f'[米游社] {forum_name} API 中止: {e}')
                    break
                except Exception as e:
                    logger.error(f'[米游社] {forum_name} 第{page}页失败: {e}')
                    # 单页失败继续下一页
                    continue

        if not all_posts:
            logger.warning('[米游社] 未采集到任何数据')

        # 记录指标
        context.metrics['game_id'] = self.api_client.game_id
        context.metrics['forum_count'] = len(forum_list)
        context.metrics['pages_fetched'] = min(
            self.max_pages * len(forum_list),
            (len(all_posts) // max(self.page_size, 1)) + 1
        )

        return all_posts

    async def _fetch_page(self, forum_id: int, page: int) -> list[dict[str, Any]]:
        """采集单页帖子数据

        使用 BaseCrawler 的 fetch_json 发送请求（自动处理频率限制 + 重试），
        再通过 MiHoYoApiClient 的 get_headers() 生成 DS 签名。
        """
        params = {
            'gids': self.api_client.game_id,
            'page_size': self.page_size,
            'page_num': page,
            'sort_type': self.sort_type,
        }
        if forum_id > 0:
            params['fid'] = forum_id

        # 通过 BaseCrawler 的 fetch_json 发出请求（自动限速+重试）
        data = await self.fetch_json(
            f'{MiHoYoApiClient.BASE_URL}{MiHoYoApiClient.API_POST_LIST}',
            params=params,
            headers=self.api_client.get_headers(),
            cookies=self.api_client.get_cookies_dict(),
        )

        # 检查 API 响应状态
        MiHoYoApiClient.check_response(data)

        # 提取帖子列表
        return MiHoYoApiClient.extract_posts(data)
