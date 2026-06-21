import sqlalchemy as sa

from backend.common.model import MappedBase, TimeZone
from backend.utils.timezone import timezone


class Datasource(MappedBase):
    """数据源配置表"""

    __tablename__ = 'sys_datasource'
    __table_args__ = {'comment': '数据源配置表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(128), unique=True, comment='数据源名称')
    db_type = sa.Column(sa.String(32), comment='数据库类型(mysql/postgresql/sqlite/mongodb/redis/mssql/oracle)')
    host = sa.Column(sa.String(256), default='localhost', comment='主机地址')
    port = sa.Column(sa.Integer, default=3306, comment='端口号')
    database_name = sa.Column(sa.String(128), default=None, comment='数据库名')
    username = sa.Column(sa.String(128), default=None, comment='用户名')
    password = sa.Column(sa.String(512), default=None, comment='密码')
    extra_params = sa.Column(sa.Text, default=None, comment='额外连接参数(JSON格式)')
    description = sa.Column(sa.String(256), default=None, comment='描述')
    dept_id = sa.Column(sa.BigInteger, default=None, comment='所属部门 ID')
    status = sa.Column(sa.Integer, default=1, comment='状态(0停用 1正常)')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')
