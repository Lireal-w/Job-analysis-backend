"""数据转换节点执行器

支持的转换类型：
- filter: 按条件过滤行
- select: 选择/重命名列
- map: 列映射与表达式计算
- aggregate: 分组聚合
- sort: 排序
- limit: 限制行数
- join: 连接两个数据集
- union: 合并两个数据集
- python_script: 自定义 Python 脚本转换
"""

from __future__ import annotations

import copy
import operator
from typing import Any

from backend.app.admin.service.etl.context import ETLContext
from backend.app.admin.service.etl.exceptions import ETLDataError, ETLNodeError
from backend.app.admin.service.etl.nodes.base import BaseNodeExecutor

# 比较操作符映射
_COMPARATORS = {
    'eq': operator.eq,
    'ne': operator.ne,
    'gt': operator.gt,
    'ge': operator.ge,
    'lt': operator.lt,
    'le': operator.le,
    'in': lambda a, b: a in b,
    'not_in': lambda a, b: a not in b,
    'contains': lambda a, b: b in str(a),
    'startswith': lambda a, b: str(a).startswith(b),
    'endswith': lambda a, b: str(a).endswith(b),
    'regex': lambda a, b: __import__('re').search(b, str(a)) is not None,
}

# 聚合函数映射
_AGGREGATORS = {
    'count': lambda col, rows: len(rows),
    'sum': lambda col, rows: sum(r.get(col, 0) or 0 for r in rows),
    'avg': lambda col, rows: (sum(r.get(col, 0) or 0 for r in rows) / len(rows)) if rows else 0,
    'min': lambda col, rows: min(r.get(col) for r in rows if r.get(col) is not None),
    'max': lambda col, rows: max(r.get(col) for r in rows if r.get(col) is not None),
    'count_distinct': lambda col, rows: len({r.get(col) for r in rows}),
}


class FilterTransformExecutor(BaseNodeExecutor):
    """过滤转换 - 按条件筛选行"""

    node_type = 'transform_filter'

    def _evaluate_condition(self, row: dict[str, Any], condition: dict[str, Any]) -> bool:
        field = condition.get('field', '')
        op = condition.get('operator', 'eq')
        value = condition.get('value')

        actual_value = row.get(field)
        compare_fn = _COMPARATORS.get(op)
        if compare_fn is None:
            self.raise_error(f'不支持的操作符: {op}')

        try:
            return compare_fn(actual_value, value)
        except Exception as e:
            return False

    def _evaluate_group(self, row: dict[str, Any], group: dict[str, Any]) -> bool:
        logic = group.get('logic', 'and').upper()
        conditions = group.get('conditions', [])

        results = [self._evaluate_condition(row, c) for c in conditions]

        if logic == 'AND':
            return all(results)
        elif logic == 'OR':
            return any(results)
        else:
            return True

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        if not inputs or not inputs[0]:
            return []

        data = inputs[0]
        conditions = self.config.get('conditions', [])
        logic = self.config.get('logic', 'and').upper()

        if not conditions:
            return data

        filtered = []
        for row in data:
            results = [self._evaluate_condition(row, c) for c in conditions]
            if logic == 'AND' and all(results):
                filtered.append(row)
            elif logic == 'OR' and any(results):
                filtered.append(row)

        context.metrics[f'node_{self.node_id}_input'] = len(data)
        context.metrics[f'node_{self.node_id}_output'] = len(filtered)
        return filtered


class SelectTransformExecutor(BaseNodeExecutor):
    """选择/重命名列"""

    node_type = 'transform_select'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        if not inputs or not inputs[0]:
            return []

        data = inputs[0]
        columns = self.config.get('columns', [])

        if not columns:
            return list(data)

        result = []
        for row in data:
            new_row = {}
            for col in columns:
                if isinstance(col, dict):
                    source = col.get('source', '')
                    target = col.get('target', source)
                    new_row[target] = row.get(source)
                else:
                    new_row[col] = row.get(col)
            result.append(new_row)

        return result


