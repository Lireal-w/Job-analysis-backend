# 多源数据管理平台

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 📋 项目简介

**多源数据管理平台** 是一个基于 FastAPI 企业级架构构建的多源数据采集、管理与监控平台。提供多种数据源的接入、爬虫任务调度分发、服务器远程管理、待办事项跟踪等完整服务能力。

**核心能力**：
- ⚡ **高性能 API**：基于 FastAPI 异步框架，支持高并发请求处理
- 🔄 **分布式爬虫集群**：主从架构，支持多节点爬虫任务分发与调度
- 🗄️ **多层次存储**：PostgreSQL/MySQL 持久化存储 + Redis 缓存加速
- 🔐 **安全认证**：JWT + RBAC 权限控制体系
- 📊 **远程服务器管理**：支持 SSH / SFTP / Telnet / RDP / VNC / HTTP / HTTPS 多协议连接测试
- ✅ **待办事项管理**：任务拆解、阶段性目标、AI 自动分阶段、进度追踪
- 🌐 **国际化支持**：内置 i18n 多语言支持
- 🚢 **容器化部署**：完整的 Docker Compose 编排，一键启动全套服务
- 📈 **可观测性**：集成 Grafana、Prometheus、OpenTelemetry 等监控组件

## 🔧 技术栈

| 技术 | 说明 |
|------|------|
| **Python 3.10+** | 开发语言 |
| **FastAPI** | 异步 Web 框架 |
| **SQLAlchemy 2.0** | ORM 框架（异步支持） |
| **Celery** | 分布式任务队列 |
| **Redis** | 消息代理 + 缓存 |
| **PostgreSQL / MySQL** | 关系型数据库 |
| **MongoDB** | NoSQL 文档数据库 |
| **Paramiko** | SSH/SFTP 远程连接 |
| **Socket.IO** | WebSocket 实时通信 |
| **Casbin** | RBAC 权限管理 |
| **Pydantic** | 数据验证与序列化 |
| **Alembic** | 数据库迁移工具 |
| **Docker** | 容器化部署 |
| **Grafana + Prometheus + OpenTelemetry** | 全链路监控与可观测性 |

## 📁 项目结构

```
fastapi-best-architecture/
├── backend/                        # 后端核心代码
│   ├── app/                        # 应用主目录
│   │   ├── admin/                  # 后台管理模块
│   │   │   ├── api/v1/sys/         # 系统管理 API（用户/角色/菜单/SSH/Worker等）
│   │   │   ├── crud/               # CRUD 操作层
│   │   │   ├── model/              # SQLAlchemy ORM 模型层
│   │   │   ├── schema/             # Pydantic 数据验证层
│   │   │   ├── service/            # 业务逻辑层
│   │   │   └── tests/              # 测试用例
│   │   ├── todo/                   # 待办事项模块（独立子应用）
│   │   │   ├── api/v1/             # 待办 API
│   │   │   ├── crud/               # 待办 CRUD
│   │   │   ├── model/              # 待办模型
│   │   │   ├── schema/             # 待办 Schema
│   │   │   ├── service/            # 待办服务（含 AI 分阶段）
│   │   │   └── tests/              # 待办测试
│   │   ├── task/                   # Celery 任务模块
│   │   │   ├── api/v1/             # 任务调度 API
│   │   │   ├── crud/               # 任务 CRUD
│   │   │   ├── model/              # 任务模型
│   │   │   ├── service/            # 任务服务
│   │   │   └── tasks/              # Celery 任务定义
│   │   └── router.py               # 全局路由注册
│   ├── agent/                      # Worker 从节点（独立可部署）
│   │   ├── api/v1/                 # 从节点 API（任务接收、健康检查）
│   │   ├── core/conf.py            # 从节点配置
│   │   ├── main.py                 # 从节点应用入口（含注册/心跳）
│   │   ├── state.py                # 从节点全局状态
│   │   ├── .env.example            # 从节点环境配置示例
│   │   └── requirements.txt        # 从节点依赖
│   ├── common/                     # 公共模块
│   │   ├── cache/                  # 多级缓存（L1内存 + L2 Redis）
│   │   ├── exception/              # 异常定义
│   │   ├── response/               # 统一响应格式
│   │   ├── security/               # JWT/RBAC 安全认证
│   │   ├── socketio/               # WebSocket 实时通信
│   │   ├── model.py                # SQLAlchemy 基类
│   │   ├── schema.py               # Pydantic 基类
│   │   ├── enums.py                # 全局枚举（含 ProtocolType）
│   │   ├── pagination.py           # 分页工具
│   │   └── ...                     # 其他公共工具
│   ├── core/                       # 核心配置
│   │   ├── conf.py                 # 全局配置（Pydantic Settings）
│   │   ├── path_conf.py            # 路径配置
│   │   └── registrar.py            # 应用注册器
│   ├── database/                   # 数据库连接
│   │   ├── db.py                   # SQLAlchemy 异步引擎/会话
│   │   ├── mongo_db.py             # MongoDB 连接
│   │   └── redis.py                # Redis 连接
│   ├── middleware/                 # 中间件
│   ├── utils/                      # 工具函数
│   ├── plugin/                     # 插件系统
│   ├── .env                        # 主节点环境配置
│   └── main.py                     # 主节点应用入口
├── deploy/                         # 部署配置
│   └── backend/
│       ├── nginx.conf
│       ├── docker-compose/
│       ├── grafana/
│       └── supervisor/
├── docker-compose.yml              # Docker 编排文件
└── pyproject.toml                  # Python 项目配置
```

