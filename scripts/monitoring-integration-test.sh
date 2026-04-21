#!/bin/bash
# HermesNexus v1.2.0 监控集成测试脚本

set -e

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 配置
CLOUD_API_URL="http://172.16.100.101:8082"
EDGE_NODE_URL="http://172.16.200.94:8081"
PROMETHEUS_URL="http://172.16.100.101:9090"
GRAFANA_URL="http://172.16.100.101:3000"

echo "=== HermesNexus v1.2.0 监控集成测试 ==="
echo ""

# 1. 测试Cloud API健康状态
log_info "测试Cloud API健康状态..."
health_response=$(curl -s "$CLOUD_API_URL/health")
if echo "$health_response" | grep -q "healthy"; then
    version=$(echo "$health_response" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    log_success "Cloud API健康 - 版本: $version"
else
    log_error "Cloud API不健康"
    exit 1
fi

# 2. 测试监控端点
log_info "测试监控端点..."
monitoring_health=$(curl -s "$CLOUD_API_URL/monitoring/health")
if echo "$monitoring_health" | grep -q "status"; then
    log_success "监控健康检查端点正常"
else
    log_error "监控健康检查端点失败"
fi

# 3. 测试Prometheus指标
log_info "测试Prometheus指标导出..."
prometheus_metrics=$(curl -s "$CLOUD_API_URL/monitoring/metrics")
if echo "$prometheus_metrics" | grep -q "hermes_system_cpu_percent"; then
    log_success "Prometheus指标导出正常"

    # 显示关键指标
    cpu_value=$(echo "$prometheus_metrics" | grep "hermes_system_cpu_percent" | tail -1 | awk '{print $2}')
    memory_value=$(echo "$prometheus_metrics" | grep "hermes_system_memory_percent" | tail -1 | awk '{print $2}')
    disk_value=$(echo "$prometheus_metrics" | grep "hermes_system_disk_percent" | tail -1 | awk '{print $2}')

    echo "  📊 当前指标:"
    echo "     CPU: ${cpu_value}%"
    echo "     内存: ${memory_value}%"
    echo "     磁盘: ${disk_value}%"
else
    log_error "Prometheus指标导出失败"
fi

# 4. 测试业务指标
log_info "测试业务指标..."
business_metrics=$(curl -s "$CLOUD_API_URL/api/nodes")
if echo "$business_metrics" | grep -q "nodes"; then
    node_count=$(echo "$business_metrics" | grep -o '"total":[0-9]*' | head -1 | cut -d':' -f2)
    log_success "节点管理API正常 - 总节点: $node_count"
else
    log_error "节点管理API失败"
fi

# 5. 测试Edge节点连接
log_info "测试Edge节点连接..."
edge_health=$(curl -s "$EDGE_NODE_URL/health")
if echo "$edge_health" | grep -q "healthy"; then
    log_success "Edge节点在线且健康"
else
    log_error "Edge节点不可访问"
fi

# 6. 测试Prometheus服务
log_info "测试Prometheus服务..."
if curl -s -f "$PROMETHEUS_URL/-/healthy" > /dev/null; then
    prometheus_health=$(curl -s "$PROMETHEUS_URL/-/healthy")
    if echo "$prometheus_health" | grep -q "Prometheus is Healthy"; then
        log_success "Prometheus服务正常"
    else
        log_warning "Prometheus响应异常"
    fi
else
    log_warning "Prometheus服务不可访问"
fi

# 7. 测试Grafana服务
log_info "测试Grafana服务..."
if curl -s -f "$GRAFANA_URL/api/health" > /dev/null; then
    grafana_health=$(curl -s "$GRAFANA_URL/api/health")
    if echo "$grafana_health" | grep -q "database"; then
        log_success "Grafana服务正常"
    else
        log_warning "Grafana响应异常"
    fi
else
    log_warning "Grafana服务不可访问"
fi

# 8. 测试指标数据
log_info "检查指标数据收集..."
if curl -s -f "$PROMETHEUS_URL/api/v1/query?query=hermes_system_cpu_percent" > /dev/null; then
    metrics_query=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=hermes_system_cpu_percent")
    if echo "$metrics_query" | grep -q "data"; then
        log_success "Prometheus指标查询正常"
    else
        log_warning "Prometheus指标查询无数据"
    fi
else
    log_warning "无法查询Prometheus指标"
fi

# 9. 系统集成测试
log_info "执行系统集成测试..."
test_timestamp=$(date +%s)

# 创建测试任务
task_response=$(curl -s -X POST "$CLOUD_API_URL/api/jobs" \
  -H "Content-Type: application/json" \
  -d "{
    \"job_id\": \"monitoring-test-$test_timestamp\",
    \"name\": \"监控集成测试任务\",
    \"job_type\": \"command\",
    \"target_node_id\": \"edge-test-001\",
    \"command\": \"echo 'HermesNexus monitoring test'\",
    \"created_by\": \"monitoring-test\"
  }")

if echo "$task_response" | grep -q "success"; then
    log_success "任务创建测试通过"

    # 验证任务在列表中
    sleep 1
    jobs_list=$(curl -s "$CLOUD_API_URL/api/jobs")
    if echo "$jobs_list" | grep -q "monitoring-test-$test_timestamp"; then
        log_success "任务列表查询正常"
    else
        log_warning "任务列表查询失败"
    fi
else
    log_error "任务创建测试失败"
fi

# 10. 最终状态总结
echo ""
echo "=== 监控集成测试总结 ==="

# 检查关键组件状态
components_status=()

# Cloud API
if curl -s -f "$CLOUD_API_URL/health" > /dev/null; then
    components_status+=("✅ Cloud API: 正常")
else
    components_status+=("❌ Cloud API: 异常")
fi

# Edge节点
if curl -s -f "$EDGE_NODE_URL/health" > /dev/null; then
    components_status+=("✅ Edge节点: 正常")
else
    components_status+=("❌ Edge节点: 异常")
fi

# Prometheus
if curl -s -f "$PROMETHEUS_URL/-/healthy" > /dev/null; then
    components_status+=("✅ Prometheus: 正常")
else
    components_status+=("❌ Prometheus: 异常")
fi

# Grafana
if curl -s -f "$GRAFANA_URL/api/health" > /dev/null; then
    components_status+=("✅ Grafana: 正常")
else
    components_status+=("❌ Grafana: 异常")
fi

# 显示状态
for status in "${components_status[@]}"; do
    echo "  $status"
done

# 计算成功率
total=${#components_status[@]}
success_count=$(echo "${components_status[@]}" | grep -o "✅" | wc -l)
success_rate=$((success_count * 100 / total))

echo ""
if [ $success_rate -eq 100 ]; then
    log_success "所有组件状态正常 - 监控集成完成！"
    echo ""
    echo "🎯 访问地址:"
    echo "  📊 Cloud API: $CLOUD_API_URL"
    echo "  📈 Prometheus: $PROMETHEUS_URL"
    echo "  📋 Grafana: $GRAFANA_URL (admin/admin)"
    echo "  💚 Edge节点: $EDGE_NODE_URL"
    echo ""
    echo "📚 重要端点:"
    echo "  健康检查: $CLOUD_API_URL/health"
    echo "  监控指标: $CLOUD_API_URL/monitoring/metrics"
    echo "  系统状态: $CLOUD_API_URL/monitoring/status"
    echo "  节点管理: $CLOUD_API_URL/api/nodes"
elif [ $success_rate -ge 75 ]; then
    log_warning "大部分组件正常 - 部分功能可能受限"
else
    log_error "关键组件异常 - 需要立即处理"
fi

echo ""
echo "🔧 故障排查建议:"
echo "  1. 检查服务日志: tail -f /home/scsun/hermesnexus-logs/*.log"
echo "  2. 查看进程状态: ps aux | grep hermes"
echo "  3. 测试网络连接: curl -v http://localhost:8082/health"
echo "  4. 查看Prometheus目标: $PROMETHEUS_URL/targets"
echo "  5. 访问Grafana仪表板: $GRAFANA_URL"
echo ""

exit 0