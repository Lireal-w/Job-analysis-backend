import sqlalchemy as sa

from backend.common.model import MappedBase, TimeZone
from backend.utils.timezone import timezone


class AuditLog(MappedBase):
    """审计日志表"""

    __tablename__ = 'sys_audit_log'
    __table_args__ = {'comment': '审计日志表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    event_type = sa.Column(sa.String(32), comment='事件类型(login/logout/data_access/data_modify/permission_change/system)')
    action = sa.Column(sa.String(64), comment='操作动作')
    resource_type = sa.Column(sa.String(32), default=None, comment='资源类型')
    resource_id = sa.Column(sa.BigInteger, default=None, comment='资源 ID')
    resource_name = sa.Column(sa.String(128), default=None, comment='资源名称')
    user_id = sa.Column(sa.BigInteger, default=None, comment='用户 ID')
    username = sa.Column(sa.String(64), default=None, comment='用户名')
    ip = sa.Column(sa.String(64), default=None, comment='IP 地址')
    user_agent = sa.Column(sa.String(512), default=None, comment='User Agent')
    request_method = sa.Column(sa.String(16), default=None, comment='请求方法')
    request_path = sa.Column(sa.String(256), default=None, comment='请求路径')
    request_body = sa.Column(sa.Text, default=None, comment='请求体')
    response_code = sa.Column(sa.Integer, default=None, comment='响应码')
    detail = sa.Column(sa.JSON, default=None, comment='详细信息(JSON)')
    status = sa.Column(sa.Integer, default=1, comment='状态(0失败 1成功)')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
