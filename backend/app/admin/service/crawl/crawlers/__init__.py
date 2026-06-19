"""爬虫插件包

约定：
- 每个平台爬虫放在独立子目录中，如 `mihoyo/`, `bilibili/`
- 每个目录下必须包含 `reader.py`，其中定义爬虫类
- 爬虫类继承 `BaseCrawler`，必须设置 `source_type` 和 `platform`
- 创建后在 `backend.app.admin.service.crawl.readers` 的 `_SOURCE_READERS` 中注册

支持的爬虫:
- mihoyo:  米游社帖子/游戏数据采集
- ...      待扩展
"""

from backend.app.admin.service.crawl.crawlers.base import BaseCrawler

__all__ = ['BaseCrawler']
