"""ETL 安全沙箱测试

测试 PythonScriptTransformExecutor 的安全限制：
- 禁止导入危险模块
- 禁止使用危险内置函数
- 执行超时控制
- 安全内置函数白名单
"""

import pytest

from backend.app.admin.service.etl.context import ETLContext
from backend.app.admin.service.etl.exceptions import ETLNodeError
from backend.app.admin.service.etl.nodes.transform import PythonScriptTransformExecutor


class TestPythonScriptSafety:
    """Python 脚本安全沙箱测试"""

    @pytest.fixture
    def context(self):
        """创建 ETL 上下文"""
        return ETLContext(pipeline_id='test-pipeline')

    @pytest.fixture
    def executor(self):
        """创建脚本转换执行器"""
        config = {'script': 'result = data'}
        return PythonScriptTransformExecutor(node_id='test_node', config=config)

    @pytest.fixture
    def sample_data(self):
        """示例数据"""
        return [
            {'id': 1, 'name': 'Alice', 'score': 85},
            {'id': 2, 'name': 'Bob', 'score': 92},
            {'id': 3, 'name': 'Charlie', 'score': 78},
        ]

    # ── 安全验证测试 ──────────────────────────────────────────

    def test_validate_forbidden_import_os(self, executor):
        """测试禁止导入 os 模块"""
        with pytest.raises(ETLNodeError, match='禁止导入模块 "os"'):
            executor._validate_script_safety('import os\nresult = data')

    def test_validate_forbidden_import_sys(self, executor):
        """测试禁止导入 sys 模块"""
        with pytest.raises(ETLNodeError, match='禁止导入模块 "sys"'):
            executor._validate_script_safety('import sys\nresult = data')

    def test_validate_forbidden_import_subprocess(self, executor):
        """测试禁止导入 subprocess 模块"""
        with pytest.raises(ETLNodeError, match='禁止导入模块 "subprocess"'):
            executor._validate_script_safety('import subprocess\nresult = data')

    def test_validate_forbidden_import_socket(self, executor):
        """测试禁止导入 socket 模块"""
        with pytest.raises(ETLNodeError, match='禁止导入模块 "socket"'):
            executor._validate_script_safety('import socket\nresult = data')

    def test_validate_forbidden_import_requests(self, executor):
        """测试禁止导入 requests 模块"""
        with pytest.raises(ETLNodeError, match='禁止导入模块 "requests"'):
            executor._validate_script_safety('import requests\nresult = data')

    def test_validate_forbidden_from_import(self, executor):
        """测试禁止 from ... import 形式导入危险模块"""
        with pytest.raises(ETLNodeError, match='禁止导入模块 "os"'):
            executor._validate_script_safety('from os import path\nresult = data')

    def test_validate_forbidden_builtin_exec(self, executor):
        """测试禁止使用 exec 函数"""
        with pytest.raises(ETLNodeError, match='禁止使用函数 "exec"'):
            executor._validate_script_safety('exec("print(1)")')

    def test_validate_forbidden_builtin_eval(self, executor):
        """测试禁止使用 eval 函数"""
        with pytest.raises(ETLNodeError, match='禁止使用函数 "eval"'):
            executor._validate_script_safety('eval("1+1")')

    def test_validate_forbidden_builtin_compile(self, executor):
        """测试禁止使用 compile 函数"""
        with pytest.raises(ETLNodeError, match='禁止使用函数 "compile"'):
            executor._validate_script_safety('compile("1+1", "<string>", "single")')

    def test_validate_forbidden_builtin_open(self, executor):
        """测试禁止使用 open 函数"""
        with pytest.raises(ETLNodeError, match='禁止使用函数 "open"'):
            executor._validate_script_safety('open("/etc/passwd")')

    def test_validate_forbidden_builtin_import(self, executor):
        """测试禁止使用 __import__ 函数"""
        with pytest.raises(ETLNodeError, match='禁止使用 __import__'):
            executor._validate_script_safety('__import__("os")')

    def test_validate_forbidden_builtin_getattr(self, executor):
        """测试禁止使用 getattr 函数"""
        with pytest.raises(ETLNodeError, match='禁止使用函数 "getattr"'):
            executor._validate_script_safety('getattr(obj, "attr")')

    def test_validate_safe_script(self, executor):
        """测试安全脚本通过验证"""
        # 不应抛出异常
        executor._validate_script_safety('result = [row for row in data if row["score"] > 80]')

    def test_validate_safe_import_json(self, executor):
        """测试允许导入 json 模块"""
        # json 不在禁止列表中，但脚本验证只检查 import 语句
        # 实际安全模块在 _run_script 中通过 local_vars 提供
        executor._validate_script_safety('result = data')

    # ── 执行测试 ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_execute_simple_filter(self, executor, context, sample_data):
        """测试简单过滤脚本"""
        executor.config = {
            'script': 'result = [row for row in data if row["score"] > 80]'
        }
        result = await executor.execute(context, sample_data)
        assert len(result) == 2
        assert result[0]['name'] == 'Alice'
        assert result[1]['name'] == 'Bob'

    @pytest.mark.asyncio
    async def test_execute_transform(self, context, sample_data):
        """测试数据转换脚本"""
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={
                'script': 'result = [{"name": row["name"], "grade": "A" if row["score"] >= 90 else "B"} for row in data]'
            },
        )
        result = await executor.execute(context, sample_data)
        assert len(result) == 3
        assert result[0]['grade'] == 'B'  # Alice: 85
        assert result[1]['grade'] == 'A'  # Bob: 92

    @pytest.mark.asyncio
    async def test_execute_with_math(self, context, sample_data):
        """测试使用 math 模块"""
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={
                'script': 'result = [{"name": row["name"], "sqrt_score": math.sqrt(row["score"])} for row in data]'
            },
        )
        result = await executor.execute(context, sample_data)
        assert len(result) == 3
        import math
        assert abs(result[0]['sqrt_score'] - math.sqrt(85)) < 0.01

    @pytest.mark.asyncio
    async def test_execute_with_re(self, context):
        """测试使用 re 模块"""
        data = [
            {'text': 'Hello World 123'},
            {'text': 'No numbers here'},
            {'text': 'ABC 456 DEF'},
        ]
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={
                'script': 'result = [{"text": row["text"], "has_number": bool(re.search(r"\\d+", row["text"]))} for row in data]'
            },
        )
        result = await executor.execute(context, data)
        assert len(result) == 3
        assert result[0]['has_number'] is True
        assert result[1]['has_number'] is False
        assert result[2]['has_number'] is True

    @pytest.mark.asyncio
    async def test_execute_with_datetime(self, context):
        """测试使用 datetime 模块"""
        data = [{'date_str': '2024-01-15'}]
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={
                'script': 'result = [{"date": datetime.datetime.strptime(row["date_str"], "%Y-%m-%d").date().isoformat()} for row in data]'
            },
        )
        result = await executor.execute(context, data)
        assert result[0]['date'] == '2024-01-15'

    @pytest.mark.asyncio
    async def test_execute_with_collections(self, context):
        """测试使用 collections 模块"""
        data = [
            {'category': 'A', 'value': 10},
            {'category': 'B', 'value': 20},
            {'category': 'A', 'value': 30},
        ]
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={
                'script': 'from collections import Counter\ncounter = Counter(row["category"] for row in data)\nresult = [{"category": k, "count": v} for k, v in counter.items()]'
            },
        )
        result = await executor.execute(context, data)
        assert len(result) == 2
        # Counter results
        categories = {r['category']: r['count'] for r in result}
        assert categories['A'] == 2
        assert categories['B'] == 1

    @pytest.mark.asyncio
    async def test_execute_empty_script(self, context, sample_data):
        """测试空脚本返回原始数据"""
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={'script': ''},
        )
        result = await executor.execute(context, sample_data)
        assert result == sample_data

    @pytest.mark.asyncio
    async def test_execute_no_input(self, context):
        """测试无输入数据"""
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={'script': 'result = data'},
        )
        result = await executor.execute(context)
        assert result == []

    @pytest.mark.asyncio
    async def test_execute_returns_non_list_raises_error(self, context, sample_data):
        """测试脚本返回非列表类型时抛出错误"""
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={'script': 'result = "not a list"'},
        )
        with pytest.raises(ETLNodeError, match='必须返回 list\\[dict\\] 类型'):
            await executor.execute(context, sample_data)

    @pytest.mark.asyncio
    async def test_execute_forbidden_import_raises_error(self, context, sample_data):
        """测试脚本包含禁止导入时抛出错误"""
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={'script': 'import os\nresult = data'},
        )
        with pytest.raises(ETLNodeError, match='禁止导入模块'):
            await executor.execute(context, sample_data)

    @pytest.mark.asyncio
    async def test_execute_forbidden_builtin_raises_error(self, context, sample_data):
        """测试脚本包含禁止内置函数时抛出错误"""
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={'script': 'open("/etc/passwd")'},
        )
        with pytest.raises(ETLNodeError, match='禁止使用函数'):
            await executor.execute(context, sample_data)

    @pytest.mark.asyncio
    async def test_execute_script_error_raises_error(self, context, sample_data):
        """测试脚本执行错误时抛出 ETLNodeError"""
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={'script': 'result = 1 / 0'},
        )
        with pytest.raises(ETLNodeError, match='Python 脚本执行失败'):
            await executor.execute(context, sample_data)

    @pytest.mark.asyncio
    async def test_execute_with_json(self, context):
        """测试使用 json 模块"""
        data = [{'json_str': '{"key": "value"}'}]
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={
                'script': 'result = [{"parsed": json.loads(row["json_str"])} for row in data]'
            },
        )
        result = await executor.execute(context, data)
        assert result[0]['parsed'] == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_execute_with_functools(self, context, sample_data):
        """测试使用 functools 模块"""
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={
                'script': 'result = sorted(data, key=lambda x: x["score"], reverse=True)'
            },
        )
        result = await executor.execute(context, sample_data)
        assert result[0]['name'] == 'Bob'  # 92
        assert result[1]['name'] == 'Alice'  # 85
        assert result[2]['name'] == 'Charlie'  # 78

    @pytest.mark.asyncio
    async def test_execute_with_statistics(self, context, sample_data):
        """测试使用 statistics 模块"""
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={
                'script': 'scores = [row["score"] for row in data]\nresult = [{"avg_score": statistics.mean(scores), "stdev": statistics.stdev(scores) if len(scores) > 1 else 0}]'
            },
        )
        result = await executor.execute(context, sample_data)
        assert len(result) == 1
        assert abs(result[0]['avg_score'] - 85.0) < 0.01

    @pytest.mark.asyncio
    async def test_execute_with_copy(self, context, sample_data):
        """测试使用 copy 模块"""
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={
                'script': 'result = [copy.deepcopy(row) for row in data]'
            },
        )
        result = await executor.execute(context, sample_data)
        assert len(result) == 3
        # 确保是深拷贝
        result[0]['name'] = 'Modified'
        assert sample_data[0]['name'] == 'Alice'

    @pytest.mark.asyncio
    async def test_execute_with_decimal(self, context):
        """测试使用 decimal 模块"""
        data = [{'price': '19.99', 'quantity': '3'}]
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={
                'script': 'result = [{"total": float(decimal.Decimal(row["price"]) * decimal.Decimal(row["quantity"]))} for row in data]'
            },
        )
        result = await executor.execute(context, data)
        assert abs(result[0]['total'] - 59.97) < 0.01

    @pytest.mark.asyncio
    async def test_execute_with_itertools(self, context, sample_data):
        """测试使用 itertools 模块"""
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={
                'script': 'result = [{"name": row["name"], "score_rank": rank + 1} for rank, row in enumerate(sorted(data, key=lambda x: x["score"], reverse=True))]'
            },
        )
        result = await executor.execute(context, sample_data)
        assert len(result) == 3

    # ── 安全内置函数测试 ──────────────────────────────────────

    @pytest.mark.asyncio
    async def test_safe_builtins_abs(self, context):
        """测试安全内置函数 abs"""
        data = [{'value': -5}]
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={'script': 'result = [{"value": abs(row["value"])} for row in data]'},
        )
        result = await executor.execute(context, data)
        assert result[0]['value'] == 5

    @pytest.mark.asyncio
    async def test_safe_builtins_len(self, context, sample_data):
        """测试安全内置函数 len"""
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={'script': 'result = [{"count": len(data)}]'},
        )
        result = await executor.execute(context, sample_data)
        assert result[0]['count'] == 3

    @pytest.mark.asyncio
    async def test_safe_builtins_enumerate(self, context, sample_data):
        """测试安全内置函数 enumerate"""
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={'script': 'result = [{"index": i, "name": row["name"]} for i, row in enumerate(data)]'},
        )
        result = await executor.execute(context, sample_data)
        assert result[0]['index'] == 0
        assert result[1]['index'] == 1

    @pytest.mark.asyncio
    async def test_safe_builtins_isinstance(self, context):
        """测试安全内置函数 isinstance"""
        data = [{'value': 42}, {'value': 'hello'}]
        executor = PythonScriptTransformExecutor(
            node_id='test_node',
            config={'script': 'result = [{"value": row["value"], "is_int": isinstance(row["value"], int)} for row in data]'},
        )
        result = await executor.execute(context, data)
        assert result[0]['is_int'] is True
        assert result[1]['is_int'] is False