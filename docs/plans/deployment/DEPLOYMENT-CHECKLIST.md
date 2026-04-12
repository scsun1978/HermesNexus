# HermesNexus 生产环境部署检查清单

## 🚀 部署前检查 (Pre-Deployment)

### 环境准备
- [ ] 服务器连接正常: `ssh scsun@172.16.100.101`
- [ ] 操作系统版本兼容 (Ubuntu 20.04+ / Debian 11+)
- [ ] 磁盘空间充足 (> 5GB 可用): `df -h`
- [ ] 内存充足 (> 2GB): `free -h`
- [ ] 网络连接正常: `ping -c 3 google.com`

### 软件依赖
- [ ] Python 3.14+ 已安装: `python3 --version`
- [ ] pip 已安装: `pip3 --version`
- [ ] Git 已安装: `git --version`
- [ ] SQLite3 已安装: `sqlite3 --version`
- [ ] 防火墙已配置: `sudo ufw status`

### 配置文件
- [ ] 生产环境配置文件已准备: `.env.production`
- [ ] 数据库路径已配置: `SQLITE_DB_PATH`
- [ ] 备份目录已配置: `BACKUP_DIR`
- [ ] 日志目录已配置: `LOG_DIR`
- [ ] 安全密钥已更新: `JWT_SECRET`, `API_AUTH_TOKEN`

### 安全检查
- [ ] 默认密码已修改
- [ ] SSH密钥认证已配置
- [ ] 防火墙规则已设置
- [ ] API端口(8080)已开放
- [ ] 敏感文件权限已设置

---

## 📦 部署步骤 (Deployment Steps)

### 1. 服务器准备 (15分钟)
```bash
# 1.1 连接到服务器
ssh scsun@172.16.100.101

# 1.2 创建项目目录
mkdir -p ~/hermesnexus
cd ~/hermesnexus
mkdir -p {data,logs,backups,scripts,cloud,edge}

# 1.3 安装系统依赖
sudo apt update
sudo apt install -y python3.14 python3-pip python3-venv git sqlite3

# 1.4 配置防火墙
sudo ufw allow ssh
sudo ufw allow 8080/tcp
sudo ufw enable
```

- [ ] 项目目录创建完成
- [ ] 系统依赖安装完成
- [ ] 防火墙配置完成

### 2. 应用部署 (30分钟)
```bash
# 2.1 克隆代码仓库 (或上传代码)
cd ~
git clone <your-repo-url> hermesnexus-temp
cd hermesnexus-temp

# 2.2 创建虚拟环境
cd ~/hermesnexus
python3 -m venv venv
source venv/bin/activate

# 2.3 安装依赖
pip install --upgrade pip
pip install fastapi uvicorn pydantic python-multipart aiohttp psutil requests

# 2.4 部署应用文件
cp -r ~/hermesnexus-temp/cloud ~/hermesnexus/
cp -r ~/hermesnexus-temp/edge ~/hermesnexus/
cp -r ~/hermesnexus-temp/scripts ~/hermesnexus/
cp ~/hermesnexus-temp/.env.production ~/hermesnexus/.env
chmod +x ~/hermesnexus/scripts/*.sh
```

- [ ] 代码部署完成
- [ ] 虚拟环境创建完成
- [ ] 依赖安装完成
- [ ] 文件权限设置完成

### 3. 配置管理 (20分钟)
```bash
# 3.1 编辑配置文件
cd ~/hermesnexus
cp .env.production .env.local
nano .env.local

# 3.2 关键配置项
# SQLITE_DB_PATH=/home/scsun/hermesnexus/data/hermesnexus.db
# BACKUP_DIR=/home/scsun/hermesnexus/backups
# LOG_DIR=/home/scsun/hermesnexus/logs
# JWT_SECRET=your-strong-secret-here
# API_AUTH_TOKEN=your-strong-token-here

# 3.3 创建systemd服务
sudo nano /etc/systemd/system/hermesnexus.service
```

**systemd服务配置**:
```ini
[Unit]
Description=HermesNexus Cloud API Service
After=network.target

[Service]
Type=simple
User=scsun
WorkingDirectory=/home/scsun/hermesnexus
Environment="PATH=/home/scsun/hermesnexus/venv/bin"
EnvironmentFile=/home/scsun/hermesnexus/.env.local
ExecStart=/home/scsun/hermesnexus/venv/bin/python cloud/api/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

- [ ] 配置文件编辑完成
- [ ] systemd服务配置完成
- [ ] 配置参数验证通过

### 4. 服务启动 (10分钟)
```bash
# 4.1 重载systemd配置
sudo systemctl daemon-reload