## 🏗️ 架构设计

### 主从分布式架构

```
┌─────────────────────┐         HTTP/API          ┌─────────────────────┐
│     Master Node      │◄────────────────────────►│    Worker Node 1     │
│  (主节点 - backend)  │                          │  (从节点 - agent)    │
│                      │  POST /register           │                     │
│  FastAPI + Celery    │  PUT /{id}/heartbeat      │  FastAPI (独立部署)  │
│                      │  POST /dispatch           │                     │
│  PostgreSQL/MySQL    │                          │  执行爬虫任务        │
│  Redis/MongoDB       │                          │  上报状态/资源       │
└─────────────────────┘                          └─────────────────────┘
                              ┌─────────────────────┐
                              │    Worker Node N     │
                              │  (更多服务器节点)    │
                              └─────────────────────┘
```

### 分层架构

| 层级 | 说明 |
|------|------|
| **接口层 (API)** | 处理 HTTP 请求/响应，参数验证，权限校验 |
| **业务层 (Service)** | 实现核心业务逻辑 |
| **数据访问层 (CRUD)** | 封装数据库操作（基于 sqlalchemy-crud-plus） |
| **模型层 (Model)** | SQLAlchemy ORM 模型定义 |
| **任务层 (Task)** | Celery 异步任务定义与调度 |

### 异步任务流程

```
客户端 → FastAPI API → 提交 Celery 任务 → Redis/RabbitMQ → Worker 进程 → 业务执行 → 结果回写 → 状态查询
```

### Worker 集群流程

```
主节点 API /dispatch → 选择最优 Worker → HTTP 请求 Worker 节点 /tasks → Worker 执行爬虫 → 返回结果
                                                 ↓
                                        心跳上报 (每30s)
                                        CPU/内存/任务数 → 主节点数据库
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-repo/fastapi-best-architecture.git
cd fastapi-best-architecture
```

### 2. 配置环境变量

```bash
cp backend/.env.example backend/.env
# 编辑 .env 文件，配置数据库、Redis 等连接信息
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
# 或使用 uv
uv sync
```

### 4. 数据库迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "init"
# 执行迁移
alembic upgrade head
```

### 5. 启动服务

```bash
# 启动 FastAPI 服务（开发模式）
fba run

# 启动 Celery Worker（新终端）
celery -A backend.app.task.celery:celery_app worker --loglevel=info --pool=solo

# （可选）启动 Celery Beat 定时调度
celery -A backend.app.task.celery:celery_app beat --loglevel=info
```

### 6. Docker Compose 一键启动（推荐）

```bash
docker-compose up -d
```

## 🌐 部署 Worker 从节点

Worker 节点可独立部署到其他服务器上，执行爬虫任务。

### 安装与启动

```bash
# 在目标服务器上
cd backend/agent
pip install -r requirements.txt

