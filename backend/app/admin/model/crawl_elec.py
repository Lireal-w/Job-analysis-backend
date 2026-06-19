"""宿舍电费采集数据记录表"""

import sqlalchemy as sa

from backend.common.model import MappedBase, TimeZone
from backend.utils.timezone import timezone


class CrawlElecRecord(MappedBase):
    """宿舍电费采集记录表"""

    __tablename__ = 'crawl_elec_record'
    __table_args__ = {'comment': '宿舍电费采集记录表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    room_id = sa.Column(sa.String(64), comment='宿舍房间 ID')
    dt = sa.Column(sa.String(32), default=None, comment='数据时间')
    remain_wq_money = sa.Column(sa.Float, default=None, comment='剩余水费')
    use_eq = sa.Column(sa.Float, default=None, comment='已用电量')
    tz_eq = sa.Column(sa.Float, default=None, comment='同种电量')
    remain_eq = sa.Column(sa.Float, default=None, comment='剩余电量')
    free_eq = sa.Column(sa.Float, default=None, comment='免费电量')
    total_eq = sa.Column(sa.Float, default=None, comment='总电量')
    recharge_eq = sa.Column(sa.Float, default=None, comment='充值电量')
    status = sa.Column(sa.Integer, default=None, comment='状态')
    raw_response = sa.Column(sa.JSON, default=None, comment='原始响应')
    task_id = sa.Column(sa.BigInteger, default=None, comment='采集任务 ID')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
