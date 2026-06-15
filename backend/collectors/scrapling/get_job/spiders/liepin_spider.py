"""猎聘网 Spider"""

import json
import time

import scrapy
from scrapy import Request

from get_job.items import LiepinCompanyItem, LiepinJobItem


class LiepinSpider(scrapy.Spider):
    """猎聘网爬虫"""

    name = "liepin"
    allowed_domains = ["liepin.com", "www.liepin.com", "m.liepin.com"]
    start_urls = ["https://www.liepin.com/"]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "COOKIES_ENABLED": True,
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS": 3,
    }

    def __init__(self, keyword: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_keyword = keyword or "Python"
        self.max_pages = 5
        self.current_page = 0

    def start_requests(self):
        """搜索请求"""
        url = "https://www.liepin.com/zhaopin/"
        params = {
            "key": self.search_keyword,
            "dq": "",  # 全国
            "pubTime": "",
            "currentPage": 0,
            "pageSize": 40,
            "scene": "1",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items() if v)
        yield Request(
            f"{url}?{query}",
            callback=self.parse_search_result,
            headers={
                "Referer": "https://www.liepin.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            dont_filter=True,
        )

    def parse_search_result(self, response):
        """解析搜索结果"""
        # 尝试解析 JSON 数据
        data = None
        for script in response.css("script::text").getall():
            if "window.__INITIAL_STATE__" in script:
                try:
                    json_str = script.split(
                        "window.__INITIAL_STATE__ = "
                    )[1].split(";</script>")[0]
                    data = json.loads(json_str)
                except (IndexError, json.JSONDecodeError):
                    pass
                break

        if data:
            job_list = (
                data.get("searchResult", {})
                .get("data", {})
                .get("list", [])
            )
            for job_data in job_list:
                item = self._build_job_item(job_data)
                if item:
                    yield item

            # 翻页
            total = data.get("searchResult", {}).get("data", {}).get("totalCount", 0)
            total_pages = (total + 39) // 40 if total else 0
            self.current_page += 1
            if self.current_page < min(total_pages, self.max_pages):
                url = (
                    f"https://www.liepin.com/zhaopin/?key={self.search_keyword}"
                    f"&currentPage={self.current_page}&pageSize=40&scene=1"
                )
                yield Request(
                    url,
                    callback=self.parse_search_result,
                    headers={"Referer": "https://www.liepin.com/zhaopin/"},
                )
        else:
            # SSR 模式直接解析
            self.logger.info("Fallback to SSR parsing")
            from get_job.spiders.liepin_parsers import JobListParserMixin

            mixin = JobListParserMixin()
            jobs = mixin.parse_job_list(response)
            for job in jobs:
                item = LiepinJobItem()
                item["job_id"] = str(hash(job.get("source_url", "")))
                item["title"] = job.get("title", "")
                item["company_name"] = job.get("company_name", "")
                item["salary_raw"] = job.get("salary_raw", "")
                item["source_url"] = job.get("source_url", "")
                item["source_platform"] = "liepin"
                item["crawl_time"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                yield item

    def _build_job_item(self, job_data: dict):
        """从 JSON 构建职位 item"""
        item = LiepinJobItem()
        item["job_id"] = str(
            job_data.get("jobId", job_data.get("id", ""))
        )
        item["title"] = job_data.get("title", job_data.get("jobName", ""))
        company = job_data.get("company", {})
        if isinstance(company, dict):
            item["company_name"] = company.get("name", company.get("companyName", ""))
            item["company_id"] = str(
                company.get("id", company.get("companyId", ""))
            )
        else:
            item["company_name"] = str(company)
        item["salary_raw"] = job_data.get(
            "salary", job_data.get("salaryDesc", "")
        )
        item["work_location"] = job_data.get(
            "city", job_data.get("workCity", "")
        )
        item["education"] = job_data.get(
            "education", job_data.get("degree", "")
        )
        item["experience"] = job_data.get(
            "experience", job_data.get("workExp", "")
        )
        item["publish_time"] = job_data.get(
            "publishTime", job_data.get("updateTime", "")
        )
        item["source_url"] = job_data.get(
            "sourceUrl", job_data.get("url", "")
        )
        item["crawl_time"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        item["source_platform"] = "liepin"
        return item
