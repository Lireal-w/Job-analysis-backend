"""Agent 开发编排枚举"""

from backend.common.enums import IntEnum, StrEnum


class DevTaskType(IntEnum):
    """开发任务类型"""

    FEATURE = 0  # 功能开发
    BUG_FIX = 1  # Bug 修复
    REFACTOR = 2  # 代码重构
    OPTIMIZE = 3  # 性能优化
    INTEGRATE = 4  # 集成对接
    CONFIG = 5  # 配置变更


class DevTaskStatus(IntEnum):
    """开发任务状态"""

    PENDING = 0  # 待处理
    PLANNING = 1  # 规划中
    IN_PROGRESS = 2  # 进行中
    REVIEWING = 3  # 评审中
    COMPLETED = 4  # 已完成
    FAILED = 5  # 失败
    CANCELLED = 6  # 已取消


class DevTaskPriority(IntEnum):
    """开发任务优先级"""

    LOW = 0
    MEDIUM = 1
    HIGH = 2
    URGENT = 3


class DevTaskSource(IntEnum):
    """开发任务来源"""

    MOBILE = 0  # 移动端
    ADMIN = 1  # 管理后台
    API = 2  # OpenAPI
    AUTO = 3  # 自动触发


class DevStageType(StrEnum):
    """任务阶段类型"""

    PLAN = 'plan'  # 需求分析/计划
    DESIGN = 'design'  # 技术设计
    CODE = 'code'  # 编码实现
    REVIEW = 'review'  # 代码评审
    TEST = 'test'  # 测试
    DEPLOY = 'deploy'  # 部署发布


class DevAgentType(StrEnum):
    """Agent 类型"""

    ORCHESTRATOR = 'orchestrator'  # 编排器
    CODER = 'coder'  # 编码 Agent
    REVIEWER = 'reviewer'  # 评审 Agent
    TESTER = 'tester'  # 测试 Agent
    DEVOPS = 'devops'  # 运维/部署 Agent


class DevStageStatus(IntEnum):
    """阶段状态"""

    PENDING = 0  # 等待中
    IN_PROGRESS = 1  # 进行中
    COMPLETED = 2  # 已完成
    FAILED = 3  # 失败
    SKIPPED = 4  # 已跳过


class DevAgentStatus(IntEnum):
    """Agent 节点状态"""

    IDLE = 0  # 空闲
    BUSY = 1  # 忙碌
    OFFLINE = 2  # 离线
