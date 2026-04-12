#!/bin/bash

# HermesNexus Phase 2 - Week 2 Test Runner
# Week 2 测试运行脚本

set -e

echo "====================================="
echo "HermesNexus Phase 2 Week 2 Tests"
echo "====================================="
echo ""

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "✗ Virtual environment not found"
    exit 1
fi

echo ""

# 测试统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 函数：运行测试
run_test() {
    local test_name="$1"
    local test_file="$2"

    echo "Running: $test_name"
    echo "-----------------------------------"

    if python3 "$test_file"; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo "✓ $test_name passed"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo "✗ $test_name failed"
    fi

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo ""
}

# 1. 数据库持久化测试
run_test "Database Persistence Tests" "tests/database/test_persistence.py"

# 2. 认证功能测试
run_test "Authentication Tests" "tests/security/test_auth.py"

# 3. 数据库功能测试
run_test "Database Functionality Tests" "tests/test_database_functionality.py"

# 输出测试结果
echo "====================================="
echo "Test Results Summary"
echo "====================================="
echo "Total tests: $TOTAL_TESTS"
echo "Passed: $PASSED_TESTS"
echo "Failed: $FAILED_TESTS"
echo "Success rate: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo "✓ All tests passed!"
    echo ""
    exit 0
else
    echo "✗ Some tests failed"
    echo ""
    exit 1
fi
