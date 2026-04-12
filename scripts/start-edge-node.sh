#!/usr/bin/env bash
#
# HermesNexus Edge Node Startup Script
# 启动边缘节点服务
#

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Python 版本
check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    log_info "Python version: $PYTHON_VERSION"
}

# 验证必需参数
validate_params() {
    local errors=0

    if [ -z "$NODE_ID" ]; then
        log_error "NODE_ID is required (export NODE_ID=node-001)"
        errors=$((errors + 1))
    fi

    if [ -z "$NODE_NAME" ]; then
        log_error "NODE_NAME is required (export NODE_NAME='Production Edge Node')"
        errors=$((errors + 1))
    fi

    if [ $errors -gt 0 ]; then
        exit 1
    fi
}

# 加载环境配置
load_env() {
    local env=${HERMES_ENV:-development}
    local env_file=".env.$env"

    if [ -f "$env_file" ]; then
        log_info "Loading environment from: $env_file"
        export $(cat "$env_file" | grep -v '^#' | grep -v '^$' | xargs)
    fi

    # 设置默认值
    export CLOUD_API_URL="${CLOUD_API_URL:-http://localhost:8080}"
    export TASK_POLL_INTERVAL="${TASK_POLL_INTERVAL:-10}"
    export TASK_EXEC_TIMEOUT="${TASK_EXEC_TIMEOUT:-300}"
    export SSH_CONNECT_TIMEOUT="${SSH_CONNECT_TIMEOUT:-30}"
    export EDGE_LOG_DIR="${EDGE_LOG_DIR:-./logs/edge}"
    export EDGE_DATA_DIR="${EDGE_DATA_DIR:-./data/edge}"
    export EDGE_CACHE_DIR="${EDGE_CACHE_DIR:-./data/edge/cache}"
    export EDGE_SCRIPTS_DIR="${EDGE_SCRIPTS_DIR:-./data/edge/scripts}"
}

# 创建必要目录
create_directories() {
    log_info "Creating directories..."

    local dirs=(
        "${EDGE_LOG_DIR}"
        "${EDGE_DATA_DIR}"
        "${EDGE_CACHE_DIR}"
        "${EDGE_SCRIPTS_DIR}"
    )

    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "Created directory: $dir"
        fi
    done
}

# 检查 Cloud API 连接
check_cloud_api() {
    log_info "Checking Cloud API connectivity..."

    local max_attempts=5
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "${CLOUD_API_URL}/health" > /dev/null 2>&1; then
            log_info "Cloud API is reachable: ${CLOUD_API_URL}"
            return 0
        fi

        log_warn "Attempt $attempt/$max_attempts: Cloud API not reachable, retrying in 5s..."
        sleep 5
        attempt=$((attempt + 1))
    done

    log_error "Cannot reach Cloud API at ${CLOUD_API_URL}"
    log_error "Please ensure Cloud API is running before starting Edge Node"
    exit 1
}

# 启动边缘节点
start_edge_node() {
    log_info "Starting HermesNexus Edge Node..."
    log_info "Node ID: $NODE_ID"
    log_info "Node Name: $NODE_NAME"
    log_info "Cloud API: $CLOUD_API_URL"
    log_info "Poll Interval: ${TASK_POLL_INTERVAL}s"
    log_info "Log Directory: ${EDGE_LOG_DIR}"

    # 检查是否已有节点在运行
    if pgrep -f "edge/runtime/main.py" > /dev/null; then
        log_error "Edge Node is already running"
        log_error "Stop existing node first: ./scripts/stop-edge-node.sh"
        exit 1
    fi

    # 启动节点
    python3 final-edge-node.py
}

# 显示状态
show_status() {
    log_info "Edge Node Configuration:"
    echo "  NODE_ID              : $NODE_ID"
    echo "  NODE_NAME            : $NODE_NAME"
    echo "  CLOUD_API_URL        : $CLOUD_API_URL"
    echo "  TASK_POLL_INTERVAL   : ${TASK_POLL_INTERVAL}s"
    echo "  TASK_EXEC_TIMEOUT    : ${TASK_EXEC_TIMEOUT}s"
    echo "  SSH_CONNECT_TIMEOUT  : ${SSH_CONNECT_TIMEOUT}s"
    echo "  EDGE_LOG_DIR         : ${EDGE_LOG_DIR}"
    echo "  EDGE_DATA_DIR        : ${EDGE_DATA_DIR}"
    echo ""
}

# 主流程
main() {
    echo "=========================================="
    echo "  HermesNexus Edge Node"
    echo "  Version: 2.0.0"
    echo "=========================================="
    echo ""

    check_python
    validate_params
    load_env
    create_directories
    show_status
    check_cloud_api
    start_edge_node
}

# 捕获退出信号
trap 'log_info "Shutting down Edge Node..."; exit 0' SIGTERM SIGINT

# 运行主流程
main "$@"
