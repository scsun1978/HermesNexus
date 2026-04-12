# HermesNexus 故障排查 Runbook

**Date**: 2026-04-12  
**Version**: 2.1.0  
**Scope**: Phase 2 Week 3 系统

---

## 🚨 快速诊断流程

### 第一步: 确认问题范围

**问题类型识别**:
```bash
# 1. 检查服务状态
sudo systemctl status hermesnexus

# 2. 检查端口监听
netstat -tuln | grep 8000

# 3. 检查进程
ps aux | grep hermesnexus

# 4. 检查日志
sudo journalctl -u hermesnexus -n 50
```

**问题分类**:
- 🔴 **服务级别**: 服务无法启动或崩溃
- 🟡 **性能级别**: 响应慢或超时
- 🟢 **功能级别**: 特定功能异常
- 🔵 **数据级别**: 数据丢失或不一致

---

## 🔴 服务级别问题

### 问题1: 服务无法启动

**症状**:
```bash
sudo systemctl start hermesnexus
# 服务启动失败
```

**诊断步骤**:
```bash
# 1. 查看详细错误
sudo journalctl -u hermesnexus -xe

# 2. 检查配置文件
cat .env | grep -v "SECRET"

# 3. 检查端口占用
sudo netstat -tuln | grep 8000
# 如果端口被占用，找到并终止占用进程
sudo lsof -ti:8000 | xargs kill -9

# 4. 检查数据库文件
ls -lh data/hermesnexus.db
# 文件损坏时重新初始化
./scripts/init-database.sh
```

**常见原因和解决方案**:

**原因1**: 配置文件错误
```bash
# 检查环境变量
set -a
source .env
set +a

# 验证必需配置
echo $DATABASE_URL
echo $SECRET_KEY
```

**原因2**: 依赖缺失
```bash
# 重新安装依赖
pip install -r requirements.txt --force-reinstall
```

**原因3**: 数据库文件损坏
```bash
# 备份现有数据库
cp data/hermesnexus.db data/hermesnexus.db.corrupted

# 重新初始化
./scripts/init-database.sh
```

### 问题2: 服务频繁崩溃

**症状**:
```bash
# 服务反复重启
sudo journalctl -u hermesnexus -f
# 显示 "Restarting..." 信息
```

**诊断步骤**:
```bash
# 1. 检查崩溃日志
sudo journalctl -u hermesnexus --since "1 hour ago" | grep -i "error\|crash\|exception"

# 2. 检查内存使用
free -h
ps aux | grep hermesnexus

# 3. 检查磁盘空间
df -h

# 4. 运行健康检查
curl http://localhost:8000/health
```

**解决方案**:

**内存不足**:
```bash
# 增加交换空间
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 优化内存使用
# 编辑 .env，减小连接池大小
POOL_SIZE=5
MAX_OVERFLOW=10
```

**数据库锁定**:
```bash
# 检查数据库锁
sqlite3 data/hermesnexus.db "PRAGMA database_list;"
sqlite3 data/hermesnexus.db "PRAGMA lock_status;"

# 重启数据库
sudo systemctl restart hermesnexus
```

---

## 🟡 性能级别问题

### 问题3: API响应缓慢

**症状**:
- API调用 > 1秒
- 用户体验明显下降
- 监控显示响应时间异常

**诊断步骤**:
```bash
# 1. 检查系统资源
htop  # 或 top

# 2. 检查数据库性能
sqlite3 data/hermesnexus.db "PRAGMA cache_size;"
sqlite3 data/hermesnexus.db "PRAGMA page_size;"

# 3. 运行性能测试
./tests/performance/run_performance_tests.sh

# 4. 检查慢查询
curl http://localhost:8000/metrics
```

**解决方案**:

**数据库连接池优化**:
```python
# 增加连接池大小
POOL_SIZE=10
MAX_OVERFLOW=20
```

**启用查询缓存**:
```python
# 在应用中启用缓存
CACHE_ENABLED=true
CACHE_TTL=300
```

**批量操作优化**:
```python
# 使用批量API代替单条操作
POST /api/v1/assets/bulk
```

