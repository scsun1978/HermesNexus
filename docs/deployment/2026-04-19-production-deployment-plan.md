# HermesNexus 生产环境部署方案
**Date**: 2026-04-19  
**Version**: 1.2.0  
**Environment**: 基于172.16.100.101 (服务端) + 172.16.200.94 (Edge端)

---

## 🎯 部署目标

在现有Hermes Agent 0.8.0基础设施上，升级部署HermesNexus 1.2.0生产版本，实现：
- Cloud API控制平面 (172.16.100.101)
- Edge节点管理 (172.16.200.94)  
- 完整监控和运维体系
- 生产级安全和性能

---

## 📊 环境现状分析

### 已有基础设施 ✅
- **服务端主机**: 172.16.100.101 (scsun) - 已部署Hermes Agent 0.8.0
- **Edge测试主机**: 172.16.200.94 (openclaw) - 已部署Hermes Agent 0.8.0  
- **网络连通性**: SSH连接验证正常
- **部署机制**: 工作树同步和软链接切换机制

### 版本升级策略
**兼容性方案**：
1. **并行部署**: HermesNexus与现有Hermes Agent共存
2. **渐进迁移**: 逐步从Hermes Agent迁移到HermesNexus
3. **回滚保障**: 保持现有系统可快速回滚

---

## 🚀 部署方案选择

### 方案A: Docker容器化部署 (推荐) ⭐

**优势**：
- 环境隔离，不影响现有Hermes Agent
- 一键部署和运维
- 完整监控栈集成
- 快速回滚和扩展

**部署架构**：
```
172.16.100.101 (服务端)
├── Hermes Agent 0.8.0 (现有，保持运行)
└── HermesNexus 1.2.0 (Docker)
    ├── Cloud API (端口8080)
    ├── 监控栈
    │   ├── Prometheus (端口9090)  
    │   └── Grafana (端口3000)
    └── 数据存储

172.16.200.94 (Edge端)
├── Hermes Agent 0.8.0 (现有，保持运行)  
└── HermesNexus Edge (Docker)
    └── Edge Node Service
```

**部署步骤**：

#### 1. 服务端部署 (172.16.100.101)

```bash
# 1.1 准备部署目录
ssh scsun@172.16.100.101
mkdir -p /home/scsun/hermesnexus/{data,logs,config}

# 1.2 上传部署文件
rsync -avz --exclude='__pycache__' \
  /Users/shengchun.sun/Library/CloudStorage/OneDrive-个人/MyCloud/Code/HermesNexus/ \
  scsun@172.16.100.101:/home/scsun/hermesnexus/current/

# 1.3 配置生产环境
cp .env.production /home/scsun/hermesnexus/config/.env
# 编辑配置文件，设置正确的数据库路径等

# 1.4 启动服务
cd /home/scsun/hermesnexus/current
./deploy.sh deploy-full

# 1.5 验证部署
./deploy.sh health
curl http://localhost:8080/monitoring/health
```

#### 2. Edge端部署 (172.16.200.94)

```bash
# 2.1 准备部署目录  
ssh openclaw@172.16.200.94
mkdir -p /home/openclaw/hermesnexus-edge/{data,logs,config}

# 2.2 上传Edge节点文件
rsync -avz --exclude='cloud' --exclude='tests' \
  /Users/shengchun.sun/Library/CloudStorage/OneDrive-个人/MyCloud/Code/HermesNexus/ \
  openclaw@172.16.200.94:/home/openclaw/hermesnexus-edge/current/

# 2.3 构建Edge镜像
cd /home/openclaw/hermesnexus-edge/current
docker build -f Dockerfile.edge -t hermesnexus-edge:1.2.0 .

# 2.4 启动Edge节点
docker run -d \
  --name hermes-edge-node \
  -p 8081:8080 \
  -v /home/openclaw/hermesnexus-edge/data:/app/data \
  -v /home/openclaw/hermesnexus-edge/logs:/app/logs \
  -e CLOUD_API_URL=http://172.16.100.101:8080 \
  -e EDGE_NODE_ID=edge-test-001 \
  hermesnexus-edge:1.2.0

# 2.5 验证连接
curl http://localhost:8081/health
```

#### 3. 网络配置验证

```bash
# 从服务端验证到Edge端的连接
curl http://172.16.200.94:8081/health

# 从Edge端验证到服务端的连接  
curl http://172.16.100.101:8080/monitoring/health
```

---

### 方案B: 直接升级部署

**优势**：
- 统一管理，资源利用率高
- 简化运维架构

**注意事项**：
- 需要停止现有Hermes Agent服务
- 建议先在测试环境验证
- 需要完整的数据迁移方案

**部署步骤**：

#### 1. 备份现有系统
```bash
# 在两台主机上分别执行
ssh scsun@172.16.100.101
cp -r /home/scsun/deployments/hermes-agent/current /home/scsun/hermes-agent-backup-20260419

ssh openclaw@172.16.200.94  
cp -r /home/openclaw/deployments/hermes-agent/current /home/openclaw/hermes-agent-backup-20260419
```

#### 2. 停止现有服务
```bash
# 停止Hermes Agent服务
ssh scsun@172.16.100.101 "systemctl --user stop hermes-agent || true"
ssh openclaw@172.16.200.94 "systemctl --user stop hermes-agent || true"
```

