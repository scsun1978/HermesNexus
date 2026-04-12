# Task #59 Execution Plan: Service-Side and Edge Node Minimum Chain

**目标**: 验证注册→心跳→任务→结果闭环  
**目标服务器**: scsun@172.16.100.101:22  
**当前状态**: 🔄 等待服务器连接恢复  

---

## 📋 执行前检查清单

### 网络连接验证 ✅
- [ ] SSH连接测试: `ssh -o ConnectTimeout=5 scsun@172.16.100.101 "whoami"`
- [ ] 网络连通性: `ping -c 3 172.16.100.101`
- [ ] 端口可达性: `nc -zv 172.16.100.101 22`

### 服务器环境检查 🔄
- [ ] Python版本验证: `python3 --version` (需要 >= 3.14)
- [ ] 磁盘空间检查: `df -h` (需要 > 5GB)
- [ ] 内存可用性: `free -h` (需要 > 2GB)
- [ ] 系统服务状态: `systemctl list-units | grep hermes`

### 文件准备状态 ✅
- [x] 部署脚本已创建: `scripts/dev-server-*.sh`
- [x] 配置文件模板已准备: `configs/dev-server/*.env`
- [x] 项目代码已同步: 所有最新代码已提交
- [x] 测试套件已通过: 87/87 测试通过

---

## 🚀 执行步骤 (按顺序)

### Phase 1: 环境初始化

**步骤 1.1**: 传输部署文件到服务器
```bash
# 创建传输脚本
cat > deploy-to-server.sh << 'EOF'
#!/bin/bash
SERVER="scsun@172.16.100.101"
PROJECT_DIR="/home/scsun/hermesnexus"

# 传输部署脚本
scp scripts/dev-server-*.sh $SERVER:~/

# 传输项目文件
rsync -av --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
    . $SERVER:$PROJECT_DIR/

# 传输配置文件
scp -r configs/ $SERVER:$PROJECT_DIR/

echo "✅ 文件传输完成"
EOF

chmod +x deploy-to-server.sh
```

**步骤 1.2**: 执行环境初始化
```bash
# 在服务器上执行初始化
ssh scsun@172.16.100.101 << 'REMOTE_EOF'
cd ~
chmod +x dev-server-init.sh
./dev-server-init.sh
REMOTE_EOF
```

### Phase 2: 服务启动

**步骤 2.1**: 启动Cloud控制平面
```bash
# 在服务器上启动服务
ssh scsun@172.16.100.101 << 'REMOTE_EOF'
cd ~
chmod +x dev-server-start.sh
./dev-server-start.sh
REMOTE_EOF
```

**步骤 2.2**: 验证Cloud API就绪
```bash
# 从本地测试服务器API
curl http://172.16.100.101:8080/health
curl http://172.16.100.101:8080/api/v1/stats
curl http://172.16.100.101:8080/api/v1/nodes
```

### Phase 3: 云边通信链路验证

**步骤 3.1**: 边缘节点注册验证
```bash
# 检查节点注册状态
curl http://172.16.100.101:8080/api/v1/nodes | jq '.nodes[] | {node_id, name, status}'
```

**预期结果**:
```json
{
  "node_id": "dev-edge-node-001",
  "name": "开发服务器边缘节点",
  "status": "active",
  "last_heartbeat": "2026-04-11T12:00:00Z"
}
```

**步骤 3.2**: 心跳机制验证
```bash
# 监控节点心跳 (持续60秒)
watch -n 5 'curl -s http://172.16.100.101:8080/api/v1/nodes | jq ".nodes[0].last_heartbeat"'
```

**预期结果**: last_heartbeat 字段每5-10秒更新一次

### Phase 4: 任务执行闭环验证

**步骤 4.1**: 创建测试任务
```bash
# 创建一个简单的SSH执行任务
curl -X POST http://172.16.100.101:8080/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-task-001",
    "node_id": "dev-edge-node-001",
    "task_type": "ssh_command",
    "target": {
      "host": "localhost",
      "command": "echo Hello from HermesNexus",
      "username": "scsun"
    }
  }' | jq '.'
```

**预期结果**:
```json
{
  "task_id": "test-task-001",
  "status": "pending",
  "created_at": "2026-04-11T12:00:00Z"
}
```

**步骤 4.2**: 监控任务执行状态
```bash
# 轮询任务状态
TASK_ID="test-task-001"
while true; do
  STATUS=$(curl -s http://172.16.100.101:8080/api/v1/tasks/$TASK_ID | jq -r '.status')
  echo "任务状态: $STATUS"
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  
  sleep 2
done
```

**步骤 4.3**: 验证任务结果
```bash
# 获取完整任务详情
curl -s http://172.16.100.101:8080/api/v1/tasks/test-task-001 | jq '.'

# 检查执行结果
curl -s http://172.16.100.101:8080/api/v1/tasks/test-task-001 | jq -r '.result.output'
```

**预期结果**: 任务状态变为 "completed"，输出包含 "Hello from HermesNexus"

### Phase 5: 完整链路压力测试

