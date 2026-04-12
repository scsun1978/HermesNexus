# HermesNexus 生产环境测试计划

## 📋 测试计划概览
**创建时间**: 2026年4月11日  
**测试环境**: scsun@172.16.100.101:22  
**测试类型**: 功能测试、性能测试、稳定性测试、安全测试  
**预计测试时间**: 3-4小时  

---

## 🎯 测试目标

验证HermesNexus在生产环境中的：
- ✅ 功能完整性和正确性
- ✅ 性能表现和扩展能力
- ✅ 系统稳定性和可靠性
- ✅ 安全性和数据保护
- ✅ 运维便利性和可维护性

---

## 📊 测试范围和覆盖率

### 功能测试 (40%)
- API接口测试
- 云边协同测试
- 数据持久化测试
- 设备管理测试
- 任务执行测试

### 性能测试 (25%)
- 响应时间测试
- 并发负载测试
- 资源使用测试
- 长期运行稳定性测试

### 稳定性测试 (20%)
- 故障恢复测试
- 数据备份恢复测试
- 异常处理测试
- 边界条件测试

### 安全测试 (15%)
- 认证授权测试
- 数据安全测试
- 网络安全测试
- 输入验证测试

---

## 🧪 详细测试用例

### 测试套件1: API功能测试 (1小时)

#### TC-API-001: 健康检查接口
**测试目标**: 验证健康检查接口正常工作

**前置条件**: 服务已启动

**测试步骤**:
```bash
curl -X GET http://172.16.100.101:8080/health
```

**预期结果**:
```json
{
  "status": "healthy",
  "timestamp": "2026-04-11T10:00:00Z",
  "version": "1.1.0"
}
```

**验证点**:
- [ ] HTTP状态码为200
- [ ] 返回JSON格式正确
- [ ] status字段为"healthy"
- [ ] timestamp有效
- [ ] version符合预期

#### TC-API-002: 节点列表查询
**测试目标**: 验证节点列表接口功能正常

**测试步骤**:
```bash
curl -X GET http://172.16.100.101:8080/api/v1/nodes
```

**预期结果**:
```json
{
  "total": 1,
  "nodes": [
    {
      "node_id": "edge-node-001",
      "name": "边缘节点001",
      "status": "online",
      "ip_address": "192.168.1.100",
      "last_heartbeat": "2026-04-11T10:00:00Z"
    }
  ]
}
```

**验证点**:
- [ ] 返回节点列表
- [ ] 节点信息完整
- [ ] 状态字段正确
- [ ] 时间戳格式正确

#### TC-API-003: 设备创建接口
**测试目标**: 验证设备创建功能

**测试步骤**:
```bash
curl -X POST http://172.16.100.101:8080/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test-device-api",
    "name": "API测试设备",
    "type": "ssh",
    "host": "localhost",
    "port": 22,
    "config": {"username": "test"}
  }'
```

**预期结果**:
```json
{
  "status": "success",
  "message": "设备创建成功",
  "device_id": "test-device-api"
}
```

**验证点**:
- [ ] 设备创建成功
- [ ] 返回设备ID
- [ ] 设备信息可查询

#### TC-API-004: 任务创建和执行
**测试目标**: 验证完整任务执行流程

**测试步骤**:
```bash
# 1. 创建任务
curl -X POST http://172.16.100.101:8080/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "api-test-job-001",
    "node_id": "edge-node-001",
    "task_type": "execute",
    "command": "echo API Test",
    "priority": "normal"
  }'

# 2. 查询任务状态
curl http://172.16.100.101:8080/api/v1/jobs/api-test-job-001

# 3. 查询执行结果
curl http://172.16.100.101:8080/api/v1/jobs/api-test-job-001/events
```

**验证点**:
- [ ] 任务创建成功
- [ ] 任务状态变化正常
- [ ] 执行结果正确回传
- [ ] 事件记录完整

### 测试套件2: 数据持久化测试 (45分钟)

#### TC-DB-001: 数据库写入测试
**测试目标**: 验证数据库写入功能

**测试步骤**:
```bash
# 创建测试数据
for i in {1..10}; do
  curl -X POST http://172.16.100.101:8080/api/v1/devices \
    -H "Content-Type: application/json" \
    -d "{
      \"device_id\": \"test-device-$i\",
      \"name\": \"测试设备$i\",
      \"type\": \"ssh\",
      \"host\": \"localhost\",
      \"port\": 22
    }"
done

# 验证数据写入
curl http://172.16.100.101:8080/api/v1/devices
```

**验证点**:
- [ ] 所有设备创建成功
- [ ] 数据库记录完整
- [ ] 数据一致性正确

#### TC-DB-002: 数据重启恢复测试
**测试目标**: 验证服务重启后数据持久化

