#!/bin/bash
# HermesNexus 生产环境紧急修复脚本
# 立即修复API v1兼容层和Edge节点连接问题

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "=== HermesNexus 生产环境紧急修复 ==="
echo "修复API v1兼容层和Edge节点连接问题"
echo ""

# 配置
CLOUD_API_PORT=8082
EDGE_NODE_PORT=8081
PROJECT_DIR="/home/scsun/hermesnexus-code"
LOG_DIR="/home/scsun/hermesnexus-logs"
DATA_DIR="/home/scsun/hermesnexus-data"

# 1. 检查当前运行的Cloud API代码
log_info "🔍 检查当前Cloud API代码..."
CURRENT_CLOUD_API="$PROJECT_DIR/cloud/api/v12_standard_cloud.py"

if [ -f "$CURRENT_CLOUD_API" ]; then
    # 检查是否包含API v1兼容端点
    if grep -q "api/v1/tasks" "$CURRENT_CLOUD_API"; then
        log_success "当前代码已包含API v1兼容层"
    else
        log_error "当前代码缺少API v1兼容层，需要立即更新"
        log_info "正在添加API v1兼容端点..."

        # 备份现有代码
        cp "$CURRENT_CLOUD_API" "$CURRENT_CLOUD_API.emergency-backup.$(date +%Y%m%d_%H%M%S)"

        # 在do_GET方法中添加API v1兼容端点（在现有的elif链条后添加）
        # 找到do_GET方法中的合适位置插入新端点
        sed -i '/elif path == '\''\/api\/jobs'\'':/i \
        # API v1 兼容层 - /api/v1/tasks\
        elif path == '\''/api/v1/tasks'\'':\
            # 重定向到任务列表\
            conn = sqlite3.connect(self.server_instance.db_path)\
            cursor = conn.cursor()\
            cursor.execute('\''SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100'\'')\
            jobs = cursor.fetchall()\
            \
            job_list = []\
            for job in jobs:\
                job_list.append({\
                    "job_id": job[1],\
                    "name": job[2],\
                    "job_type": job[3],\
                    "status": job[4],\
                    "target_node_id": job[5],\
                    "command": job[6],\
                    "result": json.loads(job[7]) if job[7] else None,\
                    "created_at": job[9]\
                })\
            \
            self.send_json_response({\
                "tasks": job_list,\
                "total": len(job_list)\
            })\
            conn.close()\
' "$CURRENT_CLOUD_API"

        log_success "API v1任务端点已添加"
    fi
else
    log_error "Cloud API文件不存在: $CURRENT_CLOUD_API"
    exit 1
fi

# 2. 修复Edge节点问题
log_info "🔍 检查Edge节点配置..."
EDGE_PROCESS=$(pgrep -f "final-edge-node.py" || true)

if [ -n "$EDGE_PROCESS" ]; then
    log_info "发现运行中的Edge节点进程 (PID: $EDGE_PROCESS)"
    log_info "Edge节点正在使用旧代码，需要重启"

    # 停止旧的Edge节点
    log_info "停止旧Edge节点..."
    kill "$EDGE_PROCESS" 2>/dev/null || true
    sleep 2

    # 如果进程还在运行，强制杀死
    if pgrep -f "final-edge-node.py" > /dev/null; then
        pkill -9 -f "final-edge-node.py" 2>/dev/null || true
        sleep 1
    fi

    log_success "旧Edge节点已停止"
fi

# 3. 启动更新的Edge节点
log_info "🚀 启动更新的Edge节点..."

# 检查enhanced_edge_node_v12.py是否存在
ENHANCED_EDGE="$PROJECT_DIR/../edge/enhanced_edge_node_v12.py"
if [ ! -f "$ENHANCED_EDGE" ]; then
    ENHANCED_EDGE="/home/scsun/hermesnexus-code/edge/enhanced_edge_node_v12.py"
fi

if [ -f "$ENHANCED_EDGE" ]; then
    log_info "使用增强版Edge节点: $ENHANCED_EDGE"

    # 检查并修复cloud_url配置
    if grep -q "cloud_url.*8080" "$ENHANCED_EDGE"; then
        log_info "修复Edge节点cloud_url配置 (8080 -> 8082)..."
        sed -i 's/cloud_url.*8080/cloud_url = "http:\/\/172.16.100.101:8082"/g' "$ENHANCED_EDGE"
        log_success "Edge节点配置已修复"
    fi

    # 启动增强版Edge节点
    cd "$PROJECT_DIR"
    nohup python3 "$ENHANCED_EDGE" > "$LOG_DIR/edge-node-v12.log" 2>&1 &
    EDGE_PID=$!
    echo "$EDGE_PID" > /tmp/edge-node-v12.pid

    log_success "增强版Edge节点已启动 (PID: $EDGE_PID)"
