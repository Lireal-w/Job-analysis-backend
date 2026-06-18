"""采集异常测试"""

import pytest

from backend.app.admin.service.crawl.exceptions import (
    CrawlConfigError,
    CrawlConnectionError,
    CrawlError,
    CrawlIncrementalError,
    CrawlSourceError,
    CrawlTargetError,
)


class TestCrawlExceptions:
    """采集异常测试"""

    def test_base_error(self):
        err = CrawlError('test error')
        assert str(err) == 'test error'
        assert isinstance(err, Exception)

    def test_source_error(self):
        err = CrawlSourceError('query failed', 'database')
        assert 'database' in str(err)
        assert 'query failed' in str(err)
        assert err.source_type == 'database'

    def test_source_error_no_type(self):
        err = CrawlSourceError('query failed')
        assert 'query failed' in str(err)
        assert err.source_type == ''

    def test_target_error(self):
        err = CrawlTargetError('write failed', 'mongodb')
        assert 'mongodb' in str(err)
        assert 'write failed' in str(err)
        assert err.target_type == 'mongodb'

    def test_config_error(self):
        err = CrawlConfigError('invalid config')
        assert str(err) == 'invalid config'

    def test_connection_error(self):
        err = CrawlConnectionError('connection refused')
        assert str(err) == 'connection refused'

    def test_incremental_error(self):
        err = CrawlIncrementalError('incremental key not found')
        assert str(err) == 'incremental key not found'

    def test_inheritance(self):
        assert issubclass(CrawlSourceError, CrawlError)
        assert issubclass(CrawlTargetError, CrawlError)
        assert issubclass(CrawlConfigError, CrawlError)
        assert issubclass(CrawlConnectionError, CrawlError)
        assert issubclass(CrawlIncrementalError, CrawlError)