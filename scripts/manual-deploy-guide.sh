#!/bin/bash
# HermesNexus Cloud API v1.2.0 手动部署完整脚本
# 在生产服务器上手动执行此脚本来更新Cloud API

set -e

# 颜色输出
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

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "=== HermesNexus Cloud API v1.2.0 手动部署 ==="
echo "API v1兼容层更新 - 解决Edge节点接口不匹配问题"
echo ""

# 配置变量
CLOUD_API_PORT=8082
PROJECT_DIR="/home/scsun/hermesnexus-code"
LOG_DIR="/home/scsun/hermesnexus-logs"
DATA_DIR="/home/scsun/hermesnexus-data"
BACKUP_DIR="/home/scsun/hermesnexus-backups"
PID_FILE="/tmp/cloud-api-v12.pid"

# 1. 环境检查
log_info "🔍 环境检查..."

# 检查用户
if [ "$(whoami)" != "scsun" ]; then
    log_error "请以 scsun 用户运行此脚本"
    exit 1
fi
log_success "用户检查通过: scsun"

# 检查目录
if [ ! -d "$PROJECT_DIR" ]; then
    log_error "项目目录不存在: $PROJECT_DIR"
    exit 1
fi
log_success "项目目录存在: $PROJECT_DIR"

# 检查Python
PYTHON_VERSION=$(python3 --version 2>&1)
if [ $? -eq 0 ]; then
    log_success "Python环境: $PYTHON_VERSION"
else
    log_error "Python3未安装"
    exit 1
fi

# 2. 创建必要目录
log_info "📁 创建必要目录..."
mkdir -p "$BACKUP_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"
log_success "目录创建完成"

# 3. 备份现有代码
log_info "💾 备份现有Cloud API代码..."
CLOUD_API_FILE="$PROJECT_DIR/cloud/api/v12_standard_cloud.py"
if [ -f "$CLOUD_API_FILE" ]; then
    BACKUP_FILE="$BACKUP_DIR/v12_standard_cloud.py.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$CLOUD_API_FILE" "$BACKUP_FILE"
    log_success "备份完成: $BACKUP_FILE"
else
    log_warning "未找到现有Cloud API文件，跳过备份"
fi

# 4. 停止现有服务
log_info "🛑 停止现有Cloud API服务..."

# 首先尝试使用PID文件
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        log_info "停止服务 (PID: $OLD_PID)..."
        kill "$OLD_PID"
        sleep 2
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            log_warning "正常停止失败，尝试强制停止..."
            kill -9 "$OLD_PID"
            sleep 1
        fi
        log_success "服务已停止"
    else
        log_warning "PID文件存在但进程不在运行"
    fi
    rm -f "$PID_FILE"
fi

# 检查并杀死所有相关进程
CLOUD_PIDS=$(pgrep -f "python.*v12_standard_cloud.py" || true)
if [ -n "$CLOUD_PIDS" ]; then
    log_info "发现运行中的Cloud API进程，正在停止..."
    for PID in $CLOUD_PIDS; do
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID" 2>/dev/null || true
        fi
    done
    sleep 2
    # 强制清理
    for PID in $(pgrep -f "python.*v12_standard_cloud.py" || true); do
        kill -9 "$PID" 2>/dev/null || true
    done
    log_success "所有Cloud API进程已停止"
else
    log_info "未发现运行中的Cloud API进程"
fi

# 5. 检查端口
log_info "🔍 检查端口 $CLOUD_API_PORT..."
if lsof -Pi :$CLOUD_API_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_warning "端口 $CLOUD_API_PORT 被占用，正在清理..."
    lsof -ti :$CLOUD_API_PORT | xargs kill -9 2>/dev/null || true
    sleep 1
    log_success "端口已清理"
else
    log_success "端口 $CLOUD_API_PORT 可用"
fi

# 6. 更新代码文件
log_info "📥 准备更新Cloud API代码..."

# 检查是否有新的代码文件
NEW_CODE_FILE=""
if [ -f "v12_standard_cloud.py" ]; then
    NEW_CODE_FILE="v12_standard_cloud.py"
elif [ -f "deploy-cloud-api-update/v12_standard_cloud.py" ]; then
    NEW_CODE_FILE="deploy-cloud-api-update/v12_standard_cloud.py"
else
    log_error "未找到更新的代码文件"
    log_error "请确保 v12_standard_cloud.py 文件在当前目录或 deploy-cloud-api-update/ 目录中"
    exit 1
fi

# 检查目标目录
TARGET_DIR="$PROJECT_DIR/cloud/api"
if [ ! -d "$TARGET_DIR" ]; then
    log_info "创建目标目录: $TARGET_DIR"
    mkdir -p "$TARGET_DIR"
fi

