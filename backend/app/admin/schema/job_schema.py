from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class JobBase(BaseModel):
    """职位基础 Schema"""

    job_id: str
    job_name: str
    company_name: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_text: Optional[str] = None
    work_location: Optional[str] = None
    education: Optional[str] = None
    experience: Optional[str] = None
    job_tags: Optional[list[str]] = None
    skills: Optional[list[str]] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    publish_date: Optional[datetime] = None


class CreateJobParam(JobBase):
    """创建职位参数"""

    pass


class UpdateJobParam(BaseModel):
    """更新职位参数"""

    job_name: Optional[str] = None
    company_name: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_text: Optional[str] = None
    work_location: Optional[str] = None
    education: Optional[str] = None
    experience: Optional[str] = None
    job_tags: Optional[list[str]] = None
    skills: Optional[list[str]] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    publish_date: Optional[datetime] = None


class GetJobDetail(JobBase):
    """获取职位详情 Schema"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class GetJobListDetail(BaseModel):
    """获取职位列表详情 Schema"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: str
    job_name: str
    company_name: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_text: Optional[str] = None
    work_location: Optional[str] = None
    education: Optional[str] = None
    experience: Optional[str] = None
    publish_date: Optional[datetime] = None
    created_at: datetime