**步骤 5.1**: 批量任务创建
```bash
# 创建10个并发任务
for i in {1..10}; do
  curl -X POST http://172.16.100.101:8080/api/v1/tasks \
    -H "Content-Type: application/json" \
    -d "{
      \"task_id\": \"batch-task-$i\",
      \"node_id\": \"dev-edge-node-001\",
      \"task_type\": \"ssh_command\",
      \"target\": {
        \"host\": \"localhost\",
        \"command\": \"echo Task $i executed successfully\",
        \"username\": \"scsun\"
      }
    }" &
done
wait
```

**步骤 5.2**: 验证并发处理
```bash
# 检查所有任务状态
sleep 10
curl -s http://172.16.100.101:8080/api/v1/tasks | jq '.tasks | length'
curl -s http://172.16.100.101:8080/api/v1/tasks | jq '.tasks[] | {task_id, status}'
```

### Phase 6: 故障恢复验证

**步骤 6.1**: 模拟边缘节点故障
```bash
# 停止边缘节点服务
ssh scsun@172.16.100.101 "sudo systemctl stop hermesnexus-edge"

# 等待30秒，检查心跳超时检测
sleep 30
curl -s http://172.16.100.101:8080/api/v1/nodes | jq '.nodes[0].status'
```

**预期结果**: 节点状态变为 "inactive" 或 "timeout"

**步骤 6.2**: 边缘节点恢复
```bash
# 重启边缘节点
ssh scsun@172.16.100.101 "sudo systemctl start hermesnexus-edge"

# 等待重新注册
sleep 10
curl -s http://172.16.100.101:8080/api/v1/nodes | jq '.nodes[0].status'
```

**预期结果**: 节点状态恢复为 "active"

---

## 📊 验证标准

### 成功标准 ✅
- [ ] Cloud API在8080端口正常响应
- [ ] 边缘节点成功注册到控制平面
- [ ] 心跳机制稳定运行 (10秒间隔)
- [ ] 任务创建→分配→执行→结果闭环完成
- [ ] 并发任务处理正常 (>5个并发)
- [ ] 故障检测和自动恢复工作正常

### 性能指标 📈
- [ ] API响应时间 < 100ms (本地网络)
- [ ] 任务执行延迟 < 5秒
- [ ] 心跳超时检测 < 30秒
- [ ] 内存使用稳定 (< 500MB per service)
- [ ] CPU使用率正常 (< 50% per service)

### 稳定性保证 🛡️
- [ ] 服务运行 > 1小时无崩溃
- [ ] 数据库事务一致性保证
- [ ] 错误处理和日志记录完整
- [ ] systemd服务自动重启功能

---

## 🔄 故障排除指南

### 常见问题诊断

**问题1: API服务无响应**
```bash
# 检查Cloud服务状态
ssh scsun@172.16.100.101 "systemctl status hermesnexus-cloud"

# 查看Cloud日志
ssh scsun@172.16.100.101 "journalctl -u hermesnexus-cloud -n 50 -f"

# 检查端口监听
ssh scsun@172.16.100.101 "netstat -tulpn | grep 8080"
```

**问题2: 边缘节点未注册**
```bash
# 检查Edge服务状态
ssh scsun@172.16.100.101 "systemctl status hermesnexus-edge"

# 查看Edge日志
ssh scsun@172.16.100.101 "journalctl -u hermesnexus-edge -n 50 -f"

# 手动测试API连接
ssh scsun@172.16.100.101 "curl -s http://localhost:8080/health"
```

**问题3: 任务执行失败**
```bash
# 检查任务详情
curl http://172.16.100.101:8080/api/v1/tasks/test-task-001 | jq '.'

# 查看错误信息
curl http://172.16.100.101:8080/api/v1/tasks/test-task-001 | jq '.error'

# 检查SSH连接
ssh scsun@172.16.100.101 "ssh -v localhost 'echo test'"
```

---

## 📝 验证报告模板

执行完成后，填写验证报告：

```markdown
## 云边通信链路验证报告

**执行时间**: 2026-04-11 HH:MM:SS  
**执行人员**: [姓名]  
**服务器环境**: scsun@172.16.100.101  

### 验证结果摘要
- Cloud API状态: ✅/❌
- 边缘节点注册: ✅/❌
- 心跳机制: ✅/❌
- 任务执行: ✅/❌
- 并发处理: ✅/❌
- 故障恢复: ✅/❌

### 关键指标
- API响应时间: XX ms
- 任务执行延迟: XX 秒
- 并发任务数: XX 个
- 服务运行时间: XX 小时

### 发现问题
[记录遇到的问题和解决方案]

### 优化建议
[记录性能优化和改进建议]

### 结论
[总体评估和建议]
```

---

## 🎯 完成条件

Task #59 完成标准：
1. ✅ 所有Phase 1-6步骤执行完成
2. ✅ 验证标准全部达标
3. ✅ 故障排除预案验证
4. ✅ 完整验证报告生成
5. ✅ 云边通信链路稳定运行 > 1小时

**阻塞条件**: 
- 🔴 服务器网络连接不可达 (当前状态)
- 🟡 Python环境不满足要求
- 🟡 系统资源不足

---

*本执行计划将在服务器连接恢复后立即执行，预计完成时间: 2小时*