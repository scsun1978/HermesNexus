# HermesNexus 生产部署快速指南

## 🚀 5分钟快速部署

### 前置条件
```bash
# 1. 确保服务器可访问
ssh scsun@172.16.100.101

# 2. 确保Python 3.14+已安装
python3 --version  # 应显示 Python 3.14.x

# 3. 确保有足够磁盘空间
df -h  # 需要 > 5GB 可用空间
```

### 一键部署命令
```bash
# 连接到服务器并执行以下命令
ssh scsun@172.16.100.101

# 创建项目目录
mkdir -p ~/hermesnexus && cd ~/hermesnexus

# 创建虚拟环境
python3 -m venv venv && source venv/bin/activate

# 安装核心依赖
pip install fastapi uvicorn pydantic python-multipart aiohttp psutil requests

# 配置防火墙
sudo ufw allow 8080/tcp

# 启动服务 (测试模式)
python -m pip install your-package  # 替换为实际的包安装命令
```

---

## 📋 部署文档导航

### 🎯 核心文档 (按优先级)

#### 1. **DEPLOYMENT-CHECKLIST.md** ⭐⭐⭐⭐⭐
**用途**: 部署时逐项检查清单  
**何时使用**: 实际部署过程中  
**关键内容**: 
- 部署前检查清单
- 分步骤部署验证
- 部署后验收标准
- 故障排查指南

#### 2. **DEPLOYMENT-GUIDE.md** ⭐⭐⭐⭐⭐
**用途**: 完整的部署指南  
**何时使用**: 部署前准备和详细参考  
**关键内容**:
- 环境要求和依赖
- 5阶段部署流程
- 配置详解
- 安全加固

#### 3. **PRODUCTION-DEPLOYMENT-PLAN.md** ⭐⭐⭐⭐
**用途**: 详细部署时间表和步骤  
**何时使用**: 制定部署计划时  
**关键内容**:
- 详细部署步骤
- 时间规划
- 人员配置
- 风险控制

#### 4. **PRODUCTION-TESTING-PLAN.md** ⭐⭐⭐⭐
**用途**: 生产环境测试计划  
**何时使用**: 部署后测试验证  
**关键内容**:
- 6大测试套件
- 18个测试用例
- 性能基准
- 测试报告模板

#### 5. **DEPLOYMENT-READINESS-REPORT.md** ⭐⭐⭐⭐⭐
**用途**: 部署就绪状态评估  
**何时使用**: 部署决策和汇报  
**关键内容**:
- 项目完成度评估
- 系统能力评估
- 性能基准指标
- 部署建议

---

## 🔧 关键运维命令

### 服务管理
```bash
# 启动服务
sudo systemctl start hermesnexus

# 停止服务
sudo systemctl stop hermesnexus

# 重启服务
sudo systemctl restart hermesnexus

# 查看服务状态
sudo systemctl status hermesnexus

# 查看服务日志
journalctl -u hermesnexus -f
```

### 健康检查
```bash
# API健康检查
curl http://localhost:8080/health

# 系统统计
curl http://localhost:8080/api/v1/stats

# 节点状态
curl http://localhost:8080/api/v1/nodes

# 运行监控脚本
cd ~/hermesnexus && python scripts/monitor.py once
```

### 备份恢复
```bash
# 执行完整备份
cd ~/hermesnexus && ./scripts/backup.sh full

# 列出备份文件
./scripts/backup.sh list

# 验证备份
./scripts/backup.sh verify backups/hermesnexus_*.db.gz

# 恢复数据
./scripts/backup.sh restore backups/hermesnexus_*.db.gz
```

### 故障排查
```bash
# 查看应用日志
tail -f ~/hermesnexus/logs/cloud.log

# 查看系统资源
htop

# 检查端口占用
netstat -tulpn | grep 8080

# 检查数据库
sqlite3 ~/hermesnexus/data/hermesnexus.db "PRAGMA integrity_check;"
```

---

## ⚠️ 常见问题和解决方案

### 问题1: 服务启动失败
```bash
# 检查服务状态
sudo systemctl status hermesnexus

# 查看详细错误
journalctl -u hermesnexus -n 50

# 常见原因：
# 1. 配置文件错误 - 检查 .env.local
# 2. 端口占用 - netstat -tulpn | grep 8080
# 3. 权限问题 - ls -l ~/hermesnexus/
```

### 问题2: API无法访问
```bash
# 1. 检查服务状态
sudo systemctl status hermesnexus

# 2. 检查防火墙
sudo ufw status

# 3. 测试本地访问
curl http://localhost:8080/health

# 4. 检查端口监听
netstat -tulpn | grep 8080
```

### 问题3: 数据库问题
```bash
# 检查数据库文件
ls -lh ~/hermesnexus/data/

# 验证数据库完整性
sqlite3 ~/hermesnexus/data/hermesnexus.db "PRAGMA integrity_check;"

# 检查数据库权限
ls -l ~/hermesnexus/data/
```

---

## 📞 支持和帮助

### 文档资源
- **部署指南**: `DEPLOYMENT-GUIDE.md`
- **运维手册**: `docs/OPERATIONS-MANUAL.md`
- **故障排查**: `docs/56-故障处理Runbook.md`

### 脚本工具
- **部署脚本**: `scripts/deploy.sh`
- **备份脚本**: `scripts/backup.sh`
- **监控脚本**: `scripts/monitor.py`

### 紧急联系
- **系统日志**: `journalctl -u hermesnexus -f`
- **应用日志**: `tail -f ~/hermesnexus/logs/*.log`
- **系统监控**: `python ~/hermesnexus/scripts/monitor.py once`

---

## ✅ 部署成功标志

当看到以下情况时，说明部署成功：

1. **服务运行正常**
```bash
sudo systemctl status hermesnexus
# 显示: Active: active (running)
```

2. **API健康检查通过**
```bash
curl http://localhost:8080/health
# 显示: {"status":"healthy","timestamp":"...","version":"1.1.0"}
```

3. **系统监控评分良好**
```bash
python scripts/monitor.py once
# 显示: 总体评分: 100/100, 状态: 🟢 优秀
```

4. **备份功能正常**
```bash
./scripts/backup.sh full
# 显示: 🎉 完整备份完成！
```

---

## 🎯 下一步行动

### 立即执行 (部署当天)
1. ✅ 按照 `DEPLOYMENT-CHECKLIST.md` 执行部署
2. ✅ 运行 `PRODUCTION-TESTING-PLAN.md` 中的基础测试
3. ✅ 配置监控和告警
4. ✅ 执行首次备份

### 部署后1周内
1. ✅ 监控系统稳定性
2. ✅ 收集性能数据
3. ✅ 处理发现的问题
4. ✅ 优化配置参数

### 持续改进
1. ✅ 定期检查系统健康
2. ✅ 验证备份恢复
3. ✅ 更新安全配置
4. ✅ 规划功能扩展

---

**记住**: 如遇到问题，首先查看 `DEPLOYMENT-CHECKLIST.md` 中的故障排查部分，然后参考 `docs/56-故障处理Runbook.md` 获取详细解决方案。

**部署成功后，系统将进入正常运行阶段，享受完整的云边协同管理能力！** 🎉

---

*快速指南版本: 1.0*  
*创建时间: 2026年4月11日*  
*适用环境: 生产环境快速部署*  
*预计部署时间: 1.5-2小时*