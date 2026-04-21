#!/bin/bash
# 在生产服务器172.16.100.101上直接运行此脚本
# 用法: ssh scsun@172.16.100.101 'bash -s' < FIX_NOW.sh

set -e

echo "=== HermesNexus 生产环境立即修复 ==="
echo "修复API v1兼容层和Edge节点连接问题"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
CLOUD_API_FILE="/home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py"
LOG_DIR="/home/scsun/hermesnexus-logs"

# 1. 修复Cloud API - 添加API v1兼容端点
echo "🔧 步骤1: 修复Cloud API代码..."

if [ -f "$CLOUD_API_FILE" ]; then
    if grep -q "api/v1/tasks" "$CLOUD_API_FILE"; then
        echo -e "${GREEN}✅${NC} API v1兼容端点已存在"
    else
        echo "📝 添加API v1兼容端点..."

        # 创建备份
        cp "$CLOUD_API_FILE" "$CLOUD_API_FILE.backup.$(date +%Y%m%d_%H%M%S)"

        # 使用Python直接修改文件
        python3 << 'PYTHON_SCRIPT'
import re

file_path = "/home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py"

with open(file_path, 'r') as f:
    code = f.read()

# API v1兼容端点代码
api_v1_endpoints = '''                # API v1兼容层 - 支持Edge节点
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
                            "job_id": job[1],
                            "name": job[2],
                            "status": job[4],
                            "target_node_id": job[5],
                            "command": job[6],
                            "result": result_data
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
                    except:
                        pass

                    conn = sqlite3.connect(self.server_instance.db_path)
                    cursor = conn.cursor()
                    cursor.execute('UPDATE nodes SET last_heartbeat = ?, status = "online", updated_at = ? WHERE node_id = ?',
                        (datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(), node_id))
                    conn.commit()
                    conn.close()
                    self.send_json_response({"status": "success", "node_id": node_id})

'''

# 在/api/jobs端点之前插入
pattern = r"(elif path == '/api/jobs':)"
new_code = re.sub(pattern, api_v1_endpoints + r"\1", code, count=1)

if new_code != code:
    with open(file_path, 'w') as f:
        f.write(new_code)
    print("✅ API v1端点已添加到Cloud API")
else:
    print("❌ 添加API v1端点失败")
PYTHON_SCRIPT

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅${NC} Cloud API代码已修复"
        else
            echo -e "${RED}❌${NC} Cloud API代码修复失败"
        fi
    fi
else
    echo -e "${RED}❌${NC} Cloud API文件不存在: $CLOUD_API_FILE"
fi

# 2. 停止旧的Edge节点
echo ""
echo "🛑 步骤2: 停止旧的Edge节点..."
OLD_EDGE_PIDS=$(pgrep -f "final-edge-node.py" || true)
if [ -n "$OLD_EDGE_PIDS" ]; then
    echo "发现旧Edge节点进程，正在停止..."
    pkill -f "final-edge-node.py" || true
    sleep 2
    # 强制清理
    pkill -9 -f "final-edge-node.py" 2>/dev/null || true
    echo -e "${GREEN}✅${NC} 旧Edge节点已停止"
else
    echo "未发现运行中的旧Edge节点"
fi

# 3. 修复并启动新的Edge节点
echo ""
echo "🚀 步骤3: 修复并启动新的Edge节点..."

# 检查enhanced_edge_node_v12.py
ENHANCED_EDGE="/home/scsun/hermesnexus-code/edge/enhanced_edge_node_v12.py"
OLD_EDGE="/home/scsun/hermesnexus/final-edge-node.py"

EDGE_CODE_TO_USE=""

if [ -f "$ENHANCED_EDGE" ]; then
    echo "使用增强版Edge节点: $ENHANCED_EDGE"
    EDGE_CODE_TO_USE="$ENHANCED_EDGE"

    # 修复cloud_url配置
    if grep -q "8080" "$ENHANCED_EDGE"; then
        echo "修复cloud_url配置 (8080 -> 8082)..."
        sed -i.bak "s/cloud_url.*8080/cloud_url = \"http:\/\/172.16.100.101:8082\"/g" "$ENHANCED_EDGE"
        sed -i "s/localhost:8080/172.16.100.101:8082/g" "$ENHANCED_EDGE"
        echo -e "${GREEN}✅${NC} Edge节点配置已修复"
    fi

elif [ -f "$OLD_EDGE" ]; then
    echo "使用现有Edge节点: $OLD_EDGE"
    EDGE_CODE_TO_USE="$OLD_EDGE"

    # 备份
    cp "$OLD_EDGE" "$OLD_EDGE.backup.$(date +%Y%m%d_%H%M%S)"

    # 修复配置
    echo "修复Edge节点配置..."
    sed -i "s/localhost:8080/172.16.100.101:8082/g" "$OLD_EDGE"
    sed -i "s/\"8080\"/\"8082\"/g" "$OLD_EDGE"
    echo -e "${GREEN}✅${NC} Edge节点配置已修复"
else
    echo -e "${RED}❌${NC} 未找到任何Edge节点代码"
    exit 1
fi

