"""猎聘网解析器"""

import json
import re
from urllib.parse import urljoin

from parsel import Selector


class JobListParserMixin:
    """职位列表解析"""

    def parse_job_list(self, response):
        """解析职位列表页"""
        sel = Selector(response.text)
        jobs = []

        # SSR 职位卡片
        for item in sel.css(".job-card, .job-list-item, [class*='job-card']"):
            title = item.css("a[class*='title']::text, .job-title::text").get("")
            url_rel = item.css("a[class*='title']::attr(href)").get()
            company = item.css(
                ".company-name::text, [class*='company']::text"
            ).get("")
            salary = item.css(
                ".salary::text, [class*='salary']::text, .money::text"
            ).get("")

            if title:
                jobs.append(
                    {
                        "title": title.strip(),
                        "company_name": company.strip() if company else "",
                        "source_url": urljoin(response.url, url_rel) if url_rel else response.url,
                        "salary_raw": salary.strip() if salary else "",
                    }
                )

        # JSON 内嵌
        if not jobs:
            jobs = self._extract_from_json_embed(response)

        return jobs

    def _extract_from_json_embed(self, response):
        """从内嵌 JSON 提取"""
        jobs = []
        patterns = [
            r"window\.__INITIAL_STATE__\s*=\s*({.*?});",
            r"<script[^>]*>window\.__NUXT__\s*=\s*({.*?})<",
            r"window\.__PRELOADED_STATE__\s*=\s*({.*?});",
        ]
        for pattern in patterns:
            match = re.search(pattern, response.text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    for key in ("jobList", "list", "dataList", "searchResult"):
                        items = data.get(key) or data.get("props", {}).get(key)
                        if items and isinstance(items, list):
                            for item in items:
                                jobs.append(
                                    {
                                        "title": item.get("title", item.get("jobName", "")),
                                        "company_name": item.get("companyName", item.get("company", "")),
                                        "source_url": item.get("url", response.url),
                                        "salary_raw": item.get("salary", item.get("salaryDesc", "")),
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
        """解析职位详情"""
        sel = Selector(response.text)
        desc = sel.css(
            ".job-description::text, .describtion::text, [class*='detail']::text"
        ).getall()
        tags = sel.css(
            ".job-tag::text, .tag-item::text, .skill-tag::text, .tag::text"
        ).getall()
        return {
            "description": "\n".join(t.strip() for t in desc if t.strip()),
            "tags": [t.strip() for t in tags if t.strip()],
        }


class CompanyDetailParserMixin:
    """公司详情解析"""

    def parse_company_detail(self, response):
        """解析公司详情"""
        sel = Selector(response.text)
        return {
            "company_size": sel.css("[class*='scale']::text, .company-size::text").get(""),
            "company_nature": sel.css("[class*='nature']::text, .company-nature::text").get(""),
            "company_industry": sel.css("[class*='industry']::text, .company-industry::text").get(""),
            "company_description": sel.css(
                ".company-description::text, [class*='desc']::text"
            ).get(""),
        }