# 4.2 启动服务
sudo systemctl start hermesnexus

# 4.3 设置开机自启
sudo systemctl enable hermesnexus

# 4.4 检查服务状态
sudo systemctl status hermesnexus
```

- [ ] systemd服务启动成功
- [ ] 开机自启已设置
- [ ] 服务运行状态正常

### 5. 健康检查 (15分钟)
```bash
# 5.1 API健康检查
curl http://localhost:8080/health

# 5.2 系统统计检查
curl http://localhost:8080/api/v1/stats

# 5.3 运行监控脚本
cd ~/hermesnexus
python scripts/monitor.py once

# 5.4 首次备份测试
./scripts/backup.sh full
```

- [ ] API健康检查通过
- [ ] 系统统计正常
- [ ] 监控脚本运行正常
- [ ] 备份功能测试通过

---

## ✅ 部署后验证 (Post-Deployment)

### 功能验证
- [ ] 健康检查接口正常: `curl http://localhost:8080/health`
- [ ] 节点列表查询正常: `curl http://localhost:8080/api/v1/nodes`
- [ ] 设备创建功能正常: 测试创建设备
- [ ] 任务执行功能正常: 测试创建任务
- [ ] Web控制台可访问: 浏览器访问 `http://172.16.100.101:8080`

### 数据验证
- [ ] 数据库文件创建: `ls -lh data/hermesnexus.db`
- [ ] 数据库连接正常: `sqlite3 data/hermesnexus.db "SELECT COUNT(*) FROM nodes;"`
- [ ] 数据持久化验证: 重启服务后数据保留
- [ ] 备份文件生成: `ls -lh backups/`

### 监控验证
- [ ] 系统监控正常: `python scripts/monitor.py once`
- [ ] 日志文件生成: `ls -lh logs/`
- [ ] 资源使用正常: CPU < 80%, 内存 < 80%
- [ ] 服务自动重启正常: 测试重启后自动恢复

### 网络验证
- [ ] 本地访问正常: `curl http://localhost:8080/health`
- [ ] 远程访问正常: 从外部访问 `http://172.16.100.101:8080`
- [ ] 防火墙规则生效: `sudo ufw status`
- [ ] 端口监听正常: `netstat -tulpn | grep 8080`

---

## 🧪 基础功能测试

### API功能测试
```bash
# 1. 健康检查
curl -X GET http://localhost:8080/health
# 预期: {"status":"healthy","timestamp":"...","version":"1.1.0"}

# 2. 获取系统统计
curl -X GET http://localhost:8080/api/v1/stats
# 预期: 返回节点、设备、任务、事件统计

# 3. 创建测试设备
curl -X POST http://localhost:8080/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{"device_id":"test-001","name":"测试设备","type":"ssh","host":"localhost","port":22}'
# 预期: {"status":"success","message":"设备创建成功"}

# 4. 创建测试任务
curl -X POST http://localhost:8080/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_id":"job-001","node_id":"edge-node-001","task_type":"execute","command":"echo test"}'
# 预期: {"status":"success","message":"任务创建成功"}
```

- [ ] 健康检查通过
- [ ] 统计查询正常
- [ ] 设备创建成功
- [ ] 任务创建成功

### 数据持久化测试
```bash
# 1. 创建测试数据
curl -X POST http://localhost:8080/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_id":"persist-test","node_id":"edge-node-001","task_type":"execute","command":"date"}'

# 2. 记录当前状态
curl http://localhost:8080/api/v1/stats

# 3. 重启服务
sudo systemctl restart hermesnexus
sleep 5

# 4. 验证数据保留
curl http://localhost:8080/api/v1/stats
```

- [ ] 测试数据创建成功
- [ ] 服务重启正常
- [ ] 数据完全保留
- [ ] 统计数据一致

### 备份恢复测试
```bash
# 1. 执行备份
cd ~/hermesnexus
./scripts/backup.sh full

# 2. 验证备份文件
./scripts/backup.sh list

# 3. 检查备份完整性
BACKUP_FILE=$(ls -t backups/hermesnexus_*.db.gz | head -1)
./scripts/backup.sh verify $BACKUP_FILE
```

- [ ] 备份文件创建成功
- [ ] 备份列表显示正常
- [ ] 备份完整性验证通过

---

## 🔧 运维配置 (Operations Setup)

### 监控配置
```bash
# 1. 添加定时监控任务
crontab -e
# 添加以下行:
# */5 * * * * /home/scsun/hermesnexus/venv/bin/python /home/scsun/hermesnexus/scripts/monitor.py once >> /home/scsun/hermesnexus/logs/monitor.log 2>&1

# 2. 添加定时备份任务
# 0 2 * * * /home/scsun/hermesnexus/scripts/backup.sh full >> /home/scsun/hermesnexus/logs/backup.log 2>&1
```

