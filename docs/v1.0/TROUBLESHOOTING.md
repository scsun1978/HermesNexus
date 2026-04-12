# HermesNexus Phase 2 故障排障 Runbook

**Version**: Phase 2 v2.0.0  
**Date**: 2026-04-12  
**Purpose**: 常见问题诊断和解决方案

## 快速诊断流程

### 第一步：确定问题类型

```
问题发生
    │
    ├─► 服务无法启动？
    │
    ├─► API 无响应？
    │
    ├─► 功能异常？
    │
    ├─► 性能问题？
    │
    └─► 数据错误？
```

## 服务启动问题

### 问题 1.1: 端口被占用

**症状**:
```
ERROR: [Errno 48] Address already in use
```

**诊断**:
```bash
# 检查端口占用
lsof -i :8080

# 或使用 netstat
netstat -tuln | grep 8080
```

**解决方案**:
```bash
# 方案1: 停止占用进程
pkill -f stable_cloud_api

# 方案2: 更换端口
export CLOUD_API_PORT=8081
./scripts/start-cloud-api.sh

# 方案3: 强制停止占用进程
kill -9 $(lsof -ti :8080)
```

### 问题 1.2: Python 模块缺失

**症状**:
```
ModuleNotFoundError: No module named 'fastapi'
```

**诊断**:
```bash
# 检查Python环境
python3 --version
which python3

# 检查虚拟环境
echo $VIRTUAL_ENV

# 检查已安装包
pip list | grep fastapi
```

**解决方案**:
```bash
# 重新安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 验证安装
python3 -c "import fastapi; print('FastAPI OK')"
```

### 问题 1.3: 配置文件错误

**症状**:
```
KeyError: 'CLOUD_API_PORT' or similar
```

**诊断**:
```bash
# 检查环境变量
env | grep HERMES

# 检查配置文件
ls -la .env*

# 验证配置
python3 scripts/validate-config.py --env development
```

**解决方案**:
```bash
# 重新生成配置文件
cp .env.development .env.local

# 或手动设置关键变量
export CLOUD_API_PORT=8080
export LOG_LEVEL=INFO
```

## API 响应问题

### 问题 2.1: API 超时

**症状**:
```
curl: (28) Failed to connect to localhost port 8080 after 10000ms
```

**诊断**:
```bash
# 检查服务状态
curl -v http://localhost:8080/health

# 检查服务进程
ps aux | grep stable_cloud_api

# 检查服务日志
tail -f logs/cloud-api.log
```

**解决方案**:
```bash
# 方案1: 重启服务
./scripts/stop-services.sh
./scripts/start-cloud-api.sh

# 方案2: 增加超时时间
export CLOUD_API_TIMEOUT=60
```

### 问题 2.2: API 返回 500 错误

**症状**:
```json
{"error": {"code": "INT_001", "message": "Database error"}}
```

**诊断**:
```bash
# 查看详细日志
tail -50 logs/cloud-api.log | grep ERROR

# 检查服务状态
curl http://localhost:8080/health

# 验证配置
python3 scripts/validate-config.py
```

**解决方案**:
```bash
# 根据错误类型处理
# INT_001: 数据库错误 -> 重启服务清理内存
# INT_002: 内部错误 -> 检查日志详细堆栈
# INT_003: 上游服务错误 -> 检查依赖服务
```

### 问题 2.3: 数据不一致

**症状**: 创建的数据查询不到

**诊断**:
```bash
# 检查内存数据（Phase 2 MVP）
# 当前实现使用内存存储，重启会丢失数据

# 验证API端点
curl http://localhost:8080/api/v1/assets/stats
curl http://localhost:8080/api/v1/tasks/stats
```

**解决方案**:
```bash
# 重启服务清理内存状态
./scripts/stop-services.sh
./scripts/start-cloud-api.sh

# 重新创建测试数据
# 这不是bug，Phase 2 MVP特性
```

## 功能异常问题

### 问题 3.1: 任务一直 Pending

**症状**: 创建的任务状态一直是 Pending

**诊断**:
```bash
# 检查任务详情
TASK_ID="<task_id>"
curl http://localhost:8080/api/v1/tasks/$TASK_ID

# 检查是否有节点在线
curl http://localhost:8080/api/v1/assets
```

**解决方案**:
```bash
# 确认任务创建时包含 node_id
# 或手动分发任务
curl -X POST http://localhost:8080/api/v1/tasks/dispatch \
  -H 'Content-Type: application/json' \
  -d '{
    "task_ids": ["'$TASK_ID'"],
    "target_node_id": "node-001",
    "dispatch_strategy": "batch"
  }'
```

### 问题 3.2: 审计日志缺失

**症状**: 某些操作没有审计记录

**诊断**:
```bash
# 检查审计统计
curl http://localhost:8080/api/v1/audit_logs/stats

# 搜索特定操作的审计日志
curl "http://localhost:8080/api/v1/audit_logs?search=<操作名称>"
```

**解决方案**:
```bash
# 检查审计服务是否正常
# Phase 2.2 中需要集成审计记录到各个服务

# 手动创建审计日志用于测试
curl -X POST http://localhost:8080/api/v1/audit_logs \
  -H 'Content-Type: application/json' \
  -d '{
    "action": "test_action",
    "category": "system",
    "level": "info",
    "actor": "admin",
    "target_type": "test",
    "message": "测试审计日志"
  }'
```

### 问题 3.3: 节点状态显示不正确

**症状**: 节点显示离线但实际在线

**诊断**:
```bash
# 检查资产状态
curl http://localhost:8080/api/v1/assets

# 检查最后心跳时间
# 节点超过120秒无心跳会被标记离线
```