# 配置 .env（参考 .env.example）
NODE_NAME='worker-1'
MASTER_URL='http://主节点IP:8000'

# 启动 Worker 节点
python -m backend.agent.main
# 或使用 granian（高性能）
granian backend.agent.main:app --host 0.0.0.0 --port 8001
```

Worker 启动后自动：
1. 向主节点注册，获取身份标识
2. 每 30 秒上报系统资源与任务状态
3. 接收主节点分发的爬虫任务并执行

## 📖 API 文档

启动服务后，访问以下地址查看自动生成的 API 文档：

- **Swagger UI**：http://localhost:8000/docs
- **ReDoc**：http://localhost:8000/redoc

### 主要 API 端点

| 模块 | 方法 | 端点 | 描述 |
|------|------|------|------|
| **认证** | POST | `/api/v1/auth/login` | 用户登录 |
| | GET | `/api/v1/auth/captcha` | 获取验证码 |
| **系统管理** | GET/POST/PUT | `/api/v1/sys/users` | 用户 CRUD |
| | GET/POST/PUT | `/api/v1/sys/roles` | 角色管理 |
| | GET/POST/PUT | `/api/v1/sys/menus` | 菜单管理 |
| **SSH/远程** | POST | `/api/v1/sys/servers/test-connection` | 测试 SSH/RDP/VNC/HTTP 连接 |
| | GET/POST/PUT | `/api/v1/sys/servers` | 服务器 CRUD |
| **Worker** | POST | `/api/v1/sys/workers/dispatch` | 分发爬虫任务 |
| | PUT | `/api/v1/sys/workers/{id}/heartbeat` | Worker 心跳上报 |
| | POST | `/api/v1/sys/workers/register` | Worker 注册 |
| | GET/POST/PUT | `/api/v1/sys/workers` | Worker 管理 |
| **待办事项** | GET | `/api/v1/todos/today` | 今日待完成 |
| | GET/POST/PUT | `/api/v1/todos` | 任务 CRUD |
| | POST | `/api/v1/todo-goals/ai-generate/{id}` | AI 自动分阶段目标 |
| **任务调度** | GET/POST/PUT | `/api/v1/schedulers` | Celery 定时任务管理 |
| **职位管理** | GET/POST/PUT | `/api/v1/jobs/pg` | 职位 PostgreSQL CRUD |
| | GET | `/api/v1/jobs/mongo` | MongoDB 职位数据查询 |

## 🧩 功能模块

### 远程服务器管理
- 支持 7 种协议连接测试：SSH、SFTP、Telnet、RDP、VNC、HTTP、HTTPS
- 服务器配置信息管理（名称、地址、凭据、标签）
- 状态监控与批量管理

### 分布式 Worker 集群
- 主从架构，Worker 节点自动注册
- 实时心跳检测，自动标记离线节点
- 智能负载分发（自动选择最优 Worker）
- 资源监控（CPU、内存、任务数）

### 待办事项管理
- 每日任务 / 周期任务 / 定时任务
- AI 自动拆解分阶段目标
- 进度追踪与操作日志
- 任务来源：上级分配 / 自己定制 / AI 生成

### 数据采集（内置爬虫引擎）
- 通过 Worker 集群分发爬虫任务
- 支持 Scrapy 框架
- MongoDB 数据存储

## 🔧 配置说明

主节点配置（`backend/.env`）：

```env
# 数据库
DATABASE_TYPE='postgresql'      # mysql / postgresql
DATABASE_HOST='localhost'
DATABASE_PORT=5432
DATABASE_USER='user'
DATABASE_PASSWORD='password'

# Redis
REDIS_HOST='localhost'
REDIS_PORT=6379
REDIS_PASSWORD=''

# Token
TOKEN_SECRET_KEY='your-secret-key'

# Celery
CELERY_BROKER='redis'          # redis / rabbitmq
```

## 📄 License

MIT License

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request。提交前请确保：
1. 代码通过 Ruff 格式化检查
2. 添加必要的单元测试
3. 更新相关文档