### 问题4: 内存泄漏

**症状**:
- 服务内存持续增长
- 长时间运行后OOM

**诊断步骤**:
```bash
# 1. 监控内存使用
watch -n 5 'ps aux | grep hermesnexus'

# 2. 内存分析
pip install memory_profiler
python3 -m memory_profiler cloud/main.py

# 3. 检查对象泄漏
import gc
print(gc.get_count())
```

**解决方案**:
```python
# 定期清理
import gc
gc.collect()

# 使用连接池
# 自动管理数据库连接生命周期
```

---

## 🟢 功能级别问题

### 问题5: 认证失败

**症状**:
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/assets/
# 返回 401 Unauthorized
```

**诊断步骤**:
```bash
# 1. 检查认证是否启用
curl http://localhost:8000/health
# 查看 "auth_enabled" 字段

# 2. 验证Token
python3 -c "
from shared.security.auth_manager import auth_manager
user_info = auth_manager.validate_token('<token>')
print(user_info)
"

# 3. 创建新Token
python3 -c "
from shared.security.auth_manager import auth_manager
user_info = {'user_id': 'admin', 'role': 'admin', 'permissions': ['*']}
token = auth_manager.create_token(user_info)
print(token)
"
```

**解决方案**:
```bash
# 开发环境可临时关闭认证
export AUTH_ENABLED=false

# 生产环境重新生成Token
# 按照上面的步骤创建新Token
```

### 问题6: 数据不一致

**症状**:
- 前端显示与数据库不一致
- 统计数据错误

**诊断步骤**:
```bash
# 1. 检查数据库完整性
sqlite3 data/hermesnexus.db "PRAGMA integrity_check;"

# 2. 检查数据一致性
python3 -c "
from shared.database.sqlite_backend import SQLiteBackend
from shared.services.asset_service import AssetService

db = SQLiteBackend(database_url='sqlite:///data/hermesnexus.db')
asset_service = AssetService(database=db)

stats = asset_service.get_statistics()
print(stats)
"

# 3. 运行集成测试
./tests/integration/run_integration_tests.sh
```

**解决方案**:
```bash
# 重建统计
# 大多数统计问题可以通过重新计算解决

# 数据迁移
# 如果结构变更，运行数据迁移脚本
```

---

## 🔵 数据级别问题

### 问题7: 数据库损坏

**症状**:
```bash
sqlite3 data/hermesnexus.db "SELECT * FROM assets LIMIT 1;"
# Error: database disk image is malformed
```

**诊断步骤**:
```bash
# 1. 检查数据库文件
file data/hermesnexus.db

# 2. 尝试修复
sqlite3 data/hermesnexus.db "PRAGMA integrity_check;"

# 3. 导出数据
sqlite3 data/hermesnexus.db ".dump" > backup.sql
```

**解决方案**:
```bash
# 1. 备份损坏的数据库
cp data/hermesnexus.db data/hermesnexus.db.corrupted

# 2. 尝试在线修复
sqlite3 data/hermesnexus.db "PRAGMA integrity_check;"
sqlite3 data/hermesnexus.db "VACUUM;"

# 3. 如果修复失败，从备份恢复
cp data/hermesnexus.db.backup data/hermesnexus.db

