# HermesNexus MVP 回滚指南

## 🔄 回滚策略

**项目**: HermesNexus MVP
**版本**: 1.0
**策略**: 快速回滚 + 数据保护

---

## 🚨 回滚触发条件

### 自动触发

- [ ] **服务崩溃** - 云端API或边缘节点连续失败3次
- [ ] **数据丢失** - 检测到数据不一致或丢失
- [ ] **性能严重下降** - 响应时间 > 10s 持续5分钟

### 手动触发

- [ ] **关键功能失效** - 核心流程无法完成
- [ ] **安全漏洞** - 发现严重安全问题
- [ ] **用户体验灾难** - 用户无法正常使用系统

---

## 📦 回滚准备

### 备份检查点

在执行任何变更前，确保以下备份可用：

```bash
# 1. 代码备份
git tag -a backup-$(date +%Y%m%d-%H%M%S) -m "部署前备份"
git push origin backup-$(date +%Y%m%d-%H%M%S)

# 2. 数据库备份
cp -r cloud/database/ cloud/database.backup.$(date +%Y%m%d-%H%M%S)/

# 3. 配置文件备份
cp .env .env.backup.$(date +%Y%m%d-%H%M%S)
cp docker-compose.yaml docker-compose.yaml.backup.$(date +%Y%m%d-%H%M%S)

# 4. 日志备份
cp -r logs/ logs.backup.$(date +%Y%m%d-%H%M%S)/
```

### 回滚版本标识

```bash
# 查看可用的回滚点
git tag | grep backup

# 查看当前版本
git log --oneline -1
```

---

## ⚡ 快速回滚步骤

### 方案1: 代码回滚 (推荐)

```bash
# 1. 停止所有服务
make stop-all

# 2. 回滚代码到指定版本
git checkout <backup-tag>

# 3. 重新安装依赖（如有变化）
source venv/bin/activate
pip install -r requirements.txt

# 4. 重启服务
make run-cloud
make run-edge

# 5. 验证回滚成功
curl http://localhost:8080/health
```

### 方案2: 配置回滚

```bash
# 1. 停止服务
make stop-all

# 2. 恢复配置文件
cp .env.backup.<timestamp> .env
cp docker-compose.yaml.backup.<timestamp> docker-compose.yaml

# 3. 重启服务
make start-all
```

### 方案3: 数据库回滚

```bash
# 1. 停止服务
make stop-all

# 2. 恢复数据库
rm -rf cloud/database/
cp -r cloud/database.backup.<timestamp>/ cloud/database/

# 3. 重启服务
make run-cloud
```

---

## 🔧 分阶段回滚

### 阶段1: 服务层回滚 (2分钟)

```bash
# 仅回滚服务层代码，保留数据
git checkout <backup-tag> -- cloud/api/
make run-cloud
```

### 阶段2: 边缘层回滚 (2分钟)

```bash
# 回滚边缘节点代码
git checkout <backup-tag> -- edge/
make run-edge
```

### 阶段3: 完整回滚 (5分钟)

```bash
# 回滚整个系统
git checkout <backup-tag>
make stop-all
make start-all
```

---

## 🛡️ 数据保护

### 数据迁移保护

```bash
# 在回滚前保护现有数据
export ROLLBACK_TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# 备份当前状态
python scripts/backup_state.py --output backup-$ROLLBACK_TIMESTAMP.json

# 记录当前任务状态
curl http://localhost:8080/api/v1/jobs > jobs-$ROLLBACK_TIMESTAMP.json
curl http://localhost:8080/api/v1/nodes > nodes-$ROLLBACK_TIMESTAMP.json
```

### 数据验证

```bash
# 回滚后验证数据完整性
python scripts/validate_data.py --backup backup-$ROLLBACK_TIMESTAMP.json

# 检查关键数据
curl http://localhost:8080/api/v1/stats
```

---

## 🔍 回滚验证

### 健康检查

```bash
# 1. 服务健康检查
curl http://localhost:8080/health

# 2. API端点检查
curl http://localhost:8080/api/v1/nodes
curl http://localhost:8080/api/v1/jobs

# 3. 控制台访问
curl http://localhost:8080/console

# 4. 边缘节点连接
python scripts/check_edge_connection.py
```

### 功能验证

