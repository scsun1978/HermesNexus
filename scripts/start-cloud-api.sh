#!/usr/bin/env bash
#
# HermesNexus Cloud API Startup Script
# 启动云端 API 服务
#

set -e

# 默认值
ENV=${HERMES_ENV:-development}
CONFIG_DIR=${CONFIG_DIR:-./config}
HOST=${CLOUD_API_HOST:-127.0.0.1}
PORT=${CLOUD_API_PORT:-8080}
WORKERS=${CLOUD_API_WORKERS:-1}

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

# 加载环境配置
load_env() {
    local env_file=".env.$ENV"

    if [ -f "$env_file" ]; then
        log_info "Loading environment from: $env_file"
        export $(cat "$env_file" | grep -v '^#' | grep -v '^$' | xargs)
    else
        log_warn "Environment file not found: $env_file"
        log_warn "Using default values"
    fi

    # 导出关键变量
    export HERMES_ENV="$ENV"
    export CLOUD_API_HOST="${HOST}"
    export CLOUD_API_PORT="${PORT}"
    export CLOUD_API_WORKERS="${WORKERS}"
}

# 创建必要目录
create_directories() {
    log_info "Creating directories..."

    local dirs=(
        "${LOG_DIR}"
        "${DATA_DIR}"
        "${ASSETS_DIR}"
        "${TASKS_DIR}"
        "${SCRIPTS_DIR}"
    )

    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "Created directory: $dir"
        fi
    done
}

# 检查配置
check_config() {
    log_info "Checking configuration..."

    # 检查必需的环境变量
    local required_vars=()
    local missing_vars=()

    if [ "$ENV" = "production" ]; then
        required_vars=("SECRET_KEY" "DATABASE_URL")
    fi

    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -ne 0 ]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        exit 1
    fi

    log_info "Configuration check passed"
}

# 启动服务
start_service() {
    log_info "Starting HermesNexus Cloud API..."
    log_info "Environment: $ENV"
    log_info "Host: $HOST"
    log_info "Port: $PORT"
    log_info "Workers: $WORKERS"
    log_info "Log Directory: ${LOG_DIR}"

    # 检查端口是否被占用
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_error "Port $PORT is already in use"
        exit 1
    fi

    # 启动服务
    if [ "$ENV" = "development" ]; then
        log_info "Starting in development mode (with auto-reload)"

        python3 -m uvicorn stable_cloud_api:app \
            --host "$HOST" \
            --port "$PORT" \
            --reload \
            --log-level "${LOG_LEVEL:-DEBUG}" \
            --log-config "${CONFIG_DIR}/logging.${ENV}.yaml" 2>/dev/null || \
        python3 -m uvicorn stable_cloud_api:app \
            --host "$HOST" \
            --port "$PORT" \
            --reload \
            --log-level "${LOG_LEVEL:-DEBUG}"
    else
        log_info "Starting in production mode (multi-workers)"

        python3 -m uvicorn stable_cloud_api:app \
            --host "$HOST" \
            --port "$PORT" \
            --workers "$WORKERS" \
            --log-level "${LOG_LEVEL:-INFO}" \
            --access-log \
            --log-config "${CONFIG_DIR}/logging.${ENV}.yaml" 2>/dev/null || \
        python3 -m uvicorn stable_cloud_api:app \
            --host "$HOST" \
            --port "$PORT" \
            --workers "$WORKERS" \
            --log-level "${LOG_LEVEL:-INFO}" \
            --access-log
    fi
}

# 主流程
main() {
    echo "=========================================="
    echo "  HermesNexus Cloud API"
    echo "  Version: 2.0.0"
    echo "=========================================="
    echo ""

    check_python
    load_env
    create_directories
    check_config
    start_service
}

# 捕获退出信号
trap 'log_info "Shutting down..."; exit 0' SIGTERM SIGINT

# 运行主流程
main "$@"
