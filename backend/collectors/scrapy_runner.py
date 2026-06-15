import json
import subprocess
import uuid
from datetime import date
from pathlib import Path

from core.conf import settings
from common.log import log

# 爬虫输出目录
OUTPUT_DIR = Path(settings.BASE_DIR) / "static" / "crawl_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 爬虫统计目录
STATS_DIR = Path(settings.BASE_DIR) / "collectors" / "stats"
STATS_DIR.mkdir(parents=True, exist_ok=True)

# 爬虫项目根目录
CRAWLER_DIR = Path(settings.BASE_DIR) / "collectors" / "scrapling"


def run_scrapy_crawler(
    spider_name: str = "xiaoyuan",
    output_format: str = "json",
    keyword: str = "",
) -> str:
    """
    在子进程中运行 Scrapy 爬虫，避免阻塞 FastAPI 事件循环

    :param spider_name: 爬虫名称 (xiaoyuan / liepin)
    :param output_format: 输出格式 (json/csv)
    :param keyword: 搜索关键词
    :return: 生成文件的绝对路径
    """
    job_id = uuid.uuid4().hex
    output_file = OUTPUT_DIR / f"{spider_name}_{job_id}.{output_format}"

    command = [
        "scrapy", "crawl", spider_name,
        "-o", str(output_file),
        "-t", output_format,
    ]

    # 附加爬虫参数
    if keyword:
        command.extend(["-a", f"keyword={keyword}"])

    log.info(f"Starting Scrapy crawler: {' '.join(command)}")

    try:
        result = subprocess.run(
            command,
            cwd=str(CRAWLER_DIR),
            capture_output=True,
            text=True,
            check=True,
            timeout=300,
        )
        log.info(f"Scrapy crawler finished. Output: {output_file}")
        return str(output_file)
    except subprocess.TimeoutExpired:
        log.error("Scrapy crawler timed out.")
        raise RuntimeError("Crawler execution timed out")
    except subprocess.CalledProcessError as e:
        log.error(f"Scrapy crawler failed: {e.stderr}")
        raise RuntimeError(f"Crawler failed: {e.stderr}")


def get_crawler_stats() -> dict:
    """
    获取爬虫运行统计

    从 stats 目录读取 CrawlerStatsExtension 生成的统计文件，
    返回总任务数、成功率、失败率、今日采集量。

    :return: 统计信息 dict
    """
    stats_file = STATS_DIR / "crawler_stats.json"
    daily_file = STATS_DIR / "daily_stats.json"

    stats = _load_json(stats_file)
    daily = _load_json(daily_file)

    today = date.today().isoformat()
    today_count = daily.get(today, 0)

    last_items = stats.get("last_items_count", 0)
    last_errors = stats.get("last_error_count", 0)
    last_total = last_items + last_errors
    success_rate = round(last_items / last_total * 100, 2) if last_total > 0 else 100.0
    failure_rate = round(100 - success_rate, 2) if last_total > 0 else 0.0

    return {
        "total_tasks": stats.get("total_tasks", 0),
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


def _load_json(filepath: Path) -> dict:
    if filepath.exists():
        try:
            with open(filepath) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}
