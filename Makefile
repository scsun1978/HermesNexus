.PHONY: help setup install test lint format clean dev prod

# 默认目标
.DEFAULT_GOAL := help

# 颜色定义
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
WHITE  := $(shell tput -Txterm setaf 7)
RESET  := $(shell tput -Txterm sgr0)

# 帮助信息
help: ## 显示此帮助信息
	@echo ''
	@echo '${GREEN}HermesNexus 开发命令${RESET}'
	@echo ''
	@echo '使用方法:'
	@echo '  ${YELLOW}make${RESET} ${GREEN}<target>${RESET}'
	@echo ''
	@echo '可用目标:'
	@awk 'BEGIN {FS = ":.*?## "} \
	      /^[a-zA-Z_-]+:.*?## / {printf "  ${YELLOW}%-15s${RESET} %s\n", $$1, $$2} \
	      /^##@/ {printf "\n${WHITE}%s${RESET}\n", substr($$0, 5)}' $(MAKEFILE_LIST)
	@echo ''

##@ 环境设置

setup: ## 初始化开发环境（推荐）
	@echo "${GREEN}初始化开发环境...${RESET}"
	@./setup-dev.sh

install: ## 安装开发依赖
	@echo "${GREEN}安装开发依赖...${RESET}"
	@pip install --upgrade pip setuptools wheel
	@if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
	@if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
	@pip install pre-commit black flake8 mypy bandit safety isort
	@pre-commit install

dev: ## 启动开发模式
	@echo "${GREEN}启动开发环境...${RESET}"
	@source venv/bin/activate && \
		export PYTHONPATH="${PYTHONPATH}:$(pwd)" && \
		echo "开发环境已激活，PYTHONPATH已设置"

##@ 代码质量

lint: ## 运行所有代码质量检查
	@echo "${GREEN}运行代码质量检查...${RESET}"
	@echo "${YELLOW}Black格式检查...${RESET}"
	@black --check --config pyproject.toml shared/ tests/ cloud/ edge/
	@echo "${YELLOW}Flake8规范检查...${RESET}"
	@flake8 shared/ tests/ cloud/ edge/ --config .flake8
	@echo "${YELLOW}MyPy类型检查...${RESET}"
	@mypy shared/ --config-file pyproject.toml
	@echo "${YELLOW}Bandit安全检查...${RESET}"
	@bandit -r shared/ -c pyproject.toml
	@echo "${GREEN}✅ 所有代码质量检查通过${RESET}"

format: ## 格式化代码
	@echo "${GREEN}格式化代码...${RESET}"
	@black shared/ tests/ cloud/ edge/ --config pyproject.toml
	@isort shared/ tests/ cloud/ edge/ --settings-path pyproject.toml
	@echo "${GREEN}✅ 代码格式化完成${RESET}"

ci-local: ## 本地运行CI检查
	@echo "${GREEN}本地运行CI检查...${RESET}"
	@make lint
	@make test-unit
	@make test-smoke
	@echo "${GREEN}✅ 本地CI检查通过${RESET}"

##@ 测试

test: ## 运行所有测试
	@echo "${GREEN}运行所有测试...${RESET}"
	@python -m pytest tests/ -v --tb=short

test-unit: ## 运行单元测试
	@echo "${GREEN}运行单元测试...${RESET}"
	@python -m pytest tests/unit/ -v --tb=short

test-smoke: ## 运行Smoke测试
	@echo "${GREEN}运行Smoke测试...${RESET}"
	@python -m pytest tests/e2e/test_smoke.py -v

##@ 清理

clean: ## 清理临时文件
	@echo "${GREEN}清理临时文件...${RESET}"
	@find . -type f -name '*.pyc' -delete
	@find . -type f -name '*.pyo' -delete
	@find . -type d -name '__pycache__' -delete
	@find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	@rm -rf build/ dist/ .pytest_cache/ .mypy_cache/
	@echo "${GREEN}✅ 清理完成${RESET}"
