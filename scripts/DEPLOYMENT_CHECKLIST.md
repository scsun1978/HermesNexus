# HermesNexus Cloud API v1.2.0 部署检查清单

## 📋 部署前检查

### 本地准备
- [x] API v1兼容层代码已实现
- [x] 部署脚本已准备完成
- [x] 部署文档已编写完毕
- [ ] 部署文件已上传到服务器

### 服务器环境
- [ ] 服务器访问权限可用 (scsun@172.16.100.101)
- [ ] Python 3.x 环境已就绪
- [ ] 端口8082可用且未被占用
- [ ] 必要目录存在 (/home/scsun/hermesnexus-code, etc.)

## 🚀 部署执行步骤

### 第1步: 准备部署文件
在本地机器执行以下命令：

```bash
# 1. 创建部署目录
mkdir -p ~/hermes-deploy
cd ~/hermes-deploy

# 2. 复制必要文件
cp cloud/api/v12_standard_cloud.py .
cp scripts/manual-deploy-guide.sh .
cp scripts/QUICK_DEPLOY_GUIDE.md .

# 3. 验证文件
ls -la
# 应该看到: v12_standard_cloud.py, manual-deploy-guide.sh, QUICK_DEPLOY_GUIDE.md
```

### 第2步: 上传到服务器
将本地部署文件上传到生产服务器：

```bash
# 上传部署文件
scp v12_standard_cloud.py scsun@172.16.100.101:/home/scsun/hermesnexus-update/
scp manual-deploy-guide.sh scsun@172.16.100.101:/home/scsun/hermesnexus-update/
```

### 第3步: 执行部署
登录服务器并执行部署：

```bash
# 1. 登录服务器
ssh scsun@172.16.100.101

# 2. 进入部署目录
cd /home/scsun/hermesnexus-update

# 3. 赋予执行权限
chmod +x manual-deploy-guide.sh

# 4. 执行部署
./manual-deploy-guide.sh
```

### 第4步: 验证部署
部署脚本会自动执行以下验证：

```bash
# 1. 健康检查
curl http://localhost:8082/health

# 2. API v1端点测试
curl http://localhost:8082/api/v1/tasks

# 3. 节点管理测试
curl http://localhost:8082/api/nodes

# 4. Edge节点连接测试
curl http://172.16.200.94:8081/health
```

## 🔍 部署验证检查清单

### 基础验证
- [ ] Cloud API进程正常运行
- [ ] 端口8082正在监听
- [ ] 健康检查端点返回200 OK
- [ ] 版本信息显示为v1.2.0

### API端点验证
- [ ] GET /api/v1/tasks 返回任务列表
- [ ] GET /api/nodes 返回节点信息
- [ ] GET /api/jobs 返回任务列表
- [ ] POST /api/jobs 可以创建新任务
- [ ] PATCH /api/jobs/{id}/status 可以更新任务状态

### 监控验证
- [ ] /monitoring/health 端点正常
- [ ] /monitoring/metrics 返回Prometheus指标
- [ ] 系统资源指标正常显示

### Edge节点验证
- [ ] Edge节点健康状态正常
- [ ] Edge节点不再显示404错误
- [ ] Edge节点可以正常连接到Cloud API
- [ ] 任务轮询机制正常工作

## 📊 部署后测试

### E2E测试流程

1. **创建测试任务**
```bash
curl -X POST http://172.16.100.101:8082/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "e2e-test-api-v1-'$(date +%s)'",
    "name": "API v1兼容性E2E测试",
    "job_type": "command",
    "target_node_id": "edge-test-001",
    "command": "echo \"API v1 E2E test passed\" && date",
    "created_by": "e2e-test"
  }'
```

2. **监控任务执行**
```bash
# 查看任务状态变化
# 预期: pending → running → completed

# 检查任务列表
curl http://172.16.100.101:8082/api/jobs | python3 -m json.tool

# 检查任务详情
curl http://172.16.100.101:8082/api/jobs/e2e-test-api-v1-<timestamp>
```

3. **验证结果**
```bash
# 等待任务完成（约10-20秒）
sleep 15

# 检查任务最终状态
curl http://172.16.100.101:8082/api/jobs/e2e-test-api-v1-<timestamp> | python3 -m json.tool
```

### 预期测试结果
- ✅ 任务状态: completed
- ✅ 执行结果: stdout包含"API v1 E2E test passed"
- ✅ 返回码: 0
- ✅ 时间戳完整: created_at, started_at, completed_at

## 🔄 回滚检查清单

如果部署出现问题，按以下步骤回滚：

- [ ] 停止新服务: `kill $(cat /tmp/cloud-api-v12.pid)`
- [ ] 找到最新备份: `ls -lt /home/scsun/hermesnexus-backups/`
- [ ] 恢复备份文件
- [ ] 重启服务
- [ ] 验证回滚成功

## 📈 成功标准

### 部署成功指标
- ✅ 所有基础验证通过
- ✅ 所有API端点验证通过
- ✅ Edge节点连接正常
- ✅ E2E测试完全通过
- ✅ 无严重错误日志

### 生产就绪度
- **部署前**: 90% (API兼容层已实现)
- **部署后**: 98%+ (完整E2E验证通过)

## 🎯 关键时间节点

1. **准备阶段**: 5分钟 - 文件上传和环境检查
2. **部署阶段**: 3分钟 - 执行部署脚本
3. **验证阶段**: 10分钟 - 端点测试和E2E验证
4. **总计**: 18分钟内完成全部部署

## 📞 支持联系

如遇到问题，请参考以下文档：
- 快速部署指南: `QUICK_DEPLOY_GUIDE.md`
- 详细部署报告: `docs/reports/2026-04-19-api-v1-compatibility-deployment-ready.md`
- 部署脚本: `manual-deploy-guide.sh`

---

**部署目标**: 解决Edge节点与Cloud API之间的接口不匹配问题，实现完整的端到端任务执行链路。

**预期结果**: 从 "Partially ready" 升级到 "完整E2E通过"，生产就绪度达到98%+。

🎯 **准备完成后，按照上述步骤执行部署，预计15-20分钟内完成。**