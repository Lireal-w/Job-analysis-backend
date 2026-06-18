"""ETL 引擎异常定义"""


class ETLError(Exception):
    """ETL 基础异常"""


class ETLNodeError(ETLError):
    """节点执行异常"""

    def __init__(self, node_id: str, msg: str) -> None:
        self.node_id = node_id
        super().__init__(f'[Node {node_id}] {msg}')


class ETLConfigError(ETLError):
    """配置异常"""


class ETLDagError(ETLError):
    """DAG 异常 (循环依赖等)"""


class ETLDataError(ETLError):
    """数据处理异常"""


class ETLConnectionError(ETLError):
    """数据源连接异常"""
