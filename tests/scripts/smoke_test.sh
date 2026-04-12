#!/usr/bin/env bash
#
# HermesNexus Phase 2 Smoke Test Script
# 烟测试脚本 - 验证系统基本功能
#

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
API_BASE="${CLOUD_API_URL:-http://localhost:8080}"
SMOKE_TEST_LOG="smoke_test_$(date +%Y%m%d_%H%M%S).log"

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$SMOKE_TEST_LOG"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$SMOKE_TEST_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$SMOKE_TEST_LOG"
}

log_test() {
    echo -e "${BLUE}[TEST]${NC} $1" | tee -a "$SMOKE_TEST_LOG"
}

# 结果统计
PASSED=0
FAILED=0

# 测试结果记录
test_result() {
    local test_name="$1"
    local result="$2"
    local message="$3"

    if [ "$result" = "PASS" ]; then
        log_info "✓ $test_name: $message"
        PASSED=$((PASSED + 1))
    else
        log_error "✗ $test_name: $message"
        FAILED=$((FAILED + 1))
    fi
}

# API 请求函数
api_request() {
    local endpoint="$1"
    local method="${2:-GET}"
    local data="$3"

    if [ -n "$data" ]; then
        curl -s -X "$method" "$API_BASE$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" "$API_BASE$endpoint"
    fi
}

echo "========================================"
echo "  HermesNexus Phase 2 Smoke Test"
echo "========================================"
echo "API Base: $API_BASE"
echo "Log File: $SMOKE_TEST_LOG"
echo "Started: $(date)"
echo ""

# ===== 1. 系统健康检查 =====
log_test "1. 系统健康检查"
HEALTH_RESPONSE=$(api_request "/health")
if echo "$HEALTH_RESPONSE" | grep -q "healthy\|status.*ok"; then
    test_result "健康检查" "PASS" "系统健康"
else
    test_result "健康检查" "FAIL" "系统不健康: $HEALTH_RESPONSE"
fi

# ===== 2. 资产管理功能 =====
log_test "2. 资产管理功能"

# 2.1 创建资产
log_info "创建测试资产..."
ASSET_RESPONSE=$(api_request "/api/v1/assets" "POST" '{
    "name": "Smoke测试资产",
    "asset_type": "linux_host",
    "description": "自动化测试资产",
    "metadata": {
        "ip_address": "192.168.1.100",
        "hostname": "smoke-test.local",
        "tags": ["smoke", "test"]
    }
}')

ASSET_ID=$(echo "$ASSET_RESPONSE" | grep -o '"asset_id":"[^"]*"' | cut -d'"' -f4)
if [ -n "$ASSET_ID" ]; then
    test_result "资产创建" "PASS" "资产ID: $ASSET_ID"
else
    test_result "资产创建" "FAIL" "无法创建资产"
fi

# 2.2 查询资产列表
log_info "查询资产列表..."
ASSETS_LIST=$(api_request "/api/v1/assets?limit=10")
if echo "$ASSETS_LIST" | grep -q '"assets"'; then
    test_result "资产列表" "PASS" "可以获取资产列表"
else
    test_result "资产列表" "FAIL" "无法获取资产列表"
fi

# 2.3 获取资产统计
log_info "获取资产统计..."
ASSETS_STATS=$(api_request "/api/v1/assets/stats")
if echo "$ASSETS_STATS" | grep -q '"total_assets"'; then
    test_result "资产统计" "PASS" "可以获取资产统计"
else
    test_result "资产统计" "FAIL" "无法获取资产统计"
fi

# ===== 3. 任务管理功能 =====
log_test "3. 任务管理功能"

# 3.1 创建任务
log_info "创建测试任务..."
TASK_RESPONSE=$(api_request "/api/v1/tasks" "POST" "{
    \"name\": \"Smoke测试任务\",
    \"task_type\": \"basic_exec\",
    \"priority\": \"normal\",
    \"target_asset_id\": \"$ASSET_ID\",
    \"command\": \"echo 'Smoke Test'\",
    \"timeout\": 30,
    \"description\": \"自动化测试任务\"
}")

TASK_ID=$(echo "$TASK_RESPONSE" | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)
if [ -n "$TASK_ID" ]; then
    test_result "任务创建" "PASS" "任务ID: $TASK_ID"
else
    test_result "任务创建" "FAIL" "无法创建任务"
fi

# 3.2 查询任务列表
log_info "查询任务列表..."
TASKS_LIST=$(api_request "/api/v1/tasks?limit=10")
if echo "$TASKS_LIST" | grep -q '"tasks"'; then
    test_result "任务列表" "PASS" "可以获取任务列表"
else
    test_result "任务列表" "FAIL" "无法获取任务列表"
fi