**测试步骤**:
```bash
# 1. 创建测试数据
curl -X POST http://172.16.100.101:8080/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "restart-test-job",
    "node_id": "edge-node-001",
    "task_type": "execute",
    "command": "echo restart-test"
  }'

# 2. 记录当前状态
curl http://172.16.100.101:8080/api/v1/stats > before_restart.json

# 3. 重启服务
sudo systemctl restart hermesnexus
sleep 10

# 4. 验证数据恢复
curl http://172.16.100.101:8080/api/v1/stats > after_restart.json

# 5. 对比数据
diff before_restart.json after_restart.json
```

**验证点**:
- [ ] 服务重启成功
- [ ] 数据完全保留
- [ ] 统计数据一致
- [ ] 无数据丢失

#### TC-DB-003: SQLite完整性检查
**测试目标**: 验证SQLite数据库完整性

**测试步骤**:
```bash
# 检查数据库文件
sqlite3 data/hermesnexus.db "PRAGMA integrity_check;"

# 检查数据库统计
sqlite3 data/hermesnexus.db "SELECT 'nodes', COUNT(*) FROM nodes 
UNION ALL SELECT 'devices', COUNT(*) FROM devices 
UNION ALL SELECT 'jobs', COUNT(*) FROM jobs 
UNION ALL SELECT 'events', COUNT(*) FROM events;"
```

**验证点**:
- [ ] 完整性检查通过
- [ ] 数据统计正确
- [ ] 无损坏页面
- [ ] 索引正常工作

### 测试套件3: 备份恢复测试 (30分钟)

#### TC-BACKUP-001: 完整备份测试
**测试目标**: 验证完整备份功能

**测试步骤**:
```bash
# 执行完整备份
cd ~/hermesnexus
./scripts/backup.sh full

# 验证备份文件
./scripts/backup.sh list

# 检查备份完整性
BACKUP_FILE=$(ls -t backups/hermesnexus_*.db.gz | head -1)
./scripts/backup.sh verify $BACKUP_FILE
```

**验证点**:
- [ ] 备份文件创建成功
- [ ] 备份文件大小合理
- [ ] 校验和验证通过
- [ ] 压缩文件正常

#### TC-BACKUP-002: 数据恢复测试
**测试目标**: 验证数据恢复功能

**测试步骤**:
```bash
# 1. 记录当前状态
curl http://172.16.100.101:8080/api/v1/stats > before_restore.json

# 2. 模拟数据损坏
rm data/hermesnexus.db

# 3. 从备份恢复
BACKUP_FILE=$(ls -t backups/hermesnexus_*.db.gz | head -1)
echo "yes" | ./scripts/backup.sh restore $BACKUP_FILE

# 4. 验证恢复结果
curl http://172.16.100.101:8080/api/v1/stats > after_restore.json

# 5. 对比数据
diff before_restore.json after_restore.json
```

**验证点**:
- [ ] 数据恢复成功
- [ ] 数据完整性保持
- [ ] 服务功能正常
- [ ] 恢复时间合理 (< 30秒)

#### TC-BACKUP-003: 增量备份测试
**测试目标**: 验证多次备份的管理

**测试步骤**:
```bash
# 执行多次备份
for i in {1..3}; do
  ./scripts/backup.sh full
  sleep 2
done

# 查看备份列表
./scripts/backup.sh list

# 查看备份统计
./scripts/backup.sh stats
```

**验证点**:
- [ ] 多个备份文件正确管理
- [ ] 备份时间戳递增
- [ ] 备份统计正确
- [ ] 磁盘空间合理使用

### 测试套件4: 性能测试 (1小时)

#### TC-PERF-001: API响应时间测试
**测试目标**: 验证API响应时间性能

**测试步骤**:
```bash
# 安装性能测试工具
sudo apt install -y curl

# 测试健康检查接口响应时间
for i in {1..100}; do
  curl -o /dev/null -s -w "%{time_total}\n" http://172.16.100.101:8080/health
done | awk '{sum+=$1; count++} END {print "平均响应时间:", sum/count "秒"}'
```

**验证点**:
- [ ] 平均响应时间 < 100ms
- [ ] 95%请求 < 200ms
- [ ] 99%请求 < 500ms
- [ ] 无超时请求

#### TC-PERF-002: 并发负载测试
**测试目标**: 验证系统并发处理能力

**测试步骤**:
```bash
# 安装Apache Bench
sudo apt install -y apache2-utils

# 并发测试
ab -n 1000 -c 10 -t 60 http://172.16.100.101:8080/health

# 不同并发级别测试
for concurrency in 1 5 10 20 50; do
  echo "测试并发级别: $concurrency"
  ab -n 500 -c $concurrency http://172.16.100.101:8080/health
done
```

