import subprocess
import os
import uuid
from pathlib import Path
from core.conf import settings
from common.log import log

# 爬虫输出目录
OUTPUT_DIR = Path(settings.BASE_DIR) / "static" / "crawl_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def run_scrapy_crawler(spider_name: str = "xiaoyuan", output_format: str = "json") -> str:
    """
    在子进程中运行 Scrapy 爬虫，避免阻塞 FastAPI 事件循环
    :param spider_name: 爬虫名称
    :param output_format: 输出格式 (json/csv)
    :return: 生成文件的绝对路径
    """
    job_id = uuid.uuid4().hex
    output_file = OUTPUT_DIR / f"{spider_name}_{job_id}.{output_format}"
    
    # 爬虫项目根目录
    crawler_dir = Path(settings.BASE_DIR) / "collectors" / "job-analysis"
    
    command = [
        "scrapy", "crawl", spider_name,
        "-o", str(output_file),
        "-t", output_format
    ]
    
    log.info(f"Starting Scrapy crawler: {' '.join(command)}")
    
    try:
        # 使用 subprocess 隔离运行，切换工作目录
        result = subprocess.run(
            command, 
            cwd=str(crawler_dir), 
            capture_output=True, 
            text=True, 
            check=True,
            timeout=300  # 默认5分钟超时保护
        )
        log.info(f"Scrapy crawler finished. Output: {output_file}")
        return str(output_file)
    except subprocess.TimeoutExpired:
        log.error("Scrapy crawler timed out.")
        raise RuntimeError("Crawler execution timed out")
    except subprocess.CalledProcessError as e:
        log.error(f"Scrapy crawler failed: {e.stderr}")
        raise RuntimeError(f"Crawler failed: {e.stderr}")
