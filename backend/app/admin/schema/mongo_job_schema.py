from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MongoJobBase(BaseModel):
    """MongoDB 职位基础 Schema"""

    job_id: str = Field(description='职位唯一ID')
    job_name: str = Field(description='职位名称')
    company_name: str = Field(description='公司名称')
    salary_text: Optional[str] = Field(None, description='原始薪资文本')
    work_location: Optional[str] = Field(None, description='工作地点')
    education: Optional[str] = Field(None, description='学历要求')
    experience: Optional[str] = Field(None, description='经验要求')
    job_tags: Optional[list[str]] = Field(None, description='职位标签')
    skills: Optional[list[str]] = Field(None, description='技能关键词')
    description: Optional[str] = Field(None, description='职位描述')
    source_url: Optional[str] = Field(None, description='来源URL')
    publish_date: Optional[datetime] = Field(None, description='发布日期')


class GetMongoJobDetail(MongoJobBase):
    """获取 MongoDB 职位详情 Schema"""

    mongo_id: str = Field(description='MongoDB 文档 ID')
    crawl_time: Optional[datetime] = Field(None, description='爬取时间')


class GetMongoJobListDetail(BaseModel):
    """获取 MongoDB 职位列表详情 Schema（精简字段）"""

    mongo_id: str = Field(description='MongoDB 文档 ID')
    job_id: str = Field(description='职位唯一ID')
    job_name: str = Field(description='职位名称')
    company_name: str = Field(description='公司名称')
    salary_text: Optional[str] = Field(None, description='原始薪资文本')
    work_location: Optional[str] = Field(None, description='工作地点')
    education: Optional[str] = Field(None, description='学历要求')
    experience: Optional[str] = Field(None, description='经验要求')
    crawl_time: Optional[datetime] = Field(None, description='爬取时间')


class MongoJobPageData(BaseModel):
    """MongoDB 职位分页数据"""

    items: list[GetMongoJobListDetail] = Field(default_factory=list, description='数据列表')
    total: int = Field(0, description='总条数')
    page: int = Field(1, description='当前页码')
    size: int = Field(20, description='每页数量')


class MongoCompanyBase(BaseModel):
    """MongoDB 公司基础 Schema"""

    company_id: str = Field(description='公司唯一ID')
    company_name: str = Field(description='公司名称')
    company_size: Optional[str] = Field(None, description='公司规模')
    industry: Optional[str] = Field(None, description='所属行业')
    company_url: Optional[str] = Field(None, description='公司网址')


class GetMongoCompanyDetail(MongoCompanyBase):
    """获取 MongoDB 公司详情 Schema"""

    mongo_id: str = Field(description='MongoDB 文档 ID')


class GetMongoCompanyListDetail(BaseModel):
    """获取 MongoDB 公司列表详情 Schema"""

    mongo_id: str = Field(description='MongoDB 文档 ID')
    company_id: str = Field(description='公司唯一ID')
    company_name: str = Field(description='公司名称')
    company_size: Optional[str] = Field(None, description='公司规模')
    industry: Optional[str] = Field(None, description='所属行业')


class MongoCompanyPageData(BaseModel):
    """MongoDB 公司分页数据"""

    items: list[GetMongoCompanyListDetail] = Field(default_factory=list, description='数据列表')
    total: int = Field(0, description='总条数')
    page: int = Field(1, description='当前页码')
    size: int = Field(20, description='每页数量')


# ==================== Dashboard Schemas ====================


class OverviewStats(BaseModel):
    """概览统计"""

    totalJobs: int = Field(0, description='总岗位数')
    todayNew: int = Field(0, description='今日新增')
    avgSalary: float = Field(0, description='平均薪资（元/月）')
    totalCompanies: int = Field(0, description='公司总数')


class TrendItem(BaseModel):
    """岗位数量趋势项"""

    month: str = Field(description='月份，如 2025-01')
    count: int = Field(0, description='岗位数量')
    avgSalary: float = Field(0, description='平均薪资（元/月）')


class IndustryItem(BaseModel):
    """行业岗位分布项"""

    industry: str = Field(description='行业名称')
    value: int = Field(0, description='岗位数量')
    percent: float = Field(0, description='占比（%）')


class EducationItem(BaseModel):
    """学历要求分布项"""

    education: str = Field(description='学历要求')
    value: int = Field(0, description='岗位数量')


class HotJobItem(BaseModel):
    """热门岗位 TOP10 项"""

    name: str = Field(description='职位名称')
    count: int = Field(0, description='岗位数量')
    salary: str = Field('', description='薪资区间')


class CityItem(BaseModel):
    """城市岗位分布项"""

    city: str = Field(description='城市名称')
    count: int = Field(0, description='岗位数量')
    avgSalary: float = Field(0, description='平均薪资（元/月）')


class ExperienceItem(BaseModel):
    """工作经验要求项"""

    experience: str = Field(description='经验要求')
    value: int = Field(0, description='岗位数量')


class SalaryRangeItem(BaseModel):
    """薪资区间分布项"""

    range: str = Field(description='薪资区间')
    value: int = Field(0, description='岗位数量')


class JobTypeItem(BaseModel):
    """岗位类型分布项"""

    type: str = Field(description='岗位类型')
    value: int = Field(0, description='岗位数量')
