from fastapi import APIRouter

from backend.collectors.scrapy_runner import get_crawler_stats
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth

router = APIRouter()


@router.get(
    '/crawler/stats',
    summary='获取爬虫运行统计',
    dependencies=[DependsJwtAuth],
)
async def crawler_stats() -> ResponseSchemaModel[dict]:
    """
    获取爬虫运行统计：
    - total_tasks: 总运行任务数
    - last_items_count: 上次采集量
    - last_error_count: 上次错误数
    - success_rate: 成功率 (%)
    - failure_rate: 失败率 (%)
    - today_items: 今日采集量
    - last_run: 最后运行时间
    - last_spider: 最后运行的爬虫
    - last_duration_seconds: 最后运行耗时
    - last_status: 最后运行状态
    """
    stats = get_crawler_stats()
    return response_base.success(data=stats)
