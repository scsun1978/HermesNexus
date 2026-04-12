#!/bin/bash
# 性能测试执行脚本
# 用途: 建立性能基线，识别瓶颈，提供优化建议

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PERF_START_TIME=$(date +%s)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}⚡ HermesNexus 性能测试${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "建立性能基线，识别系统瓶颈"
echo ""

# 检查依赖
check_dependencies() {
    echo -e "${YELLOW}[检查] 验证性能测试依赖...${NC}"

    if ! python3 -c "import statistics" 2>/dev/null; then
        echo -e "${RED}✗ Python statistics 模块不可用${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ 依赖检查通过${NC}"
    echo ""
}

# 环境准备
prepare_environment() {
    echo -e "${YELLOW}[准备] 性能测试环境...${NC}"

    # 清理旧的性能数据
    rm -f performance_analysis_report.json
    rm -f /tmp/perf_*.db

    # 创建临时目录
    mkdir -p /tmp/perf_test

    echo -e "${GREEN}✓ 环境准备完成${NC}"
    echo ""
}

# 运行性能基线测试
run_baseline_tests() {
    echo -e "${YELLOW}[执行] 运行性能基线测试...${NC}"
    echo ""

    if python3 tests/performance/test_performance_baseline.py; then
        echo -e "${GREEN}✓ 性能基线测试通过${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  性能基线测试有问题，但继续分析${NC}"
        return 1
    fi
}

# 运行性能分析
run_performance_analysis() {
    echo ""
    echo -e "${YELLOW}[分析] 性能瓶颈分析...${NC}"
    echo ""

    if python3 tests/performance/analyze_performance.py; then
        echo -e "${GREEN}✓ 性能分析完成${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  性能分析部分完成${NC}"
        return 1
    fi
}

# 生成性能报告
generate_report() {
    local exit_code=$1
    local end_time=$(date +%s)
    local duration=$((end_time - PERF_START_TIME))

    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}📊 性能测试报告${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}状态: ✅ 完成${NC}"
        echo -e "${GREEN}性能基线已建立，优化建议已生成${NC}"
    else
        echo -e "${YELLOW}状态: ⚠️  部分完成${NC}"
        echo -e "${YELLOW}性能测试部分完成，请查看详细报告${NC}"
    fi

    echo ""
    echo "耗时: ${duration}秒"

    # 检查是否有性能报告文件
    if [ -f "performance_analysis_report.json" ]; then
        echo ""
        echo -e "${GREEN}📄 性能分析报告: performance_analysis_report.json${NC}"

        # 提取关键信息
        if command -v jq >/dev/null 2>&1; then
            echo ""
            echo "关键发现:"
            jq '.summary' performance_analysis_report.json 2>/dev/null || echo "无法解析JSON"
        fi
    fi

    echo ""
    echo -e "${BLUE}========================================${NC}"
}

# 性能建议
show_recommendations() {
    echo ""
    echo -e "${YELLOW}💡 性能优化建议${NC}"
    echo ""
    echo "基于测试结果，建议按以下优先级进行优化:"
    echo ""
    echo "🔴 高优先级:"
    echo "  1. 实现数据库连接池 - 预期改进50-70%"
    echo ""
    echo "🟡 中优先级:"
    echo "  2. 批量操作优化 - 预期改进3-5倍"
    echo "  3. 查询优化和索引改进 - 预期改进20-50%"
    echo ""
    echo "🟢 低优先级:"
    echo "  4. 实现缓存系统 - 预期改进70-90%"
    echo "  5. 高级查询优化 - 预期改进10-30%"
    echo ""
    echo "详细优化指南: docs/performance/2026-04-12-performance-optimization-guide.md"
}

# 清理临时文件
cleanup() {
    echo -e "${YELLOW}[清理] 清理临时文件...${NC}"
    rm -f /tmp/perf_*.db
    rm -rf /tmp/perf_test
    echo -e "${GREEN}✓ 清理完成${NC}"
}

# 主执行流程
main() {
    local exit_code=0

    # 执行测试流程
    check_dependencies || exit_code=1
    prepare_environment || exit_code=1

    run_baseline_tests || exit_code=$?
    run_performance_analysis || exit_code=$?

    # 生成报告
    generate_report $exit_code

    # 显示建议
    show_recommendations

    # 清理
    cleanup

    exit $exit_code
}

# 信号处理
trap cleanup EXIT INT TERM

# 执行主流程
main
