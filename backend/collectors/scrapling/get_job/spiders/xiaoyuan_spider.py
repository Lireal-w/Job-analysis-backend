"""智联校园招聘 Spider"""

import json
import re
import time
from urllib.parse import urlencode

import scrapy
from scrapy import Request

from get_job.items import XiaoyuanCompanyItem, XiaoyuanJobItem
from get_job.spiders.xiaoyuan_parsers import (
    CompanyDetailParserMixin,
    JobDetailParserMixin,
    JobListParserMixin,
)


class XiaoyuanSpider(JobListParserMixin, JobDetailParserMixin, CompanyDetailParserMixin, scrapy.Spider):
    """智联校园招聘爬虫"""

    name = "xiaoyuan"
    allowed_domains = [
        "xiaoyuan.zhaopin.com",
        "zhaopin.com",
        "xiaoyuan.zhaopin.com",
    ]
    start_urls = ["https://xiaoyuan.zhaopin.com/"]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "COOKIES_ENABLED": True,
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS": 4,
    }

    def __init__(self, keyword: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_keyword = keyword or "Python"
        self.page_count = 0
        self.max_pages = 5

    def start_requests(self):
        """启动请求"""
        # 搜索接口
        search_url = "https://xiaoyuan.zhaopin.com/api/search"
        params = {
            "keyword": self.search_keyword,
            "pageSize": 30,
            "pageNum": 1,
            "city": "",
        }
        url = f"{search_url}?{urlencode(params)}"
        yield Request(
            url,
            callback=self.parse_search_result,
            headers={
                "Referer": "https://xiaoyuan.zhaopin.com/",
                "Accept": "application/json, text/plain, */*",
            },
            dont_filter=True,
        )

    def parse_search_result(self, response):
        """解析搜索结果"""
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error(f"JSON parse failed: {response.url}")
            return

        # 解析职位列表
        job_list = data.get("data", {}).get("list", [])
        if not job_list:
            job_list = data.get("data", {}).get("dataList", [])
        if not job_list:
            job_list = data.get("list", [])

        for job_data in job_list:
            item = XiaoyuanJobItem()
            item["job_id"] = str(job_data.get("jobId", job_data.get("id", "")))
            item["title"] = job_data.get("title", job_data.get("jobName", ""))
            item["company_name"] = job_data.get(
                "companyName", job_data.get("company", {})
            )
            if isinstance(item["company_name"], dict):
                item["company_name"] = item["company_name"].get("name", "")

            item["company_id"] = str(
                job_data.get("companyId", job_data.get("company", {}).get("id", ""))
            )
            item["salary_raw"] = job_data.get(
                "salary", job_data.get("salaryDesc", "")
            )
            item["work_location"] = job_data.get(
                "city", job_data.get("workCity", job_data.get("cityName", ""))
            )
            item["education"] = job_data.get("education", job_data.get("degree", ""))
            item["experience"] = job_data.get(
                "experience", job_data.get("workExp", "")
            )
            item["job_category"] = job_data.get(
                "jobType", job_data.get("category", "")
            )
            item["publish_time"] = job_data.get(
                "publishTime", job_data.get("updateTime", "")
            )
            item["source_url"] = job_data.get(
                "sourceUrl",
                job_data.get(
                    "url",
                    f"https://xiaoyuan.zhaopin.com/job/{job_data.get('jobId', '')}",
                ),
            )
            item["crawl_time"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            item["source_platform"] = "xiaoyuan"

            # 标签/技能
            tags = job_data.get("tags", job_data.get("skills", []))
            if tags and isinstance(tags, list):
                item["job_tags"] = [str(t) for t in tags]
                item["skills"] = [str(t) for t in tags]

            yield item

        # 翻页
        total_count = data.get("data", {}).get("totalCount", 0)
        page_size = data.get("data", {}).get("pageSize", 30)
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count else 0
        )
        current_page = data.get("data", {}).get("pageNum", 1)

        if current_page < min(total_pages, self.max_pages):
            next_page = current_page + 1
            params = {
                "keyword": self.search_keyword,
                "pageSize": page_size,
                "pageNum": next_page,
                "city": "",
            }
            next_url = (
                f"https://xiaoyuan.zhaopin.com/api/search?{urlencode(params)}"
            )
            yield Request(
                next_url,
                callback=self.parse_search_result,
                headers={
                    "Referer": "https://xiaoyuan.zhaopin.com/",
                    "Accept": "application/json, text/plain, */*",
                },
            )
