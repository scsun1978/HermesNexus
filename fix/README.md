# 🚨 HermesNexus 生产环境紧急修复指南

## 📋 问题诊断

根据复测结果，生产环境存在以下关键问题：

### ❌ 当前状态
- **API v1兼容端点缺失**: `/api/v1/tasks` 等404错误
- **Edge节点配置错误**: 仍连接 `localhost:8080` 而非 `172.16.100.101:8082`
- **E2E链路中断**: 任务无法从pending状态执行

### ✅ 预期状态
- **API v1兼容**: `/api/v1/tasks` 应返回200 OK
- **Edge节点正确连接**: 连接到 `172.16.100.101:8082`
- **完整E2E链路**: 任务能正常执行并返回结果

---

## 🚀 立即修复方案

### 方案一：自动修复（推荐）

#### 1. 上传修复包到服务器

```bash
# 在本地机器上执行
cd /path/to/HermesNexus
scp -r fix/ scsun@172.16.100.101:/home/scsun/hermesnexus-fix/
```

#### 2. 登录服务器并执行修复

```bash
# 登录服务器
ssh scsun@172.16.100.101

# 进入修复目录
cd /home/scsun/hermesnexus-fix

# 赋予执行权限
chmod +x EXECUTE_FIX.sh api_v1_patch.py edge_fix.py

# 执行修复
./EXECUTE_FIX.sh
```

### 方案二：分步手动修复

如果自动修复脚本出现问题，按以下步骤手动修复：

#### 步骤1: 修复Cloud API

```bash
# 在服务器上执行
cd /home/scsun/hermesnexus-fix

# 修复Cloud API代码
python3 api_v1_patch.py /home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py

# 重启Cloud API
pkill -f v12_standard_cloud.py
sleep 3
cd /home/scsun/hermesnexus-code
nohup python3 cloud/api/v12_standard_cloud.py > /home/scsun/hermesnexus-logs/cloud-api-v12.log 2>&1 &
echo $! > /tmp/cloud-api-v12.pid
```

#### 步骤2: 修复Edge节点

```bash
# 在服务器上执行
cd /home/scsun/hermesnexus-fix

# 修复Edge节点配置
python3 edge_fix.py

# 或者手动修复
# 1. 停止旧Edge节点
pkill -f final-edge-node.py
sleep 2

# 2. 修复配置并启动
if [ -f "/home/scsun/hermesnexus-code/edge/enhanced_edge_node_v12.py" ]; then
    # 使用增强版Edge节点
    EDGE_FILE="/home/scsun/hermesnexus-code/edge/enhanced_edge_node_v12.py"
elif [ -f "/home/scsun/hermesnexus/final-edge-node.py" ]; then
    # 使用现有Edge节点
    EDGE_FILE="/home/scsun/hermesnexus/final-edge-node.py"
    cp "$EDGE_FILE" "$EDGE_FILE.backup"
    sed -i "s/localhost:8080/172.16.100.101:8082/g" "$EDGE_FILE"
fi

# 启动Edge节点
nohup python3 "$EDGE_FILE" > /home/scsun/hermesnexus-logs/edge-node-fixed.log 2>&1 &
echo $! > /tmp/edge-node-fixed.pid
```

#### 步骤3: 验证修复

```bash
# 等待服务启动
sleep 10

# 验证API v1端点
curl http://localhost:8082/api/v1/tasks

# 验证Edge节点
curl http://localhost:8081/health

# 创建测试任务
curl -X POST http://localhost:8082/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_id": "manual-test-'$(date +%s)'", "name": "手动修复测试", "job_type": "command", "target_node_id": "edge-test-001", "command": "echo \"Manual fix passed\"", "created_by": "manual-test"}'
```

---

## 📊 修复验证清单

### 基础验证 ✅

- [ ] Cloud API健康检查: `curl http://localhost:8082/health` → `healthy`
- [ ] API v1任务端点: `curl http://localhost:8082/api/v1/tasks` → 200 OK
- [ ] Edge节点健康: `curl http://localhost:8081/health` → `healthy`
- [ ] Edge节点端口: 健康响应中包含 `172.16.100.101:8082`

### 日志验证 ✅

- [ ] Cloud API日志无严重错误: `tail -20 /home/scsun/hermesnexus-logs/cloud-api-v12.log`
- [ ] Edge日志无localhost:8080错误: `tail -20 /home/scsun/hermesnexus-logs/edge-node-fixed.log`
- [ ] Edge日志显示正常连接: 包含 `172.16.100.101:8082`

### E2E验证 ✅

- [ ] 创建测试任务成功
- [ ] 任务状态变化: `pending` → `running` → `completed`
- [ ] 任务执行结果: 包含正确的stdout和返回码
- [ ] 时间戳完整: created_at, started_at, completed_at

---

## 🔍 详细验证命令

### 1. API端点验证

```bash
# 测试所有API v1端点
echo "=== API v1端点测试 ==="

# /api/v1/tasks
echo "1. /api/v1/tasks:"
curl -s http://localhost:8082/api/v1/tasks | python3 -m json.tool | head -10

# /api/v1/nodes/edge-test-001/heartbeat (需要POST)
echo "2. /api/v1/nodes/edge-test-001/heartbeat:"
curl -s -X POST http://localhost:8082/api/v1/nodes/edge-test-001/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"node_id": "edge-test-001", "timestamp": "'$(date -Iseconds)'"}'

# 检查响应状态
echo "3. 端点状态码:"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8082/api/v1/tasks
```

