# HermesNexus 运维手册

## 基础信息

### 系统架构
- **云端控制平面**: FastAPI应用 (端口8080)
- **边缘节点运行时**: 异步Python应用
- **数据存储**: SQLite数据库
- **通信协议**: HTTP/RESTful API

### 目录结构
```
HermesNexus/
├── cloud/           # 云端服务
├── edge/           # 边缘节点
├── shared/         # 共享模块
├── console/        # Web控制台
├── data/          # 数据目录
├── logs/          # 日志目录
├── backups/       # 备份目录
├── scripts/       # 运维脚本
└── docs/          # 文档
```

## 日常运维操作

### 1. 系统启动

#### 完整启动
```bash
# 使用一键部署脚本
./scripts/deploy.sh deploy

# 或手动启动
export DB_TYPE=sqlite
export SQLITE_DB_PATH="./data/hermesnexus.db"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
source venv/bin/activate

# 启动云端API
python cloud/api/main.py &

# 启动边缘节点
python -m edge.runtime.core &
```

#### 检查启动状态
```bash
# 健康检查
curl http://localhost:8080/health

# 系统状态
curl http://localhost:8080/api/v1/stats

# 服务进程
ps aux | grep python
```

### 2. 系统停止

#### 正常停止
```bash
# 使用部署脚本
./scripts/deploy.sh stop

# 或手动停止
pkill -f "python.*cloud/api/main.py"
pkill -f "python.*edge/runtime/core.py"
```

#### 强制停止
```bash
# 强制终止所有相关进程
pkill -9 -f "python.*main.py"
pkill -9 -f "python.*core.py"
```

### 3. 系统重启

#### 优雅重启
```bash
# 使用部署脚本
./scripts/deploy.sh restart

# 或手动重启
./scripts/deploy.sh stop
sleep 3
./scripts/deploy.sh deploy
```

#### 滚动重启 (无停机)
```bash
# 先启动新实例
./scripts/deploy.sh deploy

# 确认新实例正常后停止旧实例
./scripts/deploy.sh stop
```

### 4. 日常监控

#### 系统健康检查
```bash
# 使用健康检查脚本
./scripts/deploy.sh health

# 手动检查各组件
curl http://localhost:8080/health
curl http://localhost:8080/api/v1/stats
curl http://localhost:8080/api/v1/nodes
curl http://localhost:8080/api/v1/jobs
```

#### 日志监控
```bash
# 查看实时日志
tail -f logs/cloud_api.log
tail -f logs/edge_node.log

# 查看错误日志
grep -i error logs/cloud_api.log
grep -i error logs/edge_node.log

# 查看最近的活动
tail -100 logs/cloud_api.log
```

#### 资源监控
```bash
# 系统资源
top
htop

# 磁盘使用
df -h

# 内存使用
free -h

# 网络连接
netstat -an | grep 8080
lsof -i :8080
```

### 5. 数据备份

#### 自动备份
```bash
# 完整备份 (数据库+配置+日志)
./scripts/backup.sh full

# 仅备份数据库
./scripts/backup.sh db

# 仅备份配置
./scripts/backup.sh configs

# 仅备份日志
./scripts/backup.sh logs
```

#### 查看备份
```bash
# 列出所有备份
./scripts/backup.sh list

# 备份统计
./scripts/backup.sh stats
```

#### 数据恢复
```bash
# 验证备份完整性
./scripts/backup.sh verify /path/to/backup.db.gz

# 恢复数据库
./scripts/backup.sh restore /path/to/backup.db.gz
```

#### 定时备份
```bash
# 设置定时备份 (每天凌晨2点)
./scripts/backup.sh cron "0 2 * * *"

# 查看定时任务
crontab -l
```

### 6. 配置管理

#### 环境配置
```bash
# 查看当前配置
cat .env

# 切换到生产配置
cp .env.production .env

# 编辑配置
nano .env
vim .env
```

#### 配置验证
```bash
# 验证配置文件语法
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('配置加载成功')"

# 测试配置
curl http://localhost:8080/health
```

## 故障排查

### 常见问题及解决方案

#### 1. 服务无法启动

**症状**: 执行启动命令后服务没有响应

**排查步骤**:
```bash
# 1. 检查端口占用
lsof -i :8080
netstat -an | grep 8080

# 2. 检查进程状态
ps aux | grep python

# 3. 检查日志文件
tail -50 logs/cloud_api.log

# 4. 检查配置文件
cat .env | grep -v "^#" | grep -v "^$"

# 5. 检查依赖安装
source venv/bin/activate
pip list | grep hermes
```

**解决方案**:
```bash
# 端口被占用
pkill -f "python.*main.py"
# 或修改配置中的端口
CLOUD_SERVICE_PORT=8081

# 依赖缺失
source venv/bin/activate
pip install -r requirements.txt

# 配置错误
cp .env.example .env
# 重新配置必要参数
```

#### 2. API请求失败

**症状**: API请求返回错误或超时

