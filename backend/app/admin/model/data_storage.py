import sqlalchemy as sa

from backend.common.model import MappedBase, TimeZone
from backend.utils.timezone import timezone


class DataLayer(MappedBase):
    """数据分层配置表"""

    __tablename__ = 'sys_data_layer'
    __table_args__ = {'comment': '数据分层配置表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(64), unique=True, comment='层级名称')
    layer_type = sa.Column(sa.String(16), comment='层级类型(ODS/DWD/DWS/ADS)')
    description = sa.Column(sa.String(256), default=None, comment='层级描述')
    sort = sa.Column(sa.Integer, default=0, comment='排序')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')


class Dataset(MappedBase):
    """数据集配置表"""

    __tablename__ = 'sys_dataset'
    __table_args__ = {'comment': '数据集配置表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(128), unique=True, comment='数据集名称')
    description = sa.Column(sa.String(512), default=None, comment='数据集描述')
    layer_id = sa.Column(sa.BigInteger, default=None, comment='所属数据层 ID')
    schema_config = sa.Column(sa.JSON, default=None, comment='Schema 配置(JSON)')
    source_type = sa.Column(sa.String(32), default=None, comment='数据来源类型(datasource/flow/manual)')
    source_id = sa.Column(sa.BigInteger, default=None, comment='数据来源 ID')
    dept_id = sa.Column(sa.BigInteger, default=None, comment='所属部门 ID')
    record_count = sa.Column(sa.BigInteger, default=0, comment='记录数')
    storage_size = sa.Column(sa.BigInteger, default=0, comment='存储大小(字节)')
    lifecycle_days = sa.Column(sa.Integer, default=None, comment='生命周期(天)')
    status = sa.Column(sa.Integer, default=1, comment='状态(0停用 1正常)')
    created_by = sa.Column(sa.BigInteger, default=None, comment='创建者')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')
