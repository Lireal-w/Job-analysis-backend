import sqlalchemy as sa

from backend.common.model import MappedBase, TimeZone
from backend.utils.timezone import timezone


class QualityRule(MappedBase):
    """数据质量规则表"""

    __tablename__ = 'sys_quality_rule'
    __table_args__ = {'comment': '数据质量规则表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(128), unique=True, comment='规则名称')
    description = sa.Column(sa.String(512), default=None, comment='规则描述')
    rule_type = sa.Column(sa.String(32), comment='规则类型(not_null/unique/range/regex/custom_sql)')
    target_table = sa.Column(sa.String(128), default=None, comment='目标表名')
    target_field = sa.Column(sa.String(128), default=None, comment='目标字段名')
    rule_config = sa.Column(sa.JSON, default=None, comment='规则配置(JSON)')
    severity = sa.Column(sa.String(16), default='warning', comment='严重级别(info/warning/error/critical)')
    enabled = sa.Column(sa.Boolean, default=True, comment='是否启用')
    status = sa.Column(sa.Integer, default=1, comment='状态(0停用 1正常)')
    created_by = sa.Column(sa.BigInteger, default=None, comment='创建者')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')


class QualityCheck(MappedBase):
    """数据质量检查记录表"""

    __tablename__ = 'sys_quality_check'
    __table_args__ = {'comment': '数据质量检查记录表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    rule_id = sa.Column(sa.BigInteger, index=True, comment='规则 ID')
    run_id = sa.Column(sa.String(64), comment='运行批次 ID')
    status = sa.Column(sa.String(16), comment='状态(running/success/failed)')
    start_time = sa.Column(TimeZone, comment='开始时间')
    end_time = sa.Column(TimeZone, default=None, comment='结束时间')
    duration = sa.Column(sa.Float, default=None, comment='耗时(秒)')
    total_checked = sa.Column(sa.Integer, default=0, comment='检查总数')
    total_passed = sa.Column(sa.Integer, default=0, comment='通过数')
    total_failed = sa.Column(sa.Integer, default=0, comment='失败数')
    score = sa.Column(sa.Float, default=None, comment='质量评分(0-100)')
    error_message = sa.Column(sa.Text, default=None, comment='错误信息')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
