import json

from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.todo.crud.crud_goal import goal_dao
from backend.app.todo.crud.crud_task import task_dao
from backend.app.todo.enums import GoalStatus, TaskSource, TaskStatus
from backend.app.todo.model import TaskGoal
from backend.app.todo.schema.goal import CreateGoalParam
from backend.app.todo.service.goal_service import goal_service
from backend.common.exception import errors


class AITaskService:
    """AI 任务服务类"""

    @staticmethod
    async def generate_goals(
        *, db: AsyncSession, task_id: int, user_id: int
    ) -> Sequence[TaskGoal]:
        """
        AI 自动为任务生成分阶段目标

        根据任务标题和描述，自动拆解为多个阶段性目标

        :param db: 数据库会话
        :param task_id: 任务ID
        :param user_id: 用户ID
        :return:
        """
        task = await task_dao.get(db, task_id)
        if not task:
            raise errors.NotFoundError(msg='任务不存在')

        # 清除已有的AI生成目标，重新生成
        existing_goals = await goal_dao.get_by_task(db, task_id)
        for goal in existing_goals:
            if goal.ai_generated and goal.status == GoalStatus.PENDING:
                await goal_dao.delete(db, goal.id)

        # 基于任务信息生成阶段性目标
        ai_goals = await AITaskService._analyze_task_and_generate_goals(task)

        # 批量创建目标
        created_goals = []
        for goal_data in ai_goals:
            goal_data['task_id'] = task_id
            goal_data['ai_generated'] = True
            goal_data['status'] = GoalStatus.PENDING.value

            # 使用API创建，记录日志
            create_param = CreateGoalParam(
                task_id=task_id,
                title=goal_data['title'],
                description=goal_data.get('description'),
                stage_order=goal_data.get('stage_order', 0),
            )
            goal = await goal_dao.create(db, create_param, user_id)
            created_goals.append(goal)

        # 更新任务来源为AI生成
        await task_dao.update(db, task_id, {'source': TaskSource.AI_GENERATED.value})

        return created_goals

    @staticmethod
    async def _analyze_task_and_generate_goals(task: Any) -> list[dict]:
        """
        分析任务并生成阶段性目标

        基于任务类型、标题和描述，智能拆解目标

        :param task: 任务对象
        :return: 目标列表
        """
        title = task.title
        description = task.description or ''
        task_type = task.task_type

        # 通用软件开发阶段模板
        common_goals = [
            {'title': '需求分析', 'description': f'分析"{title}"的需求细节，明确功能范围', 'stage_order': 0},
            {'title': '方案设计', 'description': f'设计"{title}"的技术实现方案', 'stage_order': 1},
            {'title': '测试用例设计', 'description': f'为"{title}"编写测试用例', 'stage_order': 2},
            {'title': '核心功能实现', 'description': f'实现"{title}"的核心功能', 'stage_order': 3},
            {'title': '测试验证', 'description': '执行测试用例，验证功能正确性', 'stage_order': 4},
            {'title': '代码审查与提交', 'description': '代码审查通过后提交Git', 'stage_order': 5},
        ]

        # 根据任务描述智能调整
        if description:
            # 检查是否包含特定的阶段信息
            if '前端' in description or 'UI' in description or '界面' in description:
                common_goals.insert(2, {
                    'title': 'UI/UX设计',
                    'description': '设计用户界面和交互流程',
                    'stage_order': 2,
                })
                # 重新排序
                for i, goal in enumerate(common_goals):
                    goal['stage_order'] = i

        return common_goals


ai_task_service = AITaskService()
