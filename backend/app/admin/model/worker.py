import sqlalchemy as sa

from datetime import datetime

from backend.common.model import MappedBase, TimeZone
from backend.utils.timezone import timezone


class WorkerNode(MappedBase):
    """从节点 Worker 注册表"""

    __tablename__ = 'sys_worker_node'
    __table_args__ = {'comment': '从节点 Worker 注册表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(128), unique=True, comment='节点名称')
    host = sa.Column(sa.String(256), comment='节点主机地址')
    port = sa.Column(sa.Integer, default=8001, comment='节点 API 端口')
    api_key = sa.Column(sa.String(256), comment='节点 API 密钥')
    tags = sa.Column(sa.String(512), default=None, comment='节点标签(逗号分隔)')
    description = sa.Column(sa.String(256), default=None, comment='描述')
    status = sa.Column(sa.String(16), default='offline', comment='状态(online/offline/busy)')
    version = sa.Column(sa.String(32), default=None, comment='节点版本')
    cpu_usage = sa.Column(sa.Float, default=None, comment='CPU 使用率')
    memory_usage = sa.Column(sa.Float, default=None, comment='内存使用率')
    task_count = sa.Column(sa.Integer, default=0, comment='当前运行任务数')
    max_tasks = sa.Column(sa.Integer, default=5, comment='最大并行任务数')
    last_heartbeat = sa.Column(TimeZone, default=None, comment='最后心跳时间')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')
