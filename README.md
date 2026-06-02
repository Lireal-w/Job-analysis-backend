# Job Analysis Backend — 求职情报分析平台后端

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 📋 项目简介

Job Analysis Backend 是一个基于 **FastAPI Best Architecture** 企业级架构的求职情报分析平台后端系统，提供职位数据采集、存储、查询和分析的完整服务能力。

**核心能力**：
- ⚡ **高性能 API**：基于 FastAPI 异步框架，支持高并发请求处理
- 🔄 **异步任务调度**：通过 Celery + Redis 实现爬虫任务的异步执行与状态追踪
- 🗄️ **多层次存储**：MySQL 持久化存储 + Redis 缓存加速
- 🔐 **安全认证**：JWT + RBAC 权限控制体系
- 📊 **数据采集集成**：通过 Git Submodule 集成爬虫子项目，实现采集-服务一体化
- 🚢 **容器化部署**：完整的 Docker Compose 编排，一键启动全套服务
- 📈 **可观测性**：集成 Grafana、Prometheus 等监控组件

## 🔧 技术栈

| 技术 | 说明 |
|------|------|
| **Python 3.10+** | 开发语言 |
| **FastAPI** | 异步 Web 框架 |
| **SQLAlchemy** | ORM 框架 |
| **Celery** | 分布式任务队列 |
| **Redis** | 消息代理 + 缓存 |
| **MySQL** | 关系型数据库 |
| **Casbin** | RBAC 权限管理 |
| **Pydantic** | 数据验证与序列化 |
| **Alembic** | 数据库迁移工具 |
| **Docker** | 容器化部署 |
| **Grafana + Prometheus** | 监控与可视化 |

## 📁 项目结构

```
Job-analysis-backend/
├── backend/                    # 后端核心代码
│   ├── app/                    # 应用主目录
│   │   ├── api/                # API 路由层
│   │   ├── crud/               # CRUD 操作层
│   │   ├── models/             # SQLAlchemy ORM 模型层
│   │   ├── schemas/            # Pydantic 数据验证层
│   │   ├── services/           # 业务逻辑层
│   │   ├── tasks/              # Celery 异步任务层
│   │   └── core/               # 核心配置与依赖
│   ├── collectors/             # 数据采集层
│   │   └── job-analysis/       # 爬虫子模块（Git Submodule）
│   └── .env                    # 环境配置文件
├── deploy/backend/             # 部署配置
├── docker-compose.yml          # Docker 编排文件
├── .gitmodules                 # Git 子模块配置
└── requirements.txt            # Python 依赖
```

## 🏗️ 架构设计

### 分层架构

| 层级 | 说明 |
|------|------|
| **接口层 (API)** | 处理 HTTP 请求/响应，参数验证，权限校验 |
| **业务层 (Service)** | 实现核心业务逻辑 |
| **数据访问层 (CRUD)** | 封装数据库操作 |
| **模型层 (Model)** | SQLAlchemy ORM 模型定义 |
| **任务层 (Task)** | Celery 异步任务定义 |

### 采集-服务一体化

- 爬虫项目通过 **Git Submodule** 集成到 `backend/collectors/` 目录
- FastAPI 通过 **Celery 异步任务** 调用爬虫，实现非阻塞采集
- 支持**同步模式**（小任务快速响应）和**异步模式**（大规模任务可靠调度）

### 异步任务流程

```
客户端 → FastAPI API → 提交 Celery 任务 → Redis 队列 → Celery Worker → 执行爬虫 → 数据入库 → 返回 task_id
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/Lireal-w/Job-analysis-backend.git
cd Job-analysis-backend
```

### 2. 初始化子模块

```bash
# 初始化并拉取爬虫子模块
git submodule update --init --recursive
```

### 3. 配置环境变量

```bash
cp backend/.env.example backend/.env
# 编辑 .env 文件，配置数据库、Redis 等连接信息
```

`.env` 关键配置项：
```
# 数据库
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=job_analysis

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

### 5. 数据库迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "init"

# 执行迁移
alembic upgrade head
```

### 6. 启动服务

```bash
# 启动 FastAPI 服务
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# 启动 Celery Worker（新终端）
celery -A backend.app.tasks.celery_app worker --loglevel=info

# （可选）启动 Celery Beat 定时任务
celery -A backend.app.tasks.celery_app beat --loglevel=info
```

### 7. Docker Compose 一键启动（推荐）

```bash
docker-compose up -d
```

这将启动以下服务：
- FastAPI 后端（端口 8000）
- MySQL 数据库（端口 3306）
- Redis 缓存（端口 6379）
- Celery Worker
- Celery Beat
- Flower（Celery 监控，端口 5555）
- Grafana（监控面板，端口 3000）

## 📖 API 文档

启动服务后，访问以下地址查看自动生成的 API 文档：

- **Swagger UI**：http://localhost:8000/docs
- **ReDoc**：http://localhost:8000/redoc

### 主要 API 端点

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/jobs` | 获取职位列表（支持分页/筛选） |
| GET | `/api/v1/jobs/{id}` | 获取职位详情 |
| POST | `/api/v1/crawler/run` | 手动触发爬虫采集任务 |
| GET | `/api/v1/crawler/status/{task_id}` | 查询采集任务状态 |
| POST | `/api/v1/auth/login` | 用户登录 |
| GET | `/api/v1/users/me` | 获取当前用户信息 |

## 🔧 性能优化

### 多级缓存
- **L1 内存缓存**：高频查询结果缓存（微秒级响应）
- **L2 Redis 缓存**：分布式共享缓存（亚毫秒级）

### 连接池优化
- **HTTP 连接池**：httpx.AsyncClient 连接池配置
- **数据库连接池**：SQLAlchemy `pool_size=20`, `max_overflow=10`
- **Redis 连接池**：静态化配置，消除动态伸缩开销

### 并发控制
- **API 层**：`asyncio.Semaphore` 限制并发处理请求数
- **Celery 层**：`worker_concurrency` 控制 Worker 并发数
- **爬虫层**：Scrapy 内置三级并发控制

## 📄 License

MIT License

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request。提交前请确保：
1. 代码通过 Ruff 格式化检查
2. 添加必要的单元测试
3. 更新相关文档

## 🔗 相关项目

- **爬虫模块**：[job-analysis](https://github.com/Lireal-w/job-analysis)
- **前端界面**：[Job-analysis-ui](https://github.com/Lireal-w/Job-analysis-ui)
- **源框架**：[fastapi-best-architecture](https://github.com/fastapi-practices/fastapi_best_architecture)