# 采集任务执行引擎

## 概述

采集任务执行引擎提供完整的数据采集能力，支持从多种数据源读取数据并写入目标存储。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    CrawlExecutor (核心引擎)                    │
│                                                             │
│  ┌──────────┐   ┌──────────────┐   ┌──────────────┐       │
│  │  Source   │──▶│  Incremental │──▶│   Transform   │       │
│  │  Reader   │   │    Filter    │   │   (可选)      │       │
│  └──────────┘   └──────────────┘   └──────────────┘       │
│                                            │                │
│                                            ▼                │
│                                     ┌──────────────┐       │
│                                     │    Target     │       │
│                                     │    Writer     │       │
│                                     └──────────────┘       │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  CrawlContext (执行上下文: 统计/指标/增量状态/错误)    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 支持的数据源

| 类型 | 说明 | 配置参数 |
|------|------|----------|
| `database` | 关系型数据库 | `datasource_id`, `query`, `query_params` |
| `api` | REST API | `url`, `method`, `headers`, `params`, `body`, `data_path`, `pagination` |
| `file_csv` | CSV 文件 | `file_path`, `delimiter`, `encoding`, `has_header` |
| `file_excel` | Excel 文件 | `file_path`, `sheet_name` |
| `file_json` | JSON 文件 | `file_path`, `root_path` |
| `mongodb` | MongoDB | `datasource_id`, `collection`, `filter`, `projection`, `sort`, `limit` |

## 支持的目标存储

| 类型 | 说明 | 配置参数 |
|------|------|----------|
| `database` | 关系型数据库 | `datasource_id`, `table`, `mode`(insert/upsert/truncate_insert), `batch_size`, `on_conflict` |
| `file_csv` | CSV 文件 | `file_path`, `encoding`, `mode`(write/append) |
| `file_json` | JSON 文件 | `file_path`, `indent`, `mode`(write/append) |
| `file_excel` | Excel 文件 | `file_path`, `sheet_name` |
| `mongodb` | MongoDB | `datasource_id`, `collection`, `mode`(insert/upsert), `upsert_key`, `batch_size` |

## 采集模式

### 全量采集 (full)
读取源数据的所有记录并写入目标。

### 增量采集 (incremental)
只采集增量键值大于上次采集最大值的记录：
- `incremental_key`: 增量字段名（如 `updated_time`、`id`）
- `incremental_start`: 增量起始值（上次采集的最大值）
- 采集完成后自动更新 `incremental_start` 为本次最大值

## 数据转换

通过 `source_config.transform` 配置简单的数据转换：

```json
{
  "type": "database",
  "datasource_id": 1,
  "query": "SELECT * FROM users",
  "transform": {
    "field_mapping": {"old_name": "new_name"},
    "select_fields": ["id", "name", "email"],
    "filter_fields": ["password", "secret"]
  }
}
```

## 重试机制

- `retry_enabled`: 是否启用重试
- `max_retries`: 最大重试次数
- `retry_delay`: 重试间隔(秒)
- `retry_backoff`: 是否启用指数退避策略

## 执行流程

1. **Celery 任务触发** → `crawl_task_execute` 或 `crawl_task_scheduled`
2. **创建 CrawlExecutor** → 根据配置初始化读取器和写入器
3. **读取数据** → 从源数据源读取（带重试）
4. **增量过滤** → 增量模式下过滤已采集数据
5. **数据转换** → 应用字段映射和过滤
6. **批量写入** → 分批写入目标存储（带重试和速率限制）
7. **更新统计** → 更新运行日志和任务统计