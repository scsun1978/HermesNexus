# 🚨 HermesNexus 紧急修复指南

## 问题诊断

根据复测结果，当前生产环境存在以下问题：

### ❌ 实际问题
1. **API v1兼容端点缺失**: 生产服务器上运行的Cloud API代码没有包含API v1兼容层
2. **Edge节点配置错误**: 仍在运行旧代码`final-edge-node.py`，连接`localhost:8080`
3. **服务不同步**: 本地代码修复没有真正部署到生产环境

### ✅ 预期状态
1. Cloud API应包含`/api/v1/tasks`等兼容端点
2. Edge节点应连接到`172.16.100.101:8082`
3. 完整的E2E任务执行链路应正常工作

---

## 🚀 立即修复方案

### 方法一：一键自动修复（推荐）

直接在生产服务器上运行我们准备好的修复脚本：

```bash
# 1. 将修复脚本上传到服务器
scp scripts/FIX_NOW.sh scsun@172.16.100.101:/home/scsun/

# 2. 登录服务器并执行修复
ssh scsun@172.16.100.101
cd /home/scsun
chmod +x FIX_NOW.sh
./FIX_NOW.sh
```

### 方法二：手动修复（如方法一失败）

如果自动修复脚本无法运行，按以下步骤手动修复：

#### 步骤1: 修复Cloud API代码

```bash
# 登录服务器
ssh scsun@172.16.100.101

# 备份现有代码
cd /home/scsun/hermesnexus-code
cp cloud/api/v12_standard_cloud.py cloud/api/v12_standard_cloud.py.backup.$(date +%Y%m%d_%H%M%S)

# 使用Python直接修改代码添加API v1端点
python3 << 'EOF'
import re

file_path = "cloud/api/v12_standard_cloud.py"
with open(file_path, 'r') as f:
    code = f.read()

# API v1兼容端点代码
api_v1_code = '''                # API v1兼容层
                elif path == '/api/v1/tasks':
                    conn = sqlite3.connect(self.server_instance.db_path)
                    cursor = conn.cursor()
                    cursor.execute('SELECT * FROM jobs ORDER BY created_at DESC LIMIT 50')
                    jobs = cursor.fetchall()
                    job_list = []
                    for job in jobs:
                        try:
                            result_data = json.loads(job[7]) if job[7] else None
                        except:
                            result_data = None
                        job_list.append({
                            "job_id": job[1], "name": job[2], "status": job[4],
                            "target_node_id": job[5], "command": job[6], "result": result_data
                        })
                    conn.close()
                    self.send_json_response({"tasks": job_list, "total": len(job_list)})

                elif path.startswith('/api/v1/nodes/') and 'heartbeat' in path:
                    parts = path.split('/')
                    node_id = parts[4] if len(parts) > 4 else 'unknown'
                    content_length = int(self.headers.get('Content-Length', 0))
                    post_data = self.rfile.read(content_length)
                    try:
                        body_data = json.loads(post_data.decode('utf-8'))
                        node_id = body_data.get('node_id', node_id)
                    except: pass
                    conn = sqlite3.connect(self.server_instance.db_path)
                    cursor = conn.cursor()
                    cursor.execute('UPDATE nodes SET last_heartbeat = ?, status = "online", updated_at = ? WHERE node_id = ?',
                        (datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(), node_id))
                    conn.commit()
                    conn.close()
                    self.send_json_response({"status": "success", "node_id": node_id})

'''

# 在/api/jobs端点前插入
pattern = r"(elif path == '/api/jobs':)"
new_code = re.sub(pattern, api_v1_code + r"\1", code, count=1)
with open(file_path, 'w') as f:
    f.write(new_code)
print("✅ API v1端点已添加")
EOF
```

#### 步骤2: 停止旧的Edge节点

```bash
# 停止旧的Edge节点进程
pkill -f final-edge-node.py || true
sleep 2
pkill -9 -f final-edge-node.py 2>/dev/null || true
```

#### 步骤3: 修复并启动Edge节点