**排查步骤**:
```bash
# 1. 检查服务状态
curl http://localhost:8080/health

# 2. 检查错误日志
tail -20 logs/cloud_api.log

# 3. 检查数据库状态
ls -lh data/hermesnexus.db

# 4. 测试网络连接
curl -v http://localhost:8080/api/v1/stats
```

**常见错误**:
```bash
# 502 Bad Gateway
# 原因: 服务未启动或崩溃
# 解决: 重启服务

# 504 Gateway Timeout
# 原因: 服务响应超时
# 解决: 检查系统负载，增加超时时间

# 404 Not Found
# 原因: API路径错误
# 解决: 检查API文档，确认正确路径
```

#### 3. 数据库问题

**症状**: 数据操作失败或数据丢失

**排查步骤**:
```bash
# 1. 检查数据库文件
ls -lh data/hermesnexus.db

# 2. 验证数据库完整性
sqlite3 data/hermesnexus.db "PRAGMA integrity_check;"

# 3. 检查数据库内容
sqlite3 data/hermesnexus.db "SELECT COUNT(*) FROM nodes;"

# 4. 检查数据库锁定
lsof | grep hermesnexus.db
```

**解决方案**:
```bash
# 数据库损坏
# 恢复最近的备份
./scripts/backup.sh restore /path/to/backup.db.gz

# 数据库锁定
pkill -f "python.*main.py"
# 等待几秒后重启

# 数据库文件缺失
# 检查配置中的数据库路径
cat .env | grep SQLITE_DB_PATH
```

#### 4. 节点连接问题

**症状**: 边缘节点无法连接到云端

**排查步骤**:
```bash
# 1. 检查网络连接
curl http://localhost:8080/health

# 2. 检查节点状态
curl http://localhost:8080/api/v1/nodes

# 3. 检查节点日志
tail -50 logs/edge_node.log

# 4. 测试API端点
curl -X POST http://localhost:8080/api/v1/nodes/test-node/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"status":"online","cpu_usage":25.5,"memory_usage":65.3,"active_tasks":0}'
```

**解决方案**:
```bash
# 网络不通
# 检查防火墙设置
# 检查云服务器URL配置
cat .env | grep CLOUD_SERVER_URL

# 认证失败
# 检查API密钥配置
cat .env | grep API_KEY

# 节点配置错误
# 重新注册节点
# 检查节点ID配置
```

#### 5. 性能问题

**症状**: 系统响应慢或资源占用高

**排查步骤**:
```bash
# 1. 检查系统资源
top
htop

# 2. 检查进程资源
ps aux | grep python

# 3. 检查数据库性能
sqlite3 data/hermesnexus.db "EXPLAIN QUERY PLAN SELECT * FROM jobs;"

# 4. 检查API响应时间
time curl http://localhost:8080/api/v1/stats
```

**优化方案**:
```bash
# 数据库优化
# 添加索引
# 清理过期数据
# 定期执行VACUUM

# 应用优化
# 增加worker数量
# 调整超时参数
# 启用缓存机制

# 系统优化
# 增加内存
# 升级CPU
# 优化网络配置
```

## 应急处理

### 紧急故障处理流程

#### 1. 服务完全停止
```bash
# 立即尝试重启服务
./scripts/deploy.sh restart

# 如果重启失败，检查系统状态
./scripts/deploy.sh health

# 查看详细错误日志
tail -100 logs/cloud_api.log
tail -100 logs/edge_node.log
```

#### 2. 数据损坏
```bash
# 立即停止服务防止进一步损坏
./scripts/deploy.sh stop

# 恢复最近的备份
./scripts/backup.sh restore /path/to/latest/backup.db.gz

# 验证恢复的数据
curl http://localhost:8080/api/v1/stats

# 重启服务
./scripts/deploy.sh deploy
```

#### 3. 安全事件
```bash
# 立即停止所有服务
./scripts/deploy.sh stop

# 保存现场数据
./scripts/backup.sh full

# 检查日志文件中的异常活动
grep -i "attack\|breach\|unauthorized" logs/*.log

# 通知相关人员
# 按安全应急响应流程处理
```

### 恢复计划

#### 数据恢复优先级
1. **高优先级**: 数据库文件
2. **中优先级**: 配置文件
3. **低优先级**: 日志文件

#### 恢复验证清单
- [ ] 服务启动成功
- [ ] 健康检查通过
- [ ] 数据完整性验证
- [ ] 核心功能测试
- [ ] 性能指标正常
- [ ] 监控告警正常

## 维护计划

### 日常维护 (每日)
- [ ] 检查系统健康状态
- [ ] 查看错误日志
- [ ] 监控资源使用
- [ ] 验证备份完成

### 周期维护 (每周)
- [ ] 清理过期日志
- [ ] 检查磁盘空间
- [ ] 审查安全日志
- [ ] 性能评估

### 月度维护 (每月)
- [ ] 全面备份验证
- [ ] 安全更新检查
- [ ] 性能优化评估
- [ ] 容量规划评估
- [ ] 文档更新

---

**运维手册版本**: v1.0  
**最后更新**: 2024年4月11日  
**维护状态**: 活跃维护