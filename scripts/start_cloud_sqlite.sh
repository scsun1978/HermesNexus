#!/bin/bash
# HermesNexus 云端API启动脚本 (SQLite版本)

# 设置Python路径
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 设置数据库类型为SQLite
export DB_TYPE=sqlite
export SQLITE_DB_PATH="./data/hermesnexus.db"

# 激活虚拟环境
source venv/bin/activate

# 启动云端API服务
echo "🚀 启动HermesNexus云端API (SQLite数据库)..."
python cloud/api/main.py