#!/bin/bash
# HermesNexus 开发服务器环境初始化脚本
# 在开发服务器上首次部署前执行

set -e

echo "🚀 开始HermesNexus开发服务器环境初始化..."

# 配置变量
PROJECT_ROOT="/home/scsun/hermesnexus"
SERVER_USER="scsun"
PYTHON_VERSION="3.14"

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

# 检查是否为正确用户
if [ "$(whoami)" != "$SERVER_USER" ]; then
    log_error "此脚本必须由 $SERVER_USER 用户执行"
    exit 1
fi

# 1. 创建项目目录结构
log_info "📁 创建项目目录结构..."
mkdir -p "$PROJECT_ROOT"/{data,logs,backups,configs,scripts}
mkdir -p "$PROJECT_ROOT"/logs/{cloud,edge,audit}
mkdir -p "$PROJECT_ROOT"/configs/{local,dev-server}

log_success "✅ 项目目录结构创建完成"

# 2. 检查Python环境
log_info "🐍 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 未安装"
    exit 1
fi

PYTHON_VER=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
log_info "当前Python版本: $PYTHON_VER"

if [ "$(echo "$PYTHON_VER < 3.14" | bc)" -eq 1 ]; then
    log_error "Python版本必须 >= 3.14"
    exit 1
fi

log_success "✅ Python环境检查通过"

# 3. 创建虚拟环境
log_info "🔧 创建Python虚拟环境..."
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    python3 -m venv "$PROJECT_ROOT/venv"
    log_success "✅ 虚拟环境创建完成"
else
    log_info "虚拟环境已存在"
fi

# 4. 激活虚拟环境并安装依赖
log_info "📦 安装项目依赖..."
source "$PROJECT_ROOT/venv/bin/activate"

# 升级pip
pip install --upgrade pip -q

# 安装核心依赖
pip install -q \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    paramiko==3.3.1 \
    aiosqlite==0.19.0 \
    psutil==5.9.6 \
    requests==2.31.0 \
    aiohttp==3.9.1

log_success "✅ 依赖安装完成"

# 5. 创建配置文件
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

# 6. 创建systemd服务文件
log_info "🔧 创建系统服务配置..."

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

sudo mv /tmp/hermesnexus-cloud.service /etc/systemd/system/
sudo systemctl daemon-reload
log_success "✅ Cloud服务配置完成"

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

sudo mv /tmp/hermesnexus-edge.service /etc/systemd/system/
sudo systemctl daemon-reload
log_success "✅ Edge服务配置完成"

# 7. 配置防火墙
log_info "🛡️ 配置防火墙..."
sudo ufw allow 8080/tcp
sudo ufw allow from 127.0.0.1 to any port 8080
log_success "✅ 防火墙配置完成"

# 8. 配置日志轮转
log_info "📋 配置日志轮转..."
cat > /tmp/hermesnexus-logrotate << 'EOF'
/home/scsun/hermesnexus/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 scsun scsun
    sharedscripts
    postrotate
        systemctl reload hermesnexus-cloud >/dev/null 2>&1 || true
        systemctl reload hermesnexus-edge >/dev/null 2>&1 || true
    endscript
}
EOF

sudo mv /tmp/hermesnexus-logrotate /etc/logrotate.d/
log_success "✅ 日志轮转配置完成"

# 9. 设置环境变量
log_info "🌍 设置环境变量..."
cat >> "$HOME/.bashrc" << 'EOF'

# HermesNexus环境变量
export HERMES_HOME="/home/scsun/hermesnexus"
export PYTHONPATH="/home/scsun/hermesnexus:$PYTHONPATH"
EOF

source "$HOME/.bashrc"
log_success "✅ 环境变量设置完成"

# 10. 最终验证
log_info "🔍 执行环境验证..."

echo "检查目录结构..."
[ -d "$PROJECT_ROOT/venv" ] && echo "✅ 虚拟环境存在" || echo "❌ 虚拟环境缺失"
[ -d "$PROJECT_ROOT/data" ] && echo "✅ 数据目录存在" || echo "❌ 数据目录缺失"
[ -d "$PROJECT_ROOT/logs" ] && echo "✅ 日志目录存在" || echo "❌ 日志目录缺失"

echo "检查配置文件..."
[ -f "$PROJECT_ROOT/configs/dev-server/cloud.env" ] && echo "✅ Cloud配置存在" || echo "❌ Cloud配置缺失"
[ -f "$PROJECT_ROOT/configs/dev-server/edge.env" ] && echo "✅ Edge配置存在" || echo "❌ Edge配置缺失"

echo "检查系统服务..."
systemctl list-units | grep hermesnexus && echo "✅ 系统服务已注册" || echo "❌ 系统服务未注册"

echo "检查防火墙..."
sudo ufw status | grep 8080 && echo "✅ 防火墙规则已配置" || echo "❌ 防火墙规则缺失"

log_success "🎉 开发服务器环境初始化完成！"
log_info "📋 下一步: 运行 ./scripts/start-all.sh 启动所有服务"