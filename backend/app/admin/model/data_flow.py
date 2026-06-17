import sqlalchemy as sa

from backend.common.model import MappedBase, TimeZone
from backend.utils.timezone import timezone


class DataFlow(MappedBase):
    """ETL 数据流配置表"""

    __tablename__ = 'sys_data_flow'
    __table_args__ = {'comment': 'ETL 数据流配置表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(128), unique=True, comment='流程名称')
    description = sa.Column(sa.String(512), default=None, comment='流程描述')
    nodes = sa.Column(sa.JSON, default=None, comment='节点配置(JSON数组)')
    edges = sa.Column(sa.JSON, default=None, comment='边配置(JSON数组)')
    status = sa.Column(sa.String(16), default='draft', comment='状态(draft/published/archived)')
    version = sa.Column(sa.Integer, default=1, comment='版本号')
    enabled = sa.Column(sa.Boolean, default=True, comment='是否启用')
    created_by = sa.Column(sa.BigInteger, default=None, comment='创建者')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')


class DataFlowRun(MappedBase):
    """ETL 数据流运行记录表"""

    __tablename__ = 'sys_data_flow_run'
    __table_args__ = {'comment': 'ETL 数据流运行记录表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    flow_id = sa.Column(sa.BigInteger, index=True, comment='流程 ID')
    run_id = sa.Column(sa.String(64), comment='运行批次 ID')
    status = sa.Column(sa.String(16), comment='状态(running/success/failed)')
    start_time = sa.Column(TimeZone, comment='开始时间')
    end_time = sa.Column(TimeZone, default=None, comment='结束时间')
    duration = sa.Column(sa.Float, default=None, comment='耗时(秒)')
    total_input = sa.Column(sa.Integer, default=0, comment='输入记录数')
    total_output = sa.Column(sa.Integer, default=0, comment='输出记录数')
    total_error = sa.Column(sa.Integer, default=0, comment='错误数')
    error_message = sa.Column(sa.Text, default=None, comment='错误信息')
    log_detail = sa.Column(sa.JSON, default=None, comment='日志详情(JSON)')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
