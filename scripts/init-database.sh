#!/bin/bash

# HermesNexus Phase 2 - Database Initialization Script
# 数据库初始化脚本

set -e

echo "==================================="
echo "HermesNexus Database Initialization"
echo "==================================="

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 数据库配置
DB_TYPE=${DATABASE_TYPE:-sqlite}
DB_PATH=${DATABASE_PATH:-data/hermesnexus.db}
DB_ECHO=${DATABASE_ECHO:-false}

echo "Database Configuration:"
echo "  Type: $DB_TYPE"
echo "  Path: $DB_PATH"
echo "  Echo SQL: $DB_ECHO"
echo ""

# 创建数据目录
echo "Creating data directory..."
mkdir -p data
echo "✓ Data directory created"
echo ""

# 检查Python环境
echo "Checking Python environment..."
if ! command -v python3 &> /dev/null; then
    echo "✗ Python3 not found"
    exit 1
fi
echo "✓ Python3 found: $(python3 --version)"
echo ""

# 检查SQLAlchemy
echo "Checking dependencies..."
if ! python3 -c "import sqlalchemy" 2>/dev/null; then
    echo "✗ SQLAlchemy not installed"
    echo "Installing dependencies..."
    pip install sqlalchemy==2.0.23
fi
echo "✓ SQLAlchemy installed"
echo ""

# 初始化数据库
echo "Initializing database..."
python3 << EOF
import sys
import os

# 添加项目路径
sys.path.insert(0, '$PROJECT_ROOT')

# 设置环境变量
DB_TYPE = os.getenv('DATABASE_TYPE', '$DB_TYPE')
DB_PATH = os.getenv('DATABASE_PATH', '$DB_PATH')
DB_ECHO = os.getenv('DATABASE_ECHO', '$DB_ECHO')

try:
    from shared.database import SQLiteBackend

    # 创建数据库后端
    print(f"Creating database backend: {DB_TYPE}")
    if DB_TYPE == "sqlite":
        db = SQLiteBackend(db_path=DB_PATH, echo=(DB_ECHO == "true"))
    else:
        print(f"✗ Unsupported database type: {DB_TYPE}")
        sys.exit(1)

    # 初始化数据库
    print("Initializing database connection...")
    db.initialize()

    # 创建表
    print("Creating tables...")
    db.create_tables()

    # 健康检查
    print("Running health check...")
    if db.health_check():
        print("✓ Database is healthy")
    else:
        print("✗ Database health check failed")
        sys.exit(1)

    # 显示连接信息
    info = db.get_connection_info()
    print("")
    print("Database Connection Info:")
    print(f"  Type: {info['type']}")
    print(f"  Path: {info['path']}")
    print(f"  File exists: {info['file_exists']}")
    print(f"  File size: {info['file_size']} bytes")

    print("")
    print("✓ Database initialized successfully")
    print(f"  Database file: {DB_PATH}")

except Exception as e:
    print(f"✗ Failed to initialize database: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    # 清理资源
    if 'db' in locals():
        db.close()
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "==================================="
    echo "✓ Database initialization complete"
    echo "==================================="
    echo ""
    echo "Next steps:"
    echo "  1. Start Cloud API: ./scripts/start-cloud-api.sh"
    echo "  2. Verify API: curl http://localhost:8080/health"
    echo ""
else
    echo ""
    echo "==================================="
    echo "✗ Database initialization failed"
    echo "==================================="
    echo ""
    echo "Please check the error messages above."
    echo ""
    exit 1
fi