**验证点**:
- [ ] 10并发下无错误
- [ ] 20并发下错误率 < 1%
- [ ] 50并发下错误率 < 5%
- [ ] 系统资源使用合理

#### TC-PERF-003: 资源使用监控测试
**测试目标**: 验证系统资源使用情况

**测试步骤**:
```bash
# 启动监控
python scripts/monitor.py continuous &

# 在另一个终端执行负载测试
ab -n 1000 -c 20 http://172.16.100.101:8080/api/v1/stats

# 观察资源使用情况
# 检查CPU使用
top -b -n 1 | grep python

# 检查内存使用
ps aux | grep python | awk '{sum+=$4} END {print "总内存使用:", sum "%"}'

# 检查网络连接
netstat -an | grep 8080 | wc -l
```

**验证点**:
- [ ] CPU使用 < 80%
- [ ] 内存使用 < 80%
- [ ] 磁盘I/O正常
- [ ] 网络连接正常

### 测试套件5: 稳定性测试 (45分钟)

#### TC-STAB-001: 长时间运行测试
**测试目标**: 验证系统长时间运行稳定性

**测试步骤**:
```bash
# 记录开始时间
START_TIME=$(date +%s)

# 持续发送请求
for i in {1..1000}; do
  curl -s http://172.16.100.101:8080/health > /dev/null
  sleep 1
done

# 记录结束时间
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "测试持续时间: $DURATION 秒"

# 检查服务状态
sudo systemctl status hermesnexus
```

**验证点**:
- [ ] 服务无崩溃
- [ ] 无内存泄漏
- [ ] 响应时间稳定
- [ ] 日志无严重错误

#### TC-STAB-002: 故障恢复测试
**测试目标**: 验证故障自动恢复能力

**测试步骤**:
```bash
# 1. 模拟服务崩溃
sudo systemctl stop hermesnexus

# 2. 等待系统自动重启 (如果配置了自动重启)
sleep 5

# 3. 手动重启服务
sudo systemctl start hermesnexus

# 4. 验证服务恢复
sleep 3
curl http://localhost:8080/health

# 5. 检查数据完整性
curl http://localhost:8080/api/v1/stats
```

**验证点**:
- [ ] 服务自动重启成功
- [ ] 数据无损坏
- [ ] 功能恢复正常
- [ ] 重启时间 < 10秒

#### TC-STAB-003: 异常输入测试
**测试目标**: 验证异常输入处理能力

**测试步骤**:
```bash
# 测试无效JSON
curl -X POST http://172.16.100.101:8080/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{"invalid": json}'

# 测试超长输入
curl -X POST http://172.16.100.101:8080/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{"device_id": "'$(python -c 'print("A"*10000)')'", "name": "test"}'

# 测试特殊字符
curl -X POST http://172.16.100.101:8080/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"command": "$(rm -rf /)", "node_id": "test"}'
```

**验证点**:
- [ ] 返回适当错误信息
- [ ] 系统不崩溃
- [ ] 无安全漏洞
- [ ] 日志记录异常

### 测试套件6: 云边协同测试 (30分钟)

#### TC-EDGE-001: 节点注册测试
**测试目标**: 验证边缘节点自动注册

**测试步骤**:
```bash
# 启动边缘节点
cd ~/hermesnexus
source venv/bin/activate
python -m edge.runtime.core &

# 等待节点注册
sleep 5

# 验证节点注册
curl http://localhost:8080/api/v1/nodes
```

**验证点**:
- [ ] 节点成功注册
- [ ] 节点状态为online
- [ ] 心跳正常工作
- [ ] 节点信息完整

#### TC-EDGE-002: 任务分发执行测试
**测试目标**: 验证任务分发和执行流程

**测试步骤**:
```bash
# 创建任务
curl -X POST http://172.16.100.101:8080/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "edge-test-001",
    "node_id": "edge-node-001",
    "task_type": "execute",
    "command": "echo Hello from Edge",
    "priority": "normal"
  }'

# 等待任务完成
sleep 10

# 查询任务结果
curl http://172.16.100.101:8080/api/v1/jobs/edge-test-001

# 查询执行事件
curl http://172.16.100.101:8080/api/v1/jobs/edge-test-001/events
```

**验证点**:
- [ ] 任务成功分发
- [ ] 边缘节点接收任务
- [ ] 命令执行成功
- [ ] 结果正确回传

---

## 📈 性能基准指标

### API性能基准
| 指标 | 目标值 | 实际值 | 状态 |
|------|--------|--------|------|
| 健康检查响应时间 | < 50ms | __待测试__ | ⏳ |
| 查询接口响应时间 | < 100ms | __待测试__ | ⏳ |
| 创建接口响应时间 | < 200ms | __待测试__ | ⏳ |
| 并发处理能力 | > 10 req/s | __待测试__ | ⏳ |

