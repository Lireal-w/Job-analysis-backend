from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class DataFlowSchemaBase(SchemaBase):
    """数据流基础模型"""

    name: str = Field(max_length=128, description='流程名称')
    description: str | None = Field(default=None, max_length=512, description='流程描述')
    nodes: list | None = Field(default=None, description='节点配置(JSON数组)')
    edges: list | None = Field(default=None, description='边配置(JSON数组)')


class CreateDataFlowParam(DataFlowSchemaBase):
    """创建数据流参数"""


class UpdateDataFlowParam(SchemaBase):
    """更新数据流参数"""

    name: str | None = Field(default=None, max_length=128, description='流程名称')
    description: str | None = Field(default=None, max_length=512, description='流程描述')
    nodes: list | None = Field(default=None, description='节点配置(JSON数组)')
    edges: list | None = Field(default=None, description='边配置(JSON数组)')


class GetDataFlowDetail(DataFlowSchemaBase):
    """数据流详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='数据流 ID')
    status: str = Field(description='状态(draft/published/archived)')
    version: int = Field(description='版本号')
    enabled: bool = Field(description='是否启用')
    created_by: int | None = Field(default=None, description='创建者')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class GetDataFlowRunDetail(SchemaBase):
    """数据流运行记录详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='运行记录 ID')
    flow_id: int = Field(description='流程 ID')
    run_id: str = Field(description='运行批次 ID')
    status: str = Field(description='状态(running/success/failed)')
    start_time: datetime = Field(description='开始时间')
    end_time: datetime | None = Field(None, description='结束时间')
    duration: float | None = Field(default=None, description='耗时(秒)')
    total_input: int = Field(default=0, description='输入记录数')
    total_output: int = Field(default=0, description='输出记录数')
    total_error: int = Field(default=0, description='错误数')
    error_message: str | None = Field(default=None, description='错误信息')
    log_detail: dict | None = Field(default=None, description='日志详情(JSON)')
    created_time: datetime = Field(description='创建时间')
