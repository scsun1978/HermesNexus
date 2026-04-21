#!/usr/bin/env python3
"""
HermesNexus Phase 2 - Database Persistence Tests
数据库持久化测试
"""

import sys
import os
import unittest
from datetime import datetime

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from shared.database import SQLiteBackend
from shared.dao import AssetDAO, TaskDAO, AuditDAO
from shared.models.asset import Asset, AssetType, AssetStatus, AssetMetadata
from shared.models.task import Task, TaskType, TaskStatus, TaskPriority
from shared.models.audit import AuditLog, AuditAction, AuditCategory, EventLevel
import tempfile
import shutil


class TestDatabasePersistence(unittest.TestCase):
    """数据库持久化测试"""

    def setUp(self):
        """测试前准备"""
        # 创建临时数据库文件
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")

        # 初始化数据库
        self.db = SQLiteBackend(db_path=self.db_path, echo=False)
        self.db.initialize()
        self.db.create_tables()

        # 创建DAO
        self.asset_dao = AssetDAO(self.db)
        self.task_dao = TaskDAO(self.db)
        self.audit_dao = AuditDAO(self.db)

    def tearDown(self):
        """测试后清理"""
        self.db.close()
        # 删除临时目录
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_asset_persistence(self):
        """测试资产数据持久化"""
        # 创建资产
        asset = Asset(
            asset_id="test-asset-persist",
            name="Test Persistence Asset",
            asset_type=AssetType.LINUX_HOST,
            status=AssetStatus.REGISTERED,
            metadata=AssetMetadata(ip_address="192.168.1.100", hostname="persist.local"),
            description="Testing data persistence",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 插入数据
        created_asset = self.asset_dao.insert(asset)
        self.assertIsNotNone(created_asset)
        self.assertEqual(created_asset.asset_id, "test-asset-persist")

        # 关闭数据库连接
        self.db.close()

        # 重新打开数据库（模拟重启）
        self.db.initialize()

        # 验证数据恢复
        recovered_asset = self.asset_dao.select_by_id("test-asset-persist")
        self.assertIsNotNone(recovered_asset)
        self.assertEqual(recovered_asset.name, "Test Persistence Asset")
        self.assertEqual(recovered_asset.metadata.ip_address, "192.168.1.100")

        print("✓ Asset persistence test passed")

    def test_task_persistence(self):
        """测试任务数据持久化"""
        # 创建任务
        task = Task(
            task_id="test-task-persist",
            name="Test Persistence Task",
            task_type=TaskType.BASIC_EXEC,
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            target_asset_id="test-asset-persist",
            command="echo 'persistence test'",
            timeout=30,
            created_by="test-user",
            description="Testing task persistence",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 插入数据
        created_task = self.task_dao.insert(task)
        self.assertIsNotNone(created_task)

        # 关闭数据库连接
        self.db.close()

        # 重新打开数据库
        self.db.initialize()

        # 验证数据恢复
        recovered_task = self.task_dao.select_by_id("test-task-persist")
        self.assertIsNotNone(recovered_task)
        self.assertEqual(recovered_task.name, "Test Persistence Task")
        self.assertEqual(recovered_task.command, "echo 'persistence test'")

        print("✓ Task persistence test passed")

    def test_audit_persistence(self):
        """测试审计日志持久化"""
        # 创建审计日志
        audit_log = AuditLog(
            audit_id="test-audit-persist",
            action=AuditAction.TASK_CREATED,
            category=AuditCategory.TASK,
            level=EventLevel.INFO,
            actor="test-user",
            target_type="task",
            target_id="test-task-persist",
            message="Task created for persistence test",
            metadata={"test": "persistence"},
            created_at=datetime.utcnow(),
        )

        # 插入数据
        created_audit = self.audit_dao.insert(audit_log)
        self.assertIsNotNone(created_audit)

        # 关闭数据库连接
        self.db.close()

        # 重新打开数据库
        self.db.initialize()

        # 验证数据恢复
        recovered_audit = self.audit_dao.select_by_id("test-audit-persist")
        self.assertIsNotNone(recovered_audit)
        self.assertEqual(recovered_audit.action, AuditAction.TASK_CREATED)
        self.assertEqual(recovered_audit.message, "Task created for persistence test")

        print("✓ Audit persistence test passed")

    def test_multiple_operations(self):
        """测试多次操作的持久化"""
        # 创建多个资产
        for i in range(5):
            asset = Asset(
                asset_id=f"test-asset-{i}",
                name=f"Test Asset {i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.REGISTERED,
                metadata=AssetMetadata(ip_address=f"192.168.1.{100+i}", hostname=f"asset{i}.local"),
                description=f"Test asset {i}",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.asset_dao.insert(asset)

        # 验证数据保存
        assets = self.asset_dao.list()
        self.assertEqual(len(assets), 5)

        # 重启数据库
        self.db.close()
        self.db.initialize()

        # 验证数据恢复
        recovered_assets = self.asset_dao.list()
        self.assertEqual(len(recovered_assets), 5)

        # 验证数据完整性
        for asset in recovered_assets:
            self.assertIsNotNone(asset.asset_id)
            self.assertTrue(asset.asset_id.startswith("test-asset-"))
            self.assertIsNotNone(asset.metadata)

        print("✓ Multiple operations persistence test passed")

    def test_update_persistence(self):
        """测试更新操作的持久化"""
        # 创建资产
        asset = Asset(
            asset_id="test-asset-update",
            name="Original Name",
            asset_type=AssetType.LINUX_HOST,
            status=AssetStatus.REGISTERED,
            metadata=AssetMetadata(ip_address="192.168.1.1"),
            description="Original description",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.asset_dao.insert(asset)

        # 更新资产
        asset.name = "Updated Name"
        asset.description = "Updated description"
        asset.updated_at = datetime.utcnow()
        self.asset_dao.update(asset)

        # 重启数据库
        self.db.close()
        self.db.initialize()

        # 验证更新持久化
        recovered_asset = self.asset_dao.select_by_id("test-asset-update")
        self.assertEqual(recovered_asset.name, "Updated Name")
        self.assertEqual(recovered_asset.description, "Updated description")

        print("✓ Update persistence test passed")

    def test_delete_persistence(self):
        """测试删除操作的持久化"""
        # 创建资产
        asset = Asset(
            asset_id="test-asset-delete",
            name="To Be Deleted",
            asset_type=AssetType.LINUX_HOST,
            status=AssetStatus.REGISTERED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.asset_dao.insert(asset)

        # 删除资产
        self.asset_dao.delete("test-asset-delete")

        # 重启数据库
        self.db.close()
        self.db.initialize()

        # 验证删除持久化
        recovered_asset = self.asset_dao.select_by_id("test-asset-delete")
        self.assertIsNone(recovered_asset)

        print("✓ Delete persistence test passed")


if __name__ == "__main__":
    # 运行测试
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDatabasePersistence)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出结果
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✓ All database persistence tests passed!")
    else:
        print("✗ Some tests failed")
        sys.exit(1)
