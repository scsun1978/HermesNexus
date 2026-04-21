#!/bin/bash
# HermesNexus 生产环境完整修复执行脚本
# 在生产服务器172.16.100.101上执行此脚本

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
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

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo "=== HermesNexus 生产环境完整修复 ==="
echo "解决API v1兼容层和Edge节点连接问题"
echo ""

# 配置
CLOUD_API_FILE="/home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py"
LOG_DIR="/home/scsun/hermesnexus-logs"
FIX_DIR="/home/scsun/hermesnexus-fix"

# 1. 创建修复目录
log_info "📁 创建修复目录..."
mkdir -p "$FIX_DIR"
mkdir -p "$LOG_DIR"

# 2. 下载修复脚本
log_info "📥 准备修复脚本..."

# 这里假设修复脚本已经上传到服务器，如果没有，需要先上传
if [ ! -f "$FIX_DIR/api_v1_patch.py" ]; then
    log_error "修复脚本不存在，请先上传api_v1_patch.py到服务器"
    log_info "上传命令: scp fix/api_v1_patch.py scsun@172.16.100.101:$FIX_DIR/"
    exit 1
fi

# 3. 修复Cloud API
log_info "🔧 步骤1: 修复Cloud API代码..."
python3 "$FIX_DIR/api_v1_patch.py" "$CLOUD_API_FILE"

if [ $? -eq 0 ]; then
    log_success "Cloud API代码修复成功"
else
    log_error "Cloud API代码修复失败"
    exit 1
fi

# 4. 修复Edge节点
log_info "🔧 步骤2: 修复Edge节点配置..."

if [ -f "$FIX_DIR/edge_fix.py" ]; then
    python3 "$FIX_DIR/edge_fix.py"
    if [ $? -eq 0 ]; then
        log_success "Edge节点修复成功"
    else
        log_error "Edge节点修复失败"
    fi
else
    log_warning "Edge修复脚本不存在，尝试手动修复..."

    # 手动停止Edge节点
    log_info "停止旧Edge节点..."
    pkill -f final-edge-node.py 2>/dev/null || true
    pkill -f enhanced_edge_node 2>/dev/null || true
    sleep 2

    # 查找并修复Edge节点文件
    EDGE_FILE=""
    if [ -f "/home/scsun/hermesnexus-code/edge/enhanced_edge_node_v12.py" ]; then
        EDGE_FILE="/home/scsun/hermesnexus-code/edge/enhanced_edge_node_v12.py"
    elif [ -f "/home/scsun/hermesnexus/final-edge-node.py" ]; then
        EDGE_FILE="/home/scsun/hermesnexus/final-edge-node.py"
    fi

    if [ -n "$EDGE_FILE" ]; then
        log_info "修复Edge节点文件: $EDGE_FILE"
        # 备份
        cp "$EDGE_FILE" "$EDGE_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        # 修复配置
        sed -i "s/localhost:8080/172.16.100.101:8082/g" "$EDGE_FILE"
        sed -i 's/cloud_url.*8080/cloud_url = "http:\/\/172.16.100.101:8082"/g' "$EDGE_FILE"
        # 启动
        nohup python3 "$EDGE_FILE" > "$LOG_DIR/edge-node-fixed.log" 2>&1 &
        echo $! > /tmp/edge-node-fixed.pid
        log_success "Edge节点已启动"
    else
        log_error "未找到Edge节点文件"
    fi
fi

# 5. 重启Cloud API
log_info "🔄 步骤3: 重启Cloud API..."
pkill -f v12_standard_cloud.py 2>/dev/null || true
sleep 3

cd /home/scsun/hermesnexus-code
nohup python3 cloud/api/v12_standard_cloud.py > "$LOG_DIR/cloud-api-v12.log" 2>&1 &
CLOUD_PID=$!
echo "$CLOUD_PID" > /tmp/cloud-api-v12.pid
log_success "Cloud API已重启 (PID: $CLOUD_PID)"

# 6. 等待服务启动
log_info "⏳ 等待服务启动..."
sleep 8

# 7. 验证修复效果
log_info "🔍 步骤4: 验证修复效果..."

