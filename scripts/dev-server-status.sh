#!/bin/bash
# HermesNexus 开发服务器状态检查脚本
# 检查所有服务的运行状态和健康情况

echo "🔍 HermesNexus 开发服务器状态检查"
echo "================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✅]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠️]${NC} $1"; }
log_error() { echo -e "${RED}[❌]${NC} $1"; }

PROJECT_ROOT="/home/scsun/hermesnexus"

# 1. 系统服务状态
echo ""
echo "📊 系统服务状态:"
echo "-------------------"

echo -n "Cloud控制平面: "
if systemctl is-active --quiet hermesnexus-cloud; then
    STATUS=$(systemctl status hermesnexus-cloud | grep "Active:" | awk '{print $2}')
    UPTIME=$(systemctl status hermesnexus-cloud | grep "active (running)" | awk '{print $4}' || echo "未知")
    echo -e "${GREEN}🟢 运行中${NC} (状态: $STATUS, 运行时间: $UPTIME)"
else
    echo -e "${RED}🔴 停止${NC}"
fi

echo -n "Edge边缘节点: "
if systemctl is-active --quiet hermesnexus-edge; then
    STATUS=$(systemctl status hermesnexus-edge | grep "Active:" | awk '{print $2}')
    UPTIME=$(systemctl status hermesnexus-edge | grep "active (running)" | awk '{print $4}' || echo "未知")
    echo -e "${GREEN}🟢 运行中${NC} (状态: $STATUS, 运行时间: $UPTIME)"
else
    echo -e "${RED}🔴 停止${NC}"
fi

# 2. 端口监听状态
echo ""
echo "🌐 网络端口状态:"
echo "-------------"

echo -n "API端口8080: "
if netstat -tuln 2>/dev/null | grep -q ':8080.*LISTEN'; then
    PROCESS=$(netstat -tuln 2>/dev/null | grep ':8080.*LISTEN' | awk '{print $7}' | cut -d'/' -f1)
    echo -e "${GREEN}✅ 正常监听${NC} (进程: $PROCESS)"
else
    echo -e "${RED}❌ 未监听${NC}"
fi

# 3. API健康检查
echo ""
echo "🏥 API健康状态:"
echo "-------------"

