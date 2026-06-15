"""区域爬取基础策略"""

from abc import ABC, abstractmethod
from typing import Any


class BaseRegionStrategy(ABC):
    """区域爬取策略基类"""

    @abstractmethod
    def get_search_urls(self, keyword: str, **kwargs) -> list[str]:
        """生成搜索 URL 列表"""
        ...

    @abstractmethod
    def parse_response(self, response: Any) -> list[dict]:
        """解析响应"""
        ...
