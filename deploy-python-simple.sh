#!/bin/bash
# HermesNexus v1.2.0 简化部署脚本
# 直接使用Python部署，避免复杂的依赖

set -e

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 配置
DEPLOY_DIR="/home/scsun/hermesnexus-v12"
DATA_DIR="/home/scsun/hermesnexus-data"
LOGS_DIR="/home/scsun/hermesnexus-logs"
VENV_DIR="$DEPLOY_DIR/venv"
PID_FILE="$DEPLOY_DIR/hermesnexus-v12.pid"
LOG_FILE="$LOGS_DIR/hermesnexus-v12.log"

# 检查Python版本
check_python() {
    log_info "检查Python环境..."
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_success "Python版本: $PYTHON_VERSION"

    # 简单检查是否是Python 3.10+
    MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
        log_error "Python版本过低，需要3.10+"
        exit 1
    fi
}

# 创建虚拟环境
setup_venv() {
    log_info "设置Python虚拟环境..."
    if [ -d "$VENV_DIR" ]; then
        log_warning "虚拟环境已存在，重新创建..."
        rm -rf "$VENV_DIR"
    fi
    python3 -m venv "$VENV_DIR"
    log_success "虚拟环境创建完成"
}

# 安装依赖
install_dependencies() {
    log_info "安装Python依赖包..."
    source "$VENV_DIR/bin/activate"

    # 使用虚拟环境中的pip，避免系统包限制
    pip install --upgrade pip -q

    # 检查requirements.txt是否存在
    if [ -f "$DEPLOY_DIR/requirements.txt" ]; then
        pip install -r "$DEPLOY_DIR/requirements.txt" -q
        log_success "依赖包安装完成"
    else
        log_warning "requirements.txt不存在，安装核心依赖..."
        pip install fastapi uvicorn sqlalchemy sqlite3 -q
    fi
}

# 创建数据目录
setup_directories() {
    log_info "创建数据目录..."
    mkdir -p "$DATA_DIR"
    mkdir -p "$LOGS_DIR"
    mkdir -p "$DEPLOY_DIR/ssh_keys"
    log_success "目录创建完成"
}

# 启动服务
start_service() {
    log_info "启动HermesNexus v1.2.0服务..."

    # 检查是否已有服务在运行
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            log_warning "服务已在运行 (PID: $OLD_PID)"
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi

    # 激活虚拟环境并启动服务
    source "$VENV_DIR/bin/activate"
    export PYTHONPATH="$DEPLOY_DIR:$PYTHONPATH"
    export HERMES_ENV=production
    export DATABASE_PATH="$DATA_DIR/hermesnexus-v12.db"
    export CLOUD_HOST=0.0.0.0
    export CLOUD_PORT=8082
    export LOG_LEVEL=info

    # 检查Cloud API主文件
    if [ -f "$DEPLOY_DIR/cloud/api/main.py" ]; then
        log_info "启动Cloud API服务..."
        cd "$DEPLOY_DIR"
        nohup python3 -c "
import sys
sys.path.insert(0, '$DEPLOY_DIR')
from cloud.api.main import app
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=8082, log_level='info')
" > "$LOG_FILE" 2>&1 &
        NEW_PID=$!
    else
        log_error "Cloud API主文件不存在: $DEPLOY_DIR/cloud/api/main.py"
        exit 1
    fi

    echo $NEW_PID > "$PID_FILE"
    sleep 3

    # 检查服务状态
    if ps -p "$NEW_PID" > /dev/null 2>&1; then
        log_success "HermesNexus v1.2.0启动成功 (PID: $NEW_PID)"
        log_info "访问地址: http://172.16.100.101:8082"
        log_info "健康检查: http://172.16.100.101:8082/monitoring/health"
    else
        log_error "服务启动失败，请检查日志: $LOG_FILE"
        cat "$LOG_FILE" | tail -20
        exit 1
    fi
}

# 停止服务
stop_service() {
    log_info "停止HermesNexus v1.2.0服务..."

    if [ ! -f "$PID_FILE" ]; then
        log_warning "服务未运行"
        return 0
    fi

    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        kill "$PID" 2>/dev/null || true
        sleep 2
        if ps -p "$PID" > /dev/null 2>&1; then
            kill -9 "$PID" 2>/dev/null || true
        fi
        log_success "服务已停止"
    fi
    rm -f "$PID_FILE"
}

# 重启服务
restart_service() {
    stop_service
    sleep 2
    start_service
}

# 检查服务状态
status_service() {
    log_info "检查服务状态..."

    if [ ! -f "$PID_FILE" ]; then
        log_warning "服务未运行 (无PID文件)"
        return 1
    fi

    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        log_success "服务正在运行 (PID: $PID)"
        log_info "端口监听检查:"
        netstat -tuln | grep ":8082 " || log_warning "端口8082未监听"
        return 0
    else
        log_warning "服务进程不存在"
        return 1
    fi
}

# 查看日志
view_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        log_warning "日志文件不存在: $LOG_FILE"
    fi
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    if command -v curl &> /dev/null; then
        response=$(curl -s http://localhost:8082/monitoring/health || echo "failed")
        if [ "$response" != "failed" ]; then
            log_success "健康检查成功"
            echo "$response"
            return 0
        else
            log_error "健康检查失败"
            return 1
        fi
    else
        log_warning "curl命令未找到，跳过HTTP检查"
    fi
}

# 主函数
main() {
    case "${1:-start}" in
        setup)
            log_info "开始部署HermesNexus v1.2.0..."
            check_python
            setup_directories
            setup_venv
            install_dependencies
            log_success "部署完成，使用 '$0 start' 启动服务"
            ;;
        start)
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service
            ;;
        status)
            status_service
            ;;
        logs)
            view_logs
            ;;
        health)
            health_check
            ;;
        *)
            echo "用法: $0 {setup|start|stop|restart|status|logs|health}"
            exit 1
            ;;
    esac
}

main "$@"