#!/bin/bash
# HermesNexus v1.2.0 Python直接部署脚本
# 避免Docker镜像拉取问题，直接使用Python部署

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
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
DEPLOY_DIR="/home/scsun/hermesnexus-v12"
DATA_DIR="/home/scsun/hermesnexus-data"
LOGS_DIR="/home/scsun/hermesnexus-logs"
CONFIG_FILE="$DEPLOY_DIR/.env.production"
VENV_DIR="$DEPLOY_DIR/venv"
SERVICE_NAME="hermesnexus-v12"
PID_FILE="$DEPLOY_DIR/hermesnexus-v12.pid"
LOG_FILE="$LOGS_DIR/hermesnexus-v12.log"

# 检查Python版本
check_python() {
    log_info "检查Python环境..."
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 未安装"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    log_success "Python版本: $(python3 --version)"

    if [ "$(echo "$PYTHON_VERSION < 3.10" | bc)" -eq 1 ]; then
        log_error "Python版本过低，需要3.10+"
        exit 1
    fi
}

# 创建虚拟环境
setup_venv() {
    log_info "设置Python虚拟环境..."
    if [ -d "$VENV_DIR" ]; then
        log_warning "虚拟环境已存在，跳过创建"
    else
        python3 -m venv "$VENV_DIR"
        log_success "虚拟环境创建完成"
    fi
}

# 安装依赖
install_dependencies() {
    log_info "安装Python依赖包..."
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip -q
    pip install -r "$DEPLOY_DIR/requirements.txt" -q
    log_success "依赖包安装完成"
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
            log_warning "清理旧的PID文件"
            rm -f "$PID_FILE"
        fi
    fi

    # 激活虚拟环境并启动服务
    source "$VENV_DIR/bin/activate"
    export PYTHONPATH="$DEPLOY_DIR"
    export HERMES_ENV=production
    export DATABASE_PATH="$DATA_DIR/hermesnexus-v12.db"
    export CLOUD_HOST=0.0.0.0
    export CLOUD_PORT=8082
    export LOG_LEVEL=info

    # 启动Cloud API
    nohup python3 -m cloud.api.main > "$LOG_FILE" 2>&1 &
    NEW_PID=$!
    echo $NEW_PID > "$PID_FILE"

    # 等待服务启动
    sleep 5

    # 检查服务状态
    if ps -p "$NEW_PID" > /dev/null 2>&1; then
        log_success "HermesNexus v1.2.0启动成功 (PID: $NEW_PID)"
        log_info "访问地址: http://172.16.100.101:8082"
        log_info "健康检查: http://172.16.100.101:8082/monitoring/health"
    else
        log_error "服务启动失败，请检查日志: $LOG_FILE"
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
        kill "$PID"
        sleep 2
        if ps -p "$PID" > /dev/null 2>&1; then
            log_warning "强制停止服务..."
            kill -9 "$PID"
        fi
        log_success "服务已停止"
    else
        log_warning "服务进程不存在"
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

        # 检查端口监听
        if netstat -tuln | grep -q ":8082 "; then
            log_success "端口8082正在监听"
        else
            log_warning "端口8082未监听"
        fi

        # 检查健康状态
        if command -v curl &> /dev/null; then
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8082/monitoring/health || echo "000")
            if [ "$HTTP_CODE" = "200" ]; then
                log_success "健康检查通过 (HTTP $HTTP_CODE)"
            else
                log_warning "健康检查失败 (HTTP $HTTP_CODE)"
            fi
        fi

        return 0
    else
        log_warning "服务未运行 (PID $PID 不存在)"
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

    if ! command -v curl &> /dev/null; then
        log_error "curl命令未找到"
        return 1
    fi

    response=$(curl -s http://localhost:8082/monitoring/health || echo "failed")
    if [ "$response" != "failed" ]; then
        log_success "健康检查成功"
        echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
        return 0
    else
        log_error "健康检查失败"
        return 1
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
            echo ""
            echo "命令说明:"
            echo "  setup   - 初始化部署环境"
            echo "  start   - 启动服务"
            echo "  stop    - 停止服务"
            echo "  restart - 重启服务"
            echo "  status  - 查看服务状态"
            echo "  logs    - 查看日志"
            echo "  health  - 健康检查"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"