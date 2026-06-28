"""Agent 开发任务阶段/子任务数据模型"""

from datetime import datetime

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.app.agent_dev.enums import DevAgentType, DevStageStatus, DevStageType
from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.utils.timezone import timezone


class AgentDevStage(Base):
    """Agent 开发任务阶段表"""

    __tablename__ = 'agent_dev_stage'
    __table_args__ = {'comment': 'Agent 开发任务阶段表'}

    id: Mapped[id_key] = mapped_column(init=False)
    task_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey('agent_dev_task.id', ondelete='CASCADE'), comment='所属任务 ID')
    title: Mapped[str] = mapped_column(sa.String(256), comment='阶段标题')
    stage_type: Mapped[DevStageType] = mapped_column(sa.String(32), comment='阶段类型(plan/design/code/review/test/deploy)')

    # 以下字段有默认值
    agent_type: Mapped[DevAgentType] = mapped_column(sa.String(32), default=DevAgentType.CODER, comment='执行Agent类型')
    sequence_order: Mapped[int] = mapped_column(sa.SmallInteger, default=0, comment='执行顺序')
    description: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='阶段描述')
    status: Mapped[DevStageStatus] = mapped_column(sa.SmallInteger, default=DevStageStatus.PENDING, comment='状态(0等待中 1进行中 2已完成 3失败 4已跳过)')

    input_data: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='输入数据(JSON)')
    output_data: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='输出数据/产物(JSON)')

    agent_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='指派 Agent ID')
    agent_name: Mapped[str | None] = mapped_column(sa.String(128), default=None, comment='Agent 名称')

    started_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None, init=False, comment='开始时间')
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None, init=False, comment='完成时间')
    duration_seconds: Mapped[int | None] = mapped_column(default=None, comment='耗时(秒)')
    error_message: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='错误信息')
    retry_count: Mapped[int] = mapped_column(default=0, comment='重试次数')
    max_retries: Mapped[int] = mapped_column(default=3, comment='最大重试次数')

    remark: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='备注')

    created_by: Mapped[int] = mapped_column(sa.BigInteger, default=0, sort_order=998, comment='创建者')
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None, sort_order=998, comment='修改者')
