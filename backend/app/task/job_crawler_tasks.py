import subprocess
from pathlib import Path

from backend.app.task.celery import celery_app
from backend.collectors.scrapy_runner import get_crawler_stats, run_scrapy_crawler


@celery_app.task(name="scrapy_crawler")
def run_job_crawler(spider_name: str = "xiaoyuan", keyword: str = "") -> dict:
    """
    异步执行 Scrapy 爬虫，采集招聘数据

    :param spider_name: 爬虫名称 (xiaoyuan / liepin)
    :param keyword: 搜索关键词
    :return: 执行结果
    """
    try:
        output_file = run_scrapy_crawler(
            spider_name=spider_name,
            keyword=keyword,
        )
        return {
            "status": "success",
            "output_file": output_file,
            "spider": spider_name,
        }
    except RuntimeError as e:
        return {
            "status": "failed",
            "error": str(e),
            "spider": spider_name,
        }


@celery_app.task(name="get_crawler_stats")
def fetch_crawler_stats() -> dict:
    """
    获取爬虫运行统计

    :return: 统计信息 dict
    """
    return get_crawler_stats()


@celery_app.task(name="process_crawled_data")
def process_crawled_data() -> dict:
    """
    处理爬取后的数据（预留）

    读取 JSON/CSV 并存入数据库
    """
    return {"status": "pending", "message": "Not implemented"}