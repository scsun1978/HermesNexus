.PHONY: help install up down restart logs test lint clean deploy init venv

# Python 虚拟环境配置
VENV_PATH = venv
PYTHON = python3
ACTIVATE = . $(VENV_PATH)/bin/activate
PIP = $(VENV_PATH)/bin/pip
PYTHON_EXE = $(VENV_PATH)/bin/python

# 默认目标
help:
	@echo "HermesNexus 开发命令"
	@echo ""
	@echo "初始化:"
	@echo "  make init         - 初始化开发环境"
	@echo "  make venv         - 创建Python虚拟环境"
	@echo "  make install      - 安装依赖"
	@echo ""
	@echo "开发服务:"
	@echo "  make up           - 启动所有服务"
	@echo "  make down         - 停止所有服务"
	@echo "  make restart      - 重启服务"
	@echo "  make logs         - 查看服务日志"
	@echo "  make status       - 查看服务状态"
	@echo ""
	@echo "开发工具:"
	@echo "  make dev          - 开发模式启动"
	@echo "  make test         - 运行测试"
	@echo "  make lint         - 代码检查"
	@echo "  make format       - 代码格式化"
	@echo ""
	@echo "Python命令:"
	@echo "  make shell        - 进入Python环境"
	@echo "  make run-cloud    - 运行云端API"
	@echo "  make run-edge     - 运行边缘节点"
	@echo ""
	@echo "部署:"
	@echo "  make deploy       - 部署到开发服务器"
	@echo "  make deploy-status- 查看部署状态"
	@echo "  make deploy-logs  - 查看部署日志"
	@echo ""
	@echo "清理:"
	@echo "  make clean        - 清理临时文件"
	@echo "  make clean-venv   - 清理虚拟环境"
	@echo "  make clean-all    - 完全清理(包括数据)"

# 初始化开发环境
init:
	@echo "🚀 初始化 HermesNexus 开发环境..."
	@if [ ! -f .env ]; then \
		echo "📝 创建 .env 文件..."; \
		cp .env.example .env; \
		echo "⚠️  请编辑 .env 文件配置开发环境"; \
	else \
		echo "✅ .env 文件已存在"; \
	fi
	@if [ ! -f config.yaml ]; then \
		echo "📝 创建 config.yaml 文件..."; \
		cp config.example.yaml config.yaml; \
		echo "⚠️  请编辑 config.yaml 文件配置"; \
	else \
		echo "✅ config.yaml 文件已存在"; \
	fi
	@mkdir -p data logs uploads
	@echo "✅ 开发环境初始化完成"
	@echo "💡 下一步: make venv && make install"

# 创建Python虚拟环境
venv:
	@echo "🐍 创建Python虚拟环境..."
	@if [ ! -d $(VENV_PATH) ]; then \
		$(PYTHON) -m venv $(VENV_PATH); \
		echo "✅ 虚拟环境创建成功: $(VENV_PATH)"; \
	else \
		echo "✅ 虚拟环境已存在: $(VENV_PATH)"; \
	fi
	@echo "💡 激活虚拟环境: source $(VENV_PATH)/bin/activate"

# 安装依赖
install:
	@echo "📦 安装Python依赖..."
	@if [ -d $(VENV_PATH) ]; then \
		$(PIP) install --upgrade pip; \
		$(PIP) install -r requirements.txt; \
		$(PIP) install -r requirements-dev.txt; \
		echo "✅ 依赖安装完成"; \
	else \
		echo "❌ 虚拟环境不存在，请先运行: make venv"; \
		exit 1; \
	fi

# 启动所有服务
up:
	@echo "🚀 启动 HermesNexus 服务..."
	@docker-compose up -d
	@echo "✅ 服务启动完成"
	@make status

# 停止所有服务
down:
	@echo "🛑 停止 HermesNexus 服务..."
	@docker-compose down
	@echo "✅ 服务已停止"

# 重启服务
restart:
	@echo "🔄 重启 HermesNexus 服务..."
	@docker-compose restart
	@echo "✅ 服务重启完成"