if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    HEALTH=$(curl -s http://localhost:8080/health)
    VERSION=$(echo "$HEALTH" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    echo -e "${GREEN}✅ 服务健康${NC} (版本: $VERSION)"

    # 测试主要端点
    echo ""
    echo "API端点测试:"

    # 节点统计
    NODES=$(curl -s http://localhost:8080/api/v1/nodes)
    TOTAL_NODES=$(echo "$NODES" | grep -o '"total":[0-9]*' | cut -d':' -f2)
    echo -n "  节点数量: $TOTAL_NODES 个"
    if [ "$TOTAL_NODES" -gt 0 ]; then
        echo -e " ${GREEN}✅${NC}"
    else
        echo " (暂无节点注册)"
    fi

    # 任务统计
    JOBS=$(curl -s http://localhost:8080/api/v1/jobs)
    TOTAL_JOBS=$(echo "$JOBS" | grep -o '"total":[0-9]*' | cut -d':' -f2)
    echo -n "  任务数量: $TOTAL_JOBS 个"
    if [ "$TOTAL_JOBS" -gt 0 ]; then
        echo -e "${GREEN}✅${NC}"
    else
        echo " (暂无任务创建)"
    fi

    # 事件统计
    EVENTS=$(curl -s http://localhost:8080/api/v1/events)
    TOTAL_EVENTS=$(echo "$EVENTS" | grep -o '"total":[0-9]*' | cut -d':' -f2)
    echo "  事件数量: $TOTAL_EVENTS 个"

else
    echo -e "${RED}❌ API服务不可达${NC}"
fi

# 4. 数据库状态
echo ""
echo "🗄️  数据库状态:"
echo "-------------"

DB_PATH="$PROJECT_ROOT/data/hermesnexus.db"
if [ -f "$DB_PATH" ]; then
    DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
    DB_MOD_TIME=$(stat -f "$DB_PATH" -c %y)
    echo -e "${GREEN}✅ 数据库正常${NC} (大小: $DB_SIZE, 修改时间: $DB_MOD_TIME)"

    # 检查数据库完整性
    if command -v sqlite3 &> /dev/null; then
        if sqlite3 "$DB_PATH" "PRAGMA integrity_check" 2>/dev/null | grep -q "ok"; then
            echo "  数据库完整性: ${GREEN}✅ 通过${NC}"
        else
            echo "  数据库完整性: ${YELLOW}⚠️  无法验证${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠️  数据库文件不存在${NC}"
fi

# 5. 日志文件状态
echo ""
echo "📝 日志文件状态:"
echo "---------------"

LOG_DIR="$PROJECT_ROOT/logs"
if [ -d "$LOG_DIR" ]; then
    CLOUD_LOGS=$(find "$LOG_DIR/cloud" -name "*.log" 2>/dev/null | wc -l)
    EDGE_LOGS=$(find "$LOG_DIR/edge" -name "*.log" 2>/dev/null | wc -l)
    AUDIT_LOGS=$(find "$LOG_DIR/audit" -name "*.log" 2>/dev/null | wc -l)

    echo "  Cloud日志: $CLOUD_LOGS 个文件"
    echo "  Edge日志: $EDGE_LOGS 个文件"
    echo "  审计日志: $AUDIT_LOGS 个文件"

    # 检查最新日志
    LATEST_CLOUD=$(find "$LOG_DIR/cloud" -name "*.log" -type f -exec ls -t {} + | head -1 2>/dev/null)
    if [ -n "$LATEST_CLOUD" ]; then
        LATEST_TIME=$(stat -f "$LATEST_CLOUD" -c %y 2>/dev/null)
        echo "  最新Cloud日志: $(basename "$LATEST_CLOUD") ($LATEST_TIME)"
    fi

    TOTAL_SIZE=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)
    echo "  日志总大小: $TOTAL_SIZE"
else
    echo "  ${YELLOW}日志目录不存在${NC}"
fi

# 6. 系统资源使用
echo ""
echo "💻 系统资源使用:"
echo "---------------"

if command -v python3 &> /dev/null; then
    python3 << 'EOF'
import psutil
import json

cpu_percent = psutil.cpu_percent(interval=1)
memory = psutil.virtual_memory()
disk = psutil.disk_usage('/')

print(f"  CPU使用: {cpu_percent:.1f}%")
print(f"  内存使用: {memory.percent:.1f}% ({memory.used / 1024 / 1024 / 1024:.1f}GB / {memory.total / 1024 / 1024 / 1024:.1f}GB)")
print(f"  磁盘使用: {disk.percent:.1f}% ({disk.used / 1024 / 1024 / 1024 / 1024:.1f}GB / {disk.total / 1024 / 1024 / 1024:.1f}GB)")

if cpu_percent > 80:
    print("  ⚠️  CPU使用率较高")
if memory.percent > 80:
    print("  ⚠️  内存使用率较高")
if disk.percent > 80:
    print("  ⚠️  磁盘使用率较高")
EOF
else
    echo "  系统资源信息不可用"
fi

# 7. 总体健康评估
echo ""
echo "🏥 总体健康评估:"
echo "---------------"

HEALTHY=true

# 检查服务状态
if ! systemctl is-active --quiet hermesnexus-cloud; then
    echo -e "${RED}❌ Cloud控制平面未运行${NC}"
    HEALTHY=false
fi

# 检查API健康
if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${RED}❌ API服务不可达${NC}"
    HEALTHY=false
fi

# 检查数据库
if [ ! -f "$PROJECT_ROOT/data/hermesnexus.db" ]; then
    echo -e "${YELLOW}⚠️  数据库文件不存在${NC}"
fi

if [ "$HEALTHY" = true ]; then
    echo -e "${GREEN}🟢 系统运行正常${NC}"
else
    echo -e "${YELLOW}🟡 系统存在问题需要关注${NC}"
fi

echo ""
echo "================================"
echo "✅ 状态检查完成"
echo "================================"