### 系统资源基准
| 资源 | 正常使用 | 高负载 | 告警阈值 |
|------|----------|--------|----------|
| CPU | < 30% | < 70% | 80% |
| 内存 | < 50% | < 80% | 85% |
| 磁盘I/O | < 20% | < 60% | 80% |
| 网络 | < 10 Mbps | < 50 Mbps | 100 Mbps |

### 可靠性指标
| 指标 | 目标值 | 实际值 | 状态 |
|------|--------|--------|------|
| 服务可用性 | > 99% | __待测试__ | ⏳ |
| 数据完整性 | 100% | __待测试__ | ⏳ |
| 平均恢复时间 | < 5min | __待测试__ | ⏳ |
| 备份成功率 | > 99% | __待测试__ | ⏳ |

---

## 🎯 测试执行计划

### 测试环境准备 (15分钟)
- [ ] 服务器连接验证
- [ ] 服务部署完成
- [ ] 测试工具安装
- [ ] 测试数据准备

### 功能测试执行 (1小时)
- [ ] API功能测试 (30分钟)
- [ ] 数据持久化测试 (30分钟)

### 性能测试执行 (1小时)
- [ ] 响应时间测试 (20分钟)
- [ ] 并发负载测试 (20分钟)
- [ ] 资源监控测试 (20分钟)

### 稳定性测试执行 (45分钟)
- [ ] 长时间运行测试 (15分钟)
- [ ] 故障恢复测试 (15分钟)
- [ ] 异常处理测试 (15分钟)

### 云边协同测试 (30分钟)
- [ ] 节点注册测试 (15分钟)
- [ ] 任务执行测试 (15分钟)

### 测试结果汇总 (30分钟)
- [ ] 测试数据收集
- [ ] 问题分析总结
- [ ] 报告编写
- [ ] 改进建议

---

## 📊 测试报告模板

### 测试执行摘要
**测试日期**: __待填写__  
**测试人员**: __待填写__  
**测试环境**: scsun@172.16.100.101:22  
**系统版本**: v1.1.0  

### 测试结果统计
| 测试套件 | 总用例数 | 通过 | 失败 | 通过率 |
|----------|----------|------|------|--------|
| API功能测试 | 4 | __ | __ | __% |
| 数据持久化测试 | 3 | __ | __ | __% |
| 备份恢复测试 | 3 | __ | __ | __% |
| 性能测试 | 3 | __ | __ | __% |
| 稳定性测试 | 3 | __ | __ | __% |
| 云边协同测试 | 2 | __ | __ | __% |
| **总计** | **18** | **__** | **__** | **__%** |

### 发现问题汇总
1. **问题ID**: BUG-001  
   **严重级别**: 高/中/低  
   **问题描述**: __待填写__  
   **复现步骤**: __待填写__  
   **预期结果**: __待填写__  
   **实际结果**: __待填写__  

### 性能测试结果
| 性能指标 | 目标值 | 实际值 | 达标状态 |
|----------|--------|--------|----------|
| API响应时间 | < 100ms | __待测试__ | ⏳ |
| 并发处理能力 | > 10 req/s | __待测试__ | ⏳ |
| CPU使用率 | < 80% | __待测试__ | ⏳ |
| 内存使用率 | < 80% | __待测试__ | ⏳ |

### 验收建议
- [ ] **通过验收**: 所有关键功能正常，性能达标
- [ ] **条件通过**: 非关键问题存在，可后续修复
- [ ] **不通过**: 严重问题存在，需要修复后重新测试

### 改进建议
1. **性能优化**: __待填写__
2. **功能增强**: __待填写__
3. **安全加固**: __待填写__
4. **运维改进**: __待填写__

---

## ✅ 测试完成标准

### 功能验收标准
- [ ] 所有核心API功能正常
- [ ] 数据持久化工作正常
- [ ] 备份恢复功能验证通过
- [ ] 云边协同功能完整

### 性能验收标准
- [ ] API响应时间符合基准
- [ ] 并发处理能力满足需求
- [ ] 系统资源使用合理
- [ ] 无明显性能瓶颈

### 稳定性验收标准
- [ ] 长时间运行无异常
- [ ] 故障恢复机制正常
- [ ] 异常处理健壮
- [ ] 日志记录完整

### 安全验收标准
- [ ] 输入验证有效
- [ ] 异常处理安全
- [ ] 数据保护到位
- [ ] 访问控制正确

---

*测试计划版本: 1.0*  
*创建时间: 2026年4月11日*  
*适用环境: 生产环境测试*  
*预计测试时间: 3-4小时*