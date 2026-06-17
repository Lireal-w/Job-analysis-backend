import sqlalchemy as sa

from backend.common.model import MappedBase, TimeZone
from backend.utils.timezone import timezone


class ResourcePermission(MappedBase):
    """资源权限配置表"""

    __tablename__ = 'sys_resource_permission'
    __table_args__ = {'comment': '资源权限配置表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(128), unique=True, comment='权限名称')
    resource_type = sa.Column(sa.String(32), comment='资源类型(datasource/table/field/report/dataset)')
    resource_id = sa.Column(sa.BigInteger, default=None, comment='资源 ID')
    resource_name = sa.Column(sa.String(128), default=None, comment='资源名称')
    permission_type = sa.Column(sa.String(16), comment='权限类型(read/write/admin)')
    role_id = sa.Column(sa.BigInteger, default=None, comment='角色 ID')
    description = sa.Column(sa.String(256), default=None, comment='描述')
    enabled = sa.Column(sa.Boolean, default=True, comment='是否启用')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')


class DataMaskingRule(MappedBase):
    """数据脱敏规则表"""

    __tablename__ = 'sys_data_masking_rule'
    __table_args__ = {'comment': '数据脱敏规则表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(128), unique=True, comment='规则名称')
    mask_type = sa.Column(sa.String(32), comment='脱敏类型(mask/truncate/hash/generalize)')
    target_table = sa.Column(sa.String(128), default=None, comment='目标表名')
    target_field = sa.Column(sa.String(128), default=None, comment='目标字段名')
    mask_config = sa.Column(sa.JSON, default=None, comment='脱敏配置(JSON)')
    enabled = sa.Column(sa.Boolean, default=True, comment='是否启用')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')
