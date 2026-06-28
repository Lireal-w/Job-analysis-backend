"""天涯书库小说 API"""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from backend.app.admin.schema.novel import (
    GetChapterContent,
    GetNovelDetail,
    GetNovelListDetail,
    NovelPageData,
)
from backend.app.admin.service.novel_service import mongo_novel_service
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.mongo_db import CurrentMongoDB

router = APIRouter()


@router.get(
    '/novels',
    summary='分页获取小说列表',
    dependencies=[DependsJwtAuth],
)
async def get_novel_list(
    db: CurrentMongoDB,
    page: Annotated[int, Query(ge=1, description='页码')] = 1,
    size: Annotated[int, Query(gt=0, le=100, description='每页数量')] = 20,
    keyword: Annotated[str | None, Query(description='小说名称搜索')] = None,
    author: Annotated[str | None, Query(description='作者搜索')] = None,
    category: Annotated[str | None, Query(description='分类筛选')] = None,
) -> ResponseSchemaModel[NovelPageData]:
    """分页获取小说列表"""
    data = await mongo_novel_service.get_novel_list(
        db=db, page=page, size=size,
        keyword=keyword, author=author, category=category,
    )
    return response_base.success(data=data)


@router.get(
    '/novels/{novel_title}',
    summary='获取小说详情（含章节列表）',
    dependencies=[DependsJwtAuth],
)
async def get_novel_detail(
    db: CurrentMongoDB,
    novel_title: Annotated[str, Path(description='小说名称')],
) -> ResponseSchemaModel[GetNovelDetail]:
    """获取小说详情"""
    novel = await mongo_novel_service.get_novel_detail(db=db, novel_title=novel_title)
    return response_base.success(data=novel)


@router.get(
    '/novels/{novel_title}/chapters/{chapter_index}',
    summary='获取章节正文内容',
    dependencies=[DependsJwtAuth],
)
async def get_chapter_content(
    db: CurrentMongoDB,
    novel_title: Annotated[str, Path(description='小说名称')],
    chapter_index: Annotated[int, Path(description='章节序号')],
) -> ResponseSchemaModel[GetChapterContent]:
    """获取章节正文"""
    content = await mongo_novel_service.get_chapter_content(
        db=db, novel_title=novel_title, chapter_index=chapter_index,
    )
    return response_base.success(data=content)
