"""
集成测试 - 资产/任务/审计主线集成测试

测试资产管理、任务编排和审计追踪的完整集成流程
"""

import unittest
import tempfile
import os
from pathlib import Path
from datetime import datetime
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database.sqlite_backend import SQLiteBackend
from shared.services.asset_service import AssetService
from shared.services.task_service import TaskService
from shared.services.audit_service import AuditService
from shared.models.asset import Asset, AssetType, AssetStatus
from shared.models.task import Task, TaskType, TaskStatus, TaskPriority
from shared.models.audit import AuditLog, AuditAction, AuditCategory, EventLevel


class TestAssetTaskAuditIntegration(unittest.TestCase):
    """测试资产、任务、审计的主线集成流程"""

    def setUp(self):
        """测试前设置 - 使用临时数据库"""
        # 创建临时数据库文件
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_integration.db")

        # 初始化数据库
        self.db = SQLiteBackend(db_path=self.db_path)
        self.db.initialize()
        self.db.create_tables()  # 创建数据库表

        # 初始化服务
        self.asset_service = AssetService(database=self.db)
        self.task_service = TaskService(database=self.db)
        self.audit_service = AuditService(database=self.db)

    def tearDown(self):
        """测试后清理 - 删除临时数据库"""
        import shutil

        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_complete_asset_lifecycle(self):
        """测试资产完整生命周期: 创建 -> 任务执行 -> 状态变更 -> 审计追踪"""
        print("\n=== 测试资产完整生命周期 ===")

        # Step 1: 创建资产
        print("Step 1: 创建资产")
        asset = Asset(
            asset_id="test-asset-integration-001",
            name="集成测试资产",
            asset_type=AssetType.LINUX_HOST,
            status=AssetStatus.ACTIVE,
            description="用于集成测试的资产",
            meta_data={"ip": "192.168.1.100", "ssh_port": 22},
        )

        created_asset = self.asset_service.create_asset(asset)
        self.assertIsNotNone(created_asset)
        self.assertEqual(created_asset.asset_id, "test-asset-integration-001")

        # 验证审计日志
        audit_logs = self.audit_service.query_by_asset(
            "test-asset-integration-001", limit=5
        )
        self.assertGreater(len(audit_logs), 0, "应该有审计日志记录")

        # Step 2: 创建并执行任务
        print("Step 2: 创建并执行任务")
        task = Task(
            task_id="test-task-integration-001",
            name="集成测试任务",
            task_type=TaskType.BASIC_EXEC,
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            target_asset_id="test-asset-integration-001",
            target_node_id="test-node-001",
            command="uptime",
            timeout=30,
            description="用于集成测试的任务",
            created_by="integration-test-user",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        created_task = self.task_service.create_task(task)
        self.assertIsNotNone(created_task)
        self.assertEqual(created_task.status, TaskStatus.PENDING)

        # 验证任务相关的审计日志
        task_audit_logs = self.audit_service.query_by_task(
            "test-task-integration-001", limit=5
        )
        self.assertGreater(len(task_audit_logs), 0, "应该有任务相关的审计日志")

        # Step 3: 模拟任务状态变更
        print("Step 3: 模拟任务状态变更")

        # 分配任务
        updated_task = self.task_service.assign_node_to_task(
            "test-task-integration-001", "test-node-001"
        )
        self.assertEqual(updated_task.status, TaskStatus.ASSIGNED)

        # 开始执行
        updated_task = self.task_service.start_task(
            "test-task-integration-001", "test-node-001"
        )
        self.assertEqual(updated_task.status, TaskStatus.RUNNING)
        self.assertIsNotNone(updated_task.started_at)

        # 完成任务
        from shared.models.task import TaskExecutionResult

        result = TaskExecutionResult(
            exit_code=0,
            stdout=" load average: 0.01, 0.02, 0.05",
            stderr="",
            completed_at=datetime.utcnow(),
        )
        updated_task = self.task_service.complete_task(
            "test-task-integration-001", result
        )
        self.assertEqual(updated_task.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(updated_task.completed_at)

        # Step 4: 验证审计追踪完整性
        print("Step 4: 验证审计追踪完整性")

        # 查询资产相关的所有审计日志
        asset_audit_logs = self.audit_service.query_by_asset(
            "test-asset-integration-001"
        )
        print(f"资产相关审计日志数量: {len(asset_audit_logs)}")

        # 应该包含: 资产创建、任务创建、任务分配、任务开始、任务完成等
        audit_actions = [log.action for log in asset_audit_logs]
        print(f"审计操作类型: {audit_actions}")

        self.assertIn(AuditAction.ASSET_REGISTERED, audit_actions, "应该包含资产创建操作")
        self.assertIn(AuditAction.TASK_CREATED, audit_actions, "应该包含任务创建操作")

        # Step 5: 验证资产状态变更
        print("Step 5: 验证资产状态变更")

        # 查询资产信息
        retrieved_asset = self.asset_service.get_asset("test-asset-integration-001")
        self.assertIsNotNone(retrieved_asset)
        self.assertEqual(retrieved_asset.status, AssetStatus.ACTIVE)

        # 统计信息验证
        stats = self.asset_service.get_statistics()
        self.assertGreater(stats["total_assets"], 0)

        print("✅ 资产完整生命周期测试通过")

    def test_task_failure_audit_flow(self):
        """测试任务失败时的审计流程"""
        print("\n=== 测试任务失败审计流程 ===")

        # 创建资产
        asset = Asset(
            asset_id="test-asset-fail-001",
            name="失败测试资产",
            asset_type=AssetType.LINUX_HOST,
            status=AssetStatus.ACTIVE,
            description="用于测试失败流程的资产",
            meta_data={"ip": "192.168.1.101"},
        )

        self.asset_service.create_asset(asset)

        # 创建任务
        task = Task(
            task_id="test-task-fail-001",
            name="会失败的任务",
            task_type=TaskType.BASIC_EXEC,
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            target_asset_id="test-asset-fail-001",
            command="exit 1",  # 故意失败
            timeout=30,
            description="测试失败处理",
            created_by="integration-test-user",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.task_service.create_task(task)

        # 开始任务
        self.task_service.assign_node_to_task("test-task-fail-001", "test-node-001")
        self.task_service.start_task("test-task-fail-001", "test-node-001")

        # 标记任务失败
        from shared.models.task import TaskExecutionResult

        result = TaskExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Command failed with exit code 1",
            completed_at=datetime.utcnow(),
        )

        failed_task = self.task_service.complete_task("test-task-fail-001", result)
        self.assertEqual(failed_task.status, TaskStatus.FAILED)

        # 验证失败审计日志
        audit_logs = self.audit_service.query_by_task("test-task-fail-001")
        failure_logs = [log for log in audit_logs if log.level == EventLevel.ERROR]

        self.assertGreater(len(failure_logs), 0, "应该有错误级别的审计日志")
        print(f"失败审计日志数量: {len(failure_logs)}")

        print("✅ 任务失败审计流程测试通过")

    def test_concurrent_operations(self):
        """测试并发操作的集成"""
        print("\n=== 测试并发操作集成 ===")

        # 批量创建资产
        assets = []
        for i in range(5):
            asset = Asset(
                asset_id=f"test-asset-concurrent-{i:03d}",
                name=f"并发测试资产-{i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE,
                description=f"并发测试资产 {i}",
                meta_data={"index": i},
            )
            assets.append(asset)

        # 批量创建
        for asset in assets:
            self.asset_service.create_asset(asset)

        # 批量创建任务
        tasks = []
        for i in range(5):
            task = Task(
                task_id=f"test-task-concurrent-{i:03d}",
                name=f"并发测试任务-{i}",
                task_type=TaskType.BASIC_EXEC,
                status=TaskStatus.PENDING,
                priority=TaskPriority.NORMAL,
                target_asset_id=f"test-asset-concurrent-{i:03d}",
                command=f"echo 'concurrent test {i}'",
                timeout=30,
                description=f"并发测试任务 {i}",
                created_by="integration-test-user",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            tasks.append(task)

        # 批量创建任务
        for task in tasks:
            self.task_service.create_task(task)

        # 验证批量操作结果
        all_assets = self.asset_service.list_assets()
        self.assertGreaterEqual(len(all_assets), 5, "应该至少有5个资产")

        all_tasks = self.task_service.list_tasks()
        self.assertGreaterEqual(len(all_tasks), 5, "应该至少有5个任务")

        # 验证审计日志
        all_audit_logs = self.audit_service.list_audit_logs()
        print(f"总审计日志数量: {len(all_audit_logs)}")

        self.assertGreaterEqual(len(all_audit_logs), 10, "应该有大量审计日志记录")

        print("✅ 并发操作集成测试通过")

    def test_data_consistency(self):
        """测试数据一致性"""
        print("\n=== 测试数据一致性 ===")

        # 创建完整的业务流程
        asset = Asset(
            asset_id="test-asset-consistency-001",
            name="一致性测试资产",
            asset_type=AssetType.LINUX_HOST,
            status=AssetStatus.ACTIVE,
            description="测试数据一致性",
            meta_data={"test": "consistency"},
        )

        created_asset = self.asset_service.create_asset(asset)

        task = Task(
            task_id="test-task-consistency-001",
            name="一致性测试任务",
            task_type=TaskType.BASIC_EXEC,
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            target_asset_id="test-asset-consistency-001",
            command="echo 'consistency test'",
            timeout=30,
            created_by="consistency-test-user",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        created_task = self.task_service.create_task(task)

        # 验证数据一致性
        # 1. 资产ID一致
        retrieved_asset = self.asset_service.get_asset(created_asset.asset_id)
        self.assertEqual(retrieved_asset.asset_id, created_asset.asset_id)

        # 2. 任务关联资产ID一致
        retrieved_task = self.task_service.get_task(created_task.task_id)
        self.assertEqual(retrieved_task.target_asset_id, created_asset.asset_id)

        # 3. 审计日志关联一致
        asset_audit = self.audit_service.query_by_asset(created_asset.asset_id)
        task_audit = self.audit_service.query_by_task(created_task.task_id)

        self.assertGreater(len(asset_audit), 0, "资产审计日志应该存在")
        self.assertGreater(len(task_audit), 0, "任务审计日志应该存在")

        # 4. 统计数据一致性
        asset_stats = self.asset_service.get_statistics()
        self.assertEqual(asset_stats["total_assets"], 1)

        print("✅ 数据一致性测试通过")


if __name__ == "__main__":
    unittest.main()
