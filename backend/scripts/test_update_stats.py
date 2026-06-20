"""单独测试 _update_task_stats 函数"""
import asyncio, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ['ENVIRONMENT'] = 'dev'
from dotenv import load_dotenv
load_dotenv(Path('backend/.env'))

async def main():
    from backend.app.task.tasks.crawl_task.tasks import _update_task_stats
    from backend.common.enums import CrawlStatus
    from backend.database.db import async_db_session
    from backend.app.admin.crud.crud_crawl_task import crawl_task_dao
    from backend.utils.timezone import timezone

    task_id = 4

    # 查看更新前状态
    async with async_db_session() as db:
        task_before = await crawl_task_dao.get(db, task_id)
        if not task_before:
            print(f'❌ 任务 {task_id} 不存在')
            return
        print(f'更新前: status={task_before.status}, '
              f'total_run_count={task_before.total_run_count}, '
              f'total_records={task_before.total_records}')

    # 执行 _update_task_stats - 模拟成功的采集任务
    await _update_task_stats(
        task_id=task_id,
        status=CrawlStatus.STOPPED.value,
        total_records=10,
        last_status='success',
        duration=3.5,
    )

    # 查看更新后状态
    async with async_db_session() as db:
        task_after = await crawl_task_dao.get(db, task_id)
        print(f'更新后: status={task_after.status}, '
              f'total_run_count={task_after.total_run_count}, '
              f'total_records={task_after.total_records}, '
              f'last_status={task_after.last_status}, '
              f'last_duration={task_after.last_duration}, '
              f'last_run_time={task_after.last_run_time}')

        if task_after.total_run_count == (task_before.total_run_count or 0) + 1:
            print(f'\n✅ _update_task_stats 测试通过！total_run_count 已从 {task_before.total_run_count} 更新为 {task_after.total_run_count}')
        else:
            print(f'\n❌ total_run_count 未按预期增长')

if __name__ == '__main__':
    asyncio.run(main())
