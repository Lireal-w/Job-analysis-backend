"""智联校园招聘解析器"""

import json
import re
from datetime import datetime
from urllib.parse import urljoin

from parsel import Selector


class JobListParserMixin:
    """职位列表解析"""

    def parse_job_list(self, response):
        """解析职位列表页"""
        sel = Selector(response.text)

        # SSR 渲染模式
        jobs = []
        for item in sel.css(".job-list-item, .job-card, [class*='job-list'] > div"):
            title = item.css("a[class*='title'], .job-title::text").get("").strip()
            company = item.css(
                ".company-name::text, [class*='company']::text"
            ).get("")
            url_rel = item.css("a[class*='title']::attr(href)").get()
            url = urljoin(response.url, url_rel) if url_rel else None
            salary = item.css(
                ".salary::text, [class*='salary']::text, .money::text"
            ).get("")

            if title:
                jobs.append(
                    {
                        "title": title,
                        "company_name": company.strip() if company else "",
                        "source_url": url or response.url,
                        "salary_raw": salary.strip() if salary else "",
                        "crawl_time": datetime.now().isoformat(),
                    }
                )

        # 如果 SSR 解析失败，尝试 JSON 内嵌数据
        if not jobs:
            jobs = self._extract_from_json_embed(response)

        return jobs

    def _extract_from_json_embed(self, response):
        """从页面内嵌 JSON 中提取数据"""
        jobs = []
        patterns = [
            r"window\.__INITIAL_STATE__\s*=\s*({.*?});",
            r"<script[^>]*>window\.__NUXT__\s*=\s*({.*?})<",
            r"<script[^>]*id=\"__NEXT_DATA__\"[^>]*>({.*?})</script>",
        ]
        for pattern in patterns:
            match = re.search(pattern, response.text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    for key in (
                        "jobList",
                        "job_list",
                        "list",
                        "dataList",
                        "data_list",
                    ):
                        items = (
                            data.get(key)
                            or data.get("props", {}).get(key)
                            or data.get("state", {}).get(key)
                        )
                        if items and isinstance(items, list):
                            for item in items:
                                jobs.append(
                                    {
                                        "title": item.get("title", item.get("jobName", "")),
                                        "company_name": item.get(
                                            "companyName",
                                            item.get("company", ""),
                                        ),
                                        "source_url": item.get(
                                            "sourceUrl", item.get("url", response.url)
                                        ),
                                        "salary_raw": item.get(
                                            "salary", item.get("salaryDesc", "")
                                        ),
                                        "crawl_time": datetime.now().isoformat(),
                                    }
                                )
                            break
                except (json.JSONDecodeError, KeyError):
                    continue
                break
        return jobs


class JobDetailParserMixin:
    """职位详情解析"""

    def parse_job_detail(self, response):
        """解析职位详情页"""
        sel = Selector(response.text)

        description = sel.css(
            ".job-description::text, .jobDetail, [class*='detail']::text"
        ).getall()
        tags = sel.css(".tag-item::text, .job-tag::text, .skill-tag::text").getall()

        return {
            "description": "\n".join(t.strip() for t in description if t.strip()),
            "job_tags": [t.strip() for t in tags if t.strip()],
            "skills": [t.strip() for t in tags if t.strip()],
        }


class CompanyDetailParserMixin:
    """公司详情解析"""

    def parse_company_detail(self, response):
        """解析公司详情页"""
        sel = Selector(response.text)
        return {
            "company_size": sel.css(
                ".company-size::text, [class*='scale']::text"
            ).get(""),
            "company_nature": sel.css(
                ".company-nature::text, [class*='nature']::text"
            ).get(""),
            "company_industry": sel.css(
                ".company-industry::text, [class*='industry']::text"
            ).get(""),
        }