#### 3. 部署HermesNexus
```bash
# 使用现有的部署机制，更新工作树
rsync -avz --exclude='__pycache__' \
  /Users/shengchun.sun/Library/CloudStorage/OneDrive-个人/MyCloud/Code/HermesNexus/ \
  scsun@172.16.100.101:/home/scsun/deployments/hermes-agent/hermesnexus-1.2.0/

# 创建新的版本软链接
ssh scsun@172.16.100.101 \
  "ln -sfn /home/scsun/deployments/hermes-agent/hermesnexus-1.2.0 /home/scsun/deployments/hermes-agent/current"
```

---

## 🔍 部署验证清单

### 服务端验证 (172.16.100.101)

```bash
# 1. 服务状态检查
curl http://localhost:8080/monitoring/health

# 2. API功能测试
curl http://localhost:8080/api/nodes
curl http://localhost:8080/api/assets

# 3. 监控指标验证
curl http://localhost:8080/monitoring/metrics

# 4. 性能基准测试
python tests/performance/test_performance_baseline_day2.py
```

### Edge端验证 (172.16.200.94)

```bash
# 1. Edge节点健康检查
curl http://localhost:8081/health

# 2. 网络连通性测试
curl http://172.16.100.101:8080/monitoring/health

# 3. 任务执行测试
# 通过Cloud API创建测试任务并验证Edge端执行
```

### 集成验证

```bash
# 1. 节点注册测试
curl -X POST http://172.16.100.101:8080/api/nodes/register \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "edge-test-001",
    "node_type": "edge",
    "hostname": "edge-host",
    "ip_address": "172.16.200.94"
  }'

# 2. 心跳监控
watch -n 5 'curl -s http://172.16.100.101:8080/api/nodes | jq'

# 3. 任务执行端到端测试
curl -X POST http://172.16.100.101:8080/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-job-001",
    "target_node_id": "edge-test-001",
    "command": "echo \"Hello from HermesNexus\"",
    "executor_type": "ssh"
  }'
```

---

## 📊 监控和运维

### 访问监控界面

```bash
# Grafana仪表板
http://172.16.100.101:3000
默认用户名: admin
默认密码: admin (首次登录后修改)

# Prometheus指标
http://172.16.100.101:9090

# Cloud API健康检查
http://172.16.100.101:8080/monitoring/health

# Edge节点状态
http://172.16.200.94:8081/health
```

### 日志查看

```bash
# 服务端日志
docker logs -f hermes-cloud-api
docker logs -f prometheus
docker logs -f grafana

# Edge端日志
docker logs -f hermes-edge-node

# 或使用部署脚本
./deploy.sh logs
```

---

## 🔄 回滚方案

如果出现问题需要回滚：

### Docker部署回滚
```bash
# 停止HermesNexus服务
./deploy.sh stop

# 启动原有Hermes Agent (如果需要)
ssh scsun@172.16.100.101 "systemctl --user start hermes-agent"
ssh openclaw@172.16.200.94 "systemctl --user start hermes-agent"
```

### 直接部署回滚
```bash
# 切换回之前版本
ssh scsun@172.16.100.101 \
  "ln -sfn /home/scsun/deployments/hermes-agent/hermes-agent-0.8.0 /home/scsun/deployments/hermes-agent/current"

# 重启服务
ssh scsun@172.16.100.101 "systemctl --user restart hermes-agent"
```

---

## 📝 部署时间表

| 阶段 | 任务 | 预计时间 | 责任人 |
|------|------|----------|--------|
| **准备阶段** | 环境检查、配置文件准备 | 30分钟 | DevOps |
| **服务端部署** | Cloud API + 监控栈部署 | 1小时 | Backend |
| **Edge端部署** | Edge节点部署和连接 | 45分钟 | Edge Team |
| **集成验证** | 端到端功能测试 | 1小时 | QA |
| **监控配置** | 告警规则、仪表板配置 | 30分钟 | DevOps |
| **文档更新** | 运维文档、Runbook更新 | 30分钟 | Tech Writer |

**总计**: 约4小时

---

## 🎯 部署成功标准

1. ✅ **服务可用性**: 所有服务正常运行，健康检查通过
2. ✅ **功能完整性**: 节点注册、任务执行、结果返回正常
3. ✅ **监控可见性**: Grafana仪表板显示正确指标
4. ✅ **性能达标**: 响应时间、吞吐量符合基线要求
5. ✅ **数据完整性**: 审计日志、状态数据正确记录
6. ✅ **告警有效性**: 关键指标异常时能及时告警

---

## 🚨 风险和注意事项

### 风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| **网络不通** | 高 | 低 | 提前验证防火墙和网络策略 |
| **端口冲突** | 中 | 中 | 检查现有服务端口占用情况 |
| **数据迁移** | 高 | 低 | 保持现有系统并行，数据双写 |
| **性能不达标** | 中 | 低 | 基于已验证的性能基线部署 |
| **版本兼容** | 中 | 中 | Docker隔离，避免版本冲突 |

### 注意事项

1. **网络配置**: 确保两台主机间的防火墙允许必要端口通信
2. **资源规划**: 检查主机CPU、内存、磁盘空间是否充足
3. **依赖检查**: 确认Docker、Python等依赖版本兼容
4. **备份策略**: 部署前必须完整备份现有系统
5. **监控准备**: 提前配置好告警接收人

---

## 📞 支持联系

- **技术支持**: 开发团队
- **紧急联系**: 系统管理员
- **文档参考**: `docs/deployment/` 目录下的相关文档

---

**文档版本**: 1.0  
**最后更新**: 2026-04-19  
**状态**: ✅ 可执行