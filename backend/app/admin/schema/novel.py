"""天涯书库小说 Schema"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NovelChapterBase(BaseModel):
    """小说章节基础 Schema"""

    chapter_index: int = Field(description='章节序号')
    title: str = Field(description='章节标题')
    url: str = Field(description='章节 URL')
    content: Optional[str] = Field(None, description='章节正文')


class NovelBase(BaseModel):
    """小说基础 Schema"""

    novel_title: str = Field(description='小说名称')
    novel_author: str = Field(description='作者')
    novel_category: str = Field(description='分类')
    novel_status: Optional[str] = Field(None, description='连载状态')
    novel_cover: Optional[str] = Field(None, description='封面图片')
    novel_desc: Optional[str] = Field(None, description='简介')
    source_url: str = Field(description='来源 URL')


class GetNovelListDetail(BaseModel):
    """小说列表（精简）"""

    novel_title: str = Field(description='小说名称')
    novel_author: str = Field(description='作者')
    novel_category: str = Field(description='分类')
    novel_status: Optional[str] = Field(None, description='连载状态')
    novel_cover: Optional[str] = Field(None, description='封面图片')
    total_chapters: int = Field(0, description='总章节数')
    source_url: str = Field(description='来源 URL')
    crawl_time: Optional[datetime] = Field(None, description='爬取时间')


class GetNovelDetail(NovelBase):
    """小说详情"""

    total_chapters: int = Field(0, description='总章节数')
    chapters: list[NovelChapterBase] = Field(default_factory=list, description='章节列表(不含正文)')
    crawl_time: Optional[datetime] = Field(None, description='爬取时间')


class GetChapterContent(BaseModel):
    """章节内容"""

    novel_title: str = Field(description='小说名称')
    chapter_index: int = Field(description='章节序号')
    title: str = Field(description='章节标题')
    content: str = Field(description='章节正文')


class NovelPageData(BaseModel):
    """小说分页数据"""

    items: list[GetNovelListDetail] = Field(default_factory=list, description='数据列表')
    total: int = Field(0, description='总条数')
    page: int = Field(1, description='当前页码')
    size: int = Field(20, description='每页数量')
