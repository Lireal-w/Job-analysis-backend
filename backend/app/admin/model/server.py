import sqlalchemy as sa

from backend.common.enums import ProtocolType
from backend.common.model import MappedBase, TimeZone
from backend.utils.timezone import timezone


class Server(MappedBase):
    """服务器配置表"""

    __tablename__ = 'sys_server'
    __table_args__ = {'comment': '服务器配置表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(128), comment='服务器名称')
    host = sa.Column(sa.String(256), comment='主机地址')
    port = sa.Column(sa.Integer, default=22, comment='端口号')
    protocol = sa.Column(sa.String(16), default=ProtocolType.SSH, comment='协议类型(ssh/rdp/vnc/telnet/sftp/http/https)')
    username = sa.Column(sa.String(128), default=None, comment='用户名')
    password = sa.Column(sa.String(512), default=None, comment='密码')
    ssh_key = sa.Column(sa.Text, default=None, comment='SSH 密钥')
    description = sa.Column(sa.String(256), default=None, comment='描述')
    status = sa.Column(sa.Integer, default=1, comment='状态(0停用 1正常)')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')