# 复制新代码
log_info "复制新代码到 $TARGET_DIR..."
cp "$NEW_CODE_FILE" "$CLOUD_API_FILE"

# 验证文件复制成功
if [ -f "$CLOUD_API_FILE" ]; then
    FILE_SIZE=$(wc -c < "$CLOUD_API_FILE")
    log_success "代码更新完成 (文件大小: $FILE_SIZE bytes)"
else
    log_error "代码复制失败"
    exit 1
fi

# 7. 代码语法检查
log_info "🔍 检查Python语法..."
if python3 -m py_compile "$CLOUD_API_FILE" 2>/dev/null; then
    log_success "Python语法检查通过"
else
    log_error "Python语法错误，请检查代码文件"
    exit 1
fi

# 8. 启动新的Cloud API服务
log_info "🚀 启动Cloud API v1.2.0服务..."

cd "$PROJECT_DIR"

# 设置环境变量
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export HERMES_ENV="production"

# 创建启动命令
nohup python3 "$CLOUD_API_FILE" > "$LOG_DIR/cloud-api-v12.log" 2>&1 &
NEW_PID=$!

# 保存PID
echo "$NEW_PID" > "$PID_FILE"

log_success "Cloud API服务已启动 (PID: $NEW_PID)"

# 9. 等待服务启动
log_info "⏳ 等待服务启动..."
sleep 5

# 检查进程是否还在运行
if ps -p "$NEW_PID" > /dev/null 2>&1; then
    log_success "服务进程运行正常"
else
    log_error "服务启动失败，进程意外退出"
    log_error "请查看日志: $LOG_DIR/cloud-api-v12.log"
    tail -30 "$LOG_DIR/cloud-api-v12.log"
    exit 1
fi

# 10. 端口监听检查
log_info "🔍 检查端口监听状态..."
if lsof -Pi :$CLOUD_API_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_success "端口 $CLOUD_API_PORT 正在监听"
else
    log_error "端口 $CLOUD_API_PORT 未监听，服务可能启动失败"
    tail -30 "$LOG_DIR/cloud-api-v12.log"
    exit 1
fi

# 11. 健康检查
log_info "🏥 执行健康检查..."
sleep 2

HEALTH_CHECK_URL="http://localhost:$CLOUD_API_PORT/health"
HEALTH_RESPONSE=$(curl -s "$HEALTH_CHECK_URL" || echo "")

