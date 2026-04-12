#!/bin/bash
# HermesNexus 自动部署脚本包
# 在开发服务器上直接运行此脚本进行部署

set -e

echo "🚀 HermesNexus 自动部署开始..."

# 配置变量
PROJECT_ROOT="/home/scsun/hermesnexus"
SERVER_USER="scsun"
CURRENT_DIR="$(pwd)"

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

# 1. 环境检查
log_info "🔍 执行部署前环境检查..."

echo "检查当前用户: $(whoami)"
if [ "$(whoami)" != "$SERVER_USER" ]; then
    log_warning "当前用户不是 $SERVER_USER，某些操作可能需要sudo权限"
fi

echo "检查Python版本..."
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 未安装"
    exit 1
fi

PYTHON_VER=$(python3 --version | cut -d' ' -f2)
echo "当前Python版本: $PYTHON_VER"

echo "检查磁盘空间..."
DISK_AVAILABLE=$(df -h . | tail -1 | awk '{print $4}')
echo "可用磁盘空间: $DISK_AVAILABLE"

echo "检查当前目录..."
echo "当前目录: $CURRENT_DIR"

# 2. 项目目录创建
log_info "📁 创建项目目录结构..."
mkdir -p "$PROJECT_ROOT"/{data,logs,backups,configs,scripts,venv}
mkdir -p "$PROJECT_ROOT"/logs/{cloud,edge,audit}
mkdir -p "$PROJECT_ROOT"/configs/{local,dev-server}
log_success "✅ 目录结构创建完成"

# 3. 复制项目文件
log_info "📦 复制项目文件到目标目录..."

