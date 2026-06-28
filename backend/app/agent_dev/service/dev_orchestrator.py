"""Agent 开发编排引擎 - 核心

负责将开发任务拆解为多阶段流水线，调度各类型 Agent 分工协作完成。
编排流程:
  1. 接收任务 → 分析需求 → 生成编排计划
  2. 按序执行阶段: Plan → Design → Code → Review → Test → Deploy
  3. 每个阶段选取合适的 Agent 执行
  4. 监控进度，处理失败重试
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from loguru import logger

from backend.app.agent_dev.crud.crud_dev_stage import dev_stage_dao
from backend.app.agent_dev.crud.crud_dev_task import dev_task_dao
from backend.app.agent_dev.enums import (
    DevAgentType,
    DevStageStatus,
    DevStageType,
    DevTaskStatus,
)
from backend.app.agent_dev.model import AgentDevStage, AgentDevTask
from backend.app.agent_dev.crud.crud_dev_agent import dev_agent_dao as _dev_agent_dao
from backend.app.agent_dev.schema.dev_stage import CreateAgentDevStageParam
from backend.app.agent_dev.service.dev_agent_service import dev_agent_service
from backend.database.db import async_db_session


class DevOrchestrator:
    """开发编排器

    管理开发任务的完整生命周期，负责任务拆解、Agent 调度、进度追踪。
    """

    # 默认阶段流水线（按执行顺序）
    DEFAULT_PIPELINE: list[dict[str, Any]] = [
        {
            'stage_type': DevStageType.PLAN,
            'agent_type': DevAgentType.ORCHESTRATOR,
            'title': '需求分析与计划',
            'description': '分析需求，制定开发计划和技术方案',
        },
        {
            'stage_type': DevStageType.DESIGN,
            'agent_type': DevAgentType.CODER,
            'title': '技术方案设计',
            'description': '设计技术实现方案、接口定义和数据模型',
        },
        {
            'stage_type': DevStageType.CODE,
            'agent_type': DevAgentType.CODER,
            'title': '编码实现',
            'description': '编写代码实现功能',
        },
        {
            'stage_type': DevStageType.REVIEW,
            'agent_type': DevAgentType.REVIEWER,
            'title': '代码评审',
            'description': '审查代码质量、安全性和最佳实践',
        },
        {
            'stage_type': DevStageType.TEST,
            'agent_type': DevAgentType.TESTER,
            'title': '自动化测试',
            'description': '编写和执行测试用例，确保功能正确',
        },
        {
            'stage_type': DevStageType.DEPLOY,
            'agent_type': DevAgentType.DEVOPS,
            'title': '部署发布',
            'description': '打包构建并部署到目标环境',
        },
    ]

    async def start_orchestration(self, task_id: int) -> None:
        """启动任务编排（异步后台执行）

        1. 创建阶段流水线
        2. 按序调度各阶段
        """
        async with async_db_session() as db:
            task = await dev_task_dao.get(db, task_id)
            if not task:
                logger.error(f'[Orchestrator] Task {task_id} not found')
                return

            if task.status != DevTaskStatus.PENDING:
                logger.warning(f'[Orchestrator] Task {task_id} status is not PENDING, skip')
                return

            # 更新任务状态为规划中
            await dev_task_dao.update(db, task_id, {
                'status': DevTaskStatus.PLANNING,
                'started_at': datetime.now(),
            })
            await db.flush()

            try:
                # 1. 生成编排计划
                plan = await self._generate_plan(task)
                orchestration_plan = {
                    'pipeline': [s['stage_type'] for s in plan],
                    'total_stages': len(plan),
                    'estimated_complexity': self._estimate_complexity(task),
                }

                # 2. 创建各阶段
                for seq, stage_info in enumerate(plan):
                    create_param = CreateAgentDevStageParam(
                        stage_type=stage_info['stage_type'],
                        agent_type=stage_info['agent_type'],
                        sequence_order=seq,
                        title=stage_info['title'],
                        description=stage_info['description'],
                        input_data={
                            'task_title': task.title,
                            'task_description': task.description,
                            'requirement_doc': task.requirement_doc,
                            'language': task.language,
                            'framework': task.framework,
                            'project_name': task.project_name,
                            'related_paths': task.related_paths,
                        },
                        max_retries=3,
                    )
                    await dev_stage_dao.create(db, create_param, task_id=task_id, created_by=task.created_by)

                await db.flush()

                # 3. 更新任务状态 - 进入进行中
                await dev_task_dao.update(db, task_id, {
                    'status': DevTaskStatus.IN_PROGRESS,
                    'orchestration_plan': orchestration_plan,
                    'current_stage': plan[0]['stage_type'] if plan else None,
                    'progress': 0,
                })
                await db.commit()

                logger.info(f'[Orchestrator] Task {task_id} orchestration plan created with {len(plan)} stages')

                # 4. 开始执行第一阶段
                await self._execute_next_stage(task_id)

            except Exception as e:
                logger.error(f'[Orchestrator] Task {task_id} orchestration failed: {e}')
                await dev_task_dao.update(db, task_id, {
                    'status': DevTaskStatus.FAILED,
                    'error_message': f'Orchestration failed: {str(e)}',
                })
                await db.commit()

    async def _generate_plan(
        self, task: AgentDevTask,
    ) -> list[dict[str, Any]]:
        """根据任务信息生成编排计划

        未来可接入 LLM 动态生成，当前使用默认流水线并根据任务类型微调。
        """
        pipeline = list(self.DEFAULT_PIPELINE)

        # 根据任务类型调整
        if task.task_type == 1:  # BUG_FIX
            # Bug 修复跳过设计阶段
            pipeline = [s for s in pipeline if s['stage_type'] != DevStageType.DESIGN]
        elif task.task_type == 5:  # CONFIG
            # 配置变更只需要计划和部署
            pipeline = [s for s in pipeline if s['stage_type'] in (
                DevStageType.PLAN, DevStageType.DEPLOY,
            )]
        elif task.task_type == 3:  # OPTIMIZE
            # 优化任务跳过设计阶段
            pipeline = [s for s in pipeline if s['stage_type'] != DevStageType.DESIGN]

        # 重新排序
        for i, stage in enumerate(pipeline):
            stage['sequence_order'] = i

        return pipeline

    def _estimate_complexity(self, task: AgentDevTask) -> str:
        """估算任务复杂度"""
        desc_len = len(task.description or '')
        if desc_len > 2000:
            return 'high'
        elif desc_len > 500:
            return 'medium'
        return 'low'

    async def _execute_next_stage(self, task_id: int) -> None:
        """执行下一个待处理的阶段"""
        async with async_db_session() as db:
            next_stage = await dev_stage_dao.get_next_pending_stage(db, task_id)
            if not next_stage:
                # 所有阶段已完成
                await self._finalize_task(db, task_id)
                return

            # 更新阶段状态为进行中
            await dev_stage_dao.update(db, next_stage.id, {
                'status': DevStageStatus.IN_PROGRESS,
                'started_at': datetime.now(),
            })

            # 更新任务当前阶段
            await dev_task_dao.update(db, task_id, {
                'current_stage': next_stage.stage_type,
            })
            await db.commit()

            logger.info(f'[Orchestrator] Task {task_id} stage {next_stage.stage_type} started')

            # 异步执行阶段（模拟 Agent 执行）
            asyncio.create_task(self._execute_stage_with_agent(task_id, next_stage.id))

    async def _execute_stage_with_agent(self, task_id: int, stage_id: int) -> None:
        """执行阶段：选择 Agent 并执行"""
        async with async_db_session() as db:
            stage = await dev_stage_dao.get(db, stage_id)
            if not stage:
                return

            try:
                # 选取可用 Agent
                agent = await dev_agent_service.pick_available(
                    db=db, agent_type=stage.agent_type,
                )

                # 更新阶段 - 分配 Agent
                agent_info = {'agent_id': agent.id, 'agent_name': agent.name} if agent else {}
                if agent:
                    await dev_stage_dao.update(db, stage_id, agent_info)
                    await _dev_agent_dao.assign_task(db, agent.id)
                    await db.flush()

                # 执行阶段逻辑
                result = await self._run_agent_stage(db, stage, agent)

                if result['success']:
                    # 阶段成功
                    await dev_stage_dao.update(db, stage_id, {
                        'status': DevStageStatus.COMPLETED,
                        'output_data': result.get('output_data'),
                        'completed_at': datetime.now(),
                    })
                    if agent:
                        await _dev_agent_dao.complete_task(db, agent.id, success=True)

                    # 更新任务进度
                    await self._update_task_progress(db, task_id)
                    await db.commit()

                    logger.info(f'[Orchestrator] Task {task_id} stage {stage.stage_type} completed')

                    # 执行下一阶段
                    await self._execute_next_stage(task_id)

                else:
                    # 阶段失败 - 重试逻辑
                    await self._handle_stage_failure(db, task_id, stage, result.get('error', 'Unknown error'))

            except Exception as e:
                logger.error(f'[Orchestrator] Task {task_id} stage {stage_id} error: {e}')
                await self._handle_stage_failure(db, task_id, stage, str(e))

    async def _run_agent_stage(
        self, db: Any, stage: AgentDevStage, agent: Any | None,
    ) -> dict[str, Any]:
        """执行 Agent 阶段任务

        根据阶段类型执行不同的逻辑：
        - PLAN/ORCHESTRATOR: 分析需求，输出开发计划
        - CODE/CODER: 生成/修改代码
        - REVIEW/REVIEWER: 审查代码
        - TEST/TESTER: 生成测试
        - DEPLOY/DEVOPS: 部署

        当前为模拟实现，未来可接入 LLM 或实际 Agent Worker。
        """
        stage_type = stage.stage_type
        input_data = stage.input_data or {}

        logger.info(f'[Orchestrator] Running stage: {stage_type}, agent: {agent.name if agent else "none"}')

        # 模拟执行耗时
        await asyncio.sleep(2)

        # 根据阶段类型返回模拟结果
        result = {
            'success': True,
            'output_data': {
                'stage_type': stage_type,
                'summary': f'{stage.title} 已完成',
                'agent': agent.name if agent else 'system',
                'artifacts': [],
            },
        }

        if stage_type == DevStageType.PLAN:
            result['output_data']['artifacts'] = [
                {'type': 'plan', 'content': f'开发计划: {input_data.get("task_title", "")}'},
            ]
        elif stage_type == DevStageType.DESIGN:
            result['output_data']['artifacts'] = [
                {'type': 'design_doc', 'content': '技术方案设计文档'},
                {'type': 'api_spec', 'content': 'API 接口定义'},
            ]
        elif stage_type == DevStageType.CODE:
            result['output_data']['artifacts'] = [
                {'type': 'source_code', 'files': input_data.get('related_paths', [])},
                {'type': 'diff', 'content': '代码变更'},
            ]
        elif stage_type == DevStageType.REVIEW:
            result['output_data']['artifacts'] = [
                {'type': 'review_report', 'content': '代码审查报告'},
                {'type': 'suggestions', 'content': ['优化建议1', '优化建议2']},
            ]
        elif stage_type == DevStageType.TEST:
            result['output_data']['artifacts'] = [
                {'type': 'test_cases', 'content': ['单元测试', '集成测试']},
                {'type': 'coverage', 'content': '测试覆盖率: 85%'},
            ]
        elif stage_type == DevStageType.DEPLOY:
            result['output_data']['artifacts'] = [
                {'type': 'deployment', 'content': '部署完成'},
                {'type': 'url', 'content': 'https://staging.example.com'},
            ]

        return result

    async def _handle_stage_failure(
        self, db: Any, task_id: int, stage: AgentDevStage, error: str,
    ) -> None:
        """处理阶段失败 - 重试或标记失败"""
        stage = await dev_stage_dao.get(db, stage.id)
        if not stage:
            return

        new_retry_count = stage.retry_count + 1

        if new_retry_count <= stage.max_retries:
            # 重试
            await dev_stage_dao.update(db, stage.id, {
                'status': DevStageStatus.PENDING,
                'error_message': error,
                'retry_count': new_retry_count,
            })
            await db.commit()
            logger.info(f'[Orchestrator] Task {task_id} stage {stage.stage_type} retry {new_retry_count}/{stage.max_retries}')

            # 重新执行
            await self._execute_next_stage(task_id)
        else:
            # 超过重试次数，标记失败
            await dev_stage_dao.update(db, stage.id, {
                'status': DevStageStatus.FAILED,
                'error_message': error,
                'completed_at': datetime.now(),
            })
            await dev_task_dao.update(db, task_id, {
                'status': DevTaskStatus.FAILED,
                'error_message': f'Stage {stage.stage_type} failed after {stage.max_retries} retries: {error}',
            })
            await db.commit()
            logger.error(f'[Orchestrator] Task {task_id} stage {stage.stage_type} failed permanently')

    async def _update_task_progress(self, db: Any, task_id: int) -> None:
        """更新任务整体进度"""
        stages = await dev_stage_dao.get_by_task(db, task_id)
        if not stages:
            return

        total = len(stages)
        completed = sum(1 for s in stages if s.status == DevStageStatus.COMPLETED)
        progress = int((completed / total) * 100)

        await dev_task_dao.update_progress(db, task_id, progress)

    async def _finalize_task(self, db: Any, task_id: int) -> None:
        """完成任务"""
        task = await dev_task_dao.get(db, task_id)
        if not task:
            return

        # 收集各阶段产出
        stages = await dev_stage_dao.get_by_task(db, task_id)
        outputs = {}
        for stage in stages:
            if stage.output_data:
                outputs[stage.stage_type] = stage.output_data

        await dev_task_dao.update(db, task_id, {
            'status': DevTaskStatus.COMPLETED,
            'progress': 100,
            'result_summary': '所有开发阶段已完成',
            'output_data': outputs,
            'completed_at': datetime.now(),
        })
        await db.commit()
        logger.info(f'[Orchestrator] Task {task_id} completed successfully')

    async def execute_stage(
        self,
        task_id: int,
        stage_id: int,
        agent_response: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """外部调用：手动执行或继续执行指定阶段（由 Agent Worker 回调）"""
        async with async_db_session() as db:
            stage = await dev_stage_dao.get(db, stage_id)
            if not stage:
                return {'success': False, 'error': 'Stage not found'}

            if agent_response:
                # Agent Worker 返回执行结果
                if agent_response.get('success'):
                    await dev_stage_dao.update(db, stage_id, {
                        'status': DevStageStatus.COMPLETED,
                        'output_data': agent_response.get('output_data'),
                        'completed_at': datetime.now(),
                    })
                    await self._update_task_progress(db, task_id)
                    await db.commit()

                    # 继续下一阶段
                    asyncio.create_task(self._execute_next_stage(task_id))
                    return {'success': True, 'message': 'Stage completed'}
                else:
                    await self._handle_stage_failure(
                        db, task_id, stage,
                        agent_response.get('error', 'Agent execution failed'),
                    )
                    return {'success': False, 'error': agent_response.get('error')}

            return {'success': False, 'error': 'No agent response'}

    async def retry_stage(self, task_id: int, stage_id: int) -> dict[str, Any]:
        """重试指定阶段"""
        async with async_db_session() as db:
            stage = await dev_stage_dao.get(db, stage_id)
            if not stage:
                return {'success': False, 'error': 'Stage not found'}

            await dev_stage_dao.update(db, stage_id, {
                'status': DevStageStatus.PENDING,
                'error_message': None,
                'retry_count': 0,
            })
            await dev_task_dao.update(db, task_id, {
                'status': DevTaskStatus.IN_PROGRESS,
                'error_message': None,
            })
            await db.commit()

            asyncio.create_task(self._execute_stage_with_agent(task_id, stage_id))
            return {'success': True, 'message': 'Stage retry initiated'}


dev_orchestrator: DevOrchestrator = DevOrchestrator()
