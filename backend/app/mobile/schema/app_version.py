"""移动端版本管理 Schema"""

from datetime import datetime

from pydantic import ConfigDict, Field

from backend.app.mobile.enums import PlatformType, PublishStatus
from backend.common.schema import SchemaBase


class AppVersionSchemaBase(SchemaBase):
    """版本基础模型"""

    app_name: str = Field(max_length=64, description='应用名称')
    bundle_id: str | None = Field(default=None, max_length=128, description='包名/Bundle ID')
    platform: PlatformType = Field(default=PlatformType.ANDROID, description='平台(0安卓 1iOS 2鸿蒙)')
    version_name: str = Field(max_length=32, description='版本名称(如 2.1.0)')
    version_code: int = Field(description='版本号(如 210)')
    changelog: str | None = Field(default=None, description='更新日志')
    download_url: str | None = Field(default=None, max_length=512, description='下载链接')
    apk_file_path: str | None = Field(default=None, max_length=512, description='APK 文件路径')
    apk_file_size: int = Field(default=0, description='文件大小(字节)')
    apk_md5: str | None = Field(default=None, max_length=64, description='文件 MD5')
    min_version_code: int = Field(default=0, description='最低兼容版本号')
    force_update: bool = Field(default=False, description='是否强制更新')
    publish_status: PublishStatus = Field(default=PublishStatus.DRAFT, description='发布状态(0草稿 1已发布 2已归档)')
    remark: str | None = Field(default=None, max_length=256, description='备注')


class CreateAppVersionParam(AppVersionSchemaBase):
    """创建版本参数"""


class UpdateAppVersionParam(SchemaBase):
    """更新版本参数"""

    app_name: str | None = Field(default=None, max_length=64, description='应用名称')
    bundle_id: str | None = Field(default=None, max_length=128, description='包名/Bundle ID')
    platform: PlatformType | None = Field(default=None, description='平台')
    version_name: str | None = Field(default=None, max_length=32, description='版本名称')
    version_code: int | None = Field(default=None, description='版本号')
    changelog: str | None = Field(default=None, description='更新日志')
    download_url: str | None = Field(default=None, max_length=512, description='下载链接')
    apk_file_path: str | None = Field(default=None, max_length=512, description='APK 文件路径')
    apk_file_size: int | None = Field(default=None, description='文件大小(字节)')
    apk_md5: str | None = Field(default=None, max_length=64, description='文件 MD5')
    min_version_code: int | None = Field(default=None, description='最低兼容版本号')
    force_update: bool | None = Field(default=None, description='是否强制更新')
    publish_status: PublishStatus | None = Field(default=None, description='发布状态')
    remark: str | None = Field(default=None, max_length=256, description='备注')


class GetAppVersionDetail(AppVersionSchemaBase):
    """版本详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='版本 ID')
    download_count: int = Field(description='下载次数')
    status: int = Field(description='状态(0停用 1正常)')
    created_by: int | None = Field(None, description='创建者')
    updated_by: int | None = Field(None, description='修改者')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
