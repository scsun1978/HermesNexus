#!/bin/bash
# 快速验证脚本 - 用于本地快速检查代码质量

echo "⚡ HermesNexus 快速验证"
echo "========================"

SUCCESS_COUNT=0
FAIL_COUNT=0

# 快速检查函数
quick_check() {
    local name="$1"
    local command="$2"

    echo -n "🔍 $name... "

    if eval "$command" > /dev/null 2>&1; then
        echo "✅"
        ((SUCCESS_COUNT++))
        return 0
    else
        echo "❌"
        ((FAIL_COUNT++))
        return 1
    fi
}

# 核心检查
echo ""
echo "📋 核心检查:"

quick_check "Python语法" "python3 -m compileall shared/ tests/"
quick_check "导入检查" "python3 -c 'import sys; sys.path.insert(0, \".\"); from shared.database.sqlite_backend import SQLiteBackend'"
quick_check "DAO导入" "python3 -c 'import sys; sys.path.insert(0, \".\"); from shared.dao.asset_dao import AssetDAO; from shared.dao.task_dao import TaskDAO; from shared.dao.audit_dao import AuditDAO'"
quick_check "服务导入" "python3 -c 'import sys; sys.path.insert(0, \".\"); from shared.services.asset_service import AssetService; from shared.services.task_service import TaskService; from shared.services.audit_service import AuditService'"
quick_check "模型导入" "python3 -c 'import sys; sys.path.insert(0, \".\"); from shared.models.asset import Asset; from shared.models.task import Task; from shared.models.audit import AuditLog'"

# 文件结构检查
echo ""
echo "📁 文件结构检查:"

quick_check "核心目录存在" "test -d shared/ && test -d cloud/ && test -d edge/"
quick_check "测试目录存在" "test -d tests/"
quick_check "配置文件存在" "test -f docs/62-环境变量与配置文件规范.md"
quick_check "脚本目录存在" "test -d scripts/"

# 关键文件检查
echo ""
echo "📄 关键文件检查:"

quick_check "README存在" "test -f README.md"
quick_check "数据库模型" "test -f shared/database/models.py"
quick_check "DAO文件" "test -f shared/dao/asset_dao.py && test -f shared/dao/task_dao.py && test -f shared/dao/audit_dao.py"
quick_check "服务文件" "test -f shared/services/asset_service.py && test -f shared/services/task_service.py"

# 批量操作检查
echo ""
echo "🚀 批量操作检查:"

quick_check "AssetDAO批量方法" "python3 -c \"import sys; sys.path.insert(0, '.'); from shared.dao.asset_dao import AssetDAO; assert hasattr(AssetDAO, 'select_by_ids'); assert hasattr(AssetDAO, 'insert_batch'); assert hasattr(AssetDAO, 'update_batch')\""
quick_check "TaskDAO批量方法" "python3 -c \"import sys; sys.path.insert(0, '.'); from shared.dao.task_dao import TaskDAO; assert hasattr(TaskDAO, 'select_by_ids'); assert hasattr(TaskDAO, 'insert_batch'); assert hasattr(TaskDAO, 'update_batch')\""
quick_check "AuditDAO批量方法" "python3 -c \"import sys; sys.path.insert(0, '.'); from shared.dao.audit_dao import AuditDAO; assert hasattr(AuditDAO, 'select_by_ids'); assert hasattr(AuditDAO, 'insert_batch')\""

# CI配置检查
echo ""
echo "🔧 CI配置检查:"

quick_check "GitHub Actions配置" "test -f .github/workflows/ci.yml"
quick_check "CI检查脚本" "test -f scripts/ci-check.sh"
quick_check "构建脚本" "test -f scripts/build.sh"

# 汇总结果
echo ""
echo "========================"
echo "📊 检查结果汇总:"
echo "  ✅ 通过: $SUCCESS_COUNT"
echo "  ❌ 失败: $FAIL_COUNT"
echo "========================"

if [ $FAIL_COUNT -eq 0 ]; then
    echo "🎉 所有检查通过！代码已准备好CI验证"
    exit 0
else
    echo "⚠️  有 $FAIL_COUNT 项检查失败，请修复后重试"
    exit 1
fi