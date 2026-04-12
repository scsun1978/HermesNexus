#!/bin/bash
# HermesNexus 服务器部署引导脚本
# 在服务器上直接运行此脚本进行完整部署

set -e

echo "🚀 HermesNexus 服务器部署开始..."
echo "========================================"

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
log_info "🔍 执行环境检查..."

echo "当前用户: $(whoami)"
echo "当前目录: $(pwd)"
echo "操作系统: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"

# 检查Python
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 未安装，请先安装Python 3.14+"
    exit 1
fi

PYTHON_VER=$(python3 --version | cut -d' ' -f2)
echo "Python版本: $PYTHON_VER"

# 检查磁盘空间
DISK_AVAILABLE=$(df -h . | tail -1 | awk '{print $4}')
echo "可用磁盘空间: $DISK_AVAILABLE"

# 2. 设置项目目录
PROJECT_ROOT="/home/scsun/hermesnexus"
log_info "📁 设置项目目录: $PROJECT_ROOT"

# 创建目录结构
mkdir -p "$PROJECT_ROOT"
cd "$PROJECT_ROOT"

mkdir -p {data,logs,backups,configs,venv}
mkdir -p logs/{cloud,edge,audit}
mkdir -p configs/{local,dev-server}

log_success "✅ 目录结构创建完成"

# 3. 创建核心代码文件 (如果不存在)
log_info "📦 创建核心代码文件..."

# 创建Cloud API主文件
mkdir -p cloud/api
cat > cloud/api/main.py << 'PYEOF'
"""HermesNexus Cloud Control Plane API"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import sqlite3
import json
from datetime import datetime, timezone
import os
import uvicorn

app = FastAPI(title="HermesNexus Cloud API", version="1.1.0")

# 数据库配置
DB_PATH = os.getenv("SQLITE_DB_PATH", "/home/scsun/hermesnexus/data/hermesnexus.db")

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str

class NodeInfo(BaseModel):
    node_id: str
    name: str
    status: str
    last_heartbeat: str

class TaskRequest(BaseModel):
    task_id: str
    node_id: str
    task_type: str
    target: Dict[str, Any]

# 初始化数据库
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nodes (
            node_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            last_heartbeat TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            node_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            target TEXT NOT NULL,
            status TEXT NOT NULL,
            result TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

# API端点
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="healthy",
        version="1.1.0",
        timestamp=datetime.now(timezone.utc).isoformat()
    )

@app.get("/api/v1/stats")
async def get_stats():
    """获取系统统计信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM nodes WHERE status = 'active'")
    active_nodes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks")
    total_tasks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
    pending_tasks = cursor.fetchone()[0]

    conn.close()

    return {
        "active_nodes": active_nodes,
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "system_status": "operational"
    }

@app.get("/api/v1/nodes")
async def list_nodes():
    """获取节点列表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT node_id, name, status, last_heartbeat FROM nodes")
    rows = cursor.fetchall()

    nodes = []
    for row in rows:
        nodes.append({
            "node_id": row[0],
            "name": row[1],
            "status": row[2],
            "last_heartbeat": row[3] or "Never"
        })

    conn.close()

    return {
        "total": len(nodes),
        "nodes": nodes
    }

@app.post("/api/v1/nodes/{node_id}/heartbeat")
async def node_heartbeat(node_id: str, heartbeat_data: Dict[str, Any]):
    """处理节点心跳"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    current_time = datetime.now(timezone.utc).isoformat()

    cursor.execute('''
        INSERT OR REPLACE INTO nodes (node_id, name, status, last_heartbeat, created_at)
        VALUES (?, ?, ?, ?, COALESCE((SELECT created_at FROM nodes WHERE node_id = ?), CURRENT_TIMESTAMP))
    ''', (node_id, heartbeat_data.get("name", node_id), "active", current_time, node_id))

    conn.commit()
    conn.close()

    return {"status": "success", "timestamp": current_time}

