from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.enums import DatasourceType
from backend.common.schema import SchemaBase


class DatasourceSchemaBase(SchemaBase):
    """数据源基础模型"""

    name: str = Field(max_length=128, description='数据源名称')
    db_type: DatasourceType = Field(description='数据库类型')
    host: str = Field(default='localhost', max_length=256, description='主机地址')
    port: int = Field(default=3306, description='端口号')
    database_name: str | None = Field(default=None, max_length=128, description='数据库名')
    username: str | None = Field(default=None, max_length=128, description='用户名')
    password: str | None = Field(default=None, max_length=512, description='密码')
    extra_params: str | None = Field(default=None, description='额外连接参数(JSON格式)')
    description: str | None = Field(default=None, max_length=256, description='描述')


class CreateDatasourceParam(DatasourceSchemaBase):
    """创建数据源参数"""


class UpdateDatasourceParam(SchemaBase):
    """更新数据源参数"""
    name: str | None = Field(default=None, max_length=128, description='数据源名称')
    db_type: DatasourceType | None = Field(default=None, description='数据库类型')
    host: str | None = Field(default='localhost', max_length=256, description='主机地址')
    port: int | None = Field(default=None, description='端口号')
    database_name: str | None = Field(default=None, max_length=128, description='数据库名')
    username: str | None = Field(default=None, max_length=128, description='用户名')
    password: str | None = Field(default=None, max_length=512, description='密码')
    extra_params: str | None = Field(default=None, description='额外连接参数(JSON格式)')
    description: str | None = Field(default=None, max_length=256, description='描述')


class GetDatasourceDetail(DatasourceSchemaBase):
    """数据源详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='数据源 ID')
    status: int = Field(description='状态(0停用 1正常)')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class DatasourceTestParam(SchemaBase):
    """测试数据源连接参数"""

    db_type: DatasourceType = Field(description='数据库类型')
    host: str = Field(default='localhost', max_length=256, description='主机地址')
    port: int = Field(default=3306, description='端口号')
    database_name: str | None = Field(default=None, max_length=128, description='数据库名')
    username: str | None = Field(default=None, max_length=128, description='用户名')
    password: str | None = Field(default=None, max_length=512, description='密码')
    extra_params: str | None = Field(default=None, description='额外连接参数(JSON格式)')


# 数据库默认端口映射
DATASOURCE_DEFAULT_PORTS: dict[DatasourceType, int] = {
    DatasourceType.MYSQL: 3306,
    DatasourceType.POSTGRESQL: 5432,
    DatasourceType.SQLITE: 0,
    DatasourceType.MONGODB: 27017,
    DatasourceType.REDIS: 6379,
    DatasourceType.MSSQL: 1433,
    DatasourceType.ORACLE: 1521,
    DatasourceType.API_REST: 0,
    DatasourceType.FILE_CSV: 0,
    DatasourceType.FILE_EXCEL: 0,
    DatasourceType.FILE_JSON: 0,
    DatasourceType.KAFKA: 9092,
    DatasourceType.S3: 0,
}
