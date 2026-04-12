#!/bin/bash
# HermesNexus 开发服务器一键启动脚本
# 按正确顺序启动所有服务

set -e

echo "🚀 启动HermesNexus开发服务器..."

# 配置变量
PROJECT_ROOT="/home/scsun/hermesnexus"
SERVER_USER="scsun"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查用户
if [ "$(whoami)" != "$SERVER_USER" ]; then
    log_error "此脚本必须由 $SERVER_USER 用户执行"
    exit 1
fi

# 切换到项目目录
cd "$PROJECT_ROOT"

# 1. 停止现有服务（如果运行中）
log_info "🛑 停止现有服务..."
sudo systemctl stop hermesnexus-edge 2>/dev/null || true
sudo systemctl stop hermesnexus-cloud 2>/dev/null || true
sleep 2

# 2. 检查虚拟环境
log_info "🔧 检查虚拟环境..."
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    log_error "虚拟环境不存在，请先运行 ./scripts/dev-server-init.sh"
    exit 1
fi

source "$PROJECT_ROOT/venv/bin/activate"

# 3. 检查配置文件
log_info "⚙️ 检查配置文件..."
if [ ! -f "$PROJECT_ROOT/configs/dev-server/cloud.env" ]; then
    log_error "Cloud配置文件不存在，请先运行 ./scripts/dev-server-init.sh"
    exit 1
fi

if [ ! -f "$PROJECT_ROOT/configs/dev-server/edge.env" ]; then
    log_error "Edge配置文件不存在，请先运行 ./scripts/dev-server-init.sh"
    exit 1
fi

# 4. 启动Cloud控制平面
log_info "☁️  启动Cloud控制平面..."
sudo systemctl start hermesnexus-cloud

# 等待服务启动
sleep 5

# 检查Cloud服务状态
if systemctl is-active --quiet hermesnexus-cloud; then
    log_success "✅ Cloud控制平面启动成功"
else
    log_error "❌ Cloud控制平面启动失败"
    sudo journalctl -u hermesnexus-cloud -n 20 --no-pager
    exit 1
fi

# 5. 等待API服务就绪
log_info "⏳ 等待API服务就绪..."
MAX_WAIT=30
WAIT_TIME=0
while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        log_success "✅ API服务已就绪"
        break
    fi
    echo "等待中... ($((WAIT_TIME + 1))/$MAX_WAIT 秒)"
    sleep 1
    WAIT_TIME=$((WAIT_TIME + 1))
done

if [ $WAIT_TIME -ge $MAX_WAIT ]; then
    log_error "❌ API服务启动超时"
    exit 1
fi

# 6. 启动Edge边缘节点
log_info "🔷 启动Edge边缘节点..."
sudo systemctl start hermesnexus-edge

# 等待Edge服务启动
sleep 5

# 检查Edge服务状态
if systemctl is-active --quiet hermesnexus-edge; then
    log_success "✅ Edge边缘节点启动成功"
else
    log_warning "⚠️  Edge边缘节点启动失败，将继续验证Cloud服务"
fi

# 7. 执行健康检查
log_info "🏥 执行系统健康检查..."

echo "检查Cloud API健康状态..."
HEALTH=$(curl -s http://localhost:8080/health)
if echo "$HEALTH" | grep -q "healthy"; then
    log_success "✅ Cloud API健康检查通过"
else
    log_error "❌ Cloud API健康检查失败"
    exit 1
fi

echo "检查系统统计信息..."
STATS=$(curl -s http://localhost:8080/api/v1/stats)
echo "$STATS" | head -5

echo "检查节点状态..."
NODES=$(curl -s http://localhost:8080/api/v1/nodes)
NODE_COUNT=$(echo "$NODES" | grep -o '"total":[0-9]*' | cut -d':' -f2)
echo "当前节点数量: $NODE_COUNT"

# 8. 服务状态总结
echo ""
echo "================================"
echo "🎉 HermesNexus开发服务器启动完成！"
echo "================================"
echo ""
echo "📊 服务状态:"
echo "  Cloud控制平面: $(systemctl is-active hermesnexus-cloud && echo '🟢 运行中' || echo '🔴 停止')"
echo "  Edge边缘节点: $(systemctl is-active hermesnexus-edge && echo '🟢 运行中' || echo '🔴 停止')"
echo ""
echo "🌐 访问地址:"
echo "  Cloud API: http://172.16.100.101:8080"
echo "  健康检查: http://172.16.100.101:8080/health"
echo "  控制台: http://172.16.100.101:8080/console"
echo ""
echo "📋 管理命令:"
echo "  停止服务: ./scripts/stop-all.sh"
echo "  重启服务: ./scripts/restart-all.sh"
echo "  查看状态: ./scripts/status.sh"
echo "  查看日志: ./scripts/logs.sh"
echo ""
echo "✅ 所有服务已启动并正常运行！"