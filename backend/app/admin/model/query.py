import sqlalchemy as sa

from backend.common.model import MappedBase, TimeZone
from backend.utils.timezone import timezone


class QueryHistory(MappedBase):
    """查询历史记录表"""

    __tablename__ = 'sys_query_history'
    __table_args__ = {'comment': '查询历史记录表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(128), default=None, comment='查询名称')
    dataset_id = sa.Column(sa.BigInteger, default=None, comment='数据集 ID')
    query_type = sa.Column(sa.String(16), default='sql', comment='查询类型(sql/visual)')
    query_sql = sa.Column(sa.Text, default=None, comment='查询 SQL')
    query_config = sa.Column(sa.JSON, default=None, comment='可视化查询配置(JSON)')
    result_count = sa.Column(sa.Integer, default=0, comment='结果行数')
    duration = sa.Column(sa.Float, default=None, comment='执行耗时(秒)')
    status = sa.Column(sa.String(16), default='success', comment='状态(success/failed)')
    error_message = sa.Column(sa.Text, default=None, comment='错误信息')
    created_by = sa.Column(sa.BigInteger, default=None, comment='执行者')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')


class SavedQuery(MappedBase):
    """保存的查询表"""

    __tablename__ = 'sys_saved_query'
    __table_args__ = {'comment': '保存的查询表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(128), unique=True, comment='查询名称')
    description = sa.Column(sa.String(512), default=None, comment='查询描述')
    dataset_id = sa.Column(sa.BigInteger, default=None, comment='数据集 ID')
    query_type = sa.Column(sa.String(16), default='sql', comment='查询类型(sql/visual)')
    query_sql = sa.Column(sa.Text, default=None, comment='查询 SQL')
    query_config = sa.Column(sa.JSON, default=None, comment='可视化查询配置(JSON)')
    tags = sa.Column(sa.String(256), default=None, comment='标签(逗号分隔)')
    is_public = sa.Column(sa.Boolean, default=False, comment='是否公开')
    created_by = sa.Column(sa.BigInteger, default=None, comment='创建者')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')
