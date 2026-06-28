"""Agent 开发任务数据模型"""

from datetime import datetime

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.app.agent_dev.enums import DevTaskPriority, DevTaskSource, DevTaskStatus, DevTaskType
from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.utils.timezone import timezone


class AgentDevTask(Base):
    """Agent 开发编排任务表"""

    __tablename__ = 'agent_dev_task'
    __table_args__ = {'comment': 'Agent 开发编排任务表'}

    id: Mapped[id_key] = mapped_column(init=False)
    title: Mapped[str] = mapped_column(sa.String(256), comment='任务标题')
    description: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='详细需求描述')
    task_type: Mapped[DevTaskType] = mapped_column(
        sa.SmallInteger, default=DevTaskType.FEATURE, comment='任务类型(0功能 1Bug 2重构 3优化 4集成 5配置)'
    )
    status: Mapped[DevTaskStatus] = mapped_column(
        sa.SmallInteger, default=DevTaskStatus.PENDING, comment='状态(0待处理 1规划中 2进行中 3评审中 4已完成 5失败 6已取消)'
    )
    priority: Mapped[DevTaskPriority] = mapped_column(
        sa.SmallInteger, default=DevTaskPriority.MEDIUM, comment='优先级(0低 1中 2高 3紧急)'
    )
    source: Mapped[DevTaskSource] = mapped_column(
        sa.SmallInteger, default=DevTaskSource.MOBILE, comment='来源(0移动端 1管理后台 2API 3自动)'
    )

    # 项目/技术栈信息
    project_name: Mapped[str | None] = mapped_column(sa.String(128), default=None, comment='项目名称')
    language: Mapped[str | None] = mapped_column(sa.String(64), default=None, comment='编程语言')
    framework: Mapped[str | None] = mapped_column(sa.String(128), default=None, comment='框架')
    related_paths: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='关联文件路径列表')

    # 需求与验收
    requirement_doc: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='需求文档/PRD')
    acceptance_criteria: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='验收标准(JSON)')

    # 编排信息
    orchestration_plan: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='编排计划(JSON)')
    current_stage: Mapped[str | None] = mapped_column(sa.String(32), default=None, comment='当前阶段')

    # 进度与结果
    progress: Mapped[int] = mapped_column(sa.SmallInteger, default=0, comment='整体进度(0-100)')
    result_summary: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='执行结果摘要')
    error_message: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='错误信息')
    output_data: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='产出物信息(JSON)')

    # 时间信息
    started_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None, init=False, comment='开始时间')
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None, init=False, comment='完成时间')

    # 人员
    created_by: Mapped[int] = mapped_column(sa.BigInteger, default=0, sort_order=998, comment='创建者')
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None, sort_order=998, comment='修改者')
