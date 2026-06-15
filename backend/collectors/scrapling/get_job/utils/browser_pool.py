"""浏览器池管理"""

import os
import time
from queue import Queue, Empty


class BrowserPool:
    """DrissionPage 浏览器池"""

    def __init__(self, pool_size: int = 2):
        self.pool_size = pool_size
        self._queue: Queue = Queue()
        self._initialized = False

    def _init_drivers(self):
        if self._initialized:
            return
        try:
            from DrissionPage import ChromiumPage

            for _ in range(self.pool_size):
                driver = ChromiumPage()
                self._queue.put(driver)
            self._initialized = True
        except ImportError:
            raise RuntimeError("DrissionPage not installed")

    def get_driver(self, timeout: float = 30.0):
        self._init_drivers()
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            raise TimeoutError("No available browser driver")

    def recycle(self, driver) -> None:
        self._queue.put(driver)

    def close_all(self) -> None:
        while not self._queue.empty():
            try:
                driver = self._queue.get_nowait()
                driver.quit()
            except Exception:
                pass


_pool_instance: BrowserPool | None = None


def get_browser_pool(spider=None) -> BrowserPool:
    """获取全局浏览器池（单例）"""
    global _pool_instance
    if _pool_instance is None:
        size = 2
        if spider and hasattr(spider, "settings"):
            size = spider.settings.getint("BROWSER_POOL_SIZE", 2)
        _pool_instance = BrowserPool(pool_size=size)
    return _pool_instance
