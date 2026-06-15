"""
Crawler Stats Extension

通过 Scrapy 信号系统，实时采集爬虫运行统计：
- 总任务数 (spider_opened)
- 成功采集数 (item_scraped)
- 失败数 (item_error, spider_error)
- 今日采集量（按日期分类）
"""

import json
import os
from datetime import datetime, date
from pathlib import Path

from scrapy import signals
from scrapy.crawler import Crawler
from twisted.internet.defer import Deferred


class CrawlerStatsExtension:
    """爬虫统计信号扩展"""

    def __init__(self, crawler: Crawler):
        self.crawler = crawler
        self.stats = crawler.stats

        # 运行时计数器
        self._items_count = 0
        self._error_count = 0
        self._today_date = date.today().isoformat()
        self._start_time = None

        # 统计输出路径: backend/collectors/stats/
        stats_dir = Path(__file__).resolve().parent.parent.parent / "stats"
        stats_dir.mkdir(parents=True, exist_ok=True)
        self._stats_file = stats_dir / "crawler_stats.json"
        self._daily_stats_file = stats_dir / "daily_stats.json"

        # 连接信号
        crawler.signals.connect(self.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(self.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(self.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(self.item_error, signal=signals.item_error)
        crawler.signals.connect(self.spider_error, signal=signals.spider_error)

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> "CrawlerStatsExtension":
        return cls(crawler)

    def spider_opened(self, spider) -> None:
        """爬虫启动：记录总任务数"""
        self._start_time = datetime.now()
        spider.logger.info(f"[Stats] Spider started: {spider.name}")

        # 更新总任务数
        stats = self._load_json(self._stats_file)
        stats["total_tasks"] = stats.get("total_tasks", 0) + 1
        stats["last_run"] = self._start_time.isoformat()
        stats["last_spider"] = spider.name
        self._save_json(self._stats_file, stats)

    def spider_closed(self, spider, reason: str) -> None:
        """爬虫关闭：汇总统计"""
        elapsed = datetime.now() - self._start_time if self._start_time else 0
        spider.logger.info(
            f"[Stats] Spider finished: {spider.name}, "
            f"items={self._items_count}, errors={self._error_count}, "
            f"elapsed={elapsed}, reason={reason}"
        )

        # 更新运行统计
        stats = self._load_json(self._stats_file)
        stats["last_duration_seconds"] = int(elapsed.total_seconds()) if self._start_time else 0
        stats["last_status"] = "completed" if reason == "finished" else reason
        stats["last_items_count"] = self._items_count
        stats["last_error_count"] = self._error_count
        self._save_json(self._stats_file, stats)

    def item_scraped(self, item, spider) -> None:
        """成功采集一个 item"""
        self._items_count += 1

        # 更新今日采集量
        daily = self._load_json(self._daily_stats_file)
        today = self._today_date
        daily[today] = daily.get(today, 0) + 1
        self._save_json(self._daily_stats_file, daily)

    def item_error(self, item, response, spider, failure) -> None:
        """item 处理出错"""
        self._error_count += 1

    def spider_error(self, failure, response, spider) -> None:
        """爬虫请求出错"""
        self._error_count += 1

    @staticmethod
    def get_current_stats() -> dict:
        """获取当前爬虫统计（供后端 API 调用）"""
        stats_dir = Path(__file__).resolve().parent.parent.parent / "stats"
        stats_file = stats_dir / "crawler_stats.json"
        daily_file = stats_dir / "daily_stats.json"

        stats = {}
        if stats_file.exists():
            with open(stats_file) as f:
                stats = json.load(f)

        daily = {}
        if daily_file.exists():
            with open(daily_file) as f:
                daily = json.load(f)

        today = date.today().isoformat()
        today_count = daily.get(today, 0)

        # 计算成功率/失败率
        total_items = stats.get("total_tasks", 0)
        last_items = stats.get("last_items_count", 0)
        last_errors = stats.get("last_error_count", 0)
        last_total = last_items + last_errors
        success_rate = round(last_items / last_total * 100, 2) if last_total > 0 else 100.0
        failure_rate = round(100 - success_rate, 2) if last_total > 0 else 0.0

        return {
            "total_tasks": total_items,
            "last_items_count": last_items,
            "last_error_count": last_errors,
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "today_items": today_count,
            "last_run": stats.get("last_run"),
            "last_spider": stats.get("last_spider"),
            "last_duration_seconds": stats.get("last_duration_seconds"),
            "last_status": stats.get("last_status", "unknown"),
        }

    @staticmethod
    def _load_json(filepath: Path) -> dict:
        if filepath.exists():
            try:
                with open(filepath) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    @staticmethod
    def _save_json(filepath: Path, data: dict) -> None:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