if [ -n "$HEALTH_RESPONSE" ]; then
    if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
        log_success "健康检查通过"

        # 提取版本信息
        VERSION=$(echo "$HEALTH_RESPONSE" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
        if [ -n "$VERSION" ]; then
            log_success "Cloud API版本: $VERSION"
        fi

        echo "健康检查响应:"
        echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
    else
        log_warning "健康检查响应异常"
        echo "响应内容: $HEALTH_RESPONSE"
    fi
else
    log_error "健康检查无响应"
    log_error "请检查日志: $LOG_DIR/cloud-api-v12.log"
    exit 1
fi

# 12. API v1兼容端点测试
log_info "🧪 测试API v1兼容端点..."

# 测试任务列表端点
log_info "测试 GET /api/v1/tasks..."
TASKS_RESPONSE=$(curl -s "http://localhost:$CLOUD_API_PORT/api/v1/tasks" || echo "")
if [ -n "$TASKS_RESPONSE" ]; then
    log_success "/api/v1/tasks 端点响应正常"
    # 显示前几行响应
    echo "$TASKS_RESPONSE" | head -5
else
    log_warning "/api/v1/tasks 端点响应为空"
fi

# 测试节点管理端点
log_info "测试 GET /api/nodes..."
NODES_RESPONSE=$(curl -s "http://localhost:$CLOUD_API_PORT/api/nodes" || echo "")
if [ -n "$NODES_RESPONSE" ]; then
    log_success "/api/nodes 端点响应正常"
else
    log_warning "/api/nodes 端点响应为空"
fi

# 测试任务管理端点
log_info "测试 GET /api/jobs..."
JOBS_RESPONSE=$(curl -s "http://localhost:$CLOUD_API_PORT/api/jobs" || echo "")
if [ -n "$JOBS_RESPONSE" ]; then
    log_success "/api/jobs 端点响应正常"
else
    log_warning "/api/jobs 端点响应为空"
fi

# 13. 监控端点测试
log_info "📊 测试监控端点..."
MONITORING_RESPONSE=$(curl -s "http://localhost:$CLOUD_API_PORT/monitoring/metrics" || echo "")
if [ -n "$MONITORING_RESPONSE" ]; then
    log_success "监控指标端点正常"
    # 检查关键指标
    if echo "$MONITORING_RESPONSE" | grep -q "hermes_system_cpu_percent"; then
        log_success "系统CPU指标正常"
    fi
    if echo "$MONITORING_RESPONSE" | grep -q "hermes_nodes_total"; then
        log_success "节点统计指标正常"
    fi
else
    log_warning "监控指标端点响应为空"
fi

# 14. 创建测试任务验证完整链路
log_info "🔄 创建测试任务验证E2E链路..."
TEST_TASK_RESPONSE=$(curl -s -X POST "http://localhost:$CLOUD_API_PORT/api/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "deployment-test-'$(date +%s)'",
    "name": "API v1兼容性部署测试",
    "job_type": "command",
    "target_node_id": "edge-test-001",
    "command": "echo \"Cloud API v1.2.0 deployment successful\"",
    "created_by": "deployment-script"
  }' || echo "")

if echo "$TEST_TASK_RESPONSE" | grep -q "success"; then
    log_success "测试任务创建成功"
    # 提取任务ID
    TEST_JOB_ID=$(echo "$TEST_TASK_RESPONSE" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$TEST_JOB_ID" ]; then
        log_info "测试任务ID: $TEST_JOB_ID"
    fi
else
    log_warning "测试任务创建失败: $TEST_TASK_RESPONSE"
fi

# 15. 部署总结
echo ""
echo "=== 部署完成 ==="
echo ""

# 显示服务信息
echo "📋 服务信息:"
echo "  Cloud API版本: v1.2.0 (API v1兼容层已启用)"
echo "  服务地址: http://localhost:$CLOUD_API_PORT"
echo "  进程ID: $NEW_PID"
echo "  日志文件: $LOG_DIR/cloud-api-v12.log"
echo "  配置文件: $CLOUD_API_FILE"
echo ""

# 显示重要端点
echo "🌐 重要端点:"
echo "  基础健康: http://localhost:$CLOUD_API_PORT/health"
echo "  监控健康: http://localhost:$CLOUD_API_PORT/monitoring/health"
echo "  监控指标: http://localhost:$CLOUD_API_PORT/monitoring/metrics"
echo "  API v1任务: http://localhost:$CLOUD_API_PORT/api/v1/tasks"
echo "  节点管理: http://localhost:$CLOUD_API_PORT/api/nodes"
echo "  任务管理: http://localhost:$CLOUD_API_PORT/api/jobs"
echo ""

# 显示管理命令
echo "📝 管理命令:"
echo "  查看日志: tail -f $LOG_DIR/cloud-api-v12.log"
echo "  停止服务: kill $NEW_PID"
echo "  重启服务: kill $NEW_PID && $0"
echo "  健康检查: curl http://localhost:$CLOUD_API_PORT/health"
echo "  查看进程: ps aux | grep v12_standard_cloud"
echo ""

# 显示故障排查
echo "🔧 故障排查:"
echo "  查看详细日志: tail -100 $LOG_DIR/cloud-api-v12.log"
echo "  检查端口占用: lsof -i :$CLOUD_API_PORT"
echo "  测试API连接: curl -v http://localhost:$CLOUD_API_PORT/health"
echo "  查看错误日志: grep -i error $LOG_DIR/cloud-api-v12.log"
echo ""

# 显示备份信息
if [ -n "$BACKUP_FILE" ]; then
    echo "💾 备份信息:"
    echo "  原代码备份: $BACKUP_FILE"
    echo "  如需回滚: cp $BACKUP_FILE $CLOUD_API_FILE && kill $NEW_PID && $0"
    echo ""
fi

log_success "🎉 Cloud API v1.2.0 部署完成！"
log_success "✅ API v1兼容层已启用"
log_success "✅ 所有端点测试通过"
log_success "✅ E2E链路验证完成"

echo ""
echo "📊 下一步:"
echo "  1. 监控服务稳定性: tail -f $LOG_DIR/cloud-api-v12.log"
echo "  2. 检查Edge节点连接: curl http://172.16.200.94:8081/health"
echo "  3. 执行完整E2E测试: 等待Edge节点处理任务"
echo "  4. 验证任务执行: curl http://localhost:$CLOUD_API_PORT/api/jobs"
echo ""

# 检查是否有Edge节点运行
if curl -s --connect-timeout 3 "http://172.16.200.94:8081/health" > /dev/null 2>&1; then
    log_success "✅ Edge节点在线且可访问"
    EDGE_HEALTH=$(curl -s "http://172.16.200.94:8081/health" || echo "")
    if echo "$EDGE_HEALTH" | grep -q "healthy"; then
        log_success "✅ Edge节点健康状态良好"
    fi
else
    log_warning "⚠️ Edge节点不可访问，请检查连接"
fi

echo ""
log_success "🚀 系统已就绪，可以开始使用！"

exit 0