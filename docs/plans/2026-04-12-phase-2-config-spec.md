# Phase 2 配置规范文档

**Date**: 2026-04-12
**Status**: Day 2 冻结版本
**Purpose**: 去掉固定路径依赖，实现本机与开发服务器统一部署方式

## 1. 环境变量规范

### 1.1 核心原则
- 所有可变配置必须通过环境变量注入
- 禁止硬编码路径、端口、密钥
- 提供合理的默认值
- 敏感信息必须通过环境变量传递

### 1.2 必需环境变量

#### Cloud API 服务配置
```bash
# 服务基础配置
HERMES_ENV=production          # 运行环境: development, staging, production
CLOUD_API_HOST=0.0.0.0         # 监听地址
CLOUD_API_PORT=8080            # 监听端口
CLOUD_API_WORKERS=4            # Worker 进程数

# 数据库配置
DATABASE_TYPE=postgresql       # 数据库类型: sqlite, postgresql
DATABASE_URL=postgresql://user:pass@localhost:5432/hermesnexus
DATABASE_POOL_SIZE=20          # 连接池大小
DATABASE_POOL_MAX_OVERFLOW=10 # 连接池最大溢出

# Redis 配置
REDIS_ENABLED=true             # 是否启用 Redis
REDIS_HOST=localhost           # Redis 主机
REDIS_PORT=6379                # Redis 端口
REDIS_PASSWORD=                # Redis 密码（可选）
REDIS_DB=0                     # Redis DB 编号

# 日志配置
LOG_LEVEL=INFO                 # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_DIR=/var/log/hermesnexus   # 日志目录
LOG_FORMAT=json                # 日志格式: json, text
LOG_MAX_BYTES=10485760         # 单个日志文件最大大小（10MB）
LOG_BACKUP_COUNT=5             # 日志文件保留数量

# 数据目录
DATA_DIR=/var/lib/hermesnexus  # 数据根目录
ASSETS_DIR=/var/lib/hermesnexus/assets      # 资产数据目录
TASKS_DIR=/var/lib/hermesnexus/tasks        # 任务数据目录
SCRIPTS_DIR=/var/lib/hermesnexus/scripts    # 脚本存储目录
```

#### Edge Node 配置
```bash
# 节点标识
NODE_ID=edge-node-001          # 节点唯一ID（必需）
NODE_NAME=生产边缘节点-001      # 节点名称（必需）
NODE_CAPABILITIES=ssh,script   # 节点能力列表（逗号分隔）

# Cloud API 连接
CLOUD_API_URL=http://cloud-api:8080     # Cloud API 地址（必需）
CLOUD_API_TIMEOUT=30                     # 请求超时（秒）
CLOUD_API_RETRY=3                        # 失败重试次数

# 任务执行配置
TASK_POLL_INTERVAL=10         # 任务轮询间隔（秒）
TASK_EXEC_TIMEOUT=300         # 任务执行超时（秒）
SSH_CONNECT_TIMEOUT=30        # SSH 连接超时（秒）

# 日志配置
EDGE_LOG_LEVEL=INFO           # 日志级别
EDGE_LOG_DIR=/var/log/hermesnexus/edge  # 边缘节点日志目录

# 数据目录
EDGE_DATA_DIR=/var/lib/hermesnexus/edge  # 边缘节点数据目录
EDGE_CACHE_DIR=/var/lib/hermesnexus/edge/cache  # 缓存目录
EDGE_SCRIPTS_DIR=/var/lib/hermesnexus/edge/scripts  # 脚本目录
```

### 1.3 可选环境变量

```bash
# 安全配置（生产环境推荐）
SECRET_KEY=your-secret-key-here  # API 加密密钥
ALLOWED_HOSTS=localhost,127.0.0.1  # 允许的主机名
CORS_ORIGINS=http://localhost:3000  # CORS 允许的源

# 性能调优
MAX_CONCURRENT_TASKS=100      # 最大并发任务数
TASK_QUEUE_SIZE=1000          # 任务队列大小
HEARTBEAT_INTERVAL=30         # 心跳间隔（秒）
HEARTBEAT_TIMEOUT=120         # 心跳超时（秒）

# 监控配置
METRICS_ENABLED=true          # 是否启用指标收集
METRICS_PORT=9090             # 指标暴露端口
HEALTH_CHECK_INTERVAL=60      # 健康检查间隔（秒）
```

## 2. 配置文件规范

### 2.1 配置文件位置

#### 配置目录结构
```
/etc/hermesnexus/
├── config.yaml               # 主配置文件（生产环境）
├── config.development.yaml   # 开发环境配置
├── config.staging.yaml       # 预发布环境配置
└── credentials/
    ├── database.yaml         # 数据库凭证（敏感）
    └── redis.yaml            # Redis 凭证（敏感）
```

#### 项目本地配置（开发用）
```
~/hermesnexus/
├── .env                      # 本地环境变量
├── .env.development          # 开发环境变量
├── .env.test                 # 测试环境变量
└── config/
    ├── local.yaml            # 本地配置覆盖
    └── credentials.yaml      # 本地凭证（不提交到 Git）
```

### 2.2 配置文件模板

