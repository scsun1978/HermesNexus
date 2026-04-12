# HermesNexus 生产环境部署计划与测试安排

## 📅 部署计划概览
**创建时间**: 2026年4月11日  
**目标环境**: scsun@172.16.100.101:22 (开发/测试服务器)  
**预计部署时间**: 1-2小时  
**部署窗口**: 建议在低峰期进行

---

## 🎯 部署目标

将HermesNexus从本地开发环境部署到目标服务器，实现：
- ✅ 生产级云边协同平台运行
- ✅ 完整的数据持久化和备份机制
- ✅ 实时监控和告警体系
- ✅ 完整的运维操作流程

---

## 📋 部署前准备清单

### 1.1 服务器环境验证
- [ ] 服务器连接验证：`ssh scsun@172.16.100.101`
- [ ] 操作系统版本检查：`cat /etc/os-release`
- [ ] 磁盘空间检查：`df -h` (需要 > 5GB 可用空间)
- [ ] 内存检查：`free -h` (建议 > 2GB)
- [ ] 网络连接检查：`ping -c 3 google.com`

### 1.2 软件依赖检查
- [ ] Python 3.14+ 安装：`python3 --version`
- [ ] Git 安装：`git --version`
- [ ] SQLite3 安装：`sqlite3 --version`
- [ ] 防火墙状态：`sudo ufw status` (确保8080端口可访问)

### 1.3 网络和安全配置
- [ ] 确认SSH密钥认证配置
- [ ] 确认服务器防火墙规则
- [ ] 准备生产环境密钥和密码
- [ ] 配置域名解析 (如需要)

### 1.4 配置文件准备
- [ ] 生产环境配置文件：`.env.production`
- [ ] 数据库路径配置：`SQLITE_DB_PATH`
- [ ] 备份目录配置：`BACKUP_DIR`
- [ ] 日志目录配置：`LOG_DIR`

---

## 🚀 详细部署步骤

### Phase 1: 服务器环境准备 (20分钟)

#### 1.1 连接到目标服务器
```bash
ssh scsun@172.16.100.101
```

#### 1.2 创建项目目录
```bash
# 创建项目根目录
mkdir -p ~/hermesnexus
cd ~/hermesnexus

# 创建必要的子目录
mkdir -p {data,logs,backups,scripts,cloud,edge}
```

#### 1.3 安装系统依赖
```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 安装必要的系统包
sudo apt install -y python3.14 python3-pip python3-venv git sqlite3

# 验证安装
python3 --version
pip3 --version
git --version
sqlite3 --version
```

#### 1.4 配置防火墙
```bash
# 允许SSH (始终保持)
sudo ufw allow ssh

# 允许HermesNexus API端口
sudo ufw allow 8080/tcp

# 启用防火墙
sudo ufw enable

# 验证状态
sudo ufw status
```

### Phase 2: 代码部署 (30分钟)

#### 2.1 克隆代码仓库
```bash
cd ~
git clone <repository-url> hermesnexus-temp
cd hermesnexus-temp
```

#### 2.2 创建Python虚拟环境
```bash
cd ~/hermesnexus
python3 -m venv venv
source venv/bin/activate

# 升级pip
pip install --upgrade pip
```

#### 2.3 安装项目依赖
```bash
cd ~/hermesnexus-temp
pip install -r requirements.txt

# 或手动安装核心依赖
pip install fastapi uvicorn pydantic python-multipart aiohttp psutil requests
```

#### 2.4 部署应用文件
```bash
# 复制核心文件到目标目录
cp -r cloud ~/hermesnexus/
cp -r edge ~/hermesnexus/
cp -r scripts ~/hermesnexus/
cp .env.production ~/hermesnexus/.env
cp -r docs ~/hermesnexus/

# 设置脚本执行权限
chmod +x ~/hermesnexus/scripts/*.sh
```

### Phase 3: 配置管理 (20分钟)

#### 3.1 配置生产环境变量
```bash
cd ~/hermesnexus
cp .env.production .env.local

# 编辑配置文件
nano .env.local
```

**关键配置项修改**：
```bash
# 数据库配置
SQLITE_DB_PATH=/home/scsun/hermesnexus/data/hermesnexus.db

# 备份配置
BACKUP_DIR=/home/scsun/hermesnexus/backups
LOG_DIR=/home/scsun/hermesnexus/logs

# 安全配置 - 使用强密码
JWT_SECRET=your-strong-jwt-secret-here
API_AUTH_TOKEN=your-strong-api-token-here

# 服务配置
CLOUD_API_HOST=0.0.0.0
CLOUD_API_PORT=8080
```