class MapTransformExecutor(BaseNodeExecutor):
    """字段映射 / 表达式计算"""

    node_type = 'transform_map'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        if not inputs or not inputs[0]:
            return []

        data = inputs[0]
        mappings = self.config.get('mappings', [])

        result = []
        for row in data:
            new_row = dict(row)
            for mapping in mappings:
                target = mapping.get('target', '')
                expression = mapping.get('expression', '')
                default = mapping.get('default', None)

                try:
                    # 简单替换: {{field_name}} → 字段值
                    resolved = expression
                    for key, val in row.items():
                        placeholder = '{{' + key + '}}'
                        if placeholder in resolved:
                            val_str = str(val) if val is not None else ''
                            resolved = resolved.replace(placeholder, val_str)

                    # 尝试数值计算
                    try:
                        new_row[target] = eval(resolved, {'__builtins__': {}}, dict(row))
                    except Exception:
                        new_row[target] = resolved
                except Exception:
                    new_row[target] = default

            result.append(new_row)

        return result


class AggregateTransformExecutor(BaseNodeExecutor):
    """分组聚合"""

    node_type = 'transform_aggregate'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        if not inputs or not inputs[0]:
            return []

        data = inputs[0]
        group_by = self.config.get('group_by', [])
        aggregations = self.config.get('aggregations', [])

        if not group_by:
            # 全表聚合
            row = {}
            for agg in aggregations:
                col = agg.get('column', '')
                func = agg.get('function', 'count')
                alias = agg.get('alias', f'{func}_{col}')
                fn = _AGGREGATORS.get(func)
                if fn:
                    row[alias] = fn(col, data)
            return [row]

        # 分组聚合
        groups: dict[str, list[dict[str, Any]]] = {}
        for row in data:
            key = tuple(str(row.get(g, '')) for g in group_by)
            if key not in groups:
                groups[key] = []
            groups[key].append(row)

        result = []
        for key, group_rows in groups.items():
            row = dict(zip(group_by, key))
            for agg in aggregations:
                col = agg.get('column', '')
                func = agg.get('function', 'count')
                alias = agg.get('alias', f'{func}_{col}')
                fn = _AGGREGATORS.get(func)
                if fn:
                    row[alias] = fn(col, group_rows)
            result.append(row)

        return result


class SortTransformExecutor(BaseNodeExecutor):
    """排序"""

    node_type = 'transform_sort'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        if not inputs or not inputs[0]:
            return []

        data = list(inputs[0])
        sort_by = self.config.get('sort_by', [])

        if not sort_by:
            return data

        import functools

        def _compare(a: dict[str, Any], b: dict[str, Any]) -> int:
            for s in sort_by:
                field = s.get('field', '')
                order = s.get('order', 'asc').lower()
                va = a.get(field)
                vb = b.get(field)

                if va is None and vb is None:
                    continue
                if va is None:
                    return 1 if order == 'asc' else -1
                if vb is None:
                    return -1 if order == 'asc' else 1

                try:
                    if va < vb:
                        return -1 if order == 'asc' else 1
                    if va > vb:
                        return 1 if order == 'asc' else -1
                except TypeError:
                    va_str, vb_str = str(va), str(vb)
                    if va_str < vb_str:
                        return -1 if order == 'asc' else 1
                    if va_str > vb_str:
                        return 1 if order == 'asc' else -1
            return 0

        data.sort(key=functools.cmp_to_key(_compare))
        return data


class LimitTransformExecutor(BaseNodeExecutor):
    """限制行数 / 分页"""

    node_type = 'transform_limit'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        if not inputs or not inputs[0]:
            return []

        data = inputs[0]
        limit = self.config.get('limit', 100)
        offset = self.config.get('offset', 0)

        return data[offset:offset + limit]