# 假设脚本在项目根目录下运行
if [ -f "cloud/api/main.py" ]; then
    log_info "检测到项目根目录，复制项目文件..."

    # 复制核心代码
    mkdir -p "$PROJECT_ROOT"/{cloud,edge,shared,tests}
    cp -r cloud/* "$PROJECT_ROOT/cloud/"
    cp -r edge/* "$PROJECT_ROOT/edge/"
    cp -r shared/* "$PROJECT_ROOT/shared/"

    log_success "✅ 项目文件复制完成"
else
    log_warning "未在项目根目录运行，请手动复制项目文件"
    log_info "项目根目录应为: $PROJECT_ROOT"
fi

# 4. Python虚拟环境设置
log_info "🐍 设置Python虚拟环境..."
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    python3 -m venv "$PROJECT_ROOT/venv"
    log_success "✅ 虚拟环境创建完成"
else
    log_info "虚拟环境已存在，跳过创建"
fi

# 激活虚拟环境
source "$PROJECT_ROOT/venv/bin/activate"

# 升级pip
pip install --upgrade pip -q

# 5. 安装依赖
log_info "📦 安装Python依赖包..."

# 核心依赖
pip install -q \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    pydantic==2.5.0 \
    aiosqlite==0.19.0 \
    paramiko==3.4.0 \
    psutil==5.9.6 \
    aiohttp==3.9.1 \
    python-dotenv==1.0.0 \
    requests==2.31.0

log_success "✅ 依赖安装完成"

# 6. 配置文件创建
log_info "⚙️  创建配置文件..."

# Cloud服务配置
cat > "$PROJECT_ROOT/configs/dev-server/cloud.env" << 'EOF'
# HermesNexus Cloud服务配置 - 开发服务器环境

# 服务配置
CLOUD_API_HOST=0.0.0.0
CLOUD_API_PORT=8080
CLOUD_WORKERS=4

# 数据库配置
DB_TYPE=sqlite
SQLITE_DB_PATH=/home/scsun/hermesnexus/data/hermesnexus.db

# 日志配置
LOG_LEVEL=INFO
LOG_DIR=/home/scsun/hermesnexus/logs/cloud

# 安全配置
JWT_SECRET=dev-secret-change-in-production-2026
API_AUTH_TOKEN=dev-token-change-in-production-2026

# 监控配置
ENABLE_METRICS=true
HEALTH_CHECK_INTERVAL=30
EOF

# Edge节点配置
cat > "$PROJECT_ROOT/configs/dev-server/edge.env" << 'EOF'
# HermesNexus Edge节点配置 - 开发服务器环境

# 节点配置
NODE_ID=dev-edge-node-001
NODE_NAME=开发服务器边缘节点
NODE_LOCATION=开发服务器

# 服务端连接
CLOUD_API_URL=http://localhost:8080
REGISTRATION_INTERVAL=30
HEARTBEAT_INTERVAL=10

# 任务执行配置
TASK_POLL_INTERVAL=5
MAX_CONCURRENT_TASKS=3
TASK_TIMEOUT=300

# SSH配置
SSH_TIMEOUT=30
SSH_MAX_RETRIES=3

# 日志配置
LOG_LEVEL=INFO
LOG_DIR=/home/scsun/hermesnexus/logs/edge
EOF

log_success "✅ 配置文件创建完成"

# 7. 设置环境变量
log_info "🌍 设置Python环境变量..."
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
export HERMES_HOME="$PROJECT_ROOT"

# 添加到bashrc
if ! grep -q "HERMES_HOME" "$HOME/.bashrc"; then
    cat >> "$HOME/.bashrc" << 'EOF'

# HermesNexus环境变量
export HERMES_HOME="/home/scsun/hermesnexus"
export PYTHONPATH="/home/scsun/hermesnexus:$PYTHONPATH"
EOF
    log_success "✅ 环境变量已添加到.bashrc"
else
    log_info "环境变量已存在于.bashrc"
fi

# 8. 创建systemd服务文件
log_info "🔧 创建systemd服务配置..."

# 检查是否有sudo权限
if command -v sudo &> /dev/null; then
    # Cloud服务
    cat > /tmp/hermesnexus-cloud.service << 'EOF'
[Unit]
Description=HermesNexus Cloud Control Plane
After=network.target
Wants=hermesnexus-edge.service

[Service]
Type=simple
User=scsun
WorkingDirectory=/home/scsun/hermesnexus
Environment="PATH=/home/scsun/hermesnexus/venv/bin"
EnvironmentFile=/home/scsun/hermesnexus/configs/dev-server/cloud.env
ExecStart=/home/scsun/hermesnexus/venv/bin/python -m uvicorn cloud.api.main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Edge服务
    cat > /tmp/hermesnexus-edge.service << 'EOF'
[Unit]
Description=HermesNexus Edge Node
After=network.target hermesnexus-cloud.service
Requires=hermesnexus-cloud.service

[Service]
Type=simple
User=scsun
WorkingDirectory=/home/scsun/hermesnexus
Environment="PATH=/home/scsun/hermesnexus/venv/bin"
EnvironmentFile=/home/scsun/hermesnexus/configs/dev-server/edge.env
ExecStart=/home/scsun/hermesnexus/venv/bin/python -m edge.runtime.core
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    log_info "systemd服务文件已创建，需要sudo权限安装"
    log_info "请手动执行: sudo mv /tmp/hermesnexus-*.service /etc/systemd/system/"
    log_info "然后执行: sudo systemctl daemon-reload"
else
    log_warning "无sudo权限，跳过systemd服务安装"
fi

# 9. 环境验证
log_info "🔍 执行环境验证..."

echo "检查目录结构..."
[ -d "$PROJECT_ROOT/venv" ] && echo "✅ 虚拟环境存在" || echo "❌ 虚拟环境缺失"
[ -d "$PROJECT_ROOT/data" ] && echo "✅ 数据目录存在" || echo "❌ 数据目录缺失"
[ -d "$PROJECT_ROOT/logs" ] && echo "✅ 日志目录存在" || echo "❌ 日志目录缺失"

echo "检查配置文件..."
[ -f "$PROJECT_ROOT/configs/dev-server/cloud.env" ] && echo "✅ Cloud配置存在" || echo "❌ Cloud配置缺失"
[ -f "$PROJECT_ROOT/configs/dev-server/edge.env" ] && echo "✅ Edge配置存在" || echo "❌ Edge配置缺失"

echo "检查Python依赖..."
source "$PROJECT_ROOT/venv/bin/activate"
python3 -c "import fastapi, uvicorn, pydantic, aiosqlite" && echo "✅ 核心依赖安装成功" || echo "❌ 核心依赖缺失"

# 10. 启动服务
log_info "🚀 准备启动服务..."

# 设置环境变量
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
source "$PROJECT_ROOT/venv/bin/activate"
source "$PROJECT_ROOT/configs/dev-server/cloud.env"

# 检查端口占用
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    log_warning "⚠️  端口8080已被占用"
    lsof -Pi :8080 -sTCP:LISTEN
    log_info "尝试停止现有进程..."
    pkill -f "uvicorn.*cloud.api.main" || true
    sleep 2
fi

# 启动Cloud API服务
log_info "☁️  启动Cloud控制平面..."
cd "$PROJECT_ROOT"
nohup python3 -m uvicorn cloud.api.main:app \
    --host 0.0.0.0 \
    --port 8080 \
    --log-level info \
    > "$PROJECT_ROOT/logs/cloud/startup.log" 2>&1 &

CLOUD_PID=$!
echo $CLOUD_PID > "$PROJECT_ROOT/cloud.pid"

log_success "✅ Cloud控制平面已启动 (PID: $CLOUD_PID)"

# 11. 服务健康检查
log_info "🏥 执行服务健康检查..."
sleep 5

MAX_WAIT=30
WAIT_TIME=0
while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        log_success "✅ API服务已就绪"
        break
    fi
    echo "等待API服务启动... ($((WAIT_TIME + 1))/$MAX_WAIT 秒)"
    sleep 1
    WAIT_TIME=$((WAIT_TIME + 1))
done

if [ $WAIT_TIME -ge $MAX_WAIT ]; then
    log_error "❌ API服务启动超时"
    echo "查看启动日志:"
    cat "$PROJECT_ROOT/logs/cloud/startup.log"
    exit 1
fi

# 12. API端点验证
log_info "🔍 验证API端点..."

HEALTH=$(curl -s http://localhost:8080/health)
echo "健康检查: $HEALTH"

echo "统计信息:"
STATS=$(curl -s http://localhost:8080/api/v1/stats)
echo "$STATS" | head -3

echo "节点状态:"
NODES=$(curl -s http://localhost:8080/api/v1/nodes)
echo "$NODES"

# 13. 最终状态报告
echo ""
echo "================================"
echo "🎉 HermesNexus 部署完成！"
echo "================================"
echo ""
echo "📊 服务状态:"
echo "  Cloud控制平面: 🟢 运行中 (PID: $CLOUD_PID)"
echo "  API端点: http://localhost:8080"
echo "  健康检查: http://localhost:8080/health"
echo ""
echo "📁 重要路径:"
echo "  项目根目录: $PROJECT_ROOT"
echo "  配置文件: $PROJECT_ROOT/configs/dev-server/"
echo "  日志文件: $PROJECT_ROOT/logs/"
echo "  数据文件: $PROJECT_ROOT/data/"
echo ""
echo "📋 管理命令:"
echo "  查看日志: tail -f $PROJECT_ROOT/logs/cloud/startup.log"
echo "  停止服务: kill $CLOUD_PID"
echo "  重启服务: cd $PROJECT_ROOT && ./deploy-package.sh"
echo "  API测试: curl http://localhost:8080/api/v1/stats"
echo ""
echo "✅ 部署成功！HermesNexus现在可以使用了。"