**解决方案**:
```bash
# 触发节点心跳更新
# 在边缘节点上执行心跳请求
curl -X POST http://localhost:8080/api/v1/assets/<asset_id>/heartbeat
```

## 性能问题

### 问题 4.1: API 响应慢

**症状**: API请求超过1秒响应

**诊断**:
```bash
# 测试响应时间
time curl http://localhost:8080/health

# 检查系统资源
top -p $(pgrep -f stable_cloud_api)

# 检查网络连接
netstat -an | grep :8080 | wc -l
```

**解决方案**:
```bash
# 方案1: 增加Worker进程
export CLOUD_API_WORKERS=4

# 方案2: 优化日志级别
export LOG_LEVEL=WARNING  # 减少日志输出

# 方案3: 重启服务清理内存
./scripts/stop-services.sh
./scripts/start-cloud-api.sh
```

### 问题 4.2: 内存占用高

**症状**: 进程内存使用持续增长

**诊断**:
```bash
# 监控内存使用
watch -n 5 'ps aux | grep stable_cloud_api | awk "{sum+=$4} END {print sum}"'

# 检查内存泄漏
valgrind --leak-check=full python3 stable-cloud-api.py
```

**解决方案**:
```bash
# Phase 2 MVP 使用内存存储，大数据量会占用较多内存
# 定期重启服务清理内存
./scripts/stop-services.sh
./scripts/start-cloud-api.sh

# Phase 2 Full 会实现数据库持久化解决此问题
```

## 控制台问题

### 问题 5.1: 页面无法加载

**症状**: 浏览器显示404或空白页

**诊断**:
```bash
# 检查静态文件
ls -la console/
ls -la console/static/

# 检查文件权限
find console -type f -name "*.html" -exec ls -la {} \;

# 测试静态文件访问
curl -I http://localhost:8080/console/index.html
```

**解决方案**:
```bash
# 检查文件路径
# 确保文件在正确的位置

# 检查权限
chmod +x console/*.html
chmod -R 755 console/static/
```

### 问题 5.2: API 跨域问题

**症状**: 浏览器控制台显示CORS错误

**诊断**:
```bash
# 检查API响应头
curl -I http://localhost:8080/api/v1/assets

# 查看CORS配置
grep -r "CORS" .env* || grep -r "cors" *.py
```

**解决方案**:
```bash
# Phase 2 MVP 默认允许所有源
# 如果有限制，更新配置
export CORS_ORIGINS="http://localhost:3000,http://localhost:8080"
```

## 数据问题

### 问题 6.1: 数据丢失

**症状**: 重启服务后数据不见了

**说明**: Phase 2 MVP 使用内存存储，这是**预期行为**

**解决方案**:
```bash
# 这不是bug，Phase 2 MVP 设计特点
# Phase 2 Full 会实现数据库持久化

# 临时方案：
# 1. 避免重启服务
# 2. 在重启前手动备份重要数据
# 3. 使用导出功能保存数据
```

### 问题 6.2: 统计数据不准确

**症状**: 仪表板显示的数据与实际不符

**诊断**:
```bash
# 验证统计API
curl http://localhost:8080/api/v1/assets/stats | jq '.'
curl http://localhost:8080/api/v1/tasks/stats | jq '.'

# 手动计算验证
curl http://localhost:8080/api/v1/assets | jq '.total'
curl http://localhost:8080/api/v1/tasks | jq '.total'
```

**解决方案**:
```bash
# 刷新浏览器缓存
# 按Ctrl+Shift+R 强制刷新

# 清空浏览器缓存
# Chrome: F12 -> Application -> Clear storage

# 重启服务重新计算统计
./scripts/stop-services.sh
./scripts/start-cloud-api.sh
```

## 紧急故障处理

### 服务完全崩溃

```bash
# 1. 立即停止所有服务
./scripts/stop-services.sh

# 2. 检查系统资源
df -h
free -h
top

# 3. 清理日志（如果磁盘满）
> logs/cloud-api.log
> logs/edge-node.log

# 4. 重新启动服务
./scripts/start-cloud-api.sh

# 5. 验证恢复
curl http://localhost:8080/health
```

### 回滚到上一版本

```bash
# 1. 停止服务
./scripts/stop-services.sh

# 2. 恢复备份版本
cd ..
git checkout <previous-version>
git pull

# 3. 重新启动
cd hermesnexus
./scripts/start-cloud-api.sh

# 4. 验证功能
./tests/scripts/smoke_test.sh
```

## 联系支持

### 何时联系支持

- **严重问题**: 服务完全不可用，影响生产环境
- **数据问题**: 数据丢失或损坏风险
- **安全问题**: 发现安全漏洞或攻击
- **无法解决**: 遵循本Runbook仍无法解决的问题

### 联系前准备

1. 收集错误信息：
   - 完整错误消息
   - 错误发生时间
   - 操作步骤

2. 系统状态信息：
   - 服务状态：`./scripts/status.sh`
   - 系统资源：`top`, `df -h`, `free -h`
   - 日志文件：`logs/cloud-api.log` (最后100行)

3. 环境信息：
   - Python版本：`python3 --version`
   - 配置文件：`cat .env.local`
   - Git版本：`git log -1`

### 支持渠道

- **GitHub Issues**: https://github.com/your-repo/issues
- **文档**: 查看 `docs/` 目录
- **Runbook**: 本文档

---

**最后更新**: 2026-04-12  
**适用版本**: Phase 2 v2.0.0  
**维护者**: Development Team
