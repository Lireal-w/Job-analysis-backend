"""数据转换节点执行器单元测试"""

from __future__ import annotations

import pytest

from backend.app.admin.service.etl.context import ETLContext
from backend.app.admin.service.etl.exceptions import ETLNodeError
from backend.app.admin.service.etl.nodes.transform import (
    AggregateTransformExecutor,
    FillNullTransformExecutor,
    FilterTransformExecutor,
    JoinTransformExecutor,
    LimitTransformExecutor,
    MapTransformExecutor,
    PythonScriptTransformExecutor,
    SelectTransformExecutor,
    SortTransformExecutor,
    UnionTransformExecutor,
    UniqueTransformExecutor,
)


@pytest.mark.asyncio
class TestFilterTransform:
    """过滤转换测试"""

    async def test_filter_equal(self, sample_data) -> None:
        executor = FilterTransformExecutor('f1', {
            'conditions': [{'field': 'city', 'operator': 'eq', 'value': 'Beijing'}],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 3
        assert all(r['city'] == 'Beijing' for r in result)

    async def test_filter_and_logic(self, sample_data) -> None:
        executor = FilterTransformExecutor('f2', {
            'logic': 'and',
            'conditions': [
                {'field': 'city', 'operator': 'eq', 'value': 'Beijing'},
                {'field': 'age', 'operator': 'gt', 'value': 30},
            ],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 2
        assert all(r['city'] == 'Beijing' and r['age'] > 30 for r in result)

    async def test_filter_or_logic(self, sample_data) -> None:
        executor = FilterTransformExecutor('f3', {
            'logic': 'or',
            'conditions': [
                {'field': 'city', 'operator': 'eq', 'value': 'Guangzhou'},
                {'field': 'age', 'operator': 'ge', 'value': 40},
            ],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 2

    async def test_filter_in_operator(self, sample_data) -> None:
        executor = FilterTransformExecutor('f4', {
            'conditions': [{'field': 'city', 'operator': 'in', 'value': ['Beijing', 'Shanghai']}],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 5

    async def test_filter_contains(self, sample_data) -> None:
        executor = FilterTransformExecutor('f5', {
            'conditions': [{'field': 'name', 'operator': 'contains', 'value': 'li'}],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 2  # Alice, Charlie

    async def test_filter_startswith(self, sample_data) -> None:
        executor = FilterTransformExecutor('f6', {
            'conditions': [{'field': 'name', 'operator': 'startswith', 'value': 'D'}],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 1
        assert result[0]['name'] == 'Diana'

    async def test_empty_conditions(self, sample_data) -> None:
        executor = FilterTransformExecutor('f7', {'conditions': []})
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 6  # 无条件，全部返回

    async def test_no_match(self, sample_data) -> None:
        executor = FilterTransformExecutor('f8', {
            'conditions': [{'field': 'age', 'operator': 'gt', 'value': 100}],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert result == []

    async def test_empty_input(self) -> None:
        executor = FilterTransformExecutor('f9', {
            'conditions': [{'field': 'age', 'operator': 'gt', 'value': 18}],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, [])
        assert result == []


@pytest.mark.asyncio
class TestSelectTransform:
    """列选择转换测试"""

    async def test_select_specific_columns(self, sample_data) -> None:
        executor = SelectTransformExecutor('s1', {
            'columns': ['name', 'age'],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 6
        assert list(result[0].keys()) == ['name', 'age']

    async def test_select_rename_columns(self, sample_data) -> None:
        executor = SelectTransformExecutor('s2', {
            'columns': [
                {'source': 'name', 'target': 'full_name'},
                {'source': 'city', 'target': 'location'},
            ],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert 'full_name' in result[0]
        assert 'location' in result[0]
        assert 'name' not in result[0]
        assert result[0]['full_name'] == 'Alice'

    async def test_empty_columns(self, sample_data) -> None:
        executor = SelectTransformExecutor('s3', {'columns': []})
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 6

    async def test_empty_input(self) -> None:
        executor = SelectTransformExecutor('s4', {'columns': ['name']})
        ctx = ETLContext()
        result = await executor.execute(ctx, [])
        assert result == []


@pytest.mark.asyncio
class TestMapTransform:
    """字段映射转换测试"""

    async def test_simple_template(self, sample_data) -> None:
        executor = MapTransformExecutor('m1', {
            'mappings': [
                {'target': 'greeting', 'expression': 'Hello {{name}}!'},
            ],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, [sample_data[0]])
        assert result[0]['greeting'] == 'Hello Alice!'

    async def test_preserve_original_fields(self, sample_data) -> None:
        executor = MapTransformExecutor('m2', {
            'mappings': [
                {'target': 'bonus', 'expression': '{{salary}}'},
            ],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, [sample_data[0]])
        assert result[0]['name'] == 'Alice'  # 保留原始字段
        assert result[0]['bonus'] == 12000  # eval('12000') → int

    async def test_empty_mappings(self, sample_data) -> None:
        executor = MapTransformExecutor('m3', {'mappings': []})
        ctx = ETLContext()
        result = await executor.execute(ctx, [sample_data[0]])
        assert result == [sample_data[0]]


@pytest.mark.asyncio
class TestAggregateTransform:
    """聚合转换测试"""

    async def test_group_by_sum(self, sample_data) -> None:
        executor = AggregateTransformExecutor('a1', {
            'group_by': ['city'],
            'aggregations': [
                {'column': 'salary', 'function': 'sum', 'alias': 'total_salary'},
                {'column': 'id', 'function': 'count', 'alias': 'count'},
            ],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        # Beijing: 3 people, salary sum = 12000+15000+0(None)=27000
        beijing = [r for r in result if r['city'] == 'Beijing'][0]
        assert beijing['count'] == 3

    async def test_group_by_avg(self, sample_data) -> None:
        executor = AggregateTransformExecutor('a2', {
            'group_by': ['city'],
            'aggregations': [
                {'column': 'age', 'function': 'avg', 'alias': 'avg_age'},
            ],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        shanghai = [r for r in result if r['city'] == 'Shanghai'][0]
        assert shanghai['avg_age'] == 28.5  # (25+32)/2

    async def test_group_by_min_max(self, sample_data) -> None:
        executor = AggregateTransformExecutor('a3', {
            'group_by': ['city'],
            'aggregations': [
                {'column': 'age', 'function': 'min', 'alias': 'min_age'},
                {'column': 'age', 'function': 'max', 'alias': 'max_age'},
            ],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        beijing = [r for r in result if r['city'] == 'Beijing'][0]
        assert beijing['min_age'] == 30
        assert beijing['max_age'] == 40

    async def test_no_group_by(self, sample_data) -> None:
        executor = AggregateTransformExecutor('a4', {
            'group_by': [],
            'aggregations': [
                {'column': 'id', 'function': 'count', 'alias': 'total'},
                {'column': 'age', 'function': 'avg', 'alias': 'avg_age'},
            ],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 1
        assert result[0]['total'] == 6

    async def test_empty_input(self) -> None:
        executor = AggregateTransformExecutor('a5', {'group_by': ['city'], 'aggregations': []})
        ctx = ETLContext()
        result = await executor.execute(ctx, [])
        assert result == []

    async def test_count_distinct(self, sample_data) -> None:
        executor = AggregateTransformExecutor('a6', {
            'aggregations': [
                {'column': 'city', 'function': 'count_distinct', 'alias': 'unique_cities'},
            ],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert result[0]['unique_cities'] == 3  # Beijing, Shanghai, Guangzhou


@pytest.mark.asyncio
class TestSortTransform:
    """排序转换测试"""

    async def test_sort_asc(self, sample_data) -> None:
        executor = SortTransformExecutor('st1', {
            'sort_by': [{'field': 'age', 'order': 'asc'}],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        ages = [r['age'] for r in result]
        assert ages == sorted(ages)

    async def test_sort_desc(self, sample_data) -> None:
        executor = SortTransformExecutor('st2', {
            'sort_by': [{'field': 'age', 'order': 'desc'}],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        ages = [r['age'] for r in result]
        assert ages == sorted(ages, reverse=True)

    async def test_sort_by_multiple_fields(self, sample_data) -> None:
        executor = SortTransformExecutor('st3', {
            'sort_by': [
                {'field': 'city', 'order': 'asc'},
                {'field': 'age', 'order': 'desc'},
            ],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        # Beijing first, then Guangzhou, then Shanghai
        assert result[0]['city'] == 'Beijing'
        assert result[0]['age'] == 40  # Beijing排序中age最大的

    async def test_empty_sort(self, sample_data) -> None:
        executor = SortTransformExecutor('st4', {'sort_by': []})
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 6  # 顺序不变


@pytest.mark.asyncio
class TestLimitTransform:
    """限制行数测试"""

    async def test_limit(self, sample_data) -> None:
        executor = LimitTransformExecutor('l1', {'limit': 3})
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 3
        assert result[0]['id'] == 1

    async def test_limit_with_offset(self, sample_data) -> None:
        executor = LimitTransformExecutor('l2', {'limit': 2, 'offset': 2})
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 2
        assert result[0]['id'] == 3

    async def test_limit_exceeds_data(self, sample_data) -> None:
        executor = LimitTransformExecutor('l3', {'limit': 100})
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 6

    async def test_zero_limit(self, sample_data) -> None:
        executor = LimitTransformExecutor('l4', {'limit': 0})
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert result == []


@pytest.mark.asyncio
class TestJoinTransform:
    """连接转换测试"""

    async def test_inner_join(self, sample_orders, sample_users) -> None:
        executor = JoinTransformExecutor('j1', {
            'left_key': 'user_id',
            'right_key': 'id',
            'join_type': 'inner',
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_orders, sample_users)
        # 只有 user_id 1,2,3 存在于 users 中
        assert len(result) == 5  # 所有 orders 都能匹配到 user
        assert 'left_user_id' in result[0] or 'right_id' in result[0]

    async def test_left_join(self, sample_orders, sample_users) -> None:
        executor = JoinTransformExecutor('j2', {
            'left_key': 'user_id',
            'right_key': 'id',
            'join_type': 'left',
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_orders, sample_users)
        # 所有 orders 都保留
        assert len(result) == 5

    async def test_right_join(self, sample_orders, sample_users) -> None:
        executor = JoinTransformExecutor('j3', {
            'left_key': 'user_id',
            'right_key': 'id',
            'join_type': 'right',
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_orders, sample_users)
        # user_id=5 (Eve) 虽无订单但会出现
        assert len(result) == 6

    async def test_single_input(self, sample_data) -> None:
        executor = JoinTransformExecutor('j4', {
            'left_key': 'id',
            'right_key': 'id',
        })
        ctx = ETLContext()
        with pytest.raises(ETLNodeError, match='JOIN 需要两个输入数据集'):
            await executor.execute(ctx, sample_data)

    async def test_custom_prefixes(self, sample_orders, sample_users) -> None:
        executor = JoinTransformExecutor('j5', {
            'left_key': 'user_id',
            'right_key': 'id',
            'join_type': 'inner',
            'left_prefix': 'order_',
            'right_prefix': 'user_',
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_orders, sample_users)
        assert 'order_user_id' in result[0]
        assert 'user_name' in result[0]


@pytest.mark.asyncio
class TestUnionTransform:
    """合并转换测试"""

    async def test_union_two_datasets(self, sample_data) -> None:
        executor = UnionTransformExecutor('u1', {})
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data[:2], sample_data[2:4])
        assert len(result) == 4

    async def test_union_three_datasets(self) -> None:
        executor = UnionTransformExecutor('u2', {})
        ctx = ETLContext()
        result = await executor.execute(ctx, [{'a': 1}], [{'a': 2}], [{'a': 3}])
        assert len(result) == 3

    async def test_union_empty_inputs(self) -> None:
        executor = UnionTransformExecutor('u3', {})
        ctx = ETLContext()
        result = await executor.execute(ctx)
        assert result == []


@pytest.mark.asyncio
class TestUniqueTransform:
    """去重转换测试"""

    async def test_unique_all_fields(self) -> None:
        data = [
            {'id': 1, 'name': 'A'},
            {'id': 2, 'name': 'B'},
            {'id': 1, 'name': 'A'},  # duplicate
            {'id': 3, 'name': 'C'},
        ]
        executor = UniqueTransformExecutor('uq1', {'keys': []})
        ctx = ETLContext()
        result = await executor.execute(ctx, data)
        assert len(result) == 3

    async def test_unique_specific_keys(self) -> None:
        data = [
            {'id': 1, 'city': 'BJ', 'name': 'A'},
            {'id': 2, 'city': 'SH', 'name': 'B'},
            {'id': 3, 'city': 'BJ', 'name': 'C'},  # 仅 city 维度去重，BJ 已存在
        ]
        executor = UniqueTransformExecutor('uq2', {'keys': ['city']})
        ctx = ETLContext()
        result = await executor.execute(ctx, data)
        assert len(result) == 2  # BJ, SH

    async def test_all_duplicates(self) -> None:
        data = [{'id': 1}, {'id': 1}, {'id': 1}]
        executor = UniqueTransformExecutor('uq3', {})
        ctx = ETLContext()
        result = await executor.execute(ctx, data)
        assert len(result) == 1


@pytest.mark.asyncio
class TestFillNullTransform:
    """空值填充测试"""

    async def test_fill_all_nulls(self, sample_data) -> None:
        executor = FillNullTransformExecutor('fn1', {'value': 0})
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        # Frank's salary is None
        frank = [r for r in result if r['name'] == 'Frank'][0]
        assert frank['salary'] == 0

    async def test_fill_specific_column(self, sample_data) -> None:
        executor = FillNullTransformExecutor('fn2', {
            'value': 'Unknown',
            'columns': ['city'],
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 6
        # city has no nulls, salary still None
        frank = [r for r in result if r['name'] == 'Frank'][0]
        assert frank['salary'] is None

    async def test_no_nulls(self) -> None:
        executor = FillNullTransformExecutor('fn3', {'value': 'N/A'})
        ctx = ETLContext()
        result = await executor.execute(ctx, [{'a': 1, 'b': 'x'}])
        assert result[0]['a'] == 1
        assert result[0]['b'] == 'x'


@pytest.mark.asyncio
class TestPythonScriptTransform:
    """Python 脚本转换测试"""

    async def test_simple_transform(self, sample_data) -> None:
        executor = PythonScriptTransformExecutor('ps1', {
            'script': """
result = [{'name': r['name'], 'age_next_year': r['age'] + 1} for r in data]
""",
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 6
        assert result[0]['age_next_year'] == 31

    async def test_filter_in_script(self, sample_data) -> None:
        executor = PythonScriptTransformExecutor('ps2', {
            'script': """
result = [r for r in data if r['age'] > 30]
""",
        })
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert len(result) == 3  # Charlie, Eve, Frank

    async def test_empty_script(self, sample_data) -> None:
        executor = PythonScriptTransformExecutor('ps3', {'script': ''})
        ctx = ETLContext()
        result = await executor.execute(ctx, sample_data)
        assert result == sample_data

    async def test_script_error(self, sample_data) -> None:
        executor = PythonScriptTransformExecutor('ps4', {
            'script': 'result = invalid_var + 1',
        })
        ctx = ETLContext()
        with pytest.raises(ETLNodeError, match='Python 脚本执行失败'):
            await executor.execute(ctx, sample_data)

    async def test_wrong_return_type(self, sample_data) -> None:
        executor = PythonScriptTransformExecutor('ps5', {
            'script': 'result = "not a list"',
        })
        ctx = ETLContext()
        with pytest.raises(ETLNodeError, match='Python 脚本必须返回 list\\[dict\\]'):
            await executor.execute(ctx, sample_data)
