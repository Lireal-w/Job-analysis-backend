import sqlalchemy as sa

from backend.common.model import MappedBase, TimeZone
from backend.utils.timezone import timezone


class ApiKey(MappedBase):
    """API 密钥认证表"""

    __tablename__ = 'sys_api_key'
    __table_args__ = {'comment': 'API 密钥认证表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(128), comment='密钥名称')
    key_prefix = sa.Column(sa.String(16), comment='密钥前缀(用于标识)')
    key_hash = sa.Column(sa.String(256), unique=True, comment='密钥哈希(SHA256)')
    user_id = sa.Column(sa.BigInteger, sa.ForeignKey('sys_user.id'), comment='创建者用户 ID')
    permissions = sa.Column(sa.Text, default=None, comment='权限标识列表(JSON 数组)')
    is_active = sa.Column(sa.Integer, default=1, comment='状态(0禁用 1启用)')
    expires_at = sa.Column(TimeZone, default=None, comment='过期时间')
    last_used_at = sa.Column(TimeZone, default=None, comment='最后使用时间')
    description = sa.Column(sa.String(256), default=None, comment='描述')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')
