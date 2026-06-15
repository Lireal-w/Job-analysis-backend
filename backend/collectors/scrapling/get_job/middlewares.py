import random
import time
from pathlib import Path
from urllib.parse import urlparse

from scrapy import Request, Spider
from scrapy.exceptions import NotConfigured
from scrapy.http import Response


class GetJobSpiderMiddleware:
    """Spider 中间件"""

    def process_spider_input(self, response: Response, spider: Spider):
        return None

    def process_spider_output(self, response: Response, result, spider: Spider):
        yield from result

    def process_spider_exception(self, response: Response, exception, spider: Spider):
        pass

    def process_start_requests(self, start_requests, spider: Spider):
        yield from start_requests


class RandomUserAgentMiddleware:
    """随机 User-Agent"""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    ]

    def process_request(self, request: Request, spider: Spider):
        request.headers["User-Agent"] = random.choice(self.USER_AGENTS)
        return None


class RequestDebugMiddleware:
    """请求调试（保存响应快照）"""

    def __init__(self):
        self.debug_dir = Path(__file__).parent.parent.parent.parent / "log" / "crawler_debug"
        self.debug_dir.mkdir(parents=True, exist_ok=True)

    def process_response(self, request: Request, response: Response, spider: Spider):
        if response.status >= 400:
            safe_name = urlparse(response.url).netloc.replace(".", "_")
            ts = int(time.time())
            debug_file = self.debug_dir / f"{spider.name}_{safe_name}_{ts}.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(response.text[:10000])
            spider.logger.warning(f"[Debug] Saved error response to {debug_file}")
        return response

    def process_exception(self, request: Request, exception, spider: Spider):
        spider.logger.error(f"[Debug] Request failed: {request.url} - {exception}")
        return None


class DrissionPageCookieMiddleware:
    """DrissionPage Cookie 注入中间件"""

    def __init__(self):
        self.browser_pool = None
        self._cookie_cache = {}

    def process_request(self, request: Request, spider: Spider):
        domain = urlparse(request.url).netloc
        if domain in self._cookie_cache:
            expire = self._cookie_cache[domain].get("expire", 0)
            if time.time() < expire:
                request.headers["Cookie"] = self._cookie_cache[domain]["cookie"]
                return None

        # 需要从浏览器获取 Cookie
        try:
            from get_job.utils.browser_pool import get_browser_pool

            pool = get_browser_pool(spider)
            if pool:
                driver = pool.get_driver()
                try:
                    driver.get(request.url)
                    time.sleep(2)
                    cookies = driver.cookies()
                    if cookies:
                        cookie_str = "; ".join(
                            f"{c['name']}={c['value']}"
                            for c in cookies
                            if "name" in c and "value" in c
                        )
                        self._cookie_cache[domain] = {
                            "cookie": cookie_str,
                            "expire": time.time()
                            + spider.settings.getint("COOKIE_EXPIRE_SECONDS", 3600),
                        }
                        request.headers["Cookie"] = cookie_str
                finally:
                    pool.recycle(driver)
        except Exception as e:
            spider.logger.warning(f"[Cookie] Browser cookie failed: {e}")

        return None
