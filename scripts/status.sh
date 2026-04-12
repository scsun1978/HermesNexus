#!/usr/bin/env bash
#
# HermesNexus Services Status Script
# 检查 HermesNexus 服务状态
#

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_detail() {
    echo -e "${BLUE}[DETAIL]${NC} $1"
}

# 检查 Cloud API 状态
check_cloud_api() {
    echo "=========================================="
    echo "  Cloud API Status"
    echo "=========================================="

    local pid=$(pgrep -f "uvicorn stable_cloud_api:app" || true)

    if [ -z "$pid" ]; then
        log_error "Cloud API: Not running"
        return 1
    fi

    log_info "Cloud API: Running"
    log_detail "PID: $pid"

    # 检查端口
    local port=${CLOUD_API_PORT:-8080}
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_detail "Port: $port (listening)"
    else
        log_warn "Port: $port (not listening)"
    fi

    # 健康检查
    local health_url="http://localhost:${port}/health"
    local health_response=$(curl -s -w "\n%{http_code}" "$health_url" 2>/dev/null || echo "000")

    local http_code=$(echo "$health_response" | tail -1)
    local body=$(echo "$health_response" | head -n -1)

    if [ "$http_code" = "200" ]; then
        log_info "Health Check: Passed"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    else
        log_error "Health Check: Failed (HTTP $http_code)"
    fi

    echo ""
}

# 检查 Edge Node 状态
check_edge_node() {
    echo "=========================================="
    echo "  Edge Node Status"
    echo "=========================================="

    local pid=$(pgrep -f "final-edge-node.py" || true)

    if [ -z "$pid" ]; then
        log_error "Edge Node: Not running"
        return 1
    fi

    log_info "Edge Node: Running"
    log_detail "PID: $pid"

    # 显示环境变量
    if [ -n "$NODE_ID" ]; then
        log_detail "NODE_ID: $NODE_ID"
    fi

    if [ -n "$NODE_NAME" ]; then
        log_detail "NODE_NAME: $NODE_NAME"
    fi

    if [ -n "$CLOUD_API_URL" ]; then
        log_detail "CLOUD_API_URL: $CLOUD_API_URL"
    fi

    echo ""
}

# 检查资源使用情况
check_resources() {
    echo "=========================================="
    echo "  System Resources"
    echo "=========================================="

    # CPU 使用率
    if command -v top &> /dev/null; then
        local cpu_usage=$(top -l 1 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')
        log_detail "CPU Usage: ${cpu_usage}%"
    fi

    # 内存使用率
    if command -vm &> /dev/null; then
        local mem_info=$(vm_stat | perl -ne '/page size of (\d+)/ and $size=$1; /Pages\s+(.+):\s+(\d+)/ and printf("%-16s % 16.2f Mi\n", "$1:", $2*$size/1048576);')
        echo "$mem_info"
    fi

    # 磁盘使用率
    if command -v df &> /dev/null; then
        log_detail "Disk Usage:"
        df -h | grep -E '(Filesystem|/$|/data|/var)'
    fi

    echo ""
}

# 检查日志文件
check_logs() {
    echo "=========================================="
    echo "  Recent Logs"
    echo "=========================================="

    local log_dir="${LOG_DIR:-./logs}"

    if [ -d "$log_dir" ]; then
        log_detail "Log Directory: $log_dir"
        echo ""

        # 显示最近的日志
        if [ -f "$log_dir/cloud-api.log" ]; then
            echo "--- Cloud API (last 10 lines) ---"
            tail -10 "$log_dir/cloud-api.log"
            echo ""
        fi

        if [ -f "$log_dir/edge-node.log" ]; then
            echo "--- Edge Node (last 10 lines) ---"
            tail -10 "$log_dir/edge-node.log"
            echo ""
        fi
    else
        log_warn "Log directory not found: $log_dir"
    fi

    echo ""
}

# 检查网络连接
check_network() {
    echo "=========================================="
    echo "  Network Connections"
    echo "=========================================="

    local port=${CLOUD_API_PORT:-8080}

    # 检查端口监听
    if lsof -i ":$port" >/dev/null 2>&1; then
        log_info "Port $port: Listening"
        lsof -i ":$port" | head -10
    else
        log_warn "Port $port: Not listening"
    fi

    echo ""
}

# 检查配置文件
check_config() {
    echo "=========================================="
    echo "  Configuration"
    echo "=========================================="

    local env=${HERMES_ENV:-development}
    local env_file=".env.$env"

    if [ -f "$env_file" ]; then
        log_info "Environment: $env"
        log_detail "Config File: $env_file"

        # 显示关键配置
        echo ""
        echo "Key Configuration Values:"
        grep -E '^(CLOUD_API|DATABASE|LOG_LEVEL|DATA_DIR)' "$env_file" | sed 's/^/  /' || true
    else
        log_warn "Environment file not found: $env_file"
    fi

    echo ""
}

# 显示摘要
show_summary() {
    echo "=========================================="
    echo "  Summary"
    echo "=========================================="

    local cloud_api_running=false
    local edge_node_running=false

    if pgrep -f "uvicorn stable_cloud_api:app" > /dev/null; then
        cloud_api_running=true
    fi

    if pgrep -f "final-edge-node.py" > /dev/null; then
        edge_node_running=true
    fi

    if [ "$cloud_api_running" = true ] && [ "$edge_node_running" = true ]; then
        log_info "All services: Running"
    elif [ "$cloud_api_running" = true ]; then
        log_warn "Cloud API: Running, Edge Node: Stopped"
    elif [ "$edge_node_running" = true ]; then
        log_warn "Edge Node: Running, Cloud API: Stopped"
    else
        log_error "All services: Stopped"
    fi

    echo ""
}

# 主流程
main() {
    echo ""
    echo "=========================================="
    echo "  HermesNexus Service Status"
    echo "  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=========================================="
    echo ""

    check_config
    check_cloud_api
    check_edge_node
    check_network
    check_resources
    show_summary

    echo "=========================================="
    echo "For detailed logs, check: ${LOG_DIR:-./logs}/"
    echo "=========================================="
}

# 运行主流程
main "$@"
