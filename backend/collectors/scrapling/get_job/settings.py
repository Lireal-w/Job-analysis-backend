import os

from dotenv import load_dotenv

# 加载 .env 文件（从 backend 根目录）
env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
load_dotenv(env_path)

BOT_NAME = "get_job"

SPIDER_MODULES = ["get_job.spiders"]
NEWSPIDER_MODULE = "get_job.spiders"

# Crawl responsibly
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

ROBOTSTXT_OBEY = False

# Concurrency
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 2

# Cookies
COOKIES_ENABLED = True
COOKIES_DEBUG = False

# Default headers
DEFAULT_REQUEST_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://xiaoyuan.zhaopin.com/",
}

# Middlewares
SPIDER_MIDDLEWARES = {
    "get_job.middlewares.GetJobSpiderMiddleware": 543,
}

DOWNLOADER_MIDDLEWARES = {
    "get_job.middlewares.DrissionPageCookieMiddleware": 100,
    "get_job.middlewares.RandomUserAgentMiddleware": 400,
    "get_job.middlewares.RequestDebugMiddleware": 950,
}

# Extensions - 启用统计信号扩展
EXTENSIONS = {
    "get_job.extensions.CrawlerStatsExtension": 500,
}

# Item Pipelines
ITEM_PIPELINES = {
    "get_job.pipelines.DataCleanPipeline": 200,
    "get_job.pipelines.JsonOutputPipeline": 300,
    "get_job.pipelines.CsvOutputPipeline": 350,
    "get_job.pipelines.MongoPipeline": 400,
}

# AutoThrottle
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

# Download timeout
DOWNLOAD_TIMEOUT = 30

# Output
FEED_EXPORT_ENCODING = "utf-8"

# 自定义配置
FORCE_LOGIN = os.getenv("FORCE_LOGIN", "False").lower() in ("true", "1", "yes")
LOGIN_TIMEOUT = int(os.getenv("LOGIN_TIMEOUT", "60"))
BROWSER_POOL_SIZE = int(os.getenv("BROWSER_POOL_SIZE", "2"))

# MongoDB
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "jobs")

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DATABASE = int(os.getenv("REDIS_DATABASE", "0"))

# Cookie
COOKIE_EXPIRE_SECONDS = int(os.getenv("COOKIE_EXPIRE_SECONDS", "3600"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_FILE = os.getenv("LOG_FILE")
