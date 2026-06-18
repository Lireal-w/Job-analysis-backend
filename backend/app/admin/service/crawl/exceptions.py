"""采集任务异常定义"""


class CrawlError(Exception):
    """采集基础异常"""


class CrawlSourceError(CrawlError):
    """数据源读取异常"""

    def __init__(self, msg: str, source_type: str = '') -> None:
        self.source_type = source_type
        super().__init__(f'[Source{f"({source_type})" if source_type else ""}] {msg}')


class CrawlTargetError(CrawlError):
    """目标存储写入异常"""

    def __init__(self, msg: str, target_type: str = '') -> None:
        self.target_type = target_type
        super().__init__(f'[Target{f"({target_type})" if target_type else ""}] {msg}')


class CrawlConfigError(CrawlError):
    """配置异常"""


class CrawlConnectionError(CrawlError):
    """数据源连接异常"""


class CrawlIncrementalError(CrawlError):
    """增量采集异常"""