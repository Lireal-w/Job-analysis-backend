"""移动端版本管理枚举"""

from backend.common.enums import IntEnum


class PlatformType(IntEnum):
    """平台类型"""

    ANDROID = 0
    IOS = 1
    HARMONY = 2


class PublishStatus(IntEnum):
    """发布状态"""

    DRAFT = 0
    PUBLISHED = 1
    ARCHIVED = 2