- [ ] 监控任务配置完成
- [ ] 备份任务配置完成
- [ ] crontab任务生效

### 日志配置
```bash
# 1. 配置日志轮转
sudo nano /etc/logrotate.d/hermesnexus

# 添加以下内容:
# /home/scsun/hermesnexus/logs/*.log {
#     daily
#     missingok
#     rotate 14
#     compress
#     delaycompress
#     notifempty
#     create 0640 scsun scsun
# }
```

- [ ] 日志轮转配置完成
- [ ] 日志目录权限正确

### 告警配置
- [ ] 监控告警通知配置 (如需要)
- [ ] 邮件通知设置 (如需要)
- [ ] Webhook通知配置 (如需要)
- [ ] 告警阈值设置

---

## 📊 部署验收标准

### 功能验收
- [ ] 所有核心API功能正常
- [ ] 云边协同功能正常
- [ ] 数据持久化工作正常
- [ ] Web控制台可访问

### 性能验收
- [ ] API响应时间 < 200ms
- [ ] 系统资源使用 < 80%
- [ ] 并发处理能力满足需求
- [ ] 无明显性能瓶颈

### 稳定性验收
- [ ] 服务连续运行 > 1小时无异常
- [ ] 自动重启机制正常
- [ ] 错误处理健壮
- [ ] 日志记录完整

### 运维验收
- [ ] 监控系统正常工作
- [ ] 备份恢复功能验证
- [ ] 运维文档完整
- [ ] 应急预案可执行

---

## 🚨 故障排查 (Troubleshooting)

### 服务启动失败
1. 检查服务状态: `sudo systemctl status hermesnexus`
2. 查看详细日志: `journalctl -u hermesnexus -n 50`
3. 检查配置文件: `cat ~/hermesnexus/.env.local`
4. 手动启动测试: `cd ~/hermesnexus && source venv/bin/activate && python cloud/api/main.py`

### API无法访问
1. 检查服务状态: `sudo systemctl status hermesnexus`
2. 检查端口监听: `netstat -tulpn | grep 8080`
3. 检查防火墙: `sudo ufw status`
4. 测试本地访问: `curl http://localhost:8080/health`

### 数据库问题
1. 检查数据库文件: `ls -lh ~/hermesnexus/data/`
2. 验证数据库完整性: `sqlite3 ~/hermesnexus/data/hermesnexus.db "PRAGMA integrity_check;"`
3. 检查文件权限: `ls -l ~/hermesnexus/data/`
4. 查看数据库日志: `tail ~/hermesnexus/logs/*.log`

### 性能问题
1. 运行监控脚本: `cd ~/hermesnexus && python scripts/monitor.py once`
2. 检查系统资源: `top`, `htop`, `free -h`
3. 查看进程状态: `ps aux | grep python`
4. 分析日志文件: `grep ERROR ~/hermesnexus/logs/*.log`

---

## 📞 支持资源

### 文档资源
- 部署指南: `DEPLOYMENT-GUIDE.md`
- 测试计划: `PRODUCTION-TESTING-PLAN.md`
- 运维手册: `docs/OPERATIONS-MANUAL.md`
- 故障排查: `docs/56-故障处理Runbook.md`

### 脚本工具
- 部署脚本: `scripts/deploy.sh`
- 备份脚本: `scripts/backup.sh`
- 监控脚本: `scripts/monitor.py`

### 系统命令
- 服务管理: `sudo systemctl status|start|stop|restart hermesnexus`
- 日志查看: `journalctl -u hermesnexus -f`
- 资源监控: `htop`, `iotop`, `netstat`

---

## ✅ 部署完成确认

当所有检查项都完成后，请确认：

- [ ] **部署状态**: ✅ 成功完成
- [ ] **功能状态**: ✅ 所有功能正常
- [ ] **性能状态**: ✅ 性能指标达标
- [ ] **监控状态**: ✅ 监控系统运行
- [ ] **备份状态**: ✅ 备份功能正常
- [ ] **文档状态**: ✅ 运维文档完整

**部署完成时间**: _____________  
**部署完成人员**: _____________  
**系统版本**: v1.1.0  
**部署环境**: scsun@172.16.100.101:22  

---

*检查清单版本: 1.0*  
*创建时间: 2026年4月11日*  
*适用环境: 生产环境部署*  
*预计部署时间: 1.5-2小时*