```bash
# 使用增强版Edge节点（如果存在）
if [ -f "edge/enhanced_edge_node_v12.py" ]; then
    # 修复配置
    sed -i "s/localhost:8080/172.16.100.101:8082/g" edge/enhanced_edge_node_v12.py
    sed -i "s/cloud_url.*8080/cloud_url = \"http:\/\/172.16.100.101:8082\"/g" edge/enhanced_edge_node_v12.py

    # 启动
    nohup python3 edge/enhanced_edge_node_v12.py > /home/scsun/hermesnexus-logs/edge-node-v12.log 2>&1 &
    echo $! > /tmp/edge-node-v12.pid
    echo "✅ 增强版Edge节点已启动"

# 否则修复现有Edge节点
elif [ -f "/home/scsun/hermesnexus/final-edge-node.py" ]; then
    # 备份
    cp /home/scsun/hermesnexus/final-edge-node.py /home/scsun/hermesnexus/final-edge-node.py.backup

    # 修复配置
    sed -i "s/localhost:8080/172.16.100.101:8082/g" /home/scsun/hermesnexus/final-edge-node.py
    sed -i "s/\"8080\"/\"8082\"/g" /home/scsun/hermesnexus/final-edge-node.py

    # 启动
    nohup python3 /home/scsun/hermesnexus/final-edge-node.py > /home/scsun/hermesnexus-logs/edge-node-fixed.log 2>&1 &
    echo $! > /tmp/edge-node-fixed.pid
    echo "✅ 修复版Edge节点已启动"
fi
```

#### 步骤4: 重启Cloud API

```bash
# 停止现有Cloud API
pkill -f v12_standard_cloud.py || true
sleep 3

# 启动新的Cloud API
nohup python3 cloud/api/v12_standard_cloud.py > /home/scsun/hermesnexus-logs/cloud-api-v12.log 2>&1 &
echo $! > /tmp/cloud-api-v12.pid
echo "✅ Cloud API已重启"
```

---

## ✅ 验证修复效果

修复完成后，执行以下验证命令：

```bash
# 1. 测试API v1端点（应该不再是404）
curl http://localhost:8082/api/v1/tasks

# 2. 测试Edge节点健康
curl http://localhost:8081/health

# 3. 检查Edge节点日志（不应再有localhost:8080错误）
tail -10 /home/scsun/hermesnexus-logs/edge-node-v12.log
# 或者
tail -10 /home/scsun/hermesnexus-logs/edge-node-fixed.log

# 4. 创建测试任务
curl -X POST http://localhost:8082/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_id": "fix-test-'$(date +%s)'", "name": "修复测试", "job_type": "command", "target_node_id": "edge-test-001", "command": "echo \"Fix passed\"", "created_by": "test"}'

# 5. 等待15秒后检查任务状态
sleep 15
curl http://localhost:8082/api/jobs | grep fix-test
```

---

## 🎯 预期结果

### 修复前 ❌
```
GET /api/v1/tasks → 404 Not Found
Edge日志: Connection refused (localhost:8080)
任务状态: pending (不执行)
```

### 修复后 ✅
```
GET /api/v1/tasks → 200 OK (返回任务列表)
Edge日志: 正常连接到 172.16.100.101:8082
任务状态: pending → running → completed
```

---

## 🔄 回滚方案

如果修复出现问题：

```bash
# 1. 停止所有服务
kill $(cat /tmp/cloud-api-v12.pid) 2>/dev/null || true
kill $(cat /tmp/edge-node-v12.pid) 2>/dev/null || true

# 2. 恢复备份
LATEST_BACKUP=$(ls -t /home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py.backup.* | head -1)
cp "$LATEST_BACKUP" /home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py

# 3. 重启原始服务
cd /home/scsun/hermesnexus-code
nohup python3 cloud/api/v12_standard_cloud.py > /home/scsun/hermesnexus-logs/cloud-api-v12.log 2>&1 &
echo $! > /tmp/cloud-api-v12.pid
```

---

## 📊 成功标准

修复成功的标志：

- ✅ `GET /api/v1/tasks` 返回200 OK和任务列表
- ✅ Edge节点日志不再显示`localhost:8080`连接错误
- ✅ Edge节点健康检查返回`healthy`状态
- ✅ 创建的任务能在15-20秒内从`pending`变为`completed`
- ✅ E2E测试任务显示完整的执行结果

---

## 🚨 注意事项

1. **执行顺序**: 必须按照上述顺序执行，先修复Cloud API，再修复Edge节点
2. **服务重启**: 代码修改后必须重启服务才能生效
3. **日志监控**: 修复后要密切关注日志输出，确保服务正常运行
4. **时间等待**: Edge节点轮询间隔为10秒，需要等待15-20秒才能看到任务执行效果

---

## 📞 故障排查

如遇到问题，请检查：

```bash
# 查看Cloud API日志
tail -f /home/scsun/hermesnexus-logs/cloud-api-v12.log

# 查看Edge节点日志
tail -f /home/scsun/hermesnexus-logs/edge-node-v12.log

# 检查进程状态
ps aux | grep -E "v12_standard_cloud|edge.*node"

# 检查端口占用
lsof -i :8082
lsof -i :8081

# 检查网络连接
ping 172.16.100.101
curl -v http://localhost:8082/health
```

---

**预计修复时间**: 5-10分钟
**验证时间**: 10-15分钟
**总计**: 20分钟内完成

🎯 **立即执行修复，解决API不匹配问题！**