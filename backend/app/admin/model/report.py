import sqlalchemy as sa

from backend.common.model import MappedBase, TimeZone
from backend.utils.timezone import timezone


class Report(MappedBase):
    """报表配置表"""

    __tablename__ = 'sys_report'
    __table_args__ = {'comment': '报表配置表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    name = sa.Column(sa.String(128), unique=True, comment='报表名称')
    description = sa.Column(sa.String(512), default=None, comment='报表描述')
    layout = sa.Column(sa.JSON, default=None, comment='布局配置(JSON数组)')
    theme = sa.Column(sa.String(32), default='default', comment='主题(default/dark/colorful)')
    refresh_interval = sa.Column(sa.Integer, default=None, comment='自动刷新间隔(秒)')
    is_public = sa.Column(sa.Boolean, default=False, comment='是否公开')
    status = sa.Column(sa.Integer, default=1, comment='状态(0停用 1正常)')
    created_by = sa.Column(sa.BigInteger, default=None, comment='创建者')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')


class ReportWidget(MappedBase):
    """报表组件配置表"""

    __tablename__ = 'sys_report_widget'
    __table_args__ = {'comment': '报表组件配置表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    report_id = sa.Column(sa.BigInteger, index=True, comment='报表 ID')
    widget_type = sa.Column(sa.String(32), comment='组件类型(bar/line/pie/scatter/area/table/stat/map/heatmap/radar/funnel/gauge)')
    title = sa.Column(sa.String(128), default=None, comment='组件标题')
    query_id = sa.Column(sa.BigInteger, default=None, comment='关联查询 ID')
    query_sql = sa.Column(sa.Text, default=None, comment='查询 SQL')
    config = sa.Column(sa.JSON, default=None, comment='组件配置(JSON: 颜色/轴/样式等)')
    position = sa.Column(sa.JSON, default=None, comment='位置配置(JSON: x/y/w/h)')
    sort = sa.Column(sa.Integer, default=0, comment='排序')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')