# 3.3 获取任务统计
log_info "获取任务统计..."
TASKS_STATS=$(api_request "/api/v1/tasks/stats")
if echo "$TASKS_STATS" | grep -q '"total_tasks"'; then
    test_result "任务统计" "PASS" "可以获取任务统计"
else
    test_result "任务统计" "FAIL" "无法获取任务统计"
fi

# ===== 4. 审计日志功能 =====
log_test "4. 审计日志功能"

# 4.1 查询审计日志
log_info "查询审计日志..."
AUDIT_LOGS=$(api_request "/api/v1/audit_logs?limit=10")
if echo "$AUDIT_LOGS" | grep -q '"audit_logs"'; then
    test_result "审计日志查询" "PASS" "可以获取审计日志"
else
    test_result "审计日志查询" "FAIL" "无法获取审计日志"
fi

# 4.2 获取审计统计
log_info "获取审计统计..."
AUDIT_STATS=$(api_request "/api/v1/audit_logs/stats")
if echo "$AUDIT_STATS" | grep -q '"total_events"'; then
    test_result "审计统计" "PASS" "可以获取审计统计"
else
    test_result "审计统计" "FAIL" "无法获取审计统计"
fi

# ===== 5. 控制台页面 =====
log_test "5. 控制台页面可访问性"

CONSOLE_PAGES=(
    "/console/index.html"
    "/console/assets.html"
    "/console/tasks.html"
    "/console/audit.html"
    "/console/nodes.html"
)

for page in "${CONSOLE_PAGES[@]}"; do
    PAGE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE$page")
    if [ "$PAGE_STATUS" = "200" ]; then
        test_result "控制台页面 $page" "PASS" "页面可访问"
    else
        test_result "控制台页面 $page" "FAIL" "HTTP $PAGE_STATUS"
    fi
done

# ===== 6. API 响应时间 =====
log_test "6. API 响应性能"

log_info "测试API响应时间..."
START_TIME=$(date +%s%3N)
api_request "/health"
END_TIME=$(date +%s%3N)
RESPONSE_TIME=$((END_TIME - START_TIME))

if [ $RESPONSE_TIME -lt 1000 ]; then
    test_result "API响应时间" "PASS" "${RESPONSE_TIME}ms (<1000ms)"
else
    test_result "API响应时间" "FAIL" "${RESPONSE_TIME}ms (>=1000ms)"
fi

# ===== 7. 数据一致性 =====
log_test "7. 数据一致性"

log_info "验证创建的资产和任务是否可查询..."

VERIFY_ASSET=$(api_request "/api/v1/assets/$ASSET_ID")
if echo "$VERIFY_ASSET" | grep -q '"asset_id":"'$ASSET_ID'"'; then
    test_result "资产查询一致性" "PASS" "创建的资产可以查询到"
else
    test_result "资产查询一致性" "FAIL" "创建的资产无法查询到"
fi

VERIFY_TASK=$(api_request "/api/v1/tasks/$TASK_ID")
if echo "$VERIFY_TASK" | grep -q '"task_id":"'$TASK_ID'"'; then
    test_result "任务查询一致性" "PASS" "创建的任务可以查询到"
else
    test_result "任务查询一致性" "FAIL" "创建的任务无法查询到"
fi

# ===== 8. 错误处理 =====
log_test "8. 错误处理"

log_info "测试错误响应..."

# 测试404错误
NOT_FOUND_RESPONSE=$(api_request "/api/v1/assets/nonexistent-id")
if echo "$NOT_FOUND_RESPONSE" | grep -q "not_found\|404"; then
    test_result "404错误处理" "PASS" "正确的404响应"
else
    test_result "404错误处理" "FAIL" "错误响应不正确"
fi

# ===== 9. 清理测试数据 =====
log_test "9. 清理测试数据"

if [ -n "$TASK_ID" ]; then
    log_info "取消测试任务..."
    CANCEL_RESPONSE=$(api_request "/api/v1/tasks/$TASK_ID/cancel" "POST")
    if echo "$CANCEL_RESPONSE" | grep -q "cancelled"; then
        test_result "任务清理" "PASS" "测试任务已取消"
    else
        log_warn "测试任务取消失败: $CANCEL_RESPONSE"
    fi
fi

if [ -n "$ASSET_ID" ]; then
    log_info "删除测试资产..."
    DELETE_RESPONSE=$(api_request "/api/v1/assets/$ASSET_ID" "DELETE" "")
    if [ $? -eq 0 ]; then
        test_result "资产清理" "PASS" "测试资产已删除"
    else
        log_warn "测试资产删除失败"
    fi
fi

# ===== 测试总结 =====
echo ""
echo "========================================"
echo "  Smoke Test Summary"
echo "========================================"
echo "Total Tests: $((PASSED + FAILED))"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "Completed: $(date)"
echo "Log File: $SMOKE_TEST_LOG"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All smoke tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some smoke tests failed!${NC}"
    exit 1
fi
