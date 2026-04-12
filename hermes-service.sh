#!/bin/bash
# HermesNexus 服务管理脚本

PROJECT_ROOT="/home/scsun/hermesnexus"
API_SCRIPT="$PROJECT_ROOT/simple-cloud-api.py"
LOG_FILE="$PROJECT_ROOT/logs/cloud-api.log"
PID_FILE="$PROJECT_ROOT/cloud.pid"

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

case "$1" in
    start)
        log_info "启动 HermesNexus 服务..."
        cd "$PROJECT_ROOT"
        mkdir -p logs data

        # 检查是否已运行
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p "$PID" > /dev/null 2>&1; then
                log_warning "服务已在运行 (PID: $PID)"
                exit 0
            else
                rm -f "$PID_FILE"
            fi
        fi

        # 启动服务
        nohup python3 "$API_SCRIPT" > "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"

        sleep 2

        # 验证启动
        if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
            log_success "✅ 服务启动成功 (PID: $(cat $PID_FILE))"
            log_info "访问地址: http://172.16.100.101:8080"
        else
            log_error "❌ 服务启动失败"
            cat "$LOG_FILE"
            exit 1
        fi
        ;;

    stop)
        log_info "停止 HermesNexus 服务..."

        if [ ! -f "$PID_FILE" ]; then
            log_warning "服务未运行"
            exit 0
        fi

        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID"
            sleep 2
            if ps -p "$PID" > /dev/null 2>&1; then
                log_warning "强制停止服务..."
                kill -9 "$PID"
            fi
            log_success "✅ 服务已停止"
        else
            log_warning "服务进程不存在"
        fi

        rm -f "$PID_FILE"
        ;;

    restart)
        log_info "重启 HermesNexus 服务..."
        $0 stop
        sleep 2
        $0 start
        ;;

    status)
        log_info "HermesNexus 服务状态:"

        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "状态: 🟢 运行中"
                echo "进程ID: $PID"
                echo "启动时间: $(ps -p $PID -o lstart=)"
                echo "内存使用: $(ps -p $PID -o rss= | awk '{print $1/1024 "MB"}')"
                echo "CPU使用: $(ps -p $PID -o %cpu=)%"

                # API健康检查
                if curl -s http://localhost:8080/health > /dev/null 2>&1; then
                    echo "API状态: ✅ 正常"
                    echo "访问地址: http://172.16.100.101:8080"
                else
                    echo "API状态: ⚠️  异常"
                fi
            else
                echo "状态: 🔴 已停止 (PID文件存在但进程不存在)"
                rm -f "$PID_FILE"
            fi
        else
            echo "状态: 🔴 已停止"
        fi

        # 端口检查
        if netstat -tulpn 2>/dev/null | grep -q ':8080.*LISTEN'; then
            echo "端口8080: ✅ 监听中"
        else
            echo "端口8080: ❌ 未监听"
        fi
        ;;

    health)
        log_info "执行健康检查..."

        echo "=== API健康检查 ==="
        curl -s http://localhost:8080/health | jq '.' || echo "❌ API不可达"

        echo ""
        echo "=== 系统统计 ==="
        curl -s http://localhost:8080/api/v1/stats | jq '.' || echo "❌ 统计API不可达"

        echo ""
        echo "=== 节点状态 ==="
        curl -s http://localhost:8080/api/v1/nodes | jq '.' || echo "❌ 节点API不可达"

        echo ""
        echo "=== 最近任务 ==="
        curl -s http://localhost:8080/api/v1/tasks | jq '.tasks[:3]' || echo "❌ 任务API不可达"
        ;;

    logs)
        log_info "显示最近日志..."
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        else
            log_error "日志文件不存在: $LOG_FILE"
        fi
        ;;

    test)
        log_info "执行API功能测试..."

        echo "1. 健康检查..."
        curl -s http://localhost:8080/health && echo " ✅" || echo " ❌"

        echo "2. 创建测试任务..."
        curl -s -X POST http://localhost:8080/api/v1/tasks \
          -H "Content-Type: application/json" \
          -d '{"task_id":"test-'$(date +%s)'","node_id":"dev-edge-node-001","task_type":"test","target":{"test":true}}' && echo " ✅" || echo " ❌"

        echo "3. 查询任务列表..."
        curl -s http://localhost:8080/api/v1/tasks | jq '.total' && echo " ✅" || echo " ❌"

        log_success "✅ 功能测试完成"
        ;;

    *)
        echo "HermesNexus 服务管理脚本"
        echo ""
        echo "用法: $0 {start|stop|restart|status|health|logs|test}"
        echo ""
        echo "命令说明:"
        echo "  start   - 启动服务"
        echo "  stop    - 停止服务"
        echo "  restart - 重启服务"
        echo "  status  - 查看服务状态"
        echo "  health  - 执行健康检查"
        echo "  logs    - 查看实时日志"
        echo "  test    - 执行API功能测试"
        echo ""
        echo "API访问地址:"
        echo "  本地: http://localhost:8080"
        echo "  外部: http://172.16.100.101:8080"
        ;;
esac