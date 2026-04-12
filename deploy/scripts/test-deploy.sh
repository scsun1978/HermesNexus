#!/bin/bash
# 测试部署脚本 - 验证开发服务器环境

set -e

SSH_KEY_PATH="${HOME}/.ssh/ubuntu_root_id_ed25519"
DEV_SERVER="scsun@172.16.100.101"
REMOTE_DIR="/opt/hermesnexus"

echo "========================================="
echo "  HermesNexus 环境测试脚本"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# 1. 测试 SSH 连接
echo "1. 测试 SSH 连接..."
if ssh -i ${SSH_KEY_PATH} -o StrictHostKeyChecking=no -o ConnectTimeout=5 ${DEV_SERVER} "echo '连接成功'" > /dev/null 2>&1; then
    log_info "SSH 连接正常"
else
    log_error "SSH 连接失败"
    exit 1
fi

# 2. 测试服务器环境信息
echo ""
echo "2. 服务器环境信息..."
ssh -i ${SSH_KEY_PATH} -o StrictHostKeyChecking=no ${DEV_SERVER} << 'ENDSSH'
    echo "系统信息:"
    uname -a
    echo ""
    echo "磁盘使用:"
    df -h | grep -E "Filesystem|/dev/"
    echo ""
    echo "内存使用:"
    free -h | head -2
ENDSSH

# 3. 测试 Docker 环境
echo ""
echo "3. Docker 环境测试..."
if ssh -i ${SSH_KEY_PATH} -o StrictHostKeyChecking=no ${DEV_SERVER} "docker --version" > /dev/null 2>&1; then
    DOCKER_VERSION=$(ssh -i ${SSH_KEY_PATH} -o StrictHostKeyChecking=no ${DEV_SERVER} "docker --version")
    log_info "Docker 已安装: ${DOCKER_VERSION}"
else
    log_error "Docker 未安装"
    exit 1
fi

if ssh -i ${SSH_KEY_PATH} -o StrictHostKeyChecking=no ${DEV_SERVER} "docker compose version" > /dev/null 2>&1; then
    COMPOSE_VERSION=$(ssh -i ${SSH_KEY_PATH} -o StrictHostKeyChecking=no ${DEV_SERVER} "docker compose version")
    log_info "Docker Compose 已安装: ${COMPOSE_VERSION}"
else
    log_error "Docker Compose 未安装"
    exit 1
fi

# 4. 测试项目目录
echo ""
echo "4. 项目目录测试..."
if ssh -i ${SSH_KEY_PATH} -o StrictHostKeyChecking=no ${DEV_SERVER} "test -d ${REMOTE_DIR}"; then
    log_info "项目目录存在: ${REMOTE_DIR}"
    PERMS=$(ssh -i ${SSH_KEY_PATH} -o StrictHostKeyChecking=no ${DEV_SERVER} "ls -ld ${REMOTE_DIR} | awk '{print \$1,\$3,\$4}'")
    echo "    权限: ${PERMS}"
else
    log_warn "项目目录不存在，将创建"
    ssh -i ${SSH_KEY_PATH} -o StrictHostKeyChecking=no ${DEV_SERVER} "sudo mkdir -p ${REMOTE_DIR} && sudo chown \$USER:\$USER ${REMOTE_DIR}"
    log_info "项目目录已创建"
fi

# 5. 测试 Docker 操作
echo ""
echo "5. Docker 功能测试..."
ssh -i ${SSH_KEY_PATH} -o StrictHostKeyChecking=no ${DEV_SERVER} << 'ENDSSH'
    # 测试拉取一个小镜像
    echo "    测试拉取 hello-world 镜像..."
    if docker pull hello-world:latest > /dev/null 2>&1; then
        echo "    ✓ 镜像拉取成功"

        # 测试运行容器
        echo "    测试运行容器..."
        if docker run --rm hello-world:latest > /dev/null 2>&1; then
            echo "    ✓ 容器运行成功"
        else
            echo "    ✗ 容器运行失败"
        fi

        # 清理
        docker rmi hello-world:latest > /dev/null 2>&1
    else
        echo "    ✗ 镜像拉取失败"
    fi

    # 检查现有容器
    echo "    当前运行的容器:"
    docker ps --format "    - {{.Names}} ({{.Status}})" || echo "    无运行容器"
ENDSSH

# 6. 测试网络连接
echo ""
echo "6. 网络连接测试..."
if ssh -i ${SSH_KEY_PATH} -o StrictHostKeyChecking=no ${DEV_SERVER} "ping -c 2 8.8.8.8 > /dev/null 2>&1"; then
    log_info "外网连接正常"
else
    log_warn "外网连接可能有问题"
fi

# 总结
echo ""
echo "========================================="
echo "  测试完成"
echo "========================================="
echo ""
echo "开发服务器环境就绪，可以开始部署工作！"
echo ""
echo "常用命令:"
echo "  - 部署到服务器: make deploy"
echo "  - 查看部署状态: make deploy-status"
echo "  - 查看部署日志: make deploy-logs"
echo "  - 直接SSH连接: ssh -i ~/.ssh/ubuntu_root_id_ed25519 scsun@172.16.100.101"
echo ""
