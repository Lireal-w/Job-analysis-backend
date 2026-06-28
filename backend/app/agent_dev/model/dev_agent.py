"""Agent 开发节点数据模型"""

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.app.agent_dev.enums import DevAgentStatus, DevAgentType
from backend.common.model import MappedBase, TimeZone
from backend.utils.timezone import timezone


class AgentDevAgent(MappedBase):
    """Agent 开发节点注册表"""

    __tablename__ = 'agent_dev_agent'
    __table_args__ = {'comment': 'Agent 开发节点注册表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(128), unique=True, comment='Agent 名称')
    agent_type = sa.Column(sa.String(32), comment='Agent 类型(coder/reviewer/tester/orchestrator/devops)')
    description = sa.Column(sa.String(256), default=None, comment='描述')

    # 关联 Worker 节点
    worker_node_id = sa.Column(sa.BigInteger, default=None, comment='关联 Worker 节点 ID(sys_worker_node)')

    # 能力与配置
    capabilities = sa.Column(sa.JSON, default=None, comment='能力列表(JSON)')
    config = sa.Column(sa.JSON, default=None, comment='Agent 配置(JSON)')

    # 状态与负载
    status = sa.Column(sa.SmallInteger, default=DevAgentStatus.IDLE, comment='状态(0空闲 1忙碌 2离线)')
    current_tasks = sa.Column(sa.Integer, default=0, comment='当前任务数')
    max_concurrent_tasks = sa.Column(sa.Integer, default=3, comment='最大并发任务数')
    total_tasks_completed = sa.Column(sa.Integer, default=0, comment='累计完成任务数')
    total_tasks_failed = sa.Column(sa.Integer, default=0, comment='累计失败任务数')

    # 健康信息
    last_heartbeat = sa.Column(TimeZone, default=None, comment='最后心跳时间')
    version = sa.Column(sa.String(32), default=None, comment='Agent 版本')

    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')