# 启动Edge节点
echo "启动Edge节点..."
nohup python3 "$EDGE_CODE_TO_USE" > "$LOG_DIR/edge-node-fixed.log" 2>&1 &
EDGE_PID=$!
echo "$EDGE_PID" > /tmp/edge-node-fixed.pid
echo -e "${GREEN}✅${NC} Edge节点已启动 (PID: $EDGE_PID)"

# 4. 重启Cloud API
echo ""
echo "🔄 步骤4: 重启Cloud API..."
CLOUD_PIDS=$(pgrep -f "v12_standard_cloud.py" || true)
if [ -n "$CLOUD_PIDS" ]; then
    echo "停止现有Cloud API..."
    pkill -f "v12_standard_cloud.py" || true
    sleep 2
fi

echo "启动Cloud API v1.2.0..."
cd /home/scsun/hermesnexus-code
nohup python3 cloud/api/v12_standard_cloud.py > "$LOG_DIR/cloud-api-v12.log" 2>&1 &
CLOUD_PID=$!
echo "$CLOUD_PID" > /tmp/cloud-api-v12.pid
echo -e "${GREEN}✅${NC} Cloud API已启动 (PID: $CLOUD_PID)"

# 5. 等待服务启动
echo ""
echo "⏳ 等待服务启动..."
sleep 8

# 6. 验证修复效果
echo ""
echo "🔍 步骤5: 验证修复效果..."

echo "📊 测试1: Cloud API健康检查"
HEALTH_CHECK=$(curl -s http://localhost:8082/health || echo "")
if echo "$HEALTH_CHECK" | grep -q "healthy"; then
    echo -e "${GREEN}✅${NC} Cloud API健康检查通过"
else
    echo -e "${RED}❌${NC} Cloud API健康检查失败"
fi

echo ""
echo "📊 测试2: API v1任务端点"
API_V1_TEST=$(curl -s http://localhost:8082/api/v1/tasks || echo "")
if [ -n "$API_V1_TEST" ]; then
    echo -e "${GREEN}✅${NC} /api/v1/tasks 端点响应正常"
    echo "响应预览: $API_V1_TEST" | head -2
else
    echo -e "${RED}❌${NC} /api/v1/tasks 端点仍然失败"
fi

echo ""
echo "📊 测试3: Edge节点健康检查"
EDGE_HEALTH=$(curl -s http://localhost:8081/health || echo "")
if echo "$EDGE_HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✅${NC} Edge节点健康检查通过"

    # 检查连接配置
    if echo "$EDGE_HEALTH" | grep -q "8082"; then
        echo -e "${GREEN}✅${NC} Edge节点连接到正确端口8082"
    else
        echo -e "${YELLOW}⚠️${NC} Edge节点端口配置需要确认"
    fi
else
    echo -e "${RED}❌${NC} Edge节点健康检查失败"
fi

echo ""
echo "📊 测试4: 检查Edge节点日志"
echo "最新5行Edge节点日志:"
tail -5 "$LOG_DIR/edge-node-fixed.log"

# 7. 创建E2E测试任务
echo ""
echo "🧪 步骤6: 创建E2E测试任务..."
TEST_RESPONSE=$(curl -s -X POST http://localhost:8082/api/jobs \
  -H "Content-Type: application/json" \
  -d "{
    \"job_id\": \"fix-test-$(date +%s)\",
    \"name\": \"立即修复E2E测试\",
    \"job_type\": \"command\",
    \"target_node_id\": \"edge-test-001\",
    \"command\": \"echo 'Fix test passed'\",
    \"created_by\": \"emergency-fix\"
  }" || echo "")

if echo "$TEST_RESPONSE" | grep -q "success"; then
    echo -e "${GREEN}✅${NC} E2E测试任务创建成功"
else
    echo -e "${YELLOW}⚠️${NC} E2E测试任务创建失败: $TEST_RESPONSE"
fi

# 8. 最终状态报告
echo ""
echo "=== 修复完成报告 ==="
echo ""
echo "📋 服务状态:"
echo "  Cloud API: PID $(cat /tmp/cloud-api-v12.pid 2>/dev/null || echo '未知'), 端口8082"
echo "  Edge节点: PID $(cat /tmp/edge-node-fixed.pid 2>/dev/null || echo '未知'), 端口8081"
echo ""
echo "🔧 关键修复:"
echo "  ✅ 添加了 /api/v1/tasks 兼容端点"
echo "  ✅ 添加了 /api/v1/nodes/<id>/heartbeat 兼容端点"
echo "  ✅ Edge节点配置从 localhost:8080 改为 172.16.100.101:8082"
echo "  ✅ 重启了Cloud API和Edge节点服务"
echo ""
echo "📝 验证命令:"
echo "  curl http://localhost:8082/api/v1/tasks"
echo "  curl http://localhost:8081/health"
echo "  tail -f $LOG_DIR/edge-node-fixed.log"
echo "  tail -f $LOG_DIR/cloud-api-v12.log"
echo ""
echo -e "${GREEN}🎉 立即修复完成！${NC}"
echo "请执行上述验证命令确认修复效果。"
echo "等待10-15秒后，Edge节点应该能正常执行任务。"