@app.post("/api/v1/tasks")
async def create_task(task: TaskRequest):
    """创建新任务"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    current_time = datetime.now(timezone.utc).isoformat()

    try:
        cursor.execute('''
            INSERT INTO tasks (task_id, node_id, task_type, target, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (task.task_id, task.node_id, task.task_type, json.dumps(task.target), "pending", current_time))

        conn.commit()
        conn.close()

        return {
            "task_id": task.task_id,
            "status": "pending",
            "created_at": current_time,
            "message": "Task created successfully"
        }
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Task ID already exists")

@app.get("/api/v1/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务详情"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT task_id, node_id, task_type, target, status, result, created_at FROM tasks WHERE task_id = ?", (task_id,))
    row = cursor.fetchone()

    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": row[0],
        "node_id": row[1],
        "task_type": row[2],
        "target": json.loads(row[3]),
        "status": row[4],
        "result": json.loads(row[5]) if row[5] else None,
        "created_at": row[6]
    }

@app.get("/api/v1/tasks")
async def list_tasks():
    """获取任务列表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT task_id, node_id, task_type, status, created_at FROM tasks ORDER BY created_at DESC LIMIT 50")
    rows = cursor.fetchall()

    tasks = []
    for row in rows:
        tasks.append({
            "task_id": row[0],
            "node_id": row[1],
            "task_type": row[2],
            "status": row[3],
            "created_at": row[4]
        })

    conn.close()

    return {
        "total": len(tasks),
        "tasks": tasks
    }

