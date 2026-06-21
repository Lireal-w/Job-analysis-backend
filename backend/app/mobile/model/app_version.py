"""移动端版本与应用包管理数据模型"""

import sqlalchemy as sa

from backend.app.mobile.enums import PlatformType, PublishStatus
from backend.common.model import MappedBase, TimeZone, UniversalText
from backend.utils.timezone import timezone


class AppVersion(MappedBase):
    """移动端应用版本表"""

    __tablename__ = 'mobile_app_version'
    __table_args__ = {'comment': '移动端应用版本表'}

    id = sa.Column(sa.BigInteger, primary_key=True, unique=True, index=True, autoincrement=True, comment='主键 ID')
    app_name = sa.Column(sa.String(64), comment='应用名称')
    bundle_id = sa.Column(sa.String(128), default=None, comment='包名/ Bundle ID')
    platform = sa.Column(sa.SmallInteger, default=PlatformType.ANDROID, comment='平台(0安卓 1iOS 2鸿蒙)')
    version_name = sa.Column(sa.String(32), comment='版本名称(如 2.1.0)')
    version_code = sa.Column(sa.Integer, comment='版本号(如 210)')
    changelog = sa.Column(UniversalText, default=None, comment='更新日志')
    download_url = sa.Column(sa.String(512), default=None, comment='下载链接')
    apk_file_path = sa.Column(sa.String(512), default=None, comment='APK 文件路径(服务器本地)')
    apk_file_size = sa.Column(sa.BigInteger, default=0, comment='文件大小(字节)')
    apk_md5 = sa.Column(sa.String(64), default=None, comment='文件 MD5 校验值')
    min_version_code = sa.Column(sa.Integer, default=0, comment='最低兼容版本号')
    force_update = sa.Column(sa.Boolean, default=False, comment='是否强制更新')
    download_count = sa.Column(sa.Integer, default=0, comment='下载次数')
    status = sa.Column(sa.Integer, default=1, comment='状态(0停用 1正常)')
    publish_status = sa.Column(sa.SmallInteger, default=PublishStatus.DRAFT, comment='发布状态(0草稿 1已发布 2已归档)')
    remark = sa.Column(sa.String(256), default=None, comment='备注')
    created_by = sa.Column(sa.BigInteger, default=None, comment='创建者')
    updated_by = sa.Column(sa.BigInteger, default=None, comment='修改者')
    created_time = sa.Column(TimeZone, default=timezone.now, comment='创建时间')
    updated_time = sa.Column(TimeZone, default=None, onupdate=timezone.now, comment='更新时间')
