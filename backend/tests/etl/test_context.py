"""ETL 上下文单元测试"""

from backend.app.admin.service.etl.context import ETLContext


class TestETLContext:
    """ETLContext 基本功能测试"""

    def test_default_creation(self) -> None:
        ctx = ETLContext()
        assert ctx.pipeline_id is not None
        assert ctx.flow_id == 0
        assert ctx.run_record_id == 0
        assert ctx.variables == {}
        assert ctx.metrics == {}

    def test_flow_id_assignment(self) -> None:
        ctx = ETLContext()
        ctx.flow_id = 42
        assert ctx.flow_id == 42

    def test_run_record_id_assignment(self) -> None:
        ctx = ETLContext()
        ctx.run_record_id = 99
        assert ctx.run_record_id == 99

    def test_variable_set_and_get(self) -> None:
        ctx = ETLContext()
        ctx['key1'] = 'value1'
        assert ctx['key1'] == 'value1'
        assert ctx.get('key1') == 'value1'

    def test_variable_get_default(self) -> None:
        ctx = ETLContext()
        assert ctx.get('nonexistent') is None
        assert ctx.get('nonexistent', 'default') == 'default'

    def test_variable_update(self) -> None:
        ctx = ETLContext()
        ctx['count'] = 10
        ctx['count'] = 20
        assert ctx['count'] == 20

    def test_metrics_tracking(self) -> None:
        ctx = ETLContext()
        ctx.metrics['rows_read'] = 100
        ctx.metrics['rows_written'] = 50
        assert ctx.metrics['rows_read'] == 100
        assert ctx.metrics['rows_written'] == 50

    def test_variables_and_metrics_independence(self) -> None:
        ctx = ETLContext()
        ctx['var'] = 1
        ctx.metrics['metric'] = 2
        assert ctx.variables == {'var': 1}
        assert ctx.metrics == {'metric': 2}