# 启动时初始化数据库
@app.on_event("startup")
async def startup_event():
    init_db()
    print("🚀 HermesNexus Cloud API started successfully")
    print(f"📊 Database: {DB_PATH}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
PYEOF

log_success "✅ Cloud API主文件创建完成"

# 4. 创建Python虚拟环境
log_info "🐍 创建Python虚拟环境..."
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    python3 -m venv "$PROJECT_ROOT/venv"
    log_success "✅ 虚拟环境创建完成"
else
    log_info "虚拟环境已存在"
fi

# 激活虚拟环境
source "$PROJECT_ROOT/venv/bin/activate"

# 5. 升级pip并安装依赖
log_info "📦 安装Python依赖包..."
pip install --upgrade pip -q

pip install -q \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    pydantic==2.5.0 \
    aiosqlite==0.19.0 \
    requests==2.31.0

log_success "✅ 依赖安装完成"

# 6. 创建配置文件
log_info "⚙️  创建配置文件..."

cat > "$PROJECT_ROOT/configs/dev-server/cloud.env" << 'EOF'
# HermesNexus Cloud服务配置
CLOUD_API_HOST=0.0.0.0
CLOUD_API_PORT=8080
LOG_LEVEL=INFO
LOG_DIR=/home/scsun/hermesnexus/logs/cloud
SQLITE_DB_PATH=/home/scsun/hermesnexus/data/hermesnexus.db
EOF

cat > "$PROJECT_ROOT/configs/dev-server/edge.env" << 'EOF'
# HermesNexus Edge节点配置
NODE_ID=dev-edge-node-001
NODE_NAME=开发服务器边缘节点
CLOUD_API_URL=http://localhost:8080
LOG_LEVEL=INFO
LOG_DIR=/home/scsun/hermesnexus/logs/edge
EOF

log_success "✅ 配置文件创建完成"

# 7. 设置环境变量
log_info "🌍 设置环境变量..."
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
export HERMES_HOME="$PROJECT_ROOT"

# 添加到.bashrc
if ! grep -q "HERMES_HOME" "$HOME/.bashrc"; then
    cat >> "$HOME/.bashrc" << 'EOF'

# HermesNexus环境变量
export HERMES_HOME="/home/scsun/hermesnexus"
export PYTHONPATH="/home/scsun/hermesnexus:$PYTHONPATH"
EOF
    log_success "✅ 环境变量已添加到.bashrc"
fi

# 8. 初始化数据库
log_info "🗄️  初始化数据库..."
source "$PROJECT_ROOT/venv/bin/activate"
python3 << 'PYDB'
import sqlite3
import os

db_path = "/home/scsun/hermesnexus/data/hermesnexus.db"
os.makedirs(os.path.dirname(db_path), exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 创建节点表
cursor.execute('''
    CREATE TABLE IF NOT EXISTS nodes (
        node_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        status TEXT NOT NULL,
        last_heartbeat TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
''')

# 创建任务表
cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        node_id TEXT NOT NULL,
        task_type TEXT NOT NULL,
        target TEXT NOT NULL,
        status TEXT NOT NULL,
        result TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
''')

# 创建示例节点
cursor.execute('''
    INSERT OR REPLACE INTO nodes (node_id, name, status, last_heartbeat)
    VALUES ('dev-edge-node-001', '开发服务器边缘节点', 'active', datetime('now'))
''')

conn.commit()
conn.close()
print("✅ 数据库初始化完成")
PYDB

log_success "✅ 数据库初始化完成"

# 9. 检查端口并启动服务
log_info "🚀 准备启动Cloud控制平面..."

# 检查端口占用
if netstat -tuln 2>/dev/null | grep -q ':8080.*LISTEN'; then
    log_warning "⚠️  端口8080已被占用"
    PORT_PROCESS=$(netstat -tuln 2>/dev/null | grep ':8080.*LISTEN' | awk '{print $7}' | cut -d'/' -f1)
    log_info "正在停止占用进程: $PORT_PROCESS"
    kill -9 $PORT_PROCESS 2>/dev/null || true
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

# 10. 等待服务就绪
log_info "⏳ 等待API服务就绪..."
sleep 5

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
    echo "查看启动日志:"
    cat "$PROJECT_ROOT/logs/cloud/startup.log"
    exit 1
fi

# 11. 执行健康检查和功能验证
log_info "🏥 执行系统健康检查..."

echo ""
echo "=== API健康检查 ==="
HEALTH=$(curl -s http://localhost:8080/health)
echo "$HEALTH" | head -3

echo ""
echo "=== 系统统计信息 ==="
STATS=$(curl -s http://localhost:8080/api/v1/stats)
echo "$STATS"

echo ""
echo "=== 节点状态 ==="
NODES=$(curl -s http://localhost:8080/api/v1/nodes)
echo "$NODES"

# 12. 创建测试任务
log_info "🧪 执行功能测试..."

# 创建测试任务
TEST_RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-deployment-001",
    "node_id": "dev-edge-node-001",
    "task_type": "system_test",
    "target": {"test": "deployment_verification"}
  }')

echo "测试任务创建响应:"
echo "$TEST_RESPONSE"

# 13. 最终状态报告
echo ""
echo "================================"
echo "🎉 HermesNexus 部署完成！"
echo "================================"
echo ""
echo "📊 服务状态:"
echo "  Cloud控制平面: 🟢 运行中 (PID: $CLOUD_PID)"
echo "  API端点: http://localhost:8080"
echo "  外部访问: http://172.16.100.101:8080"
echo ""
echo "📁 重要路径:"
echo "  项目根目录: $PROJECT_ROOT"
echo "  数据库文件: $PROJECT_ROOT/data/hermesnexus.db"
echo "  日志文件: $PROJECT_ROOT/logs/cloud/startup.log"
echo ""
echo "📋 管理命令:"
echo "  查看日志: tail -f $PROJECT_ROOT/logs/cloud/startup.log"
echo "  停止服务: kill $CLOUD_PID"
echo "  重启服务: cd $PROJECT_ROOT && python3 -m uvicorn cloud.api.main:app --host 0.0.0.0 --port 8080 &"
echo ""
echo "🧪 测试命令:"
echo "  健康检查: curl http://localhost:8080/health"
echo "  系统统计: curl http://localhost:8080/api/v1/stats"
echo "  节点列表: curl http://localhost:8080/api/v1/nodes"
echo "  任务列表: curl http://localhost:8080/api/v1/tasks"
echo ""
echo "✅ 部署成功！HermesNexus Cloud控制平面现已运行。"
echo "🌐 可以从外部访问: http://172.16.100.101:8080"