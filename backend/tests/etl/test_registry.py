"""节点注册表单元测试"""

from __future__ import annotations

import pytest

from backend.app.admin.service.etl.nodes.base import BaseNodeExecutor
from backend.app.admin.service.etl.registry import get_node_executor, register_node_executor


class TestRegistry:
    """注册表基本功能测试"""

    def test_get_source_database(self) -> None:
        executor = get_node_executor('n1', 'source_database', {'datasource_id': 1})
        assert executor.node_type == 'source_database'
        assert executor.node_id == 'n1'

    def test_get_transform_filter(self) -> None:
        executor = get_node_executor('n1', 'transform_filter', {})
        assert executor.node_type == 'transform_filter'

    def test_get_load_database(self) -> None:
        executor = get_node_executor('n1', 'load_database', {})
        assert executor.node_type == 'load_database'

    def test_get_unknown_type(self) -> None:
        with pytest.raises(ValueError, match='不支持的节点类型'):
            get_node_executor('n1', 'nonexistent_type', {})

    def test_register_custom_type(self) -> None:
        class CustomExecutor(BaseNodeExecutor):
            node_type = 'custom_test'

            async def execute(self, context, *inputs):
                return [{'result': 'ok'}]

        register_node_executor('custom_test', CustomExecutor)
        executor = get_node_executor('c1', 'custom_test', {})
        assert isinstance(executor, CustomExecutor)

    def test_all_source_types(self) -> None:
        types = ['source_database', 'source_file_csv', 'source_file_excel',
                 'source_file_json', 'source_api', 'source_file_text']
        for t in types:
            executor = get_node_executor('n', t, {})
            assert executor.node_type == t

    def test_all_transform_types(self) -> None:
        types = ['transform_filter', 'transform_select', 'transform_map',
                 'transform_aggregate', 'transform_sort', 'transform_limit',
                 'transform_join', 'transform_union', 'transform_unique',
                 'transform_fill_null', 'transform_python_script']
        for t in types:
            executor = get_node_executor('n', t, {})
            assert executor.node_type == t

    def test_all_load_types(self) -> None:
        types = ['load_database', 'load_file_csv', 'load_file_json',
                 'load_file_excel', 'load_log']
        for t in types:
            executor = get_node_executor('n', t, {})
            assert executor.node_type == t

    def test_validate_config_empty(self) -> None:
        executor = get_node_executor('n', 'load_log', {})
        # load_log with empty config is valid
        executor.validate_config()

    def test_executor_raises_error(self) -> None:
        executor = get_node_executor('n', 'load_log', {})
        with pytest.raises(Exception, match='\[Node n\]'):
            executor.raise_error('test error')
