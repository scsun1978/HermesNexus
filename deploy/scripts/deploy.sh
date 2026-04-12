#!/bin/bash
# HermesNexus 部署脚本
# 用于在开发服务器上部署和更新 HermesNexus 服务

set -e  # 遇到错误立即退出

# 配置变量
DEV_SERVER="scsun@172.16.100.101"
DEV_SERVER_PORT=22
SSH_KEY_PATH="${HOME}/.ssh/ubuntu_root_id_ed25519"
PROJECT_NAME="hermesnexus"
REMOTE_DIR="/opt/hermesnexus"
COMPOSE_FILE="docker-compose.yaml"

# SSH 命令别名
SSH_CMD="ssh -i ${SSH_KEY_PATH} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
RSYNC_SSH="ssh -i ${SSH_KEY_PATH} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查本地环境
check_local_env() {
    log_info "检查本地环境..."

    if [ ! -f "docker-compose.yaml" ]; then
        log_error "缺少 docker-compose.yaml 文件"
        exit 1
    fi

    if [ ! -f ".env" ]; then
        log_warn "缺少 .env 文件，使用默认配置"
    fi

    log_info "本地环境检查完成"
}

# 测试服务器连接
test_server_connection() {
    log_info "测试服务器连接..."

    if ${SSH_CMD} -p ${DEV_SERVER_PORT} -o ConnectTimeout=5 ${DEV_SERVER} "echo '连接成功'" > /dev/null 2>&1; then
        log_info "服务器连接正常"
    else
        log_error "无法连接到服务器 ${DEV_SERVER}"
        log_error "请检查:"
        log_error "  1. 密钥文件存在: ${SSH_KEY_PATH}"
        log_error "  2. 服务器地址正确: ${DEV_SERVER}"
        log_error "  3. 网络连接正常"
        exit 1
    fi
}

# 在远程服务器上准备环境
prepare_remote_env() {
    log_info "准备远程服务器环境..."

    ${SSH_CMD} -p ${DEV_SERVER_PORT} ${DEV_SERVER} << 'ENDSSH'
        # 创建项目目录
        sudo mkdir -p ${REMOTE_DIR}
        sudo chown $USER:$USER ${REMOTE_DIR}

        # 创建必要的子目录
        mkdir -p ${REMOTE_DIR}/{data,logs,uploads,config}

        # 检查 Docker
        if ! command -v docker &> /dev/null; then
            echo "Docker 未安装，请先安装 Docker"
            exit 1
        fi

        # 检查 Docker Compose
        if ! docker compose version &> /dev/null; then
            echo "Docker Compose 未安装，请先安装 Docker Compose"
            exit 1
        fi

        echo "远程环境准备完成"
ENDSSH

    log_info "远程环境准备完成"
}

# 同步文件到服务器
sync_files() {
    log_info "同步文件到服务器..."

    # 排除不必要的文件
    EXCLUDE="--exclude=.git --exclude=node_modules --exclude=__pycache__ "
    EXCLUDE+="--exclude=*.pyc --exclude=.DS_Store --exclude=logs/* "
    EXCLUDE+="--exclude=data/* --exclude=uploads/*"

    # 使用 rsync 同步文件
    rsync -avz --delete ${EXCLUDE} \
          -e "${RSYNC_SSH} -p ${DEV_SERVER_PORT}" \
          ./ ${DEV_SERVER}:${REMOTE_DIR}/

    log_info "文件同步完成"
}

# 在服务器上部署
deploy_on_server() {
    log_info "在服务器上部署服务..."

    ${SSH_CMD} -p ${DEV_SERVER_PORT} ${DEV_SERVER} << 'ENDSSH'
        cd ${REMOTE_DIR}

        # 停止现有服务
        if [ -f "docker-compose.yaml" ]; then
            echo "停止现有服务..."
            docker compose down
        fi

        # 拉取最新镜像
        echo "拉取 Docker 镜像..."
        docker compose pull

        # 启动服务
        echo "启动服务..."
        docker compose up -d

        # 等待服务启动
        echo "等待服务启动..."
        sleep 10

        # 显示服务状态
        echo "服务状态:"
        docker compose ps

        # 显示日志
        echo "最新日志:"
        docker compose logs --tail=20
ENDSSH

    log_info "服务部署完成"
}

# 验证部署
verify_deployment() {
    log_info "验证部署..."

    # 检查健康状态
    log_info "检查服务健康状态..."

    # 这里可以添加具体的健康检查逻辑
    # 例如: curl http://172.16.100.101:8080/health

    log_info "部署验证完成"
}

# 显示部署信息
show_deployment_info() {
    echo ""
    log_info "🎉 部署完成！"
    echo ""
    echo "服务地址:"
    echo "  - 云端服务: http://172.16.100.101:8080"
    echo "  - 控制台: http://172.16.100.101:3000"
    echo ""
    echo "常用命令:"
    echo "  - 查看状态: make deploy-status"
    echo "  - 查看日志: make deploy-logs"
    echo "  - SSH 登录: ssh ${DEV_SERVER}"
    echo ""
}

# 主函数
main() {
    echo "========================================"
    echo "  HermesNexus 自动部署脚本"
    echo "========================================"
    echo ""

    # 检查参数
    if [ "$1" == "--skip-env" ]; then
        log_warn "跳过环境准备步骤"
    else
        check_local_env
        test_server_connection
        prepare_remote_env
    fi

    if [ "$1" == "--sync-only" ]; then
        sync_files
        log_info "文件同步完成"
        exit 0
    fi

    sync_files
    deploy_on_server
    verify_deployment
    show_deployment_info
}

# 执行主函数
main "$@"
