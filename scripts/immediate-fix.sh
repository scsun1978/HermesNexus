#!/bin/bash
# 立即修复生产环境的API v1兼容性和Edge节点问题
# 在生产服务器上直接执行此脚本

echo "=== HermesNexus 立即修复脚本 ==="
echo "在生产服务器上执行以下命令"
echo ""

YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}请在服务器172.16.100.101上依次执行以下命令:${NC}"
echo ""

echo "## 1. 首先下载并运行API修复脚本"
echo 'cd /home/scsun/hermesnexus-code'
echo 'python3 -c "
import re

# 读取Cloud API文件
with open(\"cloud/api/v12_standard_cloud.py\", \"r\") as f:
    code = f.read()

# 检查是否已包含API v1端点
if \"api/v1/tasks\" not in code:
    # 在/api/jobs端点前插入API v1兼容端点
    api_v1_code = \"\"\"
                # API v1兼容层
                elif path == \"/api/v1/tasks\":
                    conn = sqlite3.connect(self.server_instance.db_path)
                    cursor = conn.cursor()
                    cursor.execute(\"SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100\")
                    jobs = cursor.fetchall()

                    job_list = []
                    for job in jobs:
                        try:
                            result_data = json.loads(job[7]) if job[7] else None
                        except:
                            result_data = None

                        job_list.append({
                            \"job_id\": job[1],
                            \"name\": job[2],
                            \"status\": job[4],
                            \"command\": job[6],
                            \"result\": result_data
                        })

                    conn.close()
                    self.send_json_response({\"tasks\": job_list, \"total\": len(job_list)})

                elif path.startswith(\"/api/v1/nodes/\") and path.endswith(\"/heartbeat\"):
                    parts = path.split(\"/\")
                    node_id = parts[4]
                    content_length = int(self.headers.get(\"Content-Length\", 0))
                    post_data = self.rfile.read(content_length)
                    try:
                        body_data = json.loads(post_data.decode(\"utf-8\"))
                    except:
                        body_data = {}
                    node_id = body_data.get(\"node_id\", node_id)

                    conn = sqlite3.connect(self.server_instance.db_path)
                    cursor = conn.cursor()
                    cursor.execute(\"UPDATE nodes SET last_heartbeat = ?, status = \"online\", updated_at = ? WHERE node_id = ?\",
                        (datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(), node_id))
                    conn.commit()
                    conn.close()
                    self.send_json_response({\"status\": \"success\", \"node_id\": node_id})

\"\"\"

    # 找到插入点并插入
    pattern = r\"(elif path == \"/api/jobs\":)\"
    new_code = re.sub(pattern, api_v1_code + r\"\\1\", code, count=1)

    if new_code != code:
        with open(\"cloud/api/v12_standard_cloud.py\", \"w\") as f:
            f.write(new_code)
        print(\"✅ API v1端点已添加\")
    else:
        print(\"❌ 添加失败\")
else:
    print(\"✅ API v1端点已存在\")
"'
echo ""

echo "## 2. 停止旧的Edge节点"
echo "pkill -f final-edge-node.py || true"
echo "sleep 2"
echo ""

echo "## 3. 修复Edge节点配置并重启"
echo "# 检查enhanced_edge_node_v12.py是否存在"
echo 'if [ -f "edge/enhanced_edge_node_v12.py" ]; then'
echo "  # 修复cloud_url配置"
echo '  sed -i "s/cloud_url.*8080/cloud_url = \"http:\/\/172.16.100.101:8082\"/g" edge/enhanced_edge_node_v12.py'
echo "  # 启动增强版Edge节点"
echo "  nohup python3 edge/enhanced_edge_node_v12.py > /home/scsun/hermesnexus-logs/edge-node-v12.log 2>&1 &"
echo '  echo $! > /tmp/edge-node-v12.pid'
echo "  echo \"✅ 增强版Edge节点已启动\""
echo 'elif [ -f "/home/scsun/hermesnexus/final-edge-node.py" ]; then'
echo "  # 备份并修复现有Edge节点"
echo '  cp /home/scsun/hermesnexus/final-edge-node.py /home/scsun/hermesnexus/final-edge-node.py.backup'
echo '  sed -i "s/localhost:8080/172.16.100.101:8082/g" /home/scsun/hermesnexus/final-edge-node.py'
echo '  sed -i "s/8080/8082/g" /home/scsun/hermesnexus/final-edge-node.py'
echo "  nohup python3 /home/scsun/hermesnexus/final-edge-node.py > /home/scsun/hermesnexus-logs/edge-node-fixed.log 2>&1 &"
echo '  echo $! > /tmp/edge-node-fixed.pid'
echo "  echo \"✅ 修复版Edge节点已启动\""
echo "fi"
echo ""

echo "## 4. 重启Cloud API (如果需要)"
echo "pkill -f v12_standard_cloud.py || true"
echo "sleep 3"
echo "cd /home/scsun/hermesnexus-code"
echo "nohup python3 cloud/api/v12_standard_cloud.py > /home/scsun/hermesnexus-logs/cloud-api-v12.log 2>&1 &"
echo 'echo $! > /tmp/cloud-api-v12.pid'
echo ""

echo "## 5. 验证修复效果"
echo "sleep 5"
echo "echo \"=== 测试API v1端点 ===\""
echo "curl -s http://localhost:8082/api/v1/tasks | head -3"
echo ""
echo "echo \"=== 测试Edge节点 ===\""
echo "curl -s http://localhost:8081/health"
echo ""
echo "echo \"=== 检查Edge节点日志 ===\""
echo "tail -5 /home/scsun/hermesnexus-logs/edge-node-v12.log"
echo ""

echo "## 6. 创建E2E测试任务"
echo 'curl -X POST http://localhost:8082/api/jobs -H "Content-Type: application/json" -d '"'"'{"job_id": "fix-test-'$(date +%s)'", "name": "修复测试", "job_type": "command", "target_node_id": "edge-test-001", "command": "echo \"Fix test passed\"", "created_by": "fix"}'"'"''
echo ""

echo "🎯 修复完成后，请检查:"
echo "1. /api/v1/tasks 端点应返回任务列表 (不再是404)"
echo "2. Edge节点日志不再显示localhost:8080连接错误"
echo "3. Edge节点应正常连接到172.16.100.101:8082"
echo "4. 任务执行链路应完整工作"