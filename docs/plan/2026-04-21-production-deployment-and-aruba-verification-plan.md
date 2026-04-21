# 生产环境部署和真机验证计划

**目标**: 在生产环境中部署Phase 4A+4B功能，并进行Aruba设备真机验证  
**时间**: 2026-04-21 开始  
**状态**: 🚀 准备执行

---

## 📋 部署前准备

### 安全修复状态 ✅
- ✅ 移除 `shell=True` 安全债务
- ✅ 修复 FastAPI 弃用警告  
- ✅ 添加安全测试验证
- ✅ 强制安全执行模式

### 生产检查清单
- [ ] 备份现有生产环境
- [ ] 准备回滚方案
- [ ] 检查依赖兼容性
- [ ] 配置监控和告警
- [ ] 准备测试设备

---

## 🚀 生产环境部署步骤

### Step 1: 代码部署 (30分钟)

#### 1.1 创建部署分支
```bash
# 从feature分支创建部署分支
git checkout -b deploy/phase4-production

# 确保包含所有安全修复
git add .
git commit -m "Security fixes: Remove shell=True, enforce safe execution"

# 推送到远程
git push origin deploy/phase4-production
```

#### 1.2 服务器部署
```bash
# 连接到生产服务器 scsun@172.16.100.101:22
ssh scsun@172.16.100.101

# 进入项目目录
cd /path/to/HermesNexus

# 拉取最新代码
git fetch origin
git checkout deploy/phase4-production
git pull origin deploy/phase4-production

# 安装依赖（如有需要）
pip install -r requirements.txt

# 重启服务
sudo systemctl restart hermesnexus-cloud
sudo systemctl restart hermesnexus-edge

# 验证服务状态
sudo systemctl status hermesnexus-cloud
sudo systemctl status hermesnexus-edge
```

#### 1.3 数据库迁移
```bash
# 备份现有数据库
cp data/tasks.db data/tasks.db.backup.$(date +%Y%m%d)

# 验证数据库表结构
sqlite3 data/tasks.db ".schema tasks"
sqlite3 data/tasks.db ".schema device_groups"
```

---

### Step 2: 功能验证 (1小时)

#### 2.1 API健康检查
```bash
# 检查云端API
curl http://172.16.100.101:8082/health

# 检查v2 API可用性
curl http://172.16.100.101:8082/api/v2/tasks/list

# 检查批量API
curl http://172.16.100.101:8082/api/v2/tasks/batch/list
```

#### 2.2 创建测试任务
```bash
# 创建单个测试任务
curl -X POST "http://172.16.100.101:8082/api/v2/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "生产环境测试",
    "command": "uptime && df -h",
    "target_device_id": "test-server-001",
    "task_type": "inspection"
  }'

# 验证任务创建成功
curl "http://172.16.100.101:8082/api/v2/tasks/{task_id}"
```

#### 2.3 批量任务测试
```bash
# 创建批量任务
curl -X POST "http://172.16.100.101:8082/api/v2/tasks/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "批量巡检测试",
    "command": "uptime && df -h",
    "device_ids": ["server-001", "server-002", "server-003"],
    "parallel": true
  }'

# 查询批次进度
curl "http://172.16.100.101:8082/api/v2/tasks/batch/{batch_id}/progress"
```

---

## 🔬 Aruba 真机验证 (核心目标)

### 验证环境准备

#### Aruba 测试设备
- **Aruba Mobility Controller 7200** (或虚拟实例)
- **Aruba Switch 2930F** (或虚拟实例)
- 网络连通性确认
- SSH 访问配置

#### 访问配置
```python
# Aruba 设备配置示例
aruba_controller_config = {
    'hostname': 'aruba-master-01.example.com',
    'vendor': 'aruba',
    'model': '7200',
    'device_type': 'router',
    'ssh_user': 'admin',
    'ssh_port': 22,
    'ssh_password': 'your_password'  # 或使用密钥
}
```

### 真机验证测试用例

#### Test 1: Aruba 设备注册
```bash
# 注册 Aruba 控制器
curl -X POST "http://172.16.100.101:8082/api/v1/nodes/register" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "aruba-master-01",
    "node_type": "edge",
    "hostname": "aruba-master-01",
    "ip_address": "192.168.1.100",
    "port": 8081,
    "status": "online",
    "capabilities": {
      "task_models": ["v1", "v2"],
      "batch_support": true,
      "vendor": "aruba"
    },
    "version": "2.0.0",
    "orchestration_ready": true
  }'

# 验证注册成功
curl "http://172.16.100.101:8082/api/v1/nodes/aruba-master-01"
```

#### Test 2: Aruba 命令适配验证
```bash
# 创建 Aruba 巡检任务
curl -X POST "http://172.16.100.101:8082/api/v2/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Aruba控制器巡检",
    "command": "show version && show ap database && show client summary",
    "target_device_id": "aruba-master-01",
    "task_type": "inspection"
  }'

# 监控任务执行
curl "http://172.16.100.101:8082/api/v2/tasks/{task_id}"

# 验证命令适配正确
# 预期: show version, show ap database 等命令正确执行
```

