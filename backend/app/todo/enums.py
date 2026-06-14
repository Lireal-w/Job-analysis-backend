from backend.common.enums import IntEnum, StrEnum


class TaskType(IntEnum):
    """任务类型"""

    DAILY = 0
    PERIODIC = 1
    SCHEDULED = 2


class TaskPriority(IntEnum):
    """任务优先级"""

    LOW = 0
    MEDIUM = 1
    HIGH = 2
    URGENT = 3


class TaskStatus(IntEnum):
    """任务状态"""

    TODO = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    CANCELLED = 3


class TaskSource(IntEnum):
    """任务来源"""

    ASSIGNED = 0
    SELF_CREATED = 1
    AI_GENERATED = 2


class GoalStatus(IntEnum):
    """目标状态"""

    PENDING = 0
    IN_PROGRESS = 1
    COMPLETED = 2


class TaskLogAction(IntEnum):
    """任务日志动作"""

    CREATED = 0
    UPDATED = 1
    PROGRESS_UPDATED = 2
    COMPLETED = 3
    CANCELLED = 4
    RESTARTED = 5
