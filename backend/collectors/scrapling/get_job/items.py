import scrapy


class XiaoyuanJobItem(scrapy.Item):
    """智联校园招聘职位"""

    # 基本信息
    job_id = scrapy.Field()
    title = scrapy.Field()
    company_name = scrapy.Field()
    company_id = scrapy.Field()
    company_size = scrapy.Field()
    company_nature = scrapy.Field()
    company_industry = scrapy.Field()

    # 职位详情
    salary_min = scrapy.Field()
    salary_max = scrapy.Field()
    salary_raw = scrapy.Field()
    work_location = scrapy.Field()
    experience = scrapy.Field()
    education = scrapy.Field()
    job_category = scrapy.Field()
    job_tags = scrapy.Field()
    skills = scrapy.Field()

    # 时间信息
    publish_time = scrapy.Field()
    crawl_time = scrapy.Field()

    # 来源
    source_platform = scrapy.Field()
    source_url = scrapy.Field()

    # 其他
    description = scrapy.Field()
    is_campus = scrapy.Field()


class LiepinJobItem(scrapy.Item):
    """猎聘职位"""

    job_id = scrapy.Field()
    title = scrapy.Field()
    company_name = scrapy.Field()
    company_id = scrapy.Field()
    company_size = scrapy.Field()
    company_nature = scrapy.Field()
    company_industry = scrapy.Field()

    salary_min = scrapy.Field()
    salary_max = scrapy.Field()
    salary_raw = scrapy.Field()
    work_location = scrapy.Field()
    experience = scrapy.Field()
    education = scrapy.Field()
    job_category = scrapy.Field()
    tags = scrapy.Field()

    publish_time = scrapy.Field()
    crawl_time = scrapy.Field()
    source_platform = scrapy.Field()
    source_url = scrapy.Field()
    description = scrapy.Field()


class LiepinCompanyItem(scrapy.Item):
    """猎聘公司信息"""

    company_id = scrapy.Field()
    company_name = scrapy.Field()
    company_size = scrapy.Field()
    company_nature = scrapy.Field()
    company_industry = scrapy.Field()
    company_description = scrapy.Field()
    company_website = scrapy.Field()
    company_address = scrapy.Field()
    source_url = scrapy.Field()
    crawl_time = scrapy.Field()


class XiaoyuanCompanyItem(scrapy.Item):
    """智联校园公司信息"""

    company_id = scrapy.Field()
    company_name = scrapy.Field()
    company_size = scrapy.Field()
    company_nature = scrapy.Field()
    company_industry = scrapy.Field()
    company_description = scrapy.Field()
    source_url = scrapy.Field()
    crawl_time = scrapy.Field()