#### 3.2 创建系统服务配置
```bash
# 创建systemd服务文件
sudo nano /etc/systemd/system/hermesnexus.service
```

**服务配置内容**：
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

#### 3.3 配置日志轮转
```bash
sudo nano /etc/logrotate.d/hermesnexus
```

**日志轮转配置**：
```
/home/scsun/hermesnexus/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 scsun scsun
    sharedscripts
    postrotate
        systemctl reload hermesnexus >/dev/null 2>&1 || true
    endscript
}
```

### Phase 4: 启动和验证 (20分钟)

#### 4.1 启动服务
```bash
cd ~/hermesnexus
source venv/bin/activate

# 手动启动测试
python cloud/api/main.py &

# 或使用systemd
sudo systemctl daemon-reload
sudo systemctl start hermesnexus
sudo systemctl enable hermesnexus
```

#### 4.2 健康检查
```bash
# 检查服务状态
sudo systemctl status hermesnexus

# API健康检查
curl http://localhost:8080/health

# 系统统计检查
curl http://localhost:8080/api/v1/stats
```

#### 4.3 运行监控脚本
```bash
cd ~/hermesnexus
python scripts/monitor.py once
```

#### 4.4 首次备份测试
```bash
cd ~/hermesnexus
./scripts/backup.sh full
```

### Phase 5: 边缘节点部署 (15分钟)

#### 5.1 在目标服务器上部署边缘节点
```bash
cd ~/hermesnexus
source venv/bin/activate

# 启动边缘节点服务
python -m edge.runtime.core &
```

#### 5.2 验证节点注册
```bash
# 检查节点是否成功注册
curl http://localhost:8080/api/v1/nodes
```

#### 5.3 创建测试设备
```bash
# 创建测试设备
curl -X POST http://localhost:8080/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test-device-001",
    "name": "测试设备001",
    "type": "ssh",
    "host": "localhost",
    "port": 22
  }'
```

---

## 🧪 生产环境测试计划

### 测试阶段1: 功能验证测试 (30分钟)

#### 1.1 API功能测试
```bash
# API健康检查
curl -X GET http://172.16.100.101:8080/health

# 节点管理测试
curl -X GET http://172.16.100.101:8080/api/v1/nodes

# 设备管理测试
curl -X POST http://172.16.100.101:8080/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{"device_id": "device-test", "name": "测试设备", "type": "ssh", "host": "localhost", "port": 22}'

# 任务创建测试
curl -X POST http://172.16.100.101:8080/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_id": "job-test-001", "node_id": "edge-node-001", "task_type": "execute", "command": "echo Hello World"}'
```

#### 1.2 数据持久化测试
```bash
# 创建测试数据
curl -X POST http://172.16.100.101:8080/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_id": "persistence-test", "node_id": "edge-node-001", "task_type": "execute", "command": "date"}'

# 重启服务
sudo systemctl restart hermesnexus
sleep 5

# 验证数据是否保留
curl http://172.16.100.101:8080/api/v1/jobs
```

#### 1.3 备份恢复测试
```bash
# 执行完整备份
./scripts/backup.sh full

# 列出备份文件
./scripts/backup.sh list

# 验证备份完整性
./scripts/backup.sh verify backups/hermesnexus_*.db.gz
```

### 测试阶段2: 性能和压力测试 (20分钟)

#### 2.1 并发请求测试
```bash
# 安装Apache Bench
sudo apt install -y apache2-utils

# 并发测试
ab -n 1000 -c 10 http://172.16.100.101:8080/health
```

#### 2.2 资源监控测试
```bash
# 启动持续监控
python scripts/monitor.py continuous

# 观察CPU、内存使用情况
# 在另一个终端执行压力测试
```

### 测试阶段3: 故障恢复测试 (15分钟)

#### 3.1 服务重启测试
```bash
# 重启服务
sudo systemctl restart hermesnexus

# 检查启动时间
time curl http://localhost:8080/health
```

#### 3.2 数据恢复测试
```bash
# 备份当前数据
./scripts/backup.sh full

# 模拟数据损坏
rm data/hermesnexus.db

# 从备份恢复
./scripts/backup.sh restore backups/hermesnexus_*.db.gz

# 验证恢复结果
curl http://localhost:8080/api/v1/stats
```

