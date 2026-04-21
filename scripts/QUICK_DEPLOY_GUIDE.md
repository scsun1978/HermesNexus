# HermesNexus Cloud API v1.2.0 快速部署指南

## 🚀 5分钟快速部署

### 前置条件
- 服务器访问权限: scsun@172.16.100.101
- Python 3.x 环境
- 端口 8082 可用

### 部署步骤

#### 方式一：直接复制部署（推荐）

1. **在本地机器上准备部署文件**
   ```bash
   # 确认部署包已准备好
   ls -la deploy-cloud-api-update/
   ```

2. **登录到生产服务器**
   ```bash
   ssh scsun@172.16.100.101
   ```

3. **在服务器上创建更新目录**
   ```bash
   mkdir -p /home/scsun/hermesnexus-update
   cd /home/scsun/hermesnexus-update
   ```

4. **从本地上传部署文件到服务器** (在本地机器执行)
   ```bash
   # 上传更新的代码文件
   scp cloud/api/v12_standard_cloud.py scsun@172.16.100.101:/home/scsun/hermesnexus-update/

   # 上传部署脚本
   scp scripts/manual-deploy-guide.sh scsun@172.16.100.101:/home/scsun/hermesnexus-update/
   ```

5. **在服务器上执行部署** (在服务器上执行)
   ```bash
   cd /home/scsun/hermesnexus-update
   chmod +x manual-deploy-guide.sh
   ./manual-deploy-guide.sh
   ```

#### 方式二：手动更新文件

1. **登录服务器**
   ```bash
   ssh scsun@172.16.100.101
   ```

2. **备份现有文件**
   ```bash
   cp /home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py \
      /home/scsun/hermesnexus-backups/v12_standard_cloud.py.backup.$(date +%Y%m%d_%H%M%S)
   ```

3. **停止现有服务**
   ```bash
   pkill -f "python.*v12_standard_cloud.py"
   ```

4. **更新代码文件** (需要先上传新文件到服务器)
   ```bash
   # 假设新文件已经上传到 /home/scsun/hermesnexus-update/
   cp /home/scsun/hermesnexus-update/v12_standard_cloud.py \
      /home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py
   ```

5. **启动新服务**
   ```bash
   cd /home/scsun/hermesnexus-code
   nohup python3 cloud/api/v12_standard_cloud.py \
      > /home/scsun/hermesnexus-logs/cloud-api-v12.log 2>&1 &
   echo $! > /tmp/cloud-api-v12.pid
   ```

6. **验证部署**
   ```bash
   # 健康检查
   curl http://localhost:8082/health

   # 测试API v1端点
   curl http://localhost:8082/api/v1/tasks
   ```

## 🔍 部署验证

### 基础检查
```bash
# 1. 检查进程状态
ps aux | grep v12_standard_cloud

# 2. 检查端口监听
lsof -i :8082

# 3. 健康检查
curl http://localhost:8082/health
```

### API端点测试
```bash
# API v1兼容端点
curl http://localhost:8082/api/v1/tasks
curl http://localhost:8082/api/nodes
curl http://localhost:8082/api/jobs

# 监控端点
curl http://localhost:8082/monitoring/health
curl http://localhost:8082/monitoring/metrics
```

### Edge节点验证
```bash
# 检查Edge节点状态
curl http://172.16.200.94:8081/health

# 查看Edge节点日志
tail -f /home/scsun/hermesnexus-logs/edge-node.log
```

## 📊 预期结果

### 成功标志
- ✅ 健康检查返回 `"status": "healthy"`
- ✅ `/api/v1/tasks` 返回任务列表（不再404）
- ✅ Edge节点日志不再显示连接错误
- ✅ 进程稳定运行，PID文件存在

### 服务信息
```
📍 Cloud API: http://172.16.100.101:8082
💚 Edge节点: http://172.16.200.94:8081
📊 监控指标: http://172.16.100.101:8082/monitoring/metrics
📋 任务管理: http://172.16.100.101:8082/api/jobs
```

## 🔄 回滚方案

如果出现问题，立即执行回滚：

```bash
# 1. 停止新服务
kill $(cat /tmp/cloud-api-v12.pid)

# 2. 恢复备份
LATEST_BACKUP=$(ls -t /home/scsun/hermesnexus-backups/v12_standard_cloud.py.backup.* | head -1)
cp "$LATEST_BACKUP" /home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py

# 3. 重启服务
cd /home/scsun/hermesnexus-code
nohup python3 cloud/api/v12_standard_cloud.py \
   > /home/scsun/hermesnexus-logs/cloud-api-v12.log 2>&1 &
echo $! > /tmp/cloud-api-v12.pid

# 4. 验证回滚
curl http://localhost:8082/health
```

## 📝 管理命令

### 日常管理
```bash
# 查看日志
tail -f /home/scsun/hermesnexus-logs/cloud-api-v12.log

# 重启服务
kill $(cat /tmp/cloud-api-v12.pid) && \
nohup python3 /home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py \
   > /home/scsun/hermesnexus-logs/cloud-api-v12.log 2>&1 & \
echo $! > /tmp/cloud-api-v12.pid

# 停止服务
kill $(cat /tmp/cloud-api-v12.pid)
```

### 监控命令
```bash
# 系统状态
curl http://localhost:8082/monitoring/health | python3 -m json.tool

# 性能指标
curl http://localhost:8082/monitoring/metrics | grep hermes_system

# 任务统计
curl http://localhost:8082/api/jobs | python3 -m json.tool
```

## 🎯 关键改进

本次部署解决了以下问题：

1. **API 404错误** - 新增 `/api/v1/tasks` 等兼容端点
2. **Edge连接失败** - 统一端口为8082，修正连接配置
3. **任务执行链路** - 完整的端到端任务执行流程
4. **错误处理** - 完善的异常处理和日志记录

## ⚠️ 注意事项

1. **端口配置**: 确保使用端口8082（不是8080）
2. **权限检查**: 确保数据库文件有正确权限
3. **内存监控**: 注意监控服务内存使用情况
4. **日志轮转**: 定期清理日志文件，避免磁盘满

## 📞 故障排查

### 问题1: 服务启动失败
```bash
# 查看错误日志
tail -50 /home/scsun/hermesnexus-logs/cloud-api-v12.log

# 检查端口占用
lsof -i :8082

# 检查Python环境
python3 --version
```

### 问题2: API响应异常
```bash
# 查看API调用日志
grep "api/v1" /home/scsun/hermesnexus-logs/cloud-api-v12.log

# 测试基础连接
curl -v http://localhost:8082/health
```

### 问题3: Edge节点连接问题
```bash
# 检查Edge节点状态
curl http://172.16.200.94:8081/health

# 查看Edge节点日志
tail -f /home/scsun/hermesnexus-logs/edge-node.log

# 检查网络连接
ping 172.16.200.94
```

---

**部署时间**: 约5分钟
**验证时间**: 约10分钟
**总计**: 15分钟内完成部署和验证

🎯 **部署完成后，系统将具备完整的API v1兼容性，Edge节点可以正常连接和执行任务。**