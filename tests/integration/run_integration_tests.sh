#!/bin/bash
# 集成测试执行脚本

echo "================================"
echo "HermesNexus 集成测试执行"
echo "================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 运行测试函数
run_test() {
    local test_file=$1
    local test_name=$2

    echo "运行测试: $test_name"
    echo "文件: $test_file"
    echo "----------------------------------------"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    # 运行测试并捕获结果
    if python3 -m pytest "$test_file" -v --tb=short; then
        echo -e "${GREEN}✓ $test_name 通过${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ $test_name 失败${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi

    echo ""
}

# 检查依赖
check_dependencies() {
    echo "检查测试依赖..."
    if ! python3 -c "import pytest" 2>/dev/null; then
        echo -e "${YELLOW}警告: pytest 未安装，尝试安装...${NC}"
        pip3 install pytest --user
    fi

    if ! python3 -c "import sqlalchemy" 2>/dev/null; then
        echo -e "${RED}错误: sqlalchemy 未安装${NC}"
        echo "请运行: pip3 install sqlalchemy"
        exit 1
    fi

    echo "依赖检查完成"
    echo ""
}

# 主测试流程
main() {
    check_dependencies

    echo "开始执行集成测试..."
    echo ""

    # 资产/任务/审计主线集成测试
    run_test \
        "tests/integration/test_asset_task_audit_integration.py" \
        "资产/任务/审计主线集成测试"

    # 认证链路集成测试
    run_test \
        "tests/integration/test_auth_integration.py" \
        "认证链路集成测试"

    # 数据隔离测试
    run_test \
        "tests/integration/test_data_isolation.py" \
        "测试数据隔离和清理"

    # 云边链路集成测试 (如果存在且可运行)
    if [ -f "tests/integration/test_cloud_edge_integration.py" ]; then
        echo -e "${YELLOW}注意: 云边链路集成测试需要边缘节点环境${NC}"
        echo "跳过云边链路集成测试"
        echo ""
    fi

    # 输出测试总结
    echo "================================"
    echo "集成测试执行总结"
    echo "================================"
    echo "总测试数: $TOTAL_TESTS"
    echo -e "${GREEN}通过: $PASSED_TESTS${NC}"
    echo -e "${RED}失败: $FAILED_TESTS${NC}"
    echo ""

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}🎉 所有集成测试通过！${NC}"
        exit 0
    else
        echo -e "${RED}❌ 有 $FAILED_TESTS 个测试失败${NC}"
        exit 1
    fi
}

# 执行主流程
main