else
    log_error "未找到增强版Edge节点代码: $ENHANCED_EDGE"
    log_info "尝试使用现有Edge节点代码并修复配置..."

    # 使用现有的Edge节点代码但修复配置
    EXISTING_EDGE="/home/scsun/hermesnexus/final-edge-node.py"
    if [ -f "$EXISTING_EDGE" ]; then
        # 备份现有代码
        cp "$EXISTING_EDGE" "$EXISTING_EDGE.backup.$(date +%Y%m%d_%H%M%S)"

        # 修复cloud_url和端口配置
        sed -i 's/localhost:8080/172.16.100.101:8082/g' "$EXISTING_EDGE"
        sed -i 's/8080/8082/g' "$EXISTING_EDGE"

        # 启动修复后的Edge节点
        nohup python3 "$EXISTING_EDGE" > "$LOG_DIR/edge-node-fixed.log" 2>&1 &
        EDGE_PID=$!
        echo "$EDGE_PID" > /tmp/edge-node-fixed.pid

        log_success "修复版Edge节点已启动 (PID: $EDGE_PID)"
    else
        log_error "未找到任何Edge节点代码"
    fi
fi

# 4. 等待服务启动
log_info "⏳ 等待服务启动..."
sleep 5

# 5. 验证API v1端点
log_info "🔍 验证API v1兼容端点..."

# 测试/api/v1/tasks
log_info "测试 GET /api/v1/tasks..."
API_V1_TEST=$(curl -s "http://localhost:$CLOUD_API_PORT/api/v1/tasks" || echo "")
if [ -n "$API_V1_TEST" ]; then
    log_success "/api/v1/tasks 端点现在可以访问"
    echo "响应: $API_V1_TEST" | head -3
else
    log_error "/api/v1/tasks 端点仍然无法访问"
fi

# 6. 验证Edge节点
log_info "🔍 验证Edge节点状态..."
sleep 3

EDGE_HEALTH=$(curl -s "http://localhost:$EDGE_NODE_PORT/health" || echo "")
if echo "$EDGE_HEALTH" | grep -q "healthy"; then
    log_success "Edge节点健康状态正常"

    # 检查Edge节点配置
    EDGE_STATUS=$(curl -s "http://localhost:$EDGE_NODE_PORT/status" || echo "")
    if echo "$EDGE_STATUS" | grep -q "8082"; then
        log_success "Edge节点现在连接到端口8082"
    else
        log_warning "Edge节点可能仍在连接错误端口"
    fi
else
    log_error "Edge节点健康检查失败"
fi

# 7. 检查Edge节点日志
log_info "📋 检查Edge节点日志（最新10行）..."
if [ -f "$LOG_DIR/edge-node-v12.log" ]; then
    tail -10 "$LOG_DIR/edge-node-v12.log"
elif [ -f "$LOG_DIR/edge-node-fixed.log" ]; then
    tail -10 "$LOG_DIR/edge-node-fixed.log"
fi

# 8. 创建E2E测试任务
log_info "🧪 创建E2E测试任务..."
TEST_RESPONSE=$(curl -s -X POST "http://localhost:$CLOUD_API_PORT/api/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "emergency-fix-test-'$(date +%s)'",
    "name": "紧急修复E2E测试",
    "job_type": "command",
    "target_node_id": "edge-test-001",
    "command": "echo \"Emergency fix E2E test passed\",
    "created_by": "emergency-fix"
  }' || echo "")

if echo "$TEST_RESPONSE" | grep -q "success"; then
    log_success "E2E测试任务创建成功"
else
    log_warning "E2E测试任务创建失败: $TEST_RESPONSE"
fi

# 9. 最终状态检查
echo ""
echo "=== 紧急修复完成 ==="
echo ""

echo "📋 服务状态:"
echo "  Cloud API端口: $CLOUD_API_PORT"
echo "  Edge节点端口: $EDGE_NODE_PORT"

if [ -f "/tmp/cloud-api-v12.pid" ]; then
    CLOUD_PID=$(cat /tmp/cloud-api-v12.pid)
    echo "  Cloud API进程: $CLOUD_PID"
fi

if [ -f "/tmp/edge-node-v12.pid" ]; then
    EDGE_PID=$(cat /tmp/edge-node-v12.pid)
    echo "  Edge节点进程: $EDGE_PID"
elif [ -f "/tmp/edge-node-fixed.pid" ]; then
    EDGE_PID=$(cat /tmp/edge-node-fixed.pid)
    echo "  Edge节点进程: $EDGE_PID"
fi

echo ""
echo "🔍 验证命令:"
echo "  API v1测试: curl http://localhost:$CLOUD_API_PORT/api/v1/tasks"
echo "  节点健康: curl http://localhost:$EDGE_NODE_PORT/health"
echo "  Cloud日志: tail -f $LOG_DIR/cloud-api-v12.log"
echo "  Edge日志: tail -f $LOG_DIR/edge-node-v12.log"
echo ""

log_success "🚨 紧急修复完成！请执行上述验证命令确认修复效果。"

exit 0