#### Test 3: Aruba 模板测试
```bash
# 使用 Aruba 巡检模板
curl -X POST "http://172.16.100.101:8082/api/v2/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "aruba-inspection",
    "target_device_id": "aruba-master-01"
  }'

# 验证模板渲染正确
curl "http://172.16.100.101:8082/api/v2/tasks/{task_id}"
```

#### Test 4: Aruba AP 重启测试
```bash
# 使用 Aruba AP 重启模板（带参数）
curl -X POST "http://172.16.100.101:8082/api/v2/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "aruba-ap-restart",
    "target_device_id": "aruba-master-01",
    "params": {
      "ap_name": "ap-floor2-05"
    }
  }'

# 验证 AP 重启命令
# 预期: ap restart ap-floor2-05
```

#### Test 5: Aruba 批量调度测试
```bash
# 创建设备分组
curl -X POST "http://172.16.100.101:8082/api/v2/tasks/batch/groups" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "aruba-devices",
    "group_name": "Aruba设备组",
    "device_ids": ["aruba-master-01", "aruba-switch-01", "aruba-switch-02"],
    "metadata": {
      "environment": "production",
      "vendor": "aruba"
    }
  }'

# 批量调度到 Aruba 设备组
curl -X POST "http://172.16.100.101:8082/api/v2/tasks/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Aruba设备批量巡检",
    "template_id": "aruba-inspection",
    "group_id": "aruba-devices",
    "parallel": true
  }'

# 验证批量执行结果
curl "http://172.16.100.101:8082/api/v2/tasks/batch/{batch_id}"
```

---

## 📊 真机验证指标

### 功能验证
- [ ] Aruba 设备成功注册
- [ ] Aruba 命令适配正确工作
- [ ] Aruba 模板渲染正确
- [ ] 批量调度功能正常
- [ ] 设备分组管理正常

### 性能验证
- [ ] 单个命令执行时间 < 5秒
- [ ] 批量任务调度时间 < 10秒
- [ ] 内存使用合理
- [ ] CPU 使用正常

### 安全验证
- [ ] 安全执行模式生效
- [ ] 无命令注入风险
- [ ] 访问控制正常
- [ ] 日志记录完整

### 兼容性验证
- [ ] v1 任务仍然工作
- [ ] v2 任务功能增强
- [ ] 向后兼容无破坏
- [ ] API 响应格式正确

---

## 🔄 回滚方案

### 回滚触发条件
- 关键功能异常
- 性能严重下降
- 安全问题发现
- 兼容性重大问题

### 回滚步骤
```bash
# 1. 停止服务
sudo systemctl stop hermesnexus-cloud
sudo systemctl stop hermesnexus-edge

# 2. 回滚代码
git checkout main
git pull origin main

# 3. 恢复数据库（如需要）
cp data/tasks.db.backup.YYYYMMDD data/tasks.db

# 4. 重启服务
sudo systemctl start hermesnexus-cloud
sudo systemctl start hermesnexus-edge

# 5. 验证回滚成功
curl http://172.16.100.101:8082/health
```

---

## 📈 监控和告警

### 关键指标监控
```bash
# 服务状态
sudo systemctl status hermesnexus-cloud
sudo systemctl status hermesnexus-edge

# 资源使用
htop
iostat -x 5

# 日志监控
tail -f /var/log/hermesnexus/cloud.log
tail -f /var/log/hermesnexus/edge.log

# API 监控
curl -s http://172.16.100.101:8082/health | jq .
```

### 告警设置
- 服务异常 > 5分钟
- API 响应时间 > 10秒
- 错误率 > 5%
- 内存使用 > 80%
- 磁盘使用 > 90%

---

## ✅ 验收标准

### 生产部署验收
- [ ] 服务正常运行
- [ ] API 功能完整
- [ ] 数据无丢失
- [ ] 性能无明显下降
- [ ] 监控正常工作

### Aruba 真机验收
- [ ] 设备注册成功
- [ ] 命令适配正确
- [ ] 模板功能正常
- [ ] 批量调度工作
- [ ] 无安全风险

### 最终确认
- [ ] 所有测试用例通过
- [ ] 生产环境稳定运行
- [ ] Aruba 设备管理正常
- [ ] 用户反馈良好

---

## 🎯 下一步行动

### 立即执行 (今天)
1. **安全修复部署**: 推送安全修复到生产
2. **环境准备**: 准备 Aruba 测试设备
3. **基础验证**: 验证核心功能正常

### 短期计划 (本周)
1. **真机验证**: 执行 Aruba 设备测试
2. **性能测试**: 验证批量调度性能
3. **用户培训**: 准备使用文档和培训

### 中期计划 (下周)
1. **扩大规模**: 增加 Aruba 设备数量
2. **功能优化**: 根据真机验证结果优化
3. **生产推广**: 推广到更多设备类型

---

**状态**: ✅ 安全修复完成，准备生产部署  
**下一步**: 执行生产部署和 Aruba 真机验证  
**预计完成**: 2026-04-22

---

**创建时间**: 2026-04-21  
**执行团队**: HermesNexus 开发团队  
**审核状态**: ✅ 已批准，准备执行