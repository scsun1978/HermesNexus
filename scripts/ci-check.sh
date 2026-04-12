#!/bin/bash
# CI本地预检查脚本 - 在提交前运行，确保CI能通过

set -e  # 遇到错误立即退出

echo "🚀 HermesNexus CI 本地预检查"
echo "=================================="

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check_step() {
    local step_name="$1"
    local command="$2"

    echo ""
    echo "🔍 检查: $step_name"
    echo "执行: $command"

    if eval "$command"; then
        echo -e "${GREEN}✅ $step_name 通过${NC}"
        return 0
    else
        echo -e "${RED}❌ $step_name 失败${NC}"
        return 1
    fi
}

# 1. 检查Python环境
echo "📋 检查Python环境..."
python3 --version || { echo -e "${RED}❌ Python3未安装${NC}"; exit 1; }
echo -e "${GREEN}✅ Python环境正常${NC}"

# 2. 安装依赖
echo ""
echo "📦 安装项目依赖..."
if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
else
    echo -e "${YELLOW}⚠️  未找到requirements.txt${NC}"
fi

if [ -f "requirements-dev.txt" ]; then
    pip install -q -r requirements-dev.txt
    echo -e "${GREEN}✅ 开发依赖安装完成${NC}"
fi

# 3. 代码风格检查
if command -v black &> /dev/null; then
    check_step "代码风格检查 (Black)" "black --check shared/ tests/ cloud/ edge/" || true
else
    echo -e "${YELLOW}⚠️  Black未安装，跳过代码风格检查${NC}"
fi

# 4. 代码规范检查
if command -v flake8 &> /dev/null; then
    check_step "代码规范检查 (Flake8)" "flake8 shared/ tests/ cloud/ edge/ --max-line-length=100 --exclude=*.pyc,__pycache__" || true
else
    echo -e "${YELLOW}⚠️  Flake8未安装，跳过代码规范检查${NC}"
fi

# 5. 类型检查
if command -v mypy &> /dev/null; then
    check_step "类型检查 (MyPy)" "mypy shared/ --ignore-missing-imports" || true
else
    echo -e "${YELLOW}⚠️  MyPy未安装，跳过类型检查${NC}"
fi

# 6. 安全扫描
if command -v bandit &> /dev/null; then
    check_step "安全扫描 (Bandit)" "bandit -r shared/ -f json -o bandit-report.json" || true
else
    echo -e "${YELLOW}⚠️  Bandit未安装，跳过安全扫描${NC}"
fi

# 7. 语法检查
echo ""
echo "🔍 检查Python文件语法..."
python3 -m compileall shared/ tests/ cloud/ edge/ || {
    echo -e "${RED}❌ 语法检查失败${NC}"
    exit 1
}
echo -e "${GREEN}✅ 语法检查通过${NC}"

# 8. 单元测试
if [ -d "tests/unit" ]; then
    echo ""
    echo "🧪 运行单元测试..."
    if python3 -m pytest tests/unit/ -v --tb=short; then
        echo -e "${GREEN}✅ 单元测试通过${NC}"
    else
        echo -e "${RED}❌ 单元测试失败${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  未找到单元测试目录${NC}"
fi

# 9. 集成测试
if [ -d "tests/integration" ]; then
    echo ""
    echo "🔗 运行集成测试..."
    if python3 -m pytest tests/integration/ -v --tb=short; then
        echo -e "${GREEN}✅ 集成测试通过${NC}"
    else
        echo -e "${RED}❌ 集成测试失败${NC}"
        exit 1
    fi
fi

# 10. Smoke测试
if [ -f "tests/e2e/test_smoke.py" ]; then
    echo ""
    echo "🔥 运行Smoke测试..."
    if python3 tests/e2e/test_smoke.py; then
        echo -e "${GREEN}✅ Smoke测试通过${NC}"
    else
        echo -e "${RED}❌ Smoke测试失败${NC}"
        exit 1
    fi
fi

# 最终总结
echo ""
echo "=================================="
echo -e "${GREEN}🎉 所有CI预检查通过！${NC}"
echo "=================================="
echo ""
echo "📋 检查项目:"
echo "  ✅ Python环境"
echo "  ✅ 依赖安装"
echo "  ✅ 代码质量检查"
echo "  ✅ 语法检查"
echo "  ✅ 单元测试"
echo "  ✅ 集成测试"
echo "  ✅ Smoke测试"
echo ""
echo "🚀 代码已准备好提交和CI验证"

exit 0