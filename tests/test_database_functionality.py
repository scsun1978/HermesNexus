#!/usr/bin/env python3
"""
HermesNexus Phase 2 - Database Functionality Test
数据库功能测试
"""

import sys
import os
import tempfile
import shutil
from datetime import datetime

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from shared.database import SQLiteBackend
from shared.dao import AssetDAO, TaskDAO, AuditDAO
from shared.models.asset import (
    Asset,
    AssetCreateRequest,
    AssetType,
    AssetStatus,
    AssetMetadata,
)
from shared.models.task import (
    Task,
    TaskCreateRequest,
    TaskType,
    TaskStatus,
    TaskPriority,
)
from shared.models.audit import (
    AuditLog,
    AuditLogCreateRequest,
    AuditCategory,
    EventLevel,
)


def _make_isolated_db():
    temp_dir = tempfile.mkdtemp(prefix="hermesnexus_db_test_")
    db_path = os.path.join(temp_dir, "test.db")
    db = SQLiteBackend(db_path=db_path)
    db.initialize()
    db.create_tables()
    return db, temp_dir


def _cleanup_isolated_db(db, temp_dir):
    try:
        db.close()
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def test_asset_crud():
    """测试资产CRUD功能"""
    print("Testing Asset CRUD...")

    # 创建数据库连接
    db, temp_dir = _make_isolated_db()

    # 创建AssetDAO
    asset_dao = AssetDAO(db)

    # 创建测试资产
    asset = Asset(
        asset_id="test-asset-001",
        name="Test Asset",
        asset_type=AssetType.LINUX_HOST,
        status=AssetStatus.REGISTERED,
        metadata=AssetMetadata(
            ip_address="192.168.1.100",
            hostname="test.local",
            ssh_port=22,
            ssh_username="testuser",
        ),
        description="Test asset for database validation",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # 测试插入
    created_asset = asset_dao.insert(asset)
    assert created_asset.asset_id == "test-asset-001"
    print("  ✓ Asset created successfully")

    # 测试查询
    found_asset = asset_dao.select_by_id("test-asset-001")
    assert found_asset is not None
    assert found_asset.name == "Test Asset"
    assert found_asset.metadata.ip_address == "192.168.1.100"
    print("  ✓ Asset retrieved successfully")

    # 测试更新
    found_asset.description = "Updated description"
    found_asset.updated_at = datetime.utcnow()
    updated_asset = asset_dao.update(found_asset)
    assert updated_asset.description == "Updated description"
    print("  ✓ Asset updated successfully")

    # 测试列表查询
    assets = asset_dao.list(limit=10)
    assert len(assets) > 0
    print(f"  ✓ Found {len(assets)} asset(s)")

    # 测试统计
    count = asset_dao.count()
    assert count > 0
    print(f"  ✓ Total assets: {count}")

    _cleanup_isolated_db(db, temp_dir)
    print("✓ Asset CRUD test passed\n")


def test_task_crud():
    """测试任务CRUD功能"""
    print("Testing Task CRUD...")

    # 创建数据库连接
    db, temp_dir = _make_isolated_db()

    # 创建TaskDAO
    task_dao = TaskDAO(db)

    # 创建测试任务
    task = Task(
        task_id="test-task-001",
        name="Test Task",
        task_type=TaskType.BASIC_EXEC,
        status=TaskStatus.PENDING,
        priority=TaskPriority.NORMAL,
        target_asset_id="test-asset-001",
        command="uptime",
        timeout=30,
        created_by="test-user",
        description="Test task for database validation",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # 测试插入
    created_task = task_dao.insert(task)
    assert created_task.task_id == "test-task-001"
    print("  ✓ Task created successfully")

    # 测试查询
    found_task = task_dao.select_by_id("test-task-001")
    assert found_task is not None
    assert found_task.name == "Test Task"
    assert found_task.command == "uptime"
    print("  ✓ Task retrieved successfully")

    # 测试列表查询
    tasks = task_dao.list(limit=10)
    assert len(tasks) > 0
    print(f"  ✓ Found {len(tasks)} task(s)")

    # 测试统计
    count = task_dao.count()
    assert count > 0
    print(f"  ✓ Total tasks: {count}")

    _cleanup_isolated_db(db, temp_dir)
    print("✓ Task CRUD test passed\n")


def test_audit_crud():
    """测试审计日志CRUD功能"""
    print("Testing Audit Log CRUD...")

    # 创建数据库连接
    db, temp_dir = _make_isolated_db()

    # 创建AuditDAO
    audit_dao = AuditDAO(db)

    # 创建测试审计日志
    audit_log = AuditLog(
        audit_id="test-audit-001",
        action="task_created",
        category=AuditCategory.TASK,
        level=EventLevel.INFO,
        actor="admin",
        target_type="task",
        target_id="test-task-001",
        message="Task created for testing",
        metadata={"test": True},
        created_at=datetime.utcnow(),
    )

    # 测试插入
    created_audit = audit_dao.insert(audit_log)
    assert created_audit.audit_id == "test-audit-001"
    print("  ✓ Audit log created successfully")

    # 测试查询
    found_audit = audit_dao.select_by_id("test-audit-001")
    assert found_audit is not None
    assert found_audit.action == "task_created"
    assert found_audit.message == "Task created for testing"
    print("  ✓ Audit log retrieved successfully")

    # 测试列表查询
    audits = audit_dao.list(limit=10)
    assert len(audits) > 0
    print(f"  ✓ Found {len(audits)} audit log(s)")

    # 测试按任务查询
    task_audits = audit_dao.query_by_task("test-task-001", limit=5)
    assert len(task_audits) > 0
    print(f"  ✓ Found {len(task_audits)} audit log(s) for task")

    _cleanup_isolated_db(db, temp_dir)
    print("✓ Audit Log CRUD test passed\n")


def main():
    """主测试函数"""
    print("=" * 50)
    print("HermesNexus Database Functionality Test")
    print("=" * 50)
    print()

    try:
        # 运行测试
        test_asset_crud()
        test_task_crud()
        test_audit_crud()

        print("=" * 50)
        print("✓ All tests passed successfully!")
        print("=" * 50)
        return 0

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
