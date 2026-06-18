# 项目差距分析与优化建议

> 基于蓝图 v1.0 与当前代码的对比分析 | 2026-06-18

---

## 📊 模块实现深度总览

| 模块 | 实现深度 | 蓝图对应 | 说明 |
|------|----------|----------|------|
| 数据源管理 | ✅ FULL | M1-3 | 支持 20+ 种数据源类型，连接测试完整 |
| 采集任务 | ✅ FULL | M1-4 | CrawlExecutor 完整实现，6 种源/5 种目标 |
| ETL/数据流 | ✅ FULL | M2-1 | DAG 引擎 + 22 种节点类型 |
| 权限系统 | ✅ FULL | M4-1 | RBAC + 数据权限 + Casbin 插件 |
| 插件系统 | ✅ FULL | M5-3 | 插件校验/配置/热加载架构完备 |
| **数据质量** | ✅ FULL | M2-3 | 5 种规则执行器 + 告警联动 + 27 测试 |
| **告警模块** | ✅ FULL | M4-4 | 评估引擎 + 4 渠道通知 + 去重抑制 + 36 测试 |
| **查询引擎** | ✅ FULL | M1-6 | 真实 SQL 执行 + 注入防护 + 缓存 + 44 测试 |
| 报表/可视化 | ⚠️ PARTIAL | M3-2/3 | CRUD 完整，数据绑定为 mock |
| 实时/流处理 | ⚠️ PARTIAL | M3-4 | Socket.IO 基础在，流计算引擎缺失 |

---

## 🔴 P0 - 关键缺失（蓝图核心功能未实现）

### P0-1: 数据质量规则引擎 ✅ 已实现

**实现内容**：
- `QualityRuleExecutor`：5 种规则执行器（not_null, unique, range, regex, custom_sql）
- 规则执行器注册表模式，支持扩展
- 与数据源连接集成，支持跨数据库检查
- SQL 注入防护（custom_sql 禁止 DDL/DML）
- 检查结果写入 `sys_data_quality_log`
- 质量检查完成后自动触发告警
- 27 个单元测试全部通过

**蓝图对应**：M2-3

### P0-2: 告警触发与通知引擎 ✅ 已实现

**实现内容**：
- `AlertEvaluator`：告警规则评估引擎
  - 支持 5 种条件（gt/lt/eq/gte/lte）
  - 支持 6 种指标类型（cpu/memory/disk/task_success/task_delay/data_quality）
  - 告警去重与抑制（同一规则恢复前不重复告警）
  - 自动恢复检测（指标正常时标记 firing → resolved）
- `NotificationDispatcher`：4 渠道通知
  - 邮件通知（复用 `plugin/email`，支持告警模板）
  - Webhook 通知（兼容钉钉/企微/Slack 格式）
  - SocketIO 实时推送
  - SMS 短信（预留接口）
- 类型安全枚举（AlertMetricType, AlertCondition, AlertSeverity, AlertStatus, NotifyChannel）
- API 端点：`POST /rules/{pk}/evaluate` 和 `POST /rules/evaluate-all`
- 数据质量检查与告警联动
- 36 个单元测试全部通过

**蓝图对应**：M4-4

### P0-3: 查询引擎（真实 SQL 执行） ✅ 已实现

**实现内容**：
- `QueryEngine`：真实 SQL 查询执行引擎
  - 从 `sys_datasource` 获取连接参数，支持 MySQL/PostgreSQL/SQLite/MSSQL/Oracle/ClickHouse/Elasticsearch
  - SQL 注入防护（只允许 SELECT，禁止 DDL/DML/多语句注入）
  - 查询超时控制（默认 30 秒）
  - 结果行数限制（默认 10000 行）
  - Redis 查询结果缓存（5 分钟 TTL，小结果集自动缓存）
  - 可视化查询配置转 SQL
  - 数据源表结构查询（`get_datasource_schema`）
- `query_service.py` 完整重写，替换模拟数据为真实执行
- API 端点：`GET /schema/{dataset_id}` 获取数据源表结构
- 44 个单元测试全部通过

**蓝图对应**：M1-6

---

## 🟡 P1 - 重要优化（功能可用但需增强）

### P1-1: 采集任务进度与取消 ✅

- 实现 Celery 任务撤销（`revoke`）机制
- 通过 Socket.IO 推送采集进度
- 支持断点续传

**工作量**：2-3 天 | **蓝图对应**：M1-4 | **状态**：已完成

### P1-2: ETL 安全沙箱 ✅

- `PythonScriptTransformExecutor` 禁止危险模块
- 设置执行超时
- 限制内存使用

**工作量**：2 天 | **蓝图对应**：M2-1 | **状态**：已完成

### P1-3: 数据源连接池管理 ✅

- `ConnectionPoolManager`：基于 `datasource_id` 缓存 Engine
- 连接健康检查和自动回收
- 最大连接数限制和等待超时

**工作量**：2 天 | **蓝图对应**：M1-3 | **状态**：已完成

### P1-4: 动态调度（redbeat） ✅

- 使用 `redbeat` 实现 Celery Beat 动态调度
- 任务创建/修改/删除时实时更新
- 支持分布式调度

**工作量**：1-2 天 | **蓝图对应**：M1-5 | **状态**：已完成

---

## 🟢 P2 - 体验优化

| 编号 | 优化项 | 工作量 | 蓝图对应 |
|------|--------|--------|----------|
| P2-1 | 增量状态持久化（每批更新） | 1天 | M1-4 |
| P2-2 | 错误处理细化（区分可重试/不可重试） | 1-2天 | M1-4 |
| P2-3 | 测试覆盖率提升 | 持续 | 全局 |
| P2-4 | API 规范统一（requestId） | 1天 | 全局 |
| P2-5 | 监控指标（Prometheus） | 2-3天 | M4-4 |

---

## 📋 建议实施顺序

```
P0-1(质量引擎) → P0-3(查询引擎) → P0-2(告警引擎) → P1-1(进度取消) → P1-3(连接池) → P1-4(动态调度) → P1-2(安全沙箱) → P2系列
```

先补齐蓝图核心功能（质量检查→查询→告警），再增强现有模块（进度追踪→连接池→动态调度），最后打磨体验。