- [ ] 节点能够注册和心跳
- [ ] 任务能够创建和分配
- [ ] 控制台能够正常显示
- [ ] 日志记录正常

---

## 🚨 紧急回滚场景

### 场景1: 部署后立即失败

```bash
# 1. 立即停止部署
make stop-all

# 2. 快速回滚到上一个版本
git checkout HEAD~1

# 3. 重启服务
make start-all

# 4. 验证
curl http://localhost:8080/health
```

### 场景2: 数据库损坏

```bash
# 1. 停止服务
make stop-all

# 2. 恢复数据库
rm -rf cloud/database/
cp -r cloud/database.backup.<latest>/ cloud/database/

# 3. 重启服务
make run-cloud

# 4. 验证数据
curl http://localhost:8080/api/v1/stats
```

### 场景3: 配置错误导致无法启动

```bash
# 1. 使用备份配置
cp .env.backup.<latest> .env

# 2. 验证配置
python scripts/validate_config.py

# 3. 重启服务
make start-all
```

---

## 📋 回滚检查清单

### 回滚前检查

- [ ] 确认回滚触发条件
- [ ] 备份当前数据
- [ ] 记录当前问题
- [ ] 通知相关人员
- [ ] 准备回滚环境

### 回滚中检查

- [ ] 服务停止成功
- [ ] 代码回滚完成
- [ ] 配置恢复完成
- [ ] 数据库恢复完成
- [ ] 依赖安装完成

### 回滚后检查

- [ ] 服务启动成功
- [ ] 健康检查通过
- [ ] 功能验证正常
- [ ] 数据完整性确认
- [ ] 性能正常
- [ ] 用户访问正常

---

## 📞 故障响应

### 响应时间目标

- **P0故障** - 5分钟内开始回滚
- **P1故障** - 15分钟内开始回滚
- **P2故障** - 1小时内开始回滚

### 通知机制

```bash
# 故障通知脚本
python scripts/notify_rollback.py --severity P0 --message "开始紧急回滚"
```

### 升级机制

1. **5分钟** - 技术负责人决策
2. **15分钟** - 产品负责人通知
3. **30分钟** - 管理层升级

---

## 🔄 回滚后恢复

### 问题修复流程

1. **分析根因** - 识别回滚原因
2. **修复问题** - 在测试环境修复
3. **验证修复** - 充分测试
4. **重新部署** - 小步部署

### 重新部署检查

```bash
# 1. 确保修复已验证
python -m pytest tests/ -v

# 2. 小范围测试
make run-cloud
python scripts/test_deployment.py

# 3. 逐步推广
# 先部署到1个节点观察
# 然后部署到全部节点
```

---

## 📊 回滚报告模板

### 回执报告

```markdown
# 回滚报告

## 基本信息
- 回滚时间: YYYY-MM-DD HH:MM:SS
- 回滚版本: <version>
- 目标版本: <target-version>
- 回滚原因: <reason>

## 回滚过程
1. 触发条件: <trigger>
2. 影响范围: <scope>
3. 回滚步骤: <steps>
4. 回滚结果: <result>

## 验证结果
- [ ] 服务恢复
- [ ] 功能正常
- [ ] 数据完整

## 后续行动
1. <action1>
2. <action2>
3. <action3>

## 经验教训
<lessons_learned>
```

---

## 🎯 预防措施

### 减少回滚频率

1. **更好的测试** - 提高测试覆盖率
2. **分阶段部署** - 蓝绿部署、金丝雀发布
3. **监控告警** - 早期发现问题
4. **回滚演练** - 定期演练回滚流程

### 改进回滚效率

1. **自动化脚本** - 减少手动操作
2. **快速恢复** - 优化回滚步骤
3. **文档完善** - 清晰的操作指南
4. **团队培训** - 提高应急响应能力

---

## 📞 紧急联系

### 技术团队

- **技术负责人**: [姓名] - [电话]
- **运维负责人**: [姓名] - [电话]
- **开发负责人**: [姓名] - [电话]

### 管理层

- **项目经理**: [姓名] - [电话]
- **产品负责人**: [姓名] - [电话]

---

**版本**: 1.0
**最后更新**: 2024-04-11
**维护团队**: HermesNexus开发团队

---

*注意: 本文档应在每次部署前更新，确保所有备份和恢复步骤都经过测试。*