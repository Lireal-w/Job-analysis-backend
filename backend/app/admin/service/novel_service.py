"""天涯书库小说 MongoDB 服务"""

from datetime import datetime
from typing import Any
from bson.objectid import ObjectId

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.app.admin.schema.novel import (
    GetChapterContent,
    GetNovelDetail,
    GetNovelListDetail,
    NovelPageData,
)
from backend.common.exception import errors
from backend.core.conf import settings

# 小说集合名称
MONGODB_NOVEL_COLLECTION = 'novels'


class MongoNovelService:
    """MongoDB 小说服务类"""

    @staticmethod
    async def get_novel_list(
        *,
        db: AsyncIOMotorDatabase,
        page: int = 1,
        size: int = 20,
        keyword: str | None = None,
        author: str | None = None,
        category: str | None = None,
    ) -> NovelPageData:
        """
        分页获取小说列表

        :param db: MongoDB 数据库实例
        :param page: 页码
        :param size: 每页数量
        :param keyword: 小说名称关键词
        :param author: 作者名称
        :param category: 分类
        :return:
        """
        collection = db[MONGODB_NOVEL_COLLECTION]
        query: dict[str, Any] = {}

        if keyword:
            query['novel_title'] = {'$regex': keyword, '$options': 'i'}
        if author:
            query['novel_author'] = {'$regex': author, '$options': 'i'}
        if category:
            query['novel_category'] = category

        total = await collection.count_documents(query)
        skip = (page - 1) * size
        cursor = collection.find(query, {
            'chapters': 0,  # 列表不返回章节数据
        }).sort('crawl_time', -1).skip(skip).limit(size)

        items = []
        async for doc in cursor:
            ct = doc.get('crawl_time')
            # crawl_time may be float (epoch) or string (ISO) - handle both
            if isinstance(ct, (int, float)):
                import datetime
                ct = datetime.datetime.fromtimestamp(ct).isoformat()

            items.append(GetNovelListDetail(
                novel_title=doc.get('novel_title', ''),
                novel_author=doc.get('novel_author', ''),
                novel_category=doc.get('novel_category', ''),
                novel_status=doc.get('novel_status'),
                novel_cover=doc.get('novel_cover'),
                total_chapters=doc.get('total_chapters', 0),
                source_url=doc.get('source_url', ''),
                crawl_time=ct,
            ))

        return NovelPageData(items=items, total=total, page=page, size=size)

    @staticmethod
    async def get_novel_detail(
        *,
        db: AsyncIOMotorDatabase,
        novel_title: str,
    ) -> GetNovelDetail:
        """
        获取小说详情（含章节列表）

        :param db:
        :param novel_title:
        :return:
        """
        collection = db[MONGODB_NOVEL_COLLECTION]
        doc = await collection.find_one({'novel_title': novel_title})
        if not doc:
            raise errors.NotFoundError(msg='小说不存在')

        chapters = []
        for ch in doc.get('chapters', []):
            chapters.append({
                'chapter_index': ch.get('chapter_index', 0),
                'title': ch.get('title', ''),
                'url': ch.get('url', ''),
                'content': None,  # 列表不返回正文
            })

        ct = doc.get('crawl_time')
        if isinstance(ct, (int, float)):
            import datetime
            ct = datetime.datetime.fromtimestamp(ct).isoformat()

        return GetNovelDetail(
            novel_title=doc.get('novel_title', ''),
            novel_author=doc.get('novel_author', ''),
            novel_category=doc.get('novel_category', ''),
            novel_status=doc.get('novel_status'),
            novel_cover=doc.get('novel_cover'),
            novel_desc=doc.get('novel_desc'),
            source_url=doc.get('source_url', ''),
            total_chapters=len(chapters),
            chapters=chapters,
            crawl_time=ct,
        )

    @staticmethod
    async def get_chapter_content(
        *,
        db: AsyncIOMotorDatabase,
        novel_title: str,
        chapter_index: int,
    ) -> GetChapterContent:
        """
        获取章节正文

        :param db:
        :param novel_title:
        :param chapter_index:
        :return:
        """
        collection = db[MONGODB_NOVEL_COLLECTION]
        doc = await collection.find_one(
            {'novel_title': novel_title},
            {'chapters': {'$elemMatch': {'chapter_index': chapter_index}}},
        )
        if not doc:
            raise errors.NotFoundError(msg='小说不存在')

        chapters = doc.get('chapters', [])
        if not chapters:
            raise errors.NotFoundError(msg='章节不存在')

        ch = chapters[0]
        return GetChapterContent(
            novel_title=novel_title,
            chapter_index=ch.get('chapter_index', 0),
            title=ch.get('title', ''),
            content=ch.get('content', ''),
        )


# 服务单例
mongo_novel_service = MongoNovelService()
