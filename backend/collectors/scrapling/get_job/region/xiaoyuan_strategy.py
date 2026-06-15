"""智联校园招聘策略"""

from get_job.region.base import BaseRegionStrategy


class XiaoyuanStrategy(BaseRegionStrategy):
    """智联校园招聘策略"""

    def get_search_urls(self, keyword: str, **kwargs) -> list[str]:
        page_size = kwargs.get("page_size", 30)
        max_pages = kwargs.get("max_pages", 5)
        urls = []
        for page in range(1, max_pages + 1):
            urls.append(
                f"https://xiaoyuan.zhaopin.com/api/search"
                f"?keyword={keyword}&pageSize={page_size}&pageNum={page}"
            )
        return urls

    def parse_response(self, response) -> list[dict]:
        import json

        data = json.loads(response.text)
        return data.get("data", {}).get("list", [])