#### 3.3 网络中断测试
```bash
# 暂停网络接口
sudo ip link set eth0 down
sleep 10
sudo ip link set eth0 up

# 验证服务自动恢复
curl http://localhost:8080/health
```

---

## 🔧 运维配置

### 监控和告警设置

#### 1. 定时监控任务
```bash
# 添加到crontab
crontab -e

# 每5分钟检查一次系统健康
*/5 * * * * /home/scsun/hermesnexus/venv/bin/python /home/scsun/hermesnexus/scripts/monitor.py once >> /home/scsun/hermesnexus/logs/monitor.log 2>&1

# 每天凌晨2点执行备份
0 2 * * * /home/scsun/hermesnexus/scripts/backup.sh full >> /home/scsun/hermesnexus/logs/backup.log 2>&1
```

#### 2. 日志监控
```bash
# 实时查看日志
tail -f logs/cloud.log

# 查看错误日志
grep ERROR logs/cloud.log | tail -20
```

#### 3. 性能监控
```bash
# 使用系统监控工具
htop
iotop
netstat -tulpn | grep 8080
```

### 日常运维检查清单

#### 每日检查 (自动化)
- [ ] 系统健康状态检查
- [ ] 服务运行状态检查
- [ ] 磁盘空间检查
- [ ] 备份执行状态

#### 每周检查 (手动)
- [ ] 日志文件审查
- [ ] 性能指标分析
- [ ] 安全更新检查
- [ ] 备份完整性验证

#### 每月检查
- [ ] 系统安全更新
- [ ] 性能调优评估
- [ ] 备份恢复演练
- [ ] 文档更新

---

## 📊 验收标准

### 功能验收
- ✅ 所有API端点正常响应
- ✅ 节点注册和管理正常
- ✅ 设备配置和管理正常
- ✅ 任务创建和执行正常
- ✅ 数据持久化正常工作
- ✅ Web控制台可访问

### 性能验收
- ✅ API响应时间 < 200ms
- ✅ 系统资源使用合理 (< 80%)
- ✅ 并发处理能力 > 10 req/s
- ✅ 服务可用性 > 99%

### 稳定性验收
- ✅ 服务连续运行 > 24小时无异常
- ✅ 数据备份恢复成功
- ✅ 故障自动恢复正常
- ✅ 日志记录完整

### 运维验收
- ✅ 监控告警正常工作
- ✅ 备份恢复流程验证通过
- ✅ 运维文档完整
- ✅ 应急预案可执行

---

## 🚨 应急预案

### 服务异常处理
1. 检查服务状态：`sudo systemctl status hermesnexus`
2. 查看日志：`tail -f logs/cloud.log`
3. 重启服务：`sudo systemctl restart hermesnexus`
4. 如果问题持续，检查系统资源：`htop`

### 数据异常处理
1. 立即停止服务：`sudo systemctl stop hermesnexus`
2. 备份当前数据：`./scripts/backup.sh full`
3. 从最新备份恢复：`./scripts/backup.sh restore <backup-file>`
4. 重启服务：`sudo systemctl start hermesnexus`

### 性能异常处理
1. 检查系统资源：`python scripts/monitor.py once`
2. 查看进程状态：`ps aux | grep hermes`
3. 分析日志：`grep ERROR logs/cloud.log`
4. 根据情况调整配置参数

---

## 📞 支持和联系

### 技术支持
- 项目文档：`docs/` 目录
- 运维手册：`docs/OPERATIONS-MANUAL.md`
- 部署指南：`DEPLOYMENT-GUIDE.md`
- 故障排查：`docs/56-故障处理Runbook.md`

### 监控和告警
- 系统监控：`scripts/monitor.py`
- 备份状态：`./scripts/backup.sh list`
- 服务状态：`sudo systemctl status hermesnexus`

---

## ✅ 部署完成检查

当所有步骤完成后，确认以下项目：

- [ ] 服务正常运行：`sudo systemctl status hermesnexus`
- [ ] API可访问：`curl http://localhost:8080/health`
- [ ] 节点在线：`curl http://localhost:8080/api/v1/nodes`
- [ ] 监控正常：`python scripts/monitor.py once`
- [ ] 备份完成：`./scripts/backup.sh list`
- [ ] 日志正常：`tail logs/cloud.log`

**部署完成后，系统进入正常运行阶段，开始7x24小时监控和维护。**

---

*文档版本: 1.0*  
*创建时间: 2026年4月11日*  
*适用环境: 生产环境部署*  
*预计部署时间: 1-2小时*