### 2. Edge节点验证

```bash
# Edge节点健康和配置检查
echo "=== Edge节点验证 ==="

# 健康检查
echo "1. 健康状态:"
curl -s http://localhost:8081/health | python3 -m json.tool

# 详细状态
echo "2. 详细状态:"
curl -s http://localhost:8081/status | python3 -m json.tool

# 检查连接配置
echo "3. 连接配置:"
curl -s http://localhost:8081/health | grep -o '172.16.100.101:8082'
```

### 3. E2E任务验证

```bash
# 创建并监控E2E测试任务
echo "=== E2E任务验证 ==="

# 创建任务
TASK_ID="e2e-fix-test-$(date +%s)"
echo "1. 创建测试任务: $TASK_ID"
curl -s -X POST http://localhost:8082/api/jobs \
  -H "Content-Type: application/json" \
  -d "{
    \"job_id\": \"$TASK_ID\",
    \"name\": \"紧急修复E2E测试\",
    \"job_type\": \"command\",
    \"target_node_id\": \"edge-test-001\",
    \"command\": \"echo 'Fix validation passed' && date\",
    \"created_by\": \"fix-validation\"
  }" | python3 -m json.tool

# 监控任务执行
echo "2. 监控任务执行 (每5秒检查一次，共6次):"
for i in {1..6}; do
    echo "=== 检查 $i/6 ==="
    curl -s http://localhost:8082/api/jobs | python3 -m json.tool | grep -A 10 "$TASK_ID"
    sleep 5
done

# 最终结果
echo "3. 最终任务状态:"
curl -s "http://localhost:8082/api/jobs" | python3 -m json.tool | grep -A 15 "$TASK_ID"
```

---

## 🔄 故障排查

### 问题1: API v1端点仍然404

**可能原因**: Cloud API代码未正确修复或服务未重启

**解决方法**:
```bash
# 1. 检查代码是否包含API v1端点
grep "api/v1/tasks" /home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py

# 2. 如果没有，重新运行修复脚本
cd /home/scsun/hermesnexus-fix
python3 api_v1_patch.py /home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py

# 3. 强制重启Cloud API
pkill -9 -f v12_standard_cloud.py
sleep 3
cd /home/scsun/hermesnexus-code
python3 cloud/api/v12_standard_cloud.py > /dev/null 2>&1 &
```

### 问题2: Edge节点仍连接localhost:8080

**可能原因**: Edge节点配置未修复或使用了错误的配置文件

**解决方法**:
```bash
# 1. 检查Edge节点配置
grep -r "localhost:8080" /home/scsun/hermesnexus*/ 2>/dev/null

# 2. 检查正在运行的Edge节点
ps aux | grep edge.*node

# 3. 完全重置Edge节点
pkill -9 -f edge.*node
sleep 2

# 4. 手动修复并启动
cd /home/scsun/hermesnexus-fix
python3 edge_fix.py
```

### 问题3: 任务不执行

**可能原因**: Edge节点未正确连接到Cloud API或任务轮询机制异常

**解决方法**:
```bash
# 1. 检查Edge节点日志中的连接错误
tail -50 /home/scsun/hermesnexus-logs/edge-node-fixed.log | grep -i error

# 2. 手动测试Edge节点获取任务的能力
curl -s http://localhost:8082/api/jobs | python3 -m json.tool | grep -A 5 "pending"

# 3. 检查网络连通性
ping -c 3 172.16.100.101
curl -v http://172.16.100.101:8082/health

# 4. 重启整个服务栈
pkill -f "v12_standard_cloud\|edge.*node"
sleep 5
cd /home/scsun/hermesnexus-fix
./EXECUTE_FIX.sh
```

---

## 📈 成功标准

### 修复成功的标志

- ✅ **API v1兼容**: 所有 `/api/v1/*` 端点返回200 OK
- ✅ **Edge连接**: Edge节点日志显示连接到 `172.16.100.101:8082`
- ✅ **任务执行**: 测试任务在20秒内完成，状态变为 `completed`
- ✅ **结果正确**: 任务返回正确的stdout和返回码0

### 验证E2E成功

```bash
# 执行完整的E2E验证
curl -X POST http://localhost:8082/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_id": "final-test-'$(date +%s)'", "name": "最终验证", "job_type": "command", "target_node_id": "edge-test-001", "command": "echo \"HermesNexus E2E success\"", "created_by": "final-test"}'

# 等待20秒
sleep 20

# 检查任务状态
curl -s http://localhost:8082/api/jobs | grep -A 10 "final-test" | grep completed

# 如果返回"completed"，说明E2E修复成功！
```

---

## 🎯 预期时间线

- **修复执行**: 5-8分钟
- **服务启动**: 3-5分钟
- **E2E验证**: 15-20分钟
- **总计**: 30分钟内完成

---

## 📞 支持

如遇到问题：

1. **检查日志**: `/home/scsun/hermesnexus-logs/`
2. **验证进程**: `ps aux | grep -E "cloud|edge"`
3. **测试连接**: `curl -v http://localhost:8082/health`
4. **回滚方案**: 使用备份文件恢复原始状态

---

**🚨 紧急修复完成后，系统应从"Partially ready"状态升级到"完整E2E通过"！**