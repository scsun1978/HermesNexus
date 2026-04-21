#!/bin/bash

###############################################################################
# HermesNexus One-Click Deployment Script
# 一键部署脚本 - 支持Cloud + Edge完整部署
###############################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
VERSION=${VERSION:-"1.2.0"}
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=${VCS_REF:-"$(git rev-parse --short HEAD)"}

echo -e "${BLUE}🚀 HermesNexus 一键部署脚本${NC}"
echo "================================"

# 函数：打印信息
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# 函数：检查依赖
check_dependencies() {
    info "检查部署依赖..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        error "Docker未安装，请先安装Docker"
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose未安装，请先安装Docker Compose"
    fi

    success "依赖检查通过"
}

# 函数：环境配置
setup_environment() {
    info "配置部署环境..."

    # 创建必要的目录
    mkdir -p data logs monitoring/prometheus monitoring/grafana/dashboards monitoring/grafana/datasources

    # 创建Prometheus配置
    if [ ! -f "monitoring/prometheus.yml" ]; then
        cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'hermes-cloud'
    static_configs:
      - targets: ['hermes-cloud:8080']
    metrics_path: '/metrics'

  - job_name: 'hermes-edge'
    static_configs:
      - targets: ['hermes-edge-1:8888']
    metrics_path: '/metrics'
EOF
    fi

    success "环境配置完成"
}

# 函数：构建镜像
build_images() {
    info "构建Docker镜像..."

    # 构建Cloud镜像
    info "构建Hermes Cloud镜像..."
    docker build \
        -f Dockerfile \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VERSION="$VERSION" \
        --build-arg VCS_REF="$VCS_REF" \
        -t hermesnexus/cloud:$VERSION \
        -t hermesnexus/cloud:latest \
        .

    # 构建Edge镜像
    info "构建Hermes Edge镜像..."
    docker build \
        -f Dockerfile.edge \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VERSION="$VERSION" \
        --build-arg VCS_REF="$VCS_REF" \
        -t hermesnexus/edge:$VERSION \
        -t hermesnexus/edge:latest \
        .

    success "镜像构建完成"
}

# 函数：启动服务
start_services() {
    local profile=${1:-""}

    if [ -n "$profile" ]; then
        info "启动HermesNexus服务 (Profile: $profile)..."
        docker-compose --profile "$profile" up -d
    else
        info "启动HermesNexus基础服务..."
        docker-compose up -d
    fi

    success "服务启动完成"
}

# 函数：健康检查
health_check() {
    info "等待服务启动..."

    # 等待Cloud API健康
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -f http://localhost:8080/health &> /dev/null; then
            success "Cloud API服务健康"
            break
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done

    if [ $attempt -eq $max_attempts ]; then
        error "Cloud API服务启动超时"
    fi

    # 检查容器状态
    info "容器状态:"
    docker-compose ps
}

# 函数：显示访问信息
show_access_info() {
    echo ""
    success "🎉 HermesNexus部署完成！"
    echo ""
    echo "服务访问地址:"
    echo "  📡 Cloud API:    http://localhost:8080"
    echo "  📊 Health Check: http://localhost:8080/health"
    echo "  🎨 Web Console:  http://localhost:8080/console"
    echo ""
    echo "Edge节点地址:"
    echo "  🔗 Edge Node 1:  http://localhost:8888"
    echo ""
    echo "管理命令:"
    echo "  📋 查看日志:     docker-compose logs -f"
    echo "  🛑 停止服务:     docker-compose down"
    echo "  🔄 重启服务:     docker-compose restart"
    echo "  📈 容器状态:     docker-compose ps"
    echo ""

    # 如果启用了监控
    if docker-compose ps | grep -q "prometheus"; then
        echo "监控服务地址:"
        echo "  📊 Prometheus:   http://localhost:9090"
        echo "  📈 Grafana:      http://localhost:3000 (admin/admin)"
        echo ""
    fi
}

# 函数：清理旧部署
cleanup_old_deployment() {
    warning "清理旧部署数据..."

    read -p "是否清理旧数据? (这将删除所有数据) [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v
        docker system prune -f
        success "清理完成"
    else
        info "跳过清理，保留现有数据"
    fi
}

# 函数：部署验证
verify_deployment() {
    info "运行部署验证..."

    # 运行Smoke测试
    if [ -f "tests/e2e/test_smoke.py" ]; then
        info "运行Smoke测试验证..."
        if python3 -m pytest tests/e2e/test_smoke.py -v --tb=short; then
            success "Smoke测试验证通过"
        else
            warning "Smoke测试失败，但服务可能仍在运行"
        fi
    fi
}

# 主函数
main() {
    local command=${1:-"deploy"}

    case $command in
        deploy)
            check_dependencies
            setup_environment
            build_images
            start_services
            health_check
            verify_deployment
            show_access_info
            ;;
        deploy-full)
            check_dependencies
            setup_environment
            build_images
            start_services "monitoring,enhanced"
            health_check
            show_access_info
            ;;
        start)
            info "启动现有服务..."
            docker-compose start
            health_check
            show_access_info
            ;;
        stop)
            info "停止服务..."
            docker-compose stop
            success "服务已停止"
            ;;
        restart)
            info "重启服务..."
            docker-compose restart
            health_check
            success "服务已重启"
            ;;
        down)
            warning "停止并移除容器..."
            docker-compose down
            success "容器已移除"
            ;;
        clean)
            cleanup_old_deployment
            ;;
        logs)
            info "显示服务日志..."
            docker-compose logs -f
            ;;
        status)
            info "服务状态:"
            docker-compose ps
            ;;
        health)
            health_check
            ;;
        *)
            echo "用法: $0 {deploy|deploy-full|start|stop|restart|down|clean|logs|status|health}"
            echo ""
            echo "命令说明:"
            echo "  deploy       - 一键部署 (基础服务)"
            echo "  deploy-full  - 一键部署 (包含监控)"
            echo "  start        - 启动现有服务"
            echo "  stop         - 停止服务"
            echo "  restart      - 重启服务"
            echo "  down         - 停止并移除容器"
            echo "  clean        - 清理旧部署数据"
            echo "  logs         - 查看实时日志"
            echo "  status       - 查看服务状态"
            echo "  health       - 健康检查"
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"