echo ""
echo "📊 测试1: Cloud API健康检查"
HEALTH_CHECK=$(curl -s http://localhost:8082/health || echo "")
if echo "$HEALTH_CHECK" | grep -q "healthy"; then
    log_success "Cloud API健康检查通过"
    VERSION=$(echo "$HEALTH_CHECK" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    echo "   版本: $VERSION"
else
    log_error "Cloud API健康检查失败"
fi

echo ""
echo "📊 测试2: API v1任务端点"
API_V1_TEST=$(curl -s http://localhost:8082/api/v1/tasks || echo "")
if [ -n "$API_V1_TEST" ]; then
    log_success "/api/v1/tasks 端点响应正常"
    echo "   响应: $API_V1_TEST" | head -2
else
    log_error "/api/v1/tasks 端点仍然失败"
fi

echo ""
echo "📊 测试3: Edge节点健康检查"
EDGE_HEALTH=$(curl -s http://localhost:8081/health || echo "")
if echo "$EDGE_HEALTH" | grep -q "healthy"; then
    log_success "Edge节点健康检查通过"
    if echo "$EDGE_HEALTH" | grep -q "8082"; then
        log_success "Edge节点连接到正确端口8082"
    fi
else
    log_error "Edge节点健康检查失败"
fi

echo ""
echo "📊 测试4: 检查Edge节点最新日志"
if [ -f "$LOG_DIR/edge-node-fixed.log" ]; then
    echo "最新5行日志:"
    tail -5 "$LOG_DIR/edge-node-fixed.log"
elif [ -f "$LOG_DIR/edge-node-v12.log" ]; then
    echo "最新5行日志:"
    tail -5 "$LOG_DIR/edge-node-v12.log"
fi

# 8. 创建E2E测试任务
echo ""
log_info "🧪 步骤5: 创建E2E测试任务..."
TEST_RESPONSE=$(curl -s -X POST http://localhost:8082/api/jobs \
  -H "Content-Type: application/json" \
  -d "{
    \"job_id\": \"fix-test-$(date +%s)\",
    \"name\": \"完整修复E2E测试\",
    \"job_type\": \"command\",
    \"target_node_id\": \"edge-test-001\",
    \"command\": \"echo 'HermesNexus fix completed successfully'\",
    \"created_by\": \"production-fix\"
  }" || echo "")

if echo "$TEST_RESPONSE" | grep -q "success"; then
    log_success "E2E测试任务创建成功"

    # 提取任务ID用于后续检查
    TEST_JOB_ID=$(echo "$TEST_RESPONSE" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4 | head -1)
    if [ -n "$TEST_JOB_ID" ]; then
        echo "   任务ID: $TEST_JOB_ID"
        echo "   请等待15-20秒后检查任务执行状态"
    fi
else
    log_warning "E2E测试任务创建失败: $TEST_RESPONSE"
fi

# 9. 最终状态报告
echo ""
echo "=== 修复完成报告 ==="
echo ""
echo "📋 服务状态:"
CLOUD_PID_NUM=$(cat /tmp/cloud-api-v12.pid 2>/dev/null || echo "未知")
EDGE_PID_NUM=$(cat /tmp/edge-node-fixed.pid 2>/dev/null || echo "未知")
echo "  Cloud API: PID $CLOUD_PID_NUM, 端口8082"
echo "  Edge节点: PID $EDGE_PID_NUM, 端口8081"
echo ""
echo "🔧 已执行的修复:"
echo "  ✅ 添加了 /api/v1/tasks 兼容端点"
echo "  ✅ 添加了 /api/v1/nodes/<id>/heartbeat 兼容端点"
echo "  ✅ Edge节点配置改为 172.16.100.101:8082"
echo "  ✅ 重启了Cloud API和Edge节点服务"
echo ""
echo "📝 后续验证命令:"
echo "  # 检查API v1端点"
echo "  curl http://localhost:8082/api/v1/tasks"
echo ""
echo "  # 检查Edge节点"
echo "  curl http://localhost:8081/health"
echo ""
echo "  # 监控任务执行"
echo "  watch -n 5 'curl -s http://localhost:8082/api/jobs | grep -A 5 fix-test'"
echo ""
echo "  # 查看实时日志"
echo "  tail -f $LOG_DIR/edge-node-fixed.log"
echo "  tail -f $LOG_DIR/cloud-api-v12.log"
echo ""
log_success "🎉 完整修复执行完成！"
echo ""
echo "⏰ 请等待15-20秒让Edge节点处理测试任务，然后执行上述验证命令。"
echo "🎯 如果E2E测试任务状态变为'completed'，说明修复成功！"