# 查看日志
logs:
	@docker-compose logs -f --tail=100

# 查看服务状态
status:
	@echo "📊 服务状态:"
	@docker-compose ps

# 开发模式启动
dev:
	@echo "🔧 开发模式启动..."
	@echo "🚀 启动云端API服务..."
	@$(PYTHON_EXE) cloud/api/main.py & \
	echo "✅ 云端API启动完成: http://localhost:8080"
	@echo "📋 API文档: http://localhost:8080/docs"

# 运行测试
test:
	@echo "🧪 运行Python测试..."
	@if [ -f $(PYTHON_EXE) ]; then \
		$(PYTHON_EXE) -m pytest tests/ -v --tb=short; \
	else \
		echo "❌ 虚拟环境不存在，请先运行: make venv && make install"; \
		exit 1; \
	fi

test-unit:
	@echo "🔬 运行单元测试..."
	@if [ -f $(PYTHON_EXE) ]; then \
		$(PYTHON_EXE) -m pytest tests/ -v -k "not integration and not e2e"; \
	else \
		echo "❌ 虚拟环境不存在"; \
		exit 1; \
	fi

test-integration:
	@echo "🔗 运行集成测试..."
	@if [ -f $(PYTHON_EXE) ]; then \
		$(PYTHON_EXE) -m pytest tests/ -v -k "integration"; \
	else \
		echo "❌ 虚拟环境不存在"; \
		exit 1; \
	fi

test-e2e:
	@echo "🎯 运行E2E测试..."
	@if [ -f $(PYTHON_EXE) ]; then \
		$(PYTHON_EXE) -m pytest tests/ -v -k "e2e"; \
	else \
		echo "❌ 虚拟环境不存在"; \
		exit 1; \
	fi

test-coverage:
	@echo "📊 运行测试并生成覆盖率报告..."
	@if [ -f $(PYTHON_EXE) ]; then \
		$(PYTHON_EXE) -m pytest tests/ --cov=. --cov-report=html --cov-report=term; \
		echo "📈 覆盖率报告: htmlcov/index.html"; \
	else \
		echo "❌ 虚拟环境不存在"; \
		exit 1; \
	fi

# 代码检查
lint:
	@echo "🔍 Python代码检查..."
	@if [ -f $(PYTHON_EXE) ]; then \
		$(PYTHON_EXE) -m flake8 cloud/ edge/ shared/ tests/ --max-line-length=100; \
		$(PYTHON_EXE) -m mypy cloud/ edge/ shared/ --ignore-missing-imports; \
	else \
		echo "❌ 虚拟环境不存在"; \
		exit 1; \
	fi

# 代码格式化
format:
	@echo "✨ Python代码格式化..."
	@if [ -f $(PYTHON_EXE) ]; then \
		$(PYTHON_EXE) -m black cloud/ edge/ shared/ tests/; \
		$(PYTHON_EXE) -m isort cloud/ edge/ shared/ tests/; \
		echo "✅ 代码格式化完成"; \
	else \
		echo "❌ 虚拟环境不存在"; \
		exit 1; \
	fi

# 进入Python环境
shell:
	@if [ -f $(PYTHON_EXE) ]; then \
		$(PYTHON_EXE); \
	else \
		echo "❌ 虚拟环境不存在，请先运行: make venv && make install"; \
		exit 1; \
	fi

# 运行云端API
run-cloud:
	@echo "🚀 启动云端API服务..."
	@if [ -f $(PYTHON_EXE) ]; then \
		$(PYTHON_EXE) cloud/api/main.py; \
	else \
		echo "❌ 虚拟环境不存在，请先运行: make venv && make install"; \
		exit 1; \
	fi

# 运行边缘节点
run-edge:
	@echo "🚀 启动边缘节点..."
	@if [ -f $(PYTHON_EXE) ]; then \
		$(PYTHON_EXE) edge/runtime/core.py; \
	else \
		echo "❌ 虚拟环境不存在，请先运行: make venv && make install"; \
		exit 1; \
	fi

