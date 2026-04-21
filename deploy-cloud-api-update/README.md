# HermesNexus Cloud API v1.2.0 更新部署说明

## 📋 更新内容

本次更新为Cloud API v1.2.0添加了API v1兼容层，解决了Edge节点与Cloud API之间的接口不匹配问题。

### 新增API端点

1. **GET /api/v1/tasks** - 获取任务列表（兼容Edge节点）
2. **POST /api/v1/nodes/<id>/heartbeat** - 节点心跳（兼容Edge节点）
3. **GET /api/v1/nodes/<id>/tasks/<task_id>/result** - 获取任务结果（兼容Edge节点）

### 问题修复

- ✅ 修复了Edge节点连接失败问题
- ✅ 修复了API 404错误
- ✅ 实现了完整的端到端任务执行链路

## 🚀 部署步骤

### 方式一：自动部署（推荐）

1. **上传整个部署包到服务器**
   ```bash
   scp -r deploy-cloud-api-update scsun@172.16.100.101:/home/scsun/
   ```

2. **登录服务器并执行更新**
   ```bash
   ssh scsun@172.16.100.101
   cd /home/scsun/deploy-cloud-api-update
   chmod +x update-cloud-api.sh
   ./update-cloud-api.sh
   ```

### 方式二：手动更新

1. **停止现有服务**
   ```bash
   pkill -f "python.*v12_standard_cloud.py"
   ```

2. **备份现有文件**
   ```bash
   cp /home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py \
      /home/scsun/hermesnexus-backups/v12_standard_cloud.py.backup.$(date +%Y%m%d_%H%M%S)
   ```

3. **更新代码**
   ```bash
   cp v12_standard_cloud.py /home/scsun/hermesnexus-code/cloud/api/
   ```

4. **启动新服务**
   ```bash
   cd /home/scsun/hermesnexus-code
   nohup python3 cloud/api/v12_standard_cloud.py > /home/scsun/hermesnexus-logs/cloud-api-v12.log 2>&1 &
   echo $! > /tmp/cloud-api-v12.pid
   ```

5. **验证部署**
   ```bash
   # 健康检查
   curl http://localhost:8082/health

   # 测试API v1端点
   curl http://localhost:8082/api/v1/tasks

   # 查看日志
   tail -f /home/scsun/hermesnexus-logs/cloud-api-v12.log
   ```

## 🔍 验证更新

### 1. 检查服务状态
```bash
# 检查进程
ps aux | grep v12_standard_cloud

# 检查端口
lsof -i :8082

# 检查健康状态
curl http://localhost:8082/health
```

### 2. 测试API端点
```bash
# 测试API v1任务端点
curl http://localhost:8082/api/v1/tasks

# 测试节点管理
curl http://localhost:8082/api/nodes

# 测试任务管理
curl http://localhost:8082/api/jobs
```

### 3. 验证Edge节点连接
```bash
# 检查Edge节点日志（应该不再有404错误）
tail -f /home/scsun/hermesnexus-logs/edge-node.log

# 测试Edge节点健康状态
curl http://172.16.200.94:8081/health
```

## 📊 监控和日志

### 查看服务日志
```bash
# Cloud API日志
tail -f /home/scsun/hermesnexus-logs/cloud-api-v12.log

# Edge节点日志
tail -f /home/scsun/hermesnexus-logs/edge-node.log

# 查看最近错误
grep -i error /home/scsun/hermesnexus-logs/cloud-api-v12.log
```

### 检查服务状态
```bash
# 使用状态脚本
/home/scsun/hermesnexus-code/scripts/status.sh

# 手动检查
curl http://localhost:8082/monitoring/health | python3 -m json.tool
curl http://localhost:8082/monitoring/metrics
```

## 🔄 回滚操作

如果更新出现问题，可以快速回滚：

1. **停止新服务**
   ```bash
   kill $(cat /tmp/cloud-api-v12.pid)
   ```

2. **恢复备份文件**
   ```bash
   LATEST_BACKUP=$(ls -t /home/scsun/hermesnexus-backups/v12_standard_cloud.py.backup.* | head -1)
   cp "$LATEST_BACKUP" /home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py
   ```

3. **重新启动**
   ```bash
   cd /home/scsun/hermesnexus-code
   nohup python3 cloud/api/v12_standard_cloud.py > /home/scsun/hermesnexus-logs/cloud-api-v12.log 2>&1 &
   echo $! > /tmp/cloud-api-v12.pid
   ```

## 🎯 关键改进

### API v1兼容层
- 新增 `/api/v1/tasks` 端点，返回任务列表
- 新增 `/api/v1/nodes/<id>/heartbeat` 端点，处理节点心跳
- 新增 `/api/v1/nodes/<id>/tasks/<id>/result` 端点，返回任务结果

### 错误处理
- 完善的异常处理和错误日志
- 详细的HTTP状态码返回
- 更好的错误信息提示

### 监控增强
- 更详细的审计日志
- API调用统计
- 性能监控指标

## 📞 支持

如遇到问题，请检查：
1. 服务日志文件
2. 系统资源使用情况
3. 网络连接状态
4. 数据库文件权限

## ⚠️ 注意事项

1. **端口配置**: 确保使用端口8082（不是8080）
2. **权限检查**: 确保数据库文件有正确的读写权限
3. **内存监控**: 注意监控服务内存使用情况
4. **定期备份**: 建议定期备份数据库和配置文件

更新时间: 2026-04-19
版本: v1.2.0 (API v1兼容层)
