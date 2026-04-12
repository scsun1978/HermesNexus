#!/bin/bash
# Smoke Tests 快速执行脚本
# 用途: 在5分钟内验证系统核心功能

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 计时开始
SMOKE_START_TIME=$(date +%s)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🔥 HermesNexus Smoke Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "快速系统健康检查 (5分钟内完成)"
echo "如果Smoke测试失败，不要继续其他测试"
echo ""

# 检查依赖
check_dependencies() {
    echo -e "${YELLOW}[检查] 验证测试依赖...${NC}"

    if ! python3 -c "import unittest" 2>/dev/null; then
        echo -e "${RED}✗ Python unittest 模块不可用${NC}"
        exit 1
    fi

    if ! python3 -c "import sqlalchemy" 2>/dev/null; then
        echo -e "${RED}✗ SQLAlchemy 未安装${NC}"
        echo "请运行: pip3 install sqlalchemy"
        exit 1
    fi

    echo -e "${GREEN}✓ 依赖检查通过${NC}"
    echo ""
}

# 环境准备
prepare_environment() {
    echo -e "${YELLOW}[准备] 设置测试环境...${NC}"

    # 检查磁盘空间
    available_space=$(df -k . | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 10240 ]; then
        echo -e "${RED}✗ 磁盘空间不足 (需要至少10MB)${NC}"
        exit 1
    fi

    # 创建临时目录
    mkdir -p /tmp/hermesnexus_smoke
    echo -e "${GREEN}✓ 环境准备完成${NC}"
    echo ""
}

# 快速健康检查
quick_health_check() {
    echo -e "${YELLOW}[快速检查] 核心功能验证...${NC}"

    python3 -c "
import sys
sys.path.insert(0, '.')

try:
    from shared.database.sqlite_backend import SQLiteBackend
    from shared.services.asset_service import AssetService
    from shared.security.auth_manager import AuthManager

    # 快速导入测试
    db = SQLiteBackend(database_url='sqlite:///tmp/quick_test.db')
    print('✓ 数据库模块: OK')

    asset_service = AssetService(database=db)
    print('✓ 资产服务: OK')

    auth_manager = AuthManager()
    print('✓ 认证服务: OK')

except Exception as e:
    print(f'✗ 导入失败: {e}')
    sys.exit(1)
" || exit 1

    echo -e "${GREEN}✓ 快速健康检查通过${NC}"
    echo ""
}

# 运行Smoke测试
run_smoke_tests() {
    echo -e "${YELLOW}[执行] 运行Smoke测试...${NC}"
    echo ""

    # 运行Smoke测试
    if python3 tests/e2e/test_smoke.py; then
        echo -e "${GREEN}✓ Smoke Tests 通过${NC}"
        return 0
    else
        echo -e "${RED}✗ Smoke Tests 失败${NC}"
        return 1
    fi
}

# 输出测试报告
generate_report() {
    local exit_code=$1
    local end_time=$(date +%s)
    local duration=$((end_time - SMOKE_START_TIME))

    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}📊 Smoke Tests 报告${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}状态: ✅ 通过${NC}"
        echo -e "${GREEN}系统健康，可以继续其他测试${NC}"
    else
        echo -e "${RED}状态: ❌ 失败${NC}"
        echo -e "${RED}系统存在问题，请先修复后再继续${NC}"
    fi

    echo ""
    echo "耗时: ${duration}秒"

    # 性能检查
    if [ $duration -gt 300 ]; then
        echo -e "${YELLOW}⚠️  警告: Smoke测试耗时超过5分钟${NC}"
    else
        echo -e "${GREEN}✓ 耗时正常${NC}"
    fi

    echo ""
    echo -e "${BLUE}========================================${NC}"
}

# 清理临时文件
cleanup() {
    echo -e "${YELLOW}[清理] 清理临时文件...${NC}"
    rm -f /tmp/quick_test.db
    rm -rf /tmp/hermesnexus_smoke
    echo -e "${GREEN}✓ 清理完成${NC}"
}

# 主执行流程
main() {
    local exit_code=0

    # 执行测试流程
    check_dependencies || exit_code=1
    prepare_environment || exit_code=1
    quick_health_check || exit_code=1

    if [ $exit_code -eq 0 ]; then
        run_smoke_tests || exit_code=$?
    fi

    # 生成报告
    generate_report $exit_code

    # 清理
    cleanup

    exit $exit_code
}

# 信号处理
trap cleanup EXIT INT TERM

# 执行主流程
main
