#!/bin/bash
# E2E Tests 执行脚本
# 用途: 执行端到端测试，提供详细的诊断信息

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

E2E_START_TIME=$(date +%s)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🎯 HermesNexus E2E Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "端到端测试 - 验证完整业务流程"
echo ""

# 检查是否运行了Smoke测试
check_smoke_tests() {
    echo -e "${YELLOW}[检查] 验证Smoke测试状态...${NC}"

    # 检查是否有最近的Smoke测试通过记录
    if [ -f ".smoke_test_passed" ]; then
        smoke_time=$(stat -c %Y .smoke_test_passed 2>/dev/null || stat -f %m .smoke_test_passed)
        current_time=$(date +%s)
        time_diff=$((current_time - smoke_time))

        if [ $time_diff -lt 3600 ]; then
            echo -e "${GREEN}✓ Smoke测试最近通过 (${time_diff}秒前)${NC}"
        else
            echo -e "${YELLOW}⚠️  Smoke测试通过时间较久，建议重新运行${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  未找到Smoke测试通过记录${NC}"
        echo "建议先运行: ./tests/e2e/run_smoke_tests.sh"
        read -p "是否继续E2E测试? (y/N): " choice
        if [ "$choice" != "y" ] && [ "$choice" != "Y" ]; then
            echo "已取消E2E测试"
            exit 0
        fi
    fi
    echo ""
}

# 运行E2E测试
run_e2e_tests() {
    echo -e "${YELLOW}[执行] 运行E2E测试...${NC}"
    echo ""

    local exit_code=0

    # 运行标准E2E测试
    if [ -f "tests/e2e/test_complete_workflow.py" ]; then
        echo "运行完整工作流测试..."
        if ! python3 -m pytest tests/e2e/test_complete_workflow.py -v --tb=short; then
            echo -e "${YELLOW}⚠️  完整工作流测试有问题${NC}"
            exit_code=1
        fi
    fi

    # 运行增强E2E测试
    if [ -f "tests/e2e/test_enhanced_e2e.py" ]; then
        echo "运行增强E2E测试..."
        if ! python3 -m pytest tests/e2e/test_enhanced_e2e.py -v --tb=short; then
            echo -e "${RED}✗ 增强E2E测试失败${NC}"
            exit_code=1
        fi
    fi

    return $exit_code
}

# 失败诊断
diagnose_failures() {
    echo ""
    echo -e "${YELLOW}[诊断] 分析测试失败...${NC}"

    # 检查临时文件
    if ls /tmp/e2e_test_* 2>/dev/null; then
        echo -e "${YELLOW}发现临时测试文件，可能包含诊断信息:${NC}"
        ls -lh /tmp/e2e_test_*
        echo ""
        echo "临时文件将保留用于诊断，请手动清理"
    else
        echo -e "${GREEN}✓ 没有发现临时文件残留${NC}"
    fi

    # 检查数据库文件
    if find /tmp -name "e2e_*.db" -mtime -1 2>/dev/null | head -1; then
        echo -e "${YELLOW}发现临时数据库文件${NC}"
    fi

    echo ""
}

# 生成测试报告
generate_report() {
    local exit_code=$1
    local end_time=$(date +%s)
    local duration=$((end_time - E2E_START_TIME))

    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}📊 E2E Tests 报告${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}状态: ✅ 通过${NC}"
        echo -e "${GREEN}所有E2E测试通过，系统端到端流程正常${NC}"

        # 记录测试通过时间
        touch .e2e_test_passed
    else
        echo -e "${RED}状态: ❌ 失败${NC}"
        echo -e "${RED}E2E测试失败，请查看详细诊断信息${NC}"
    fi

    echo ""
    echo "耗时: ${duration}秒"

    # 性能检查
    if [ $duration -gt 600 ]; then
        echo -e "${YELLOW}⚠️  警告: E2E测试耗时超过10分钟${NC}"
    else
        echo -e "${GREEN}✓ 耗时正常${NC}"
    fi

    echo ""
    echo -e "${BLUE}========================================${NC}"
}

# 主执行流程
main() {
    local exit_code=0

    # 检查Smoke测试状态
    check_smoke_tests

    # 运行E2E测试
    run_e2e_tests || exit_code=$?

    # 失败诊断
    if [ $exit_code -ne 0 ]; then
        diagnose_failures
    fi

    # 生成报告
    generate_report $exit_code

    exit $exit_code
}

# 信号处理
trap 'echo -e "\n${RED}测试被中断${NC}"; exit 1' INT TERM

# 执行主流程
main