#### config.yaml 模板
```yaml
# HermesNexus Configuration Template
# Version: 2.0.0

# Environment
environment: production

# Cloud API
cloud_api:
  host: 0.0.0.0
  port: 8080
  workers: 4
  reload: false

# Database
database:
  type: postgresql
  url: ${DATABASE_URL}  # 引用环境变量
  pool_size: 20
  pool_max_overflow: 10
  echo: false

# Redis
redis:
  enabled: true
  host: ${REDIS_HOST}
  port: ${REDIS_PORT}
  password: ${REDIS_PASSWORD}
  db: 0

# Logging
logging:
  level: INFO
  format: json
  dir: /var/log/hermesnexus
  max_bytes: 10485760
  backup_count: 5

# Data directories
data:
  base_dir: /var/lib/hermesnexus
  assets_dir: /var/lib/hermesnexus/assets
  tasks_dir: /var/lib/hermesnexus/tasks
  scripts_dir: /var/lib/hermesnexus/scripts

# Security
security:
  secret_key: ${SECRET_KEY}
  allowed_hosts:
    - localhost
    - 127.0.0.1
  cors_origins:
    - http://localhost:3000

# Performance
performance:
  max_concurrent_tasks: 100
  task_queue_size: 1000
  heartbeat_interval: 30
  heartbeat_timeout: 120

# Monitoring
monitoring:
  metrics_enabled: true
  metrics_port: 9090
  health_check_interval: 60
```

#### config.development.yaml 模板
```yaml
# Development Environment Configuration

environment: development

cloud_api:
  host: 127.0.0.1
  port: 8080
  workers: 1
  reload: true

database:
  type: sqlite
  url: sqlite:///./hermesnexus.db
  pool_size: 5
  echo: true  # 开发环境打印 SQL

logging:
  level: DEBUG
  format: text
  dir: ./logs

data:
  base_dir: ./data
  assets_dir: ./data/assets
  tasks_dir: ./data/tasks
  scripts_dir: ./data/scripts

monitoring:
  metrics_enabled: false
```

## 3. 环境差异配置

### 3.1 本机开发环境

#### 特征
- 数据目录: `./data`
- 日志目录: `./logs`
- 数据库: SQLite（本地文件）
- 日志级别: DEBUG
- 自动重载: 启用

#### .env.development
```bash
# Development Environment
HERMES_ENV=development
CLOUD_API_HOST=127.0.0.1
CLOUD_API_PORT=8080
CLOUD_API_WORKERS=1

DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///./hermesnexus.db

REDIS_ENABLED=false

LOG_LEVEL=DEBUG
LOG_DIR=./logs
LOG_FORMAT=text

DATA_DIR=./data
ASSETS_DIR=./data/assets
TASKS_DIR=./data/tasks
SCRIPTS_DIR=./data/scripts

SECRET_KEY=dev-secret-key-not-for-production
```

### 3.2 开发服务器环境

#### 特征
- 数据目录: `/var/lib/hermesnexus`
- 日志目录: `/var/log/hermesnexus`
- 数据库: PostgreSQL（持久化）
- 日志级别: INFO
- 自动重载: 禁用

#### .env.production
```bash
# Production Environment (Development Server)
HERMES_ENV=production
CLOUD_API_HOST=0.0.0.0
CLOUD_API_PORT=8080
CLOUD_API_WORKERS=4

DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://hermesnexus:password@localhost:5432/hermesnexus

REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379

LOG_LEVEL=INFO
LOG_DIR=/var/log/hermesnexus
LOG_FORMAT=json

DATA_DIR=/var/lib/hermesnexus
ASSETS_DIR=/var/lib/hermesnexus/assets
TASKS_DIR=/var/lib/hermesnexus/tasks
SCRIPTS_DIR=/var/lib/hermesnexus/scripts

SECRET_KEY=${SECRET_KEY}  # 从安全配置读取
```

### 3.3 配置优先级

1. **环境变量** (最高优先级)
2. **本地配置文件** (`./config/local.yaml`)
3. **环境配置文件** (`config.development.yaml`, `config.production.yaml`)
4. **默认值** (最低优先级)

## 4. 启停脚本规范

### 4.1 参数化启动脚本

#### Cloud API 启动脚本
```bash
#!/usr/bin/env bash
# scripts/start-cloud-api.sh

set -e

# 默认值
ENV=${HERMES_ENV:-development}
CONFIG_DIR=${CONFIG_DIR:-./config}
HOST=${CLOUD_API_HOST:-127.0.0.1}
PORT=${CLOUD_API_PORT:-8080}
WORKERS=${CLOUD_API_WORKERS:-1}

# 加载环境配置
if [ -f ".env.$ENV" ]; then
    export $(cat ".env.$ENV" | grep -v '^#' | xargs)
fi

# 创建必要目录
mkdir -p "${LOG_DIR}"
mkdir -p "${DATA_DIR}"
mkdir -p "${ASSETS_DIR}"
mkdir -p "${TASKS_DIR}"
mkdir -p "${SCRIPTS_DIR}"

# 启动服务
echo "Starting HermesNexus Cloud API..."
echo "Environment: $ENV"
echo "Host: $HOST"
echo "Port: $PORT"

if [ "$ENV" = "development" ]; then
    # 开发模式：单进程，自动重载
    python3 -m uvicorn cloud.api.main:app \
        --host "$HOST" \
        --port "$PORT" \
        --reload \
        --log-level "${LOG_LEVEL:-DEBUG}"
else
    # 生产模式：多进程
    python3 -m uvicorn cloud.api.main:app \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS" \
        --log-level "${LOG_LEVEL:-INFO}"
fi
```

