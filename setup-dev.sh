#!/bin/bash

###############################################################################
# HermesNexus Development Environment Setup Script
# 开发环境设置脚本 - 一键配置完整的开发环境
###############################################################################

set -e  # 遇到错误立即退出

echo "🚀 HermesNexus 开发环境设置"
echo "================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查Python版本
check_python() {
    echo -e "${BLUE}检查Python版本...${NC}"

    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 未安装${NC}"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    REQUIRED_VERSION="3.13"

    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
        echo -e "${YELLOW}⚠️  Python版本建议为 $REQUIRED_VERSION+，当前版本: $PYTHON_VERSION${NC}"
    else
        echo -e "${GREEN}✅ Python版本检查通过: $PYTHON_VERSION${NC}"
    fi
}

# 创建虚拟环境
create_venv() {
    echo -e "${BLUE}设置虚拟环境...${NC}"

    if [ ! -d "venv" ]; then
        echo "创建虚拟环境..."
        python3 -m venv venv
        echo -e "${GREEN}✅ 虚拟环境创建完成${NC}"
    else
        echo -e "${GREEN}✅ 虚拟环境已存在${NC}"
    fi
}

# 激活虚拟环境并安装依赖
install_dependencies() {
    echo -e "${BLUE}安装开发依赖...${NC}"

    # 激活虚拟环境
    source venv/bin/activate

    # 升级pip
    pip install --upgrade pip setuptools wheel

    # 安装开发依赖
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi

    if [ -f "requirements-dev.txt" ]; then
        pip install -r requirements-dev.txt
    fi

    # 安装pre-commit和开发工具
    pip install pre-commit black flake8 mypy bandit safety isort

    echo -e "${GREEN}✅ 依赖安装完成${NC}"
}

# 安装pre-commit hooks
setup_pre_commit() {
    echo -e "${BLUE}设置Pre-Commit Hooks...${NC}"

    # 激活虚拟环境
    source venv/bin/activate

    # 安装pre-commit hooks
    pre-commit install

    echo -e "${GREEN}✅ Pre-commit hooks 安装完成${NC}"
    echo -e "${YELLOW}💡 提示: 以后每次git commit都会自动运行代码质量检查${NC}"
}

# 运行代码格式化
format_code() {
    echo -e "${BLUE}运行代码格式化...${NC}"

    # 激活虚拟环境
    source venv/bin/activate

    # 运行black格式化
    echo "使用Black格式化代码..."
    black shared/ tests/ cloud/ edge/ --config pyproject.toml

    # 运行isort整理imports
    echo "使用isort整理导入..."
    isort shared/ tests/ cloud/ edge/ --settings-path pyproject.toml

    echo -e "${GREEN}✅ 代码格式化完成${NC}"
}

# 验证设置
verify_setup() {
    echo -e "${BLUE}验证开发环境设置...${NC}"

    # 激活虚拟环境
    source venv/bin/activate

    # 检查关键工具
    python3 -c "import black; print(f'Black: {black.__version__}')"
    python3 -c "import flake8; print(f'Flake8: {flake8.__version__}')"
    python3 -c "import mypy; print(f'MyPy: {mypy.__version__}')"
    python3 -c "import pytest; print(f'Pytest: {pytest.__version__}')"

    # 运行quick smoke test
    echo -e "${BLUE}运行快速测试...${NC}"
    python -m pytest tests/e2e/test_smoke.py -v --tb=short || echo -e "${YELLOW}⚠️  测试需要数据库设置${NC}"

    echo -e "${GREEN}✅ 环境验证完成${NC}"
}

# 主函数
main() {
    # 检查是否在项目根目录
    if [ ! -f "pyproject.toml" ] && [ ! -f ".flake8" ]; then
        echo -e "${RED}❌ 请在项目根目录运行此脚本${NC}"
        exit 1
    fi

    check_python
    create_venv
    install_dependencies
    setup_pre_commit

    # 询问是否需要格式化现有代码
    echo -e "${YELLOW}是否需要格式化现有代码? (y/N)${NC}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        format_code
    fi

    verify_setup

    echo ""
    echo -e "${GREEN}🎉 开发环境设置完成！${NC}"
    echo ""
    echo "使用方法:"
    echo "  1. 激活虚拟环境: source venv/bin/activate"
    echo "  2. 运行测试: python -m pytest tests/"
    echo "  3. 格式化代码: black shared/ tests/ cloud/ edge/"
    echo "  4. 检查代码规范: flake8 shared/ tests/ cloud/ edge/"
    echo "  5. 手动运行pre-commit: pre-commit run --all-files"
    echo ""
}

# 运行主函数
main