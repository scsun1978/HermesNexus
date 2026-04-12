# HermesNexus 部署指南 (Phase 2 Week 3)

**Date**: 2026-04-12  
**Version**: 2.1.0  
**Phase**: Week 3 - 部署就绪版本

---

## 🎯 部署目标

将 HermesNexus 从开发环境推进到**可部署、可验证、可监控**的生产就绪状态。

### Week 3 新增能力
- ✅ 数据持久化 (SQLite + SQLAlchemy)
- ✅ API 安全认证 (Token + API Key)
- ✅ 完整测试体系 (单元 + 集成 + E2E + 性能)
- ✅ 性能基线和优化方案
- ✅ 故障排查和监控建议

---

## 📋 部署前检查清单

### 环境要求

**基础环境**:
- Python 3.8+
- SQLite 3
- 1GB+ 可用内存
- 100MB+ 可用磁盘空间

**Python依赖**:
```bash
# 核心依赖
sqlalchemy>=2.0.0
pydantic>=2.0.0
fastapi>=0.100.0
uvicorn>=0.23.0

# 安全依赖
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

### 配置检查

**必需配置项**:
- [ ] 数据库连接字符串
- [ ] API 认证密钥
- [ ] 日志配置
- [ ] 健康检查端点

### 功能验证

**核心功能测试**:
```bash
# 1. Smoke测试 (5分钟)
./tests/e2e/run_smoke_tests.sh

# 2. 集成测试 (15分钟)
./tests/integration/run_integration_tests.sh

# 3. 性能基线测试 (10分钟)
./tests/performance/run_performance_tests.sh
```

---

## 🚀 快速部署

### 方式1: 开发环境部署

**适用场景**: 本地开发、功能验证

```bash
# 1. 环境准备
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 初始化数据库
./scripts/init-database.sh

# 3. 配置环境变量
cp .env.development .env
# 编辑 .env 文件设置必要的配置

# 4. 启动服务
python3 -m uvicorn cloud.main:app --reload --host 0.0.0.0 --port 8000

# 5. 验证部署
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/assets/
```

### 方式2: 测试环境部署

**适用场景**: 集成测试、性能验证

```bash
# 1. 使用测试配置
export ENVIRONMENT=test
python3 -m uvicorn cloud.main:app --host 0.0.0.0 --port 8000

# 2. 运行完整测试套件
./tests/e2e/run_smoke_tests.sh
./tests/integration/run_integration_tests.sh
./tests/e2e/run_e2e_tests.sh

# 3. 性能验证
./tests/performance/run_performance_tests.sh
```

### 方式3: 生产环境部署

**适用场景**: 生产部署、长期运行

```bash
# 1. 系统配置
sudo cp scripts/hermesnexus.service /etc/systemd/system/
sudo systemctl daemon-reload

# 2. 数据库初始化
./scripts/init-database.sh

# 3. 配置管理
cp .env.production .env
# 编辑生产环境配置

# 4. 启动服务
sudo systemctl start hermesnexus
sudo systemctl enable hermesnexus

# 5. 健康检查
curl http://localhost:8000/health
```

---

## 🔧 配置管理

### 环境变量配置

**开发环境** (`.env.development`):
```bash
# 基础配置
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# 数据库配置
DATABASE_URL=sqlite:///data/hermesnexus.db

# API配置
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# 安全配置
SECRET_KEY=development-secret-key-change-in-production
AUTH_ENABLED=false  # 开发环境可关闭认证
```

**生产环境** (`.env.production`):
```bash
# 基础配置
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# 数据库配置
DATABASE_URL=sqlite:///data/hermesnexus.db
POOL_SIZE=10
MAX_OVERFLOW=20

# API配置
API_HOST=0.0.0.0
API_PORT=8000
WORKERS=4

# 安全配置
SECRET_KEY=<strong-random-key>
AUTH_ENABLED=true
TOKEN_EXPIRE_SECONDS=3600

# 日志配置
LOG_FILE=/var/log/hermesnexus/app.log
LOG_ROTATION=true
LOG_MAX_BYTES=10485760
```

### 配置验证

**检查脚本**:
```bash
#!/bin/bash
# 配置验证脚本

echo "验证配置文件..."

# 检查必需的配置项
required_vars=(
    "DATABASE_URL"
    "SECRET_KEY"
    "AUTH_ENABLED"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "❌ 缺少必需的配置: ${missing_vars[@]}"
    exit 1
fi

echo "✅ 配置验证通过"
```

---

## 🏥 健康检查

### 端点定义

**基础健康检查** (`/health`):
```json
{
  "status": "healthy",
  "version": "2.1.0",
  "timestamp": "2026-04-12T10:00:00Z",
  "components": {
    "database": "healthy",
    "api": "healthy",
    "storage": "healthy"
  }
}
```

**详细健康检查** (`/health/detailed`):
```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "healthy",
      "connections": 5,
      "pool_size": 10,
      "queries_per_second": 120
    },
    "api": {
      "status": "healthy",
      "uptime": 86400,
      "requests_per_second": 45
    },
    "storage": {
      "status": "healthy",
      "disk_usage": "45%",
      "read_write_speed": "normal"
    }
  }
}
```

### 监控指标

**关键指标**:
- API响应时间 (P50/P95/P99)
- 数据库连接池使用率
- 内存使用率
- 错误率
- 吞吐量 (QPS)

---

## 🛡️ 安全配置

### 认证启用

**生产环境**:
```bash
# 必须启用认证
AUTH_ENABLED=true

