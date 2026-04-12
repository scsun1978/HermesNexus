#!/bin/bash
# HermesNexus 本地演示启动脚本
# 模拟开发服务器部署流程

set -e

echo "🚀 启动HermesNexus本地演示环境..."

# 配置变量
LOCAL_DEMO_ROOT="$(pwd)/local-deploy"
export PYTHONPATH="$(pwd):$PYTHONPATH"

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

# 1. 环境准备
log_info "📁 准备本地演示环境..."
mkdir -p "$LOCAL_DEMO_ROOT"/{data,logs,configs}

# 加载配置
if [ -f "$LOCAL_DEMO_ROOT/configs/local-cloud.env" ]; then
    export $(cat "$LOCAL_DEMO_ROOT/configs/local-cloud.env" | grep -v '^#' | xargs)
    log_success "✅ Cloud配置已加载"
else
    log_error "❌ Cloud配置文件不存在"
    exit 1
fi

# 2. 检查Python依赖
log_info "🐍 检查Python环境..."
python3 -c "import fastapi, uvicorn, pydantic, aiosqlite" 2>/dev/null || {
    log_error "❌ 缺少必要依赖，请运行: pip install -r requirements.txt"
    exit 1
}
log_success "✅ Python环境检查通过"

# 3. 启动Cloud控制平面（后台）
log_info "☁️  启动Cloud控制平面..."

# 检查端口是否已占用
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    log_warning "⚠️  端口8080已被占用，尝试停止现有服务..."
    pkill -f "uvicorn.*cloud.api.main" || true
    sleep 2
fi

# 启动Cloud API服务
nohup python3 -m uvicorn cloud.api.main:app \
    --host $CLOUD_API_HOST \
    --port $CLOUD_API_PORT \
    --log-level info \
    > "$LOCAL_DEMO_ROOT/logs/cloud.log" 2>&1 &

CLOUD_PID=$!
echo $CLOUD_PID > "$LOCAL_DEMO_ROOT/cloud.pid"

log_success "✅ Cloud控制平面已启动 (PID: $CLOUD_PID)"

# 4. 等待API服务就绪
log_info "⏳ 等待API服务就绪..."
MAX_WAIT=15
WAIT_TIME=0
while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    if curl -s http://127.0.0.1:8080/health > /dev/null 2>&1; then
        log_success "✅ API服务已就绪"
        break
    fi
    echo "等待中... ($((WAIT_TIME + 1))/$MAX_WAIT 秒)"
    sleep 1
    WAIT_TIME=$((WAIT_TIME + 1))
done

if [ $WAIT_TIME -ge $MAX_WAIT ]; then
    log_error "❌ API服务启动超时"
    cat "$LOCAL_DEMO_ROOT/logs/cloud.log"
    exit 1
fi

# 5. 健康检查
log_info "🏥 执行健康检查..."

HEALTH=$(curl -s http://127.0.0.1:8080/health)
echo "健康状态: $HEALTH"

# 检查API端点
log_info "🔍 验证API端点..."

echo "检查统计信息..."
STATS=$(curl -s http://127.0.0.1:8080/api/v1/stats)
echo "$STATS" | head -3

echo "检查节点状态..."
NODES=$(curl -s http://127.0.0.1:8080/api/v1/nodes)
NODE_COUNT=$(echo "$NODES" | grep -o '"total":[0-9]*' | cut -d':' -f2)
echo "当前节点数量: $NODE_COUNT"

# 6. 服务状态总结
echo ""
echo "================================"
echo "🎉 HermesNexus本地演示环境启动完成！"
echo "================================"
echo ""
echo "📊 服务状态:"
echo "  Cloud控制平面: 🟢 运行中 (PID: $CLOUD_PID)"
echo "  API端点: http://127.0.0.1:8080"
echo ""
echo "📋 管理命令:"
echo "  查看日志: cat $LOCAL_DEMO_ROOT/logs/cloud.log"
echo "  停止服务: kill $CLOUD_PID"
echo "  健康检查: curl http://127.0.0.1:8080/health"
echo ""
echo "✅ 演示环境就绪，可以开始测试API功能！"