#### Edge Node 启动脚本
```bash
#!/usr/bin/env bash
# scripts/start-edge-node.sh

set -e

# 必需参数
NODE_ID=${NODE_ID:?Error: NODE_ID is required}
NODE_NAME=${NODE_NAME:?Error: NODE_NAME is required}

# 可选参数
CLOUD_API_URL=${CLOUD_API_URL:-http://localhost:8080}
POLL_INTERVAL=${TASK_POLL_INTERVAL:-10}
LOG_DIR=${EDGE_LOG_DIR:-./logs/edge}

# 创建必要目录
mkdir -p "$LOG_DIR"
mkdir -p "${EDGE_CACHE_DIR}"

# 启动边缘节点
echo "Starting HermesNexus Edge Node..."
echo "Node ID: $NODE_ID"
echo "Node Name: $NODE_NAME"
echo "Cloud API: $CLOUD_API_URL"

python3 edge/runtime/main.py \
    --node-id "$NODE_ID" \
    --node-name "$NODE_NAME" \
    --cloud-api-url "$CLOUD_API_URL" \
    --poll-interval "$POLL_INTERVAL"
```

### 4.2 停止脚本

```bash
#!/usr/bin/env bash
# scripts/stop-services.sh

echo "Stopping HermesNexus services..."

# 停止 Cloud API
pkill -f "uvicorn cloud.api.main:app" || true

# 停止 Edge Node
pkill -f "edge/runtime/main.py" || true

echo "Services stopped."
```

### 4.3 状态检查脚本

```bash
#!/usr/bin/env bash
# scripts/status.sh

echo "HermesNexus Service Status"
echo "=========================="

# Cloud API 状态
if pgrep -f "uvicorn cloud.api.main:app" > /dev/null; then
    echo "Cloud API: Running (PID: $(pgrep -f 'uvicorn cloud.api.main:app'))"
else
    echo "Cloud API: Stopped"
fi

# Edge Node 状态
if pgrep -f "edge/runtime/main.py" > /dev/null; then
    echo "Edge Node: Running (PID: $(pgrep -f 'edge/runtime/main.py'))"
else
    echo "Edge Node: Stopped"
fi

# 健康检查
echo ""
echo "Health Check:"
curl -s http://localhost:8080/health | jq . || echo "Health check failed"
```

## 5. 目录结构统一

### 5.1 开发环境目录结构
```
~/hermesnexus/
├── data/
│   ├── assets/           # 资产数据
│   ├── tasks/            # 任务数据
│   └── scripts/          # 脚本存储
├── logs/
│   ├── cloud-api.log     # Cloud API 日志
│   ├── edge-node.log     # Edge Node 日志
│   └── audit.log         # 审计日志
├── config/
│   ├── local.yaml        # 本地配置
│   └── credentials.yaml  # 本地凭证
└── .env.development      # 开发环境变量
```

### 5.2 生产环境目录结构
```
/var/lib/hermesnexus/
├── assets/               # 资产数据
├── tasks/                # 任务数据
└── scripts/              # 脚本存储

/var/log/hermesnexus/
├── cloud-api.log         # Cloud API 日志
├── edge-node.log         # Edge Node 日志
└── audit.log             # 审计日志

/etc/hermesnexus/
├── config.yaml           # 主配置
└── credentials/          # 凭证目录
```

## 6. 配置验证

### 6.1 配置检查脚本

```python
# scripts/validate_config.py
import os
import sys
from pathlib import Path

def validate_config():
    """验证配置完整性"""
    errors = []

    # 检查必需环境变量
    required_vars = ['NODE_ID', 'NODE_NAME', 'CLOUD_API_URL']
    for var in required_vars:
        if not os.getenv(var):
            errors.append(f"Missing required environment variable: {var}")

    # 检查目录可写性
    required_dirs = [
        os.getenv('DATA_DIR', './data'),
        os.getenv('LOG_DIR', './logs'),
    ]
    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create directory {dir_path}: {e}")
        elif not os.access(dir_path, os.W_OK):
            errors.append(f"Directory not writable: {dir_path}")

    # 报告结果
    if errors:
        print("Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("Configuration validation: PASSED")
        sys.exit(0)

if __name__ == '__main__':
    validate_config()
```

## 7. 验收标准

Day 2 完成标准：
- [ ] 环境变量规范完整且可执行
- [ ] 配置文件模板可覆盖所有场景
- [ ] 本机和开发服务器使用同一套启动脚本
- [ ] 不依赖硬编码路径
- [ ] 配置验证脚本可检测配置错误

---

**下一步**: Day 3 - 资产管理最小能力