class JoinTransformExecutor(BaseNodeExecutor):
    """连接两个数据集"""

    node_type = 'transform_join'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        if len(inputs) < 2:
            self.raise_error('JOIN 需要两个输入数据集')

        left = inputs[0]
        right = inputs[1]
        join_type = self.config.get('join_type', 'inner').lower()
        left_key = self.config.get('left_key', '')
        right_key = self.config.get('right_key', left_key)
        left_prefix = self.config.get('left_prefix', 'left_')
        right_prefix = self.config.get('right_prefix', 'right_')

        # 构建右表索引
        right_index: dict[Any, list[dict[str, Any]]] = {}
        for row in right:
            key = row.get(right_key)
            if key is not None:
                right_index.setdefault(key, []).append(row)

        result = []
        for lrow in left:
            lkey = lrow.get(left_key)
            matched = right_index.get(lkey, []) if lkey is not None else []

            if matched:
                for rrow in matched:
                    merged = {}
                    for k, v in lrow.items():
                        merged[f'{left_prefix}{k}'] = v
                    for k, v in rrow.items():
                        merged[f'{right_prefix}{k}'] = v
                    result.append(merged)
            elif join_type in ('left', 'outer'):
                merged = {}
                for k, v in lrow.items():
                    merged[f'{left_prefix}{k}'] = v
                for k in right[0] if right else []:
                    merged[f'{right_prefix}{k}'] = None
                result.append(merged)

        if join_type in ('right', 'outer'):
            right_keys = {r.get(right_key) for r in right}
            left_keys = {r.get(left_key) for r in left}
            for rkey in right_keys:
                if rkey is None or rkey in left_keys:
                    continue
                for rrow in right_index.get(rkey, []):
                    merged = {}
                    for k in left[0] if left else []:
                        merged[f'{left_prefix}{k}'] = None
                    for k, v in rrow.items():
                        merged[f'{right_prefix}{k}'] = v
                    result.append(merged)

        return result


class UnionTransformExecutor(BaseNodeExecutor):
    """合并多个数据集 (Union)"""

    node_type = 'transform_union'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        if not inputs:
            return []

        result = []
        for data in inputs:
            result.extend(data)

        return result