# 部署到开发服务器
deploy:
	@echo "🚀 部署到开发服务器..."
	@bash deploy/scripts/deploy.sh

# 查看部署状态
deploy-status:
	@echo "📊 查看部署状态..."
	@ssh -i ~/.ssh/ubuntu_root_id_ed25519 -o StrictHostKeyChecking=no scsun@172.16.100.101 "cd /opt/hermesnexus && docker compose ps"

# 查看部署日志
deploy-logs:
	@echo "📋 查看部署日志..."
	@ssh -i ~/.ssh/ubuntu_root_id_ed25519 -o StrictHostKeyChecking=no scsun@172.16.100.101 "cd /opt/hermesnexus && docker compose logs -f --tail=50"

# 清理临时文件
clean:
	@echo "🧹 清理临时文件..."
	@rm -rf logs/*.log
	@rm -rf uploads/*
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@rm -f .coverage
	@echo "✅ 临时文件清理完成"

# 清理虚拟环境
clean-venv:
	@echo "🗑️  清理Python虚拟环境..."
	@if [ -d $(VENV_PATH) ]; then \
		rm -rf $(VENV_PATH); \
		echo "✅ 虚拟环境已清理"; \
	else \
		echo "⚠️  虚拟环境不存在"; \
	fi

# 完全清理
clean-all: clean
	@echo "🗑️  完全清理(包括数据)..."
	@read -p "确认要删除所有数据吗? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		rm -rf data/*; \
		echo "✅ 完全清理完成"; \
	else \
		echo "❌ 取消清理"; \
	fi

# 创建备份
backup:
	@echo "💾 创建备份..."
	@mkdir -p backups
	@tar -czf backups/hermesnexus-$$(date +%Y%m%d-%H%M%S).tar.gz \
		data/ \
		config.yaml \
		.env \
		deploy/
	@echo "✅ 备份完成"

# 检查环境
check-env:
	@echo "🔍 检查开发环境..."
	@if command -v docker >/dev/null 2>&1; then \
		echo "✅ Docker: $$(docker --version)"; \
	else \
		echo "❌ Docker 未安装"; \
	fi
	@if command -v docker-compose >/dev/null 2>&1; then \
		echo "✅ Docker Compose: $$(docker-compose --version)"; \
	else \
		echo "❌ Docker Compose 未安装"; \
	fi
	@if [ -f .env ]; then \
		echo "✅ .env 文件存在"; \
	else \
		echo "❌ .env 文件不存在"; \
	fi
	@if [ -f config.yaml ]; then \
		echo "✅ config.yaml 文件存在"; \
	else \
		echo "❌ config.yaml 文件不存在"; \
	fi
	@if [ -d $(VENV_PATH) ]; then \
		echo "✅ Python虚拟环境存在: $(VENV_PATH)"; \
		if [ -f $(PYTHON_EXE) ]; then \
			PY_VER=$$($(PYTHON_EXE) --version 2>&1); \
			echo "   Python版本: $$PY_VER"; \
		fi; \
	else \
		echo "❌ Python虚拟环境不存在"; \
	fi
	@if ssh -i ~/.ssh/ubuntu_root_id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=5 scsun@172.16.100.101 exit 2>/dev/null; then \
		echo "✅ 开发服务器连接正常"; \
	else \
		echo "❌ 无法连接到开发服务器 scsun@172.16.100.101"; \
	fi

# 显示帮助信息
show-env:
	@echo "📋 当前环境配置:"
	@echo "   PROJECT_DIR: $$(pwd)"
	@echo "   DATA_DIR: $$(pwd)/data"
	@echo "   LOG_DIR: $$(pwd)/logs"
	@echo "   DEV_SERVER: scsun@172.16.100.101"
	@echo "   VENV_PATH: $(VENV_PATH)"
	@echo "   PYTHON: $(PYTHON)"
	@if [ -f $(PYTHON_EXE) ]; then \
		echo "   PYTHON_VERSION: $$($(PYTHON_EXE) --version 2>&1)"; \
	fi