# 4. 重新初始化
./scripts/init-database.sh
```

### 问题8: 数据丢失

**症状**:
- 数据记录数量异常减少
- 历史数据消失

**诊断步骤**:
```bash
# 1. 检查数据库文件
ls -lh data/*.db*

# 2. 检查备份
ls -lh data/backup/

# 3. 检查审计日志
curl http://localhost:8000/api/v1/audit/logs?limit=10
```

**解决方案**:
```bash
# 1. 从备份恢复
cp data/backup/hermesnexus.db.YYYYMMDD data/hermesnexus.db

# 2. 重启服务
sudo systemctl restart hermesnexus

# 3. 验证数据
./tests/integration/run_integration_tests.sh
```

---

## 🔍 高级诊断

### 系统级诊断

**1. 完整系统检查**:
```bash
#!/bin/bash
echo "=== HermesNexus 系统诊断 ==="

echo "1. 服务状态:"
sudo systemctl status hermesnexus

echo -e "\n2. 系统资源:"
echo "CPU: $(top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1)%"
echo "内存: $(free | grep Mem | awk '{printf("%.1f%%"), $3/$2*100}')"
echo "磁盘: $(df -h / | awk 'NR==2{print $5}')"

echo -e "\n3. 网络连接:"
netstat -tuln | grep :8000

echo -e "\n4. 进程信息:"
ps aux | grep [h]ermesnexus

echo -e "\n5. 最近的错误:"
sudo journalctl -u hermesnexus --since "1 hour ago" | grep -i error | tail -5

echo -e "\n6. 健康检查:"
curl -s http://localhost:8000/health | python3 -m json.tool
```

**2. 性能分析**:
```bash
# CPU性能分析
python3 -m cProfile -o profile.stats cloud/main.py
python3 -m pstats profile.stats

# 内存分析
pip install memory_profiler
python3 -m memory_profiler cloud/main.py
```

**3. 并发分析**:
```bash
# 模拟并发请求
for i in {1..100}; do
    curl http://localhost:8000/api/v1/assets/ &
done
wait
```

---

## 📞 升级处理

### 何时升级处理

**以下情况需要升级处理**:
- 服务无法恢复 (>30分钟宕机)
- 数据丢失或严重损坏
- 安全漏洞或入侵
- 性能严重下降 (>10倍)

### 紧急恢复流程

**1. 快速恢复服务**:
```bash
# 尝试快速重启
sudo systemctl restart hermesnexus

# 如果重启失败，尝试干净启动
sudo systemctl stop hermesnexus
# 清理锁文件和临时文件
sudo systemctl start hermesnexus
```

**2. 降级到上一版本**:
```bash
# 停止服务
sudo systemctl stop hermesnexus

# 回滚代码
cd /path/to/hermesnexus
git reset --hard <previous-stable-commit>

# 回滚依赖
pip install -r requirements.txt

# 启动服务
sudo systemctl start hermesnexus
```

**3. 从备份恢复**:
```bash
# 停止服务
sudo systemctl stop hermesnexus

# 恢复数据库
cp data/backup/hermesnexus.db.YYYYMMDD data/hermesnexus.db

# 启动服务
sudo systemctl start hermesnexus

# 验证恢复
./tests/e2e/run_smoke_tests.sh
```

---

## 📊 监控和告警

### 实时监控

**关键指标**:
```bash
# API响应时间
curl -s http://localhost:8000/metrics | grep response_time

# 数据库连接数
curl -s http://localhost:8000/metrics | grep db_connections

# 内存使用
ps aux | grep hermesnexus | awk '{print $6}'
```

### 告警规则

**建议配置**:
```yaml
# 告警规则示例
alerts:
  - name: high_response_time
    condition: response_time_p95 > 100ms
    action: "检查慢查询和数据库性能"

  - name: high_error_rate
    condition: error_rate > 1%
    action: "检查错误日志和服务状态"

  - name: high_memory_usage
    condition: memory_usage > 85%
    action: "检查内存泄漏和连接池"
```

---

## ✅ 预防措施

### 定期维护

**每日检查**:
- [ ] 检查服务状态
- [ ] 检查错误日志
- [ ] 检查磁盘空间

**每周检查**:
- [ ] 运行Smoke测试
- [ ] 检查性能基线
- [ ] 清理临时文件

**每月检查**:
- [ ] 运行完整测试套件
- [ ] 审查和优化索引
- [ ] 备份验证

### 容量规划

**监控指标**:
- 数据库大小增长
- API调用量增长
- 存储空间使用

**扩容建议**:
- 数据库 > 1GB: 考虑迁移到PostgreSQL
- QPS > 1000: 考虑负载均衡
- 存储 > 80%: 考虑清理或扩容

---

**Runbook维护**: 本文档将在故障排查过程中持续更新，记录新发现的问题和解决方案。

**更新频率**: 每次重大故障处理后更新，定期review。
