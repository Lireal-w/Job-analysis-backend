# ETL 执行引擎

## 概述

ETL 执行引擎是一个基于 DAG (有向无环图) 的数据处理管道系统，支持从多种数据源提取数据、进行丰富的数据转换、并写入到不同目标。

## 架构

```
POST /api/v1/sys/data-flows/{pk}/run
  └─ DataFlowService.run_flow()
       ├─ 校验数据流状态 (必须已发布)
       ├─ 创建运行记录 (status=running)
       └─ 派发 Celery 异步任务 etl_run_flow
            └─ ETLPipeline.execute()
                 ├─ DAG 拓扑排序 → 分层
                 ├─ 逐层并行执行节点
                 │   ├─ Source 节点 (读取数据)
                 │   ├─ Transform 节点 (转换数据)
                 │   └─ Load 节点 (写入数据)
                 └─ 更新运行记录 (status=success/failed)
```

## 数据流配置格式

数据流的 `nodes` 和 `edges` JSON 字段定义了 ETL 管道的 DAG：

### nodes 格式

```json
[
  {
    "id": "node_1",
    "type": "source_database",
    "label": "从 MySQL 读取",
    "config": { ... }
  },
  {
    "id": "node_2",
    "type": "transform_filter",
    "label": "过滤数据",
    "config": { ... }
  },
  {
    "id": "node_3",
    "type": "load_database",
    "label": "写入 PostgreSQL",
    "config": { ... }
  }
]
```

### edges 格式

```json
[
  { "source": "node_1", "target": "node_2" },
  { "source": "node_2", "target": "node_3" }
]
```

## 节点类型参考

### Source 节点 (数据源)

| 类型 | 说明 | 配置项 |
|------|------|--------|
| `source_database` | 关系型数据库 | `datasource_id`, `query` (SQL) |
| `source_file_csv` | CSV 文件 | `file_path`, `delimiter`, `encoding`, `has_header` |
| `source_file_excel` | Excel 文件 (需 openpyxl) | `file_path`, `sheet_name` |
| `source_file_json` | JSON 文件 | `file_path`, `root_path` |
| `source_file_text` | 文本文件 | `file_path`, `encoding`, `column_name` |
| `source_api` | REST API | `url`, `method`, `headers`, `params`, `body`, `data_path` |

#### source_database 配置示例
```json
{
  "datasource_id": 1,
  "query": "SELECT * FROM orders WHERE status = 'pending'"
}
```

#### source_api 配置示例
```json
{
  "url": "https://api.example.com/users",
  "method": "GET",
  "headers": { "Authorization": "Bearer xxx" },
  "data_path": "data.items"
}
```

### Transform 节点 (数据转换)

| 类型 | 说明 | 配置项 |
|------|------|--------|
| `transform_filter` | 条件过滤 | `conditions`, `logic` (and/or) |
| `transform_select` | 列选择/重命名 | `columns` |
| `transform_map` | 字段映射/计算 | `mappings` |
| `transform_aggregate` | 分组聚合 | `group_by`, `aggregations` |
| `transform_sort` | 排序 | `sort_by` |
| `transform_limit` | 限制行数 | `limit`, `offset` |
| `transform_join` | 数据集连接 | `left_key`, `right_key`, `join_type` |
| `transform_union` | 数据集合并 | 自动合并所有输入 |
| `transform_unique` | 去重 | `keys` |
| `transform_fill_null` | 填充空值 | `value`, `columns` |
| `transform_python_script` | Python 脚本 | `script` |

#### transform_filter 配置示例
```json
{
  "logic": "and",
  "conditions": [
    { "field": "age", "operator": "gt", "value": 18 },
    { "field": "status", "operator": "in", "value": ["active", "pending"] }
  ]
}
```

支持的 operator: `eq`, `ne`, `gt`, `ge`, `lt`, `le`, `in`, `not_in`, `contains`, `startswith`, `endswith`, `regex`

#### transform_aggregate 配置示例
```json
{
  "group_by": ["category"],
  "aggregations": [
    { "column": "amount", "function": "sum", "alias": "total_amount" },
    { "column": "id", "function": "count", "alias": "order_count" },
    { "column": "amount", "function": "avg", "alias": "avg_amount" }
  ]
}
```

支持的 function: `count`, `sum`, `avg`, `min`, `max`, `count_distinct`

#### transform_join 配置示例
```json
{
  "left_key": "user_id",
  "right_key": "id",
  "join_type": "left",
  "left_prefix": "order_",
  "right_prefix": "user_"
}
```

支持 join_type: `inner`, `left`, `right`, `outer`

#### transform_python_script 配置示例
```json
{
  "script": "result = [{'name': r['first'] + ' ' + r['last'], 'full_name_len': len(r['first'] + ' ' + r['last'])} for r in data]"
}
```

脚本中可用变量: `data` (输入数据), `context` (ETLContext), `inputs` (所有输入)
脚本必须设置 `result` 变量为 `list[dict]` 类型。

### Load 节点 (数据写入)

| 类型 | 说明 | 配置项 |
|------|------|--------|
| `load_database` | 写入数据库 | `datasource_id`, `table`, `mode`, `batch_size` |
| `load_file_csv` | 写入 CSV | `file_path`, `encoding` |
| `load_file_json` | 写入 JSON | `file_path`, `indent` |
| `load_file_excel` | 写入 Excel (需 openpyxl) | `file_path`, `sheet_name` |
| `load_log` | 日志输出 (调试用) | `preview_limit` |

#### load_database 配置示例
```json
{
  "datasource_id": 2,
  "table": "processed_orders",
  "mode": "insert",
  "batch_size": 500
}
```

mode 支持: `insert`, `truncate_insert`

## 执行流程

1. **创建数据流**: 配置节点和边 (DAG), 保存为 draft 状态
2. **发布数据流**: draft → published
3. **运行数据流**: POST `/api/v1/sys/data-flows/{pk}/run`
   - 同步返回 `{ run_id, flow_id, status: "running", record_id }`
   - 引擎异步执行, 结果更新到 `sys_data_flow_run` 表
4. **查看运行记录**: GET `/api/v1/sys/data-flows/{pk}/runs`
5. **查看运行详情**: GET `/api/v1/sys/data-flows/runs/{run_id}`

## 扩展

### 注册自定义节点执行器

```python
from backend.app.admin.service.etl.registry import register_node_executor
from backend.app.admin.service.etl.nodes.base import BaseNodeExecutor

class MyCustomExecutor(BaseNodeExecutor):
    node_type = 'transform_my_custom'

    async def execute(self, context, *inputs):
        # 自定义逻辑
        return result

register_node_executor('transform_my_custom', MyCustomExecutor)
```
