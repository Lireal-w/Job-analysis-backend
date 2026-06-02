from datetime import datetime
from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, Text, JSON
from backend.common.model import Base

class Job(Base):
    __tablename__ = "job"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(64), unique=True, index=True)        # 职位唯一ID（用于去重）
    job_name = Column(String(255), nullable=False)              # 职位名称
    company_name = Column(String(255), nullable=False)          # 公司名称
    company_id = Column(String(64))                             # 公司ID
    salary_min = Column(DECIMAL(10, 2))                         # 最低薪资(k)
    salary_max = Column(DECIMAL(10, 2))                         # 最高薪资(k)
    salary_text = Column(String(64))                            # 原始薪资文本
    work_location = Column(String(255))                         # 工作地点
    education = Column(String(32))                              # 学历要求
    experience = Column(String(64))                             # 经验要求
    job_tags = Column(JSON)                                     # 职位标签(JSON数组)
    description = Column(Text)                                  # 职位描述
    skills = Column(JSON)                                       # 技能关键词(JSON数组)
    publish_date = Column(DateTime)                             # 发布日期
    source_url = Column(String(512))                            # 来源URL
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)