#!/bin/bash
# HermesNexus MVP 一键部署脚本
# 支持云端API、边缘节点、完整系统的自动化部署

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_VERSION="${PYTHON_VERSION:-3.14}"
VENV_PATH="${VENV_PATH:-venv}"
DB_TYPE="${DB_TYPE:-sqlite}"
DATA_DIR="${DATA_DIR:-./data}"
LOG_DIR="${LOG_DIR:-./logs}"

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

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 环境检查函数
check_environment() {
    log_info "🔍 开始环境检查..."

    # 检查Python版本
    if command_exists python3; then
        PYTHON_CMD=python3
        CURRENT_VERSION=$(python3 --version | awk '{print $2}')
        log_success "✅ Python已安装: $CURRENT_VERSION"
    elif command_exists python; then
        PYTHON_CMD=python
        CURRENT_VERSION=$(python --version | awk '{print $2}')
        log_success "✅ Python已安装: $CURRENT_VERSION"
    else
        log_error "❌ Python未安装，请先安装Python $PYTHON_VERSION"
        exit 1
    fi

    # 检查pip
    if command_exists pip3 || command_exists pip; then
        log_success "✅ pip已安装"
    else
        log_error "❌ pip未安装"
        exit 1
    fi

    # 检查虚拟环境
    if [ -d "$VENV_PATH" ]; then
        log_success "✅ 虚拟环境已存在: $VENV_PATH"
    else
        log_warning "⚠️  虚拟环境不存在，将创建新虚拟环境"
        create_virtualenv
    fi

    # 检查必要的目录
    for dir in "$DATA_DIR" "$LOG_DIR" "uploads"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_success "✅ 创建目录: $dir"
        fi
    done

    # 检查.env文件
    if [ ! -f .env ]; then
        log_warning "⚠️  .env文件不存在，从模板复制"
        cp .env.example .env
        log_warning "⚠️  请编辑.env文件配置必要参数"
    fi

    # 检查端口占用
    CLOUD_PORT=$(grep "^CLOUD_SERVICE_PORT=" .env | cut -d'=' -f2)
    if command_exists lsof && lsof -Pi :$CLOUD_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_warning "⚠️  端口$CLOUD_PORT已被占用"
    else
        log_success "✅ 端口$CLOUD_PORT可用"
    fi

    log_success "✅ 环境检查完成"
}

# 创建虚拟环境
create_virtualenv() {
    log_info "📦 创建Python虚拟环境..."
    $PYTHON_CMD -m venv "$VENV_PATH"
    log_success "✅ 虚拟环境创建完成: $VENV_PATH"
}

# 安装依赖
install_dependencies() {
    log_info "📥 安装Python依赖包..."

    source "$VENV_PATH/bin/activate"

    # 更新pip
    pip install --upgrade pip setuptools wheel

    # 安装项目依赖
    if [ -f requirements.txt ]; then
        pip install -r requirements.txt
        log_success "✅ 依赖包安装完成"
    else
        log_warning "⚠️  requirements.txt不存在，跳过依赖安装"
    fi
}

# 数据库初始化
init_database() {
    log_info "🗄️  初始化数据库..."

    if [ "$DB_TYPE" = "sqlite" ]; then
        if [ ! -f "$DATA_DIR/hermesnexus.db" ]; then
            log_success "✅ SQLite数据库将在首次启动时自动创建"
        else
            log_success "✅ SQLite数据库已存在"
        fi
    fi
}

# 停止现有服务
stop_services() {
    log_info "🛑 停止现有服务..."

    # 停止云端API
    if pgrep -f "python.*cloud/api/main.py" > /dev/null; then
        log_info "停止云端API服务..."
        pkill -f "python.*cloud/api/main.py" || true
        sleep 2
    fi

    # 停止边缘节点
    if pgrep -f "python.*edge/runtime/core.py" > /dev/null; then
        log_info "停止边缘节点服务..."
        pkill -f "python.*edge/runtime/core.py" || true
        sleep 2
    fi

    log_success "✅ 服务停止完成"
}

# 启动云端API
start_cloud_api() {
    log_info "🚀 启动云端API服务..."

    cd "$PROJECT_ROOT"
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    export DB_TYPE="$DB_TYPE"
    export SQLITE_DB_PATH="$DATA_DIR/hermesnexus.db"
    source "$VENV_PATH/bin/activate"

    # 启动服务（后台运行）
    nohup python cloud/api/main.py > "$LOG_DIR/cloud_api.log" 2>&1 &

    # 等待服务启动
    local max_wait=10
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if curl -s http://localhost:${CLOUD_PORT:-8080}/health >/dev/null 2>&1; then
            log_success "✅ 云端API服务启动成功"
            return 0
        fi
        sleep 1
        ((waited++))
    done

    log_error "❌ 云端API服务启动超时"
    return 1
}

# 启动边缘节点
start_edge_node() {
    log_info "🚀 启动边缘节点服务..."

    cd "$PROJECT_ROOT"
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    source "$VENV_PATH/bin/activate"

    # 启动服务（后台运行）
    nohup python -m edge.runtime.core > "$LOG_DIR/edge_node.log" 2>&1 &

    log_success "✅ 边缘节点服务启动成功"
}

# 健康检查
health_check() {
    log_info "🏥 执行系统健康检查..."

    # 检查云端API
    local CLOUD_PORT=$(grep "^CLOUD_SERVICE_PORT=" .env | cut -d'=' -f2)
    if curl -s "http://localhost:${CLOUD_PORT:-8080}/health" >/dev/null 2>&1; then
        log_success "✅ 云端API健康: http://localhost:${CLOUD_PORT:-8080}"
    else
        log_error "❌ 云端API不健康"
        return 1
    fi

    # 检查系统状态
    local stats=$(curl -s "http://localhost:${CLOUD_PORT:-8080}/api/v1/stats")
    if [ $? -eq 0 ]; then
        log_success "✅ 系统状态获取成功"
        echo "$stats" | python3 -m json.tool 2>/dev/null || echo "$stats"
    else
        log_warning "⚠️  系统状态获取失败"
    fi

    # 检查日志文件
    if [ -f "$LOG_DIR/cloud_api.log" ]; then
        local log_size=$(wc -c < "$LOG_DIR/cloud_api.log")
        log_success "✅ 云端API日志: $log_size bytes"
    fi

    if [ -f "$LOG_DIR/edge_node.log" ]; then
        local log_size=$(wc -c < "$LOG_DIR/edge_node.log")
        log_success "✅ 边缘节点日志: $log_size bytes"
    fi
}

# 显示部署信息
show_deployment_info() {
    log_success "🎉 部署完成！"
    echo ""
    echo "📋 部署信息:"
    echo "  项目路径: $PROJECT_ROOT"
    echo "  Python版本: $PYTHON_VERSION"
    echo "  虚拟环境: $VENV_PATH"
    echo "  数据库类型: $DB_TYPE"
    echo "  数据目录: $DATA_DIR"
    echo "  日志目录: $LOG_DIR"
    echo ""
    echo "🌐 服务地址:"
    local CLOUD_PORT=$(grep "^CLOUD_SERVICE_PORT=" .env | cut -d'=' -f2)
    echo "  云端API: http://localhost:${CLOUD_PORT:-8080}"
    echo "  Web控制台: http://localhost:${CLOUD_PORT:-8080}/console"
    echo "  API文档: http://localhost:${CLOUD_PORT:-8080}/docs"
    echo ""
    echo "📝 管理命令:"
    echo "  查看日志: tail -f $LOG_DIR/cloud_api.log"
    echo "  停止服务: pkill -f 'python.*main.py'"
    echo "  重启服务: $0 restart"
    echo "  健康检查: curl http://localhost:${CLOUD_PORT:-8080}/health"
    echo ""
}

# 主函数
main() {
    local action="${1:-deploy}"

    case "$action" in
        deploy)
            log_info "🚀 开始部署HermesNexus..."
            check_environment
            install_dependencies
            init_database
            stop_services
            start_cloud_api
            start_edge_node
            sleep 3
            health_check
            show_deployment_info
            ;;
        restart)
            log_info "🔄 重启HermesNexus服务..."
            stop_services
            sleep 2
            start_cloud_api
            start_edge_node
            sleep 3
            health_check
            ;;
        stop)
            log_info "🛑 停止HermesNexus服务..."
            stop_services
            log_success "✅ 服务已停止"
            ;;
        health)
            health_check
            ;;
        clean)
            log_warning "⚠️  清理所有数据、日志和缓存..."
            read -p "确认清理? (yes/no): " confirm
            if [ "$confirm" = "yes" ]; then
                stop_services
                rm -rf "$DATA_DIR"
                rm -rf "$LOG_DIR"
                rm -rf "$VENV_PATH"
                log_success "✅ 清理完成"
            else
                log_info "取消清理"
            fi
            ;;
        *)
            echo "用法: $0 {deploy|restart|stop|health|clean}"
            echo ""
            echo "命令说明:"
            echo "  deploy  - 部署或更新系统"
            echo "  restart - 重启服务"
            echo "  stop    - 停止服务"
            echo "  health  - 健康检查"
            echo "  clean   - 清理所有数据"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"