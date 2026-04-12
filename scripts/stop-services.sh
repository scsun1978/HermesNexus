#!/usr/bin/env bash
#
# HermesNexus Services Stop Script
# 停止 HermesNexus 服务
#

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

# 停止 Cloud API
stop_cloud_api() {
    log_info "Stopping Cloud API..."

    local pids=$(pgrep -f "uvicorn stable_cloud_api:app" || true)

    if [ -z "$pids" ]; then
        log_warn "Cloud API is not running"
        return 0
    fi

    echo "$pids" | xargs kill 2>/dev/null || true

    # 等待进程结束
    local count=0
    while pgrep -f "uvicorn stable_cloud_api:app" > /dev/null; do
        if [ $count -ge 10 ]; then
            log_error "Cloud API did not stop gracefully, forcing..."
            pkill -9 -f "uvicorn stable_cloud_api:app" || true
            break
        fi
        sleep 1
        count=$((count + 1))
    done

    log_info "Cloud API stopped"
}

# 停止 Edge Node
stop_edge_node() {
    log_info "Stopping Edge Node..."

    local pids=$(pgrep -f "final-edge-node.py" || true)

    if [ -z "$pids" ]; then
        log_warn "Edge Node is not running"
        return 0
    fi

    echo "$pids" | xargs kill 2>/dev/null || true

    # 等待进程结束
    local count=0
    while pgrep -f "final-edge-node.py" > /dev/null; do
        if [ $count -ge 10 ]; then
            log_error "Edge Node did not stop gracefully, forcing..."
            pkill -9 -f "final-edge-node.py" || true
            break
        fi
        sleep 1
        count=$((count + 1))
    done

    log_info "Edge Node stopped"
}

# 主流程
main() {
    echo "=========================================="
    echo "  Stopping HermesNexus Services"
    echo "=========================================="
    echo ""

    stop_cloud_api
    stop_edge_node

    echo ""
    log_info "All HermesNexus services stopped"
}

# 运行主流程
main "$@"
