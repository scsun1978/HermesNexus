#!/bin/bash
# HermesNexus Cloud API Update Script
# 用于更新生产环境的Cloud API代码

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

# 配置
CLOUD_API_PORT=8082
PROJECT_DIR="/home/scsun/hermesnexus-code"
LOG_DIR="/home/scsun/hermesnexus-logs"
DATA_DIR="/home/scsun/hermesnexus-data"
BACKUP_DIR="/home/scsun/hermesnexus-backups"
PID_FILE="/tmp/cloud-api-v12.pid"

echo "=== HermesNexus Cloud API v1.2.0 更新脚本 ==="
echo ""

# 1. 检查是否以正确用户运行
if [ "$(whoami)" != "scsun" ]; then
    log_error "请以 scsun 用户运行此脚本"
    exit 1
fi

# 2. 创建备份目录
log_info "📁 创建备份目录..."
mkdir -p "$BACKUP_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"
log_success "目录创建完成"

# 3. 备份当前运行的Cloud API
log_info "💾 备份当前Cloud API..."
if [ -f "$PROJECT_DIR/cloud/api/v12_standard_cloud.py" ]; then
    cp "$PROJECT_DIR/cloud/api/v12_standard_cloud.py" "$BACKUP_DIR/v12_standard_cloud.py.backup.$(date +%Y%m%d_%H%M%S)"
    log_success "备份完成"
else
    log_warning "未找到现有Cloud API文件，跳过备份"
fi

# 4. 停止当前运行的Cloud API服务
log_info "🛑 停止当前Cloud API服务..."
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        kill "$OLD_PID"
        sleep 2
        # 如果进程还在运行，强制杀死
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            kill -9 "$OLD_PID"
            sleep 1
        fi
        log_success "Cloud API服务已停止 (PID: $OLD_PID)"
    else
        log_warning "PID文件存在但进程不在运行"
    fi
else
    # 尝试通过进程名查找
    CLOUD_PID=$(pgrep -f "python.*v12_standard_cloud.py" || true)
    if [ -n "$CLOUD_PID" ]; then
        kill "$CLOUD_PID"
        sleep 2
        log_success "Cloud API服务已停止 (PID: $CLOUD_PID)"
    else
        log_warning "未找到运行中的Cloud API服务"
    fi
fi

# 5. 检查端口是否被释放
log_info "🔍 检查端口 $CLOUD_API_PORT..."
sleep 2
if lsof -Pi :$CLOUD_API_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_warning "端口 $CLOUD_API_PORT 仍被占用，尝试清理..."
    lsof -ti :$CLOUD_API_PORT | xargs kill -9 2>/dev/null || true
    sleep 1
fi
log_success "端口检查完成"

# 6. 更新代码 (假设新代码已经在当前目录)
log_info "📥 更新Cloud API代码..."
# 注意：实际部署时，新代码应该已经通过scp等方式上传到了服务器
# 这里我们假设新代码已经在项目目录中
if [ -f "v12_standard_cloud.py" ]; then
    cp v12_standard_cloud.py "$PROJECT_DIR/cloud/api/v12_standard_cloud.py"
    log_success "代码更新完成"
else
    log_warning "未找到新代码文件，使用现有代码"
fi

# 7. 检查Python依赖
log_info "🐍 检查Python环境..."
PYTHON_VERSION=$(python3 --version)
log_success "Python版本: $PYTHON_VERSION"

# 检查必要的模块
python3 -c "import http.server, sqlite3, json, uuid" 2>/dev/null || {
    log_error "Python标准库检查失败"
    exit 1
}
log_success "Python标准库检查通过"

# 8. 启动新的Cloud API服务
log_info "🚀 启动Cloud API v1.2.0..."
cd "$PROJECT_DIR"

# 创建启动命令
START_CMD="nohup python3 cloud/api/v12_standard_cloud.py > $LOG_DIR/cloud-api-v12.log 2>&1 & echo \$! > $PID_FILE"

# 执行启动命令
eval $START_CMD

# 等待服务启动
log_info "⏳ 等待服务启动..."
sleep 3

# 检查服务是否启动成功
if [ -f "$PID_FILE" ]; then
    NEW_PID=$(cat "$PID_FILE")
    if ps -p "$NEW_PID" > /dev/null 2>&1; then
        log_success "Cloud API服务启动成功 (PID: $NEW_PID)"
    else
        log_error "Cloud API服务启动失败，请检查日志"
        cat "$LOG_DIR/cloud-api-v12.log" | tail -20
        exit 1
    fi
else
    log_error "PID文件未创建，服务启动失败"
    exit 1
fi

# 9. 健康检查
log_info "🏥 执行健康检查..."
sleep 2

# 检查端口是否监听
if lsof -Pi :$CLOUD_API_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_success "端口 $CLOUD_API_PORT 正在监听"
else
    log_error "端口 $CLOUD_API_PORT 未监听"
    exit 1
fi

# 检查健康端点
HEALTH_RESPONSE=$(curl -s "http://localhost:$CLOUD_API_PORT/health" || echo "")
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    log_success "健康检查端点响应正常"
    VERSION=$(echo "$HEALTH_RESPONSE" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    log_success "Cloud API版本: $VERSION"
else
    log_warning "健康检查端点响应异常: $HEALTH_RESPONSE"
fi

# 10. 测试新的API v1兼容端点
log_info "🧪 测试API v1兼容端点..."

# 测试 /api/v1/tasks
TASKS_RESPONSE=$(curl -s "http://localhost:$CLOUD_API_PORT/api/v1/tasks" || echo "")
if [ -n "$TASKS_RESPONSE" ]; then
    log_success "/api/v1/tasks 端点响应正常"
else
    log_warning "/api/v1/tasks 端点响应为空"
fi

# 测试节点管理端点
NODES_RESPONSE=$(curl -s "http://localhost:$CLOUD_API_PORT/api/nodes" || echo "")
if [ -n "$NODES_RESPONSE" ]; then
    log_success "/api/nodes 端点响应正常"
else
    log_warning "/api/nodes 端点响应为空"
fi

# 11. 显示部署信息
echo ""
echo "=== 部署完成 ==="
echo ""
echo "📋 服务信息:"
echo "  Cloud API版本: v1.2.0 (API v1兼容层已启用)"
echo "  服务地址: http://localhost:$CLOUD_API_PORT"
echo "  进程ID: $NEW_PID"
echo "  日志文件: $LOG_DIR/cloud-api-v12.log"
echo ""
echo "🌐 重要端点:"
echo "  健康检查: http://localhost:$CLOUD_API_PORT/health"
echo "  监控指标: http://localhost:$CLOUD_API_PORT/monitoring/metrics"
echo "  API v1任务: http://localhost:$CLOUD_API_PORT/api/v1/tasks"
echo "  节点管理: http://localhost:$CLOUD_API_PORT/api/nodes"
echo "  任务管理: http://localhost:$CLOUD_API_PORT/api/jobs"
echo ""
echo "📝 管理命令:"
echo "  查看日志: tail -f $LOG_DIR/cloud-api-v12.log"
echo "  停止服务: kill $NEW_PID"
echo "  重启服务: $0"
echo "  健康检查: curl http://localhost:$CLOUD_API_PORT/health"
echo ""

log_success "🎉 Cloud API v1.2.0 更新完成！"