class PythonScriptTransformExecutor(BaseNodeExecutor):
    """Python 脚本转换（安全沙箱模式）

    在受限环境中执行用户自定义 Python 脚本，禁止访问危险模块和函数。

    安全措施：
    - 禁止导入危险模块（os, sys, subprocess, socket 等）
    - 禁止使用危险内置函数（exec, eval, compile, open 等）
    - 设置执行超时（默认 30 秒）
    - 限制可用内置函数为安全子集
    """

    node_type = 'transform_python_script'

    # 禁止导入的模块
    FORBIDDEN_MODULES = frozenset({
        'os', 'sys', 'subprocess', 'socket', 'shutil', 'pathlib',
        'ctypes', 'signal', 'multiprocessing', 'threading',
        'importlib', 'pkgutil', 'code', 'codeop', 'compileall',
        'pickle', 'shelve', 'marshal', 'tempfile',
        'http', 'urllib', 'requests', 'aiohttp', 'httpx',
        'ftplib', 'smtplib', 'telnetlib', 'xmlrpc',
        'asyncio', 'concurrent', 'queue',
    })

    # 禁止使用的内置函数
    FORBIDDEN_BUILTINS = frozenset({
        'exec', 'eval', 'compile', 'open', 'input',
        'globals', 'locals', 'vars', 'dir',
        'getattr', 'setattr', 'delattr', 'type',
        '__import__', 'breakpoint', 'exit', 'quit',
    })

    # 允许的安全内置函数
    SAFE_BUILTINS = {
        'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool,
        'chr': chr, 'dict': dict, 'divmod': divmod, 'enumerate': enumerate,
        'filter': filter, 'float': float, 'format': format, 'frozenset': frozenset,
        'hash': hash, 'hex': hex, 'int': int, 'isinstance': isinstance,
        'issubclass': issubclass, 'iter': iter, 'len': len, 'list': list,
        'map': map, 'max': max, 'min': min, 'next': next, 'oct': oct,
        'ord': ord, 'pow': pow, 'print': print, 'range': range, 'repr': repr,
        'reversed': reversed, 'round': round, 'set': set, 'slice': slice,
        'sorted': sorted, 'str': str, 'sum': sum, 'tuple': tuple, 'zip': zip,
        'True': True, 'False': False, 'None': None,
    }

    # 允许的安全模块
    ALLOWED_MODULES = frozenset({
        'json', 'math', 're', 'datetime', 'decimal',
        'collections', 'itertools', 'functools', 'statistics', 'copy',
        # 内部辅助模块（被允许模块内部引用）
        '_strptime', '_decimal', '_json', 'operator',
    })

    # 执行超时（秒）
    EXECUTION_TIMEOUT = 30

    def _validate_script_safety(self, script: str) -> None:
        """验证脚本安全性

        检查脚本是否包含禁止的模块导入或函数调用。
        """
        import re

        # 检查 import 语句
        import_pattern = r'(?:^|\n)\s*(?:import\s+(\w+)|from\s+(\w+)\s+import)'
        for match in re.finditer(import_pattern, script):
            module_name = match.group(1) or match.group(2)
            if module_name in self.FORBIDDEN_MODULES:
                self.raise_error(f'安全限制：禁止导入模块 "{module_name}"')

        # 检查 __import__ 调用
        if '__import__' in script:
            self.raise_error('安全限制：禁止使用 __import__')

        # 检查危险内置函数调用
        for func_name in self.FORBIDDEN_BUILTINS:
            # 使用单词边界匹配，避免误判（如 executable 包含 exec）
            pattern = rf'\b{func_name}\b'
            if re.search(pattern, script):
                # 排除字符串中的引用（简单检查）
                self.raise_error(f'安全限制：禁止使用函数 "{func_name}"')

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        data = inputs[0] if inputs and inputs[0] else []
        script = self.config.get('script', '')

        if not script:
            return data

        # 验证脚本安全性
        self._validate_script_safety(script)

        # 构建安全的执行环境
        safe_builtins = dict(self.SAFE_BUILTINS)
        local_vars = {
            'data': data,
            'context': context,
            'inputs': inputs,
            '__builtins__': safe_builtins,
            # 允许的安全模块
            'json': __import__('json'),
            'math': __import__('math'),
            're': __import__('re'),
            'datetime': __import__('datetime'),
            'decimal': __import__('decimal'),
            'collections': __import__('collections'),
            'itertools': __import__('itertools'),
            'functools': __import__('functools'),
            'statistics': __import__('statistics'),
            'copy': __import__('copy'),
        }

        try:
            # 使用 asyncio 超时控制
            import asyncio
            result = await asyncio.wait_for(
                self._run_script(script, local_vars),
                timeout=self.EXECUTION_TIMEOUT,
            )
            if not isinstance(result, list):
                self.raise_error('Python 脚本必须返回 list[dict] 类型')
            return result
        except asyncio.TimeoutError:
            self.raise_error(f'Python 脚本执行超时（{self.EXECUTION_TIMEOUT}秒）')
        except Exception as e:
            self.raise_error(f'Python 脚本执行失败: {e}')

    async def _run_script(self, script: str, local_vars: dict) -> list[dict[str, Any]]:
        """在安全环境中执行脚本"""
        # 提供受限的 __import__ 函数，只允许导入允许的模块
        def _safe_import(name, *args, **kwargs):
            if name in self.ALLOWED_MODULES:
                return __import__(name, *args, **kwargs)
            raise ImportError(f'安全限制：禁止导入模块 "{name}"')

        local_vars['__builtins__']['__import__'] = _safe_import
        exec(script, local_vars)
        return local_vars.get('result', local_vars.get('data', []))


class UniqueTransformExecutor(BaseNodeExecutor):
    """去重"""

    node_type = 'transform_unique'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        if not inputs or not inputs[0]:
            return []

        data = inputs[0]
        keys = self.config.get('keys', [])

        if not keys:
            # 全字段去重
            seen = set()
            result = []
            for row in data:
                key = tuple(str(row.get(k, '')) for k in sorted(row.keys()))
                if key not in seen:
                    seen.add(key)
                    result.append(row)
            return result

        seen = set()
        result = []
        for row in data:
            key = tuple(str(row.get(k, '')) for k in keys)
            if key not in seen:
                seen.add(key)
                result.append(row)

        return result


class FillNullTransformExecutor(BaseNodeExecutor):
    """填充空值"""

    node_type = 'transform_fill_null'

    async def execute(self, context: ETLContext, *inputs: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        if not inputs or not inputs[0]:
            return []

        data = inputs[0]
        fill_value = self.config.get('value', '')
        columns = self.config.get('columns', [])  # 空列表表示所有列

        result = []
        for row in data:
            new_row = dict(row)
            for k in new_row:
                if new_row[k] is None:
                    if not columns or k in columns:
                        new_row[k] = fill_value
            result.append(new_row)

        return result