# 使用强密钥
SECRET_KEY=$(openssl rand -hex 32)

# Token过期时间
TOKEN_EXPIRE_SECONDS=3600
```

### API访问控制

**推荐配置**:
```python
# 在生产环境中启用所有中间件
app.add_middleware(AuthMiddleware, require_auth=True)

# 公开端点
PUBLIC_ENDPOINTS = [
    "/health",
    "/docs",
    "/openapi.json"
]

# 受保护端点
PROTECTED_ENDPOINTS = [
    "/api/v1/assets",
    "/api/v1/tasks",
    "/api/v1/audit"
]
```

---

## 📊 日志配置

### 日志级别

**开发环境**: `DEBUG`
**测试环境**: `INFO`
**生产环境**: `WARNING` 或 `ERROR`

### 日志格式

**结构化日志**:
```json
{
  "timestamp": "2026-04-12T10:00:00Z",
  "level": "INFO",
  "component": "asset_service",
  "message": "Asset created successfully",
  "context": {
    "asset_id": "asset-001",
    "user_id": "user-001"
  }
}
```

### 日志轮转

**配置**:
```python
LOG_ROTATION = True
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
```

---

## 🔄 部署流程

### 标准部署流程

**1. 预部署检查** (5分钟):
```bash
# 运行Smoke测试
./tests/e2e/run_smoke_tests.sh
```

**2. 备份数据** (按需):
```bash
# 备份数据库
cp data/hermesnexus.db data/backup/hermesnexus.db.$(date +%Y%m%d)
```

**3. 部署新版本** (2分钟):
```bash
# 停止服务
sudo systemctl stop hermesnexus

# 更新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt

# 启动服务
sudo systemctl start hermesnexus
```

**4. 部署验证** (5分钟):
```bash
# 健康检查
curl http://localhost:8000/health

# Smoke测试
./tests/e2e/run_smoke_tests.sh

# 集成测试
./tests/integration/run_integration_tests.sh
```

**5. 监控确认** (持续):
- 检查错误日志
- 监控性能指标
- 验证核心功能

### 回滚流程

**快速回滚** (5分钟):
```bash
# 1. 停止服务
sudo systemctl stop hermesnexus

# 2. 回滚代码
git reset --hard <previous-commit>

# 3. 回滚依赖
pip install -r requirements.txt

# 4. 启动服务
sudo systemctl start hermesnexus

# 5. 验证回滚
curl http://localhost:8000/health
```

---

## 📋 验收清单

### 功能验收

**核心功能**:
- [x] 资产管理 (CRUD + 统计)
- [x] 任务管理 (创建 + 执行 + 状态跟踪)
- [x] 审计追踪 (日志记录 + 查询)
- [x] API认证 (Token + API Key)

### 性能验收

**响应时间**:
- [x] 平均响应 < 10ms
- [x] P95响应 < 50ms
- [x] P99响应 < 100ms

**吞吐量**:
- [x] 支持 100+ QPS
- [x] 并发用户支持

### 可靠性验收

**稳定性**:
- [x] 服务正常运行 > 24小时
- [x] 错误率 < 1%
- [x] 自动重启机制

**可恢复性**:
- [x] 数据持久化正常
- [x] 重启后数据完整
- [x] 备份恢复流程

---

## 🔍 故障排查

### 常见问题

**1. 数据库连接失败**
```bash
# 检查数据库文件
ls -lh data/hermesnexus.db

# 检查文件权限
chmod 644 data/hermesnexus.db

# 重新初始化
./scripts/init-database.sh
```

**2. API认证失败**
```bash
# 检查认证配置
echo $AUTH_ENABLED
echo $SECRET_KEY

# 创建测试Token
python3 -c "
from shared.security.auth_manager import auth_manager
user_info = {'user_id': 'test', 'role': 'admin', 'permissions': ['*']}
token = auth_manager.create_token(user_info)
print(token)
"
```

**3. 性能问题**
```bash
# 运行性能分析
./tests/performance/run_performance_tests.sh

# 检查连接池
curl http://localhost:8000/health/detailed
```

**4. 内存不足**
```bash
# 检查内存使用
free -h

# 清理临时文件
rm -rf /tmp/hermesnexus_*

# 重启服务
sudo systemctl restart hermesnexus
```

### 日志分析

**错误日志聚合**:
```bash
# 查看最近的错误
grep ERROR /var/log/hermesnexus/app.log | tail -20

# 统计错误类型
grep ERROR /var/log/hermesnexus/app.log | awk '{print $3}' | sort | uniq -c
```

---

## 📈 监控建议

### 基础监控

**系统监控**:
- CPU使用率
- 内存使用率
- 磁盘I/O
- 网络流量

**应用监控**:
- API响应时间
- 错误率
- 吞吐量
- 数据库连接数

### 告警规则

**建议告警阈值**:
- API响应时间 P95 > 100ms
- 错误率 > 1%
- 数据库连接池使用率 > 80%
- 内存使用率 > 85%

---

## ✅ 部署验证

### 最终验证清单

**服务状态**:
- [ ] 服务进程运行正常
- [ ] 健康检查端点响应正常
- [ ] 日志正常输出
- [ ] 无错误日志

**功能验证**:
- [ ] API可正常访问
- [ ] 认证功能正常
- [ ] 核心业务流程正常
- [ ] 数据持久化正常

**性能验证**:
- [ ] Smoke测试通过
- [ ] 集成测试通过
- [ ] 性能基线正常

---

**文档维护**: 本文档将在部署过程中持续更新，确保与实际部署流程一致。
