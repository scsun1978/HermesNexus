#!/bin/bash
# HermesNexus 开发服务器停止脚本
# 优雅停止所有服务

set -e

echo "🛑 停止HermesNexus开发服务器..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# 1. 停止Edge节点（先停止边缘节点，优雅断开连接）
log_info "🔷 停止Edge边缘节点..."
if systemctl is-active --quiet hermesnexus-edge; then
    sudo systemctl stop hermesnexus-edge
    log_success "✅ Edge边缘节点已停止"
else
    log_info "Edge边缘节点未运行"
fi

# 2. 停止Cloud控制平面
log_info "☁️  停止Cloud控制平面..."
if systemctl is-active --quiet hermesnexus-cloud; then
    sudo systemctl stop hermesnexus-cloud
    log_success "✅ Cloud控制平面已停止"
else
    log_info "Cloud控制平面未运行"
fi

# 3. 等待服务完全停止
sleep 3

# 4. 验证服务状态
echo ""
echo "================================"
echo "🛑 服务停止状态确认"
echo "================================"
echo ""
echo "Cloud控制平面: $(systemctl is-active hermesnexus-cloud 2>/dev/null || echo '🔴 已停止')"
echo "Edge边缘节点: $(systemctl is-active hermesnexus-edge 2>/dev/null || echo '🔴 已停止')"
echo ""
echo "端口状态检查:"
if netstat -tuln 2>/dev/null | grep -q ':8080.*LISTEN'; then
    echo "⚠️  端口8080仍在使用，可能有其他进程占用"
else
    echo "✅ 端口8080已释放"
fi

log_success "🎉 HermesNexus开发服务器已完全停止！"