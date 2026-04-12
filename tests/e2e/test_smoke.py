"""
Smoke Tests - 快速系统健康检查

在5分钟内验证系统核心功能是否正常工作
这是每次代码变更后的第一道验证门禁
"""

import unittest
import tempfile
import os
import time
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy import text

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database.sqlite_backend import SQLiteBackend
from shared.services.asset_service import AssetService
from shared.services.task_service import TaskService
from shared.services.audit_service import AuditService
from shared.security.auth_manager import AuthManager
from shared.models.asset import Asset, AssetType, AssetStatus
from shared.models.task import Task, TaskType, TaskStatus, TaskPriority
from shared.models.audit import AuditLog, AuditAction, AuditCategory, EventLevel


class TestSmokeHealthCheck(unittest.TestCase):
    """系统健康检查 - Smoke Tests"""

    @classmethod
    def setUpClass(cls):
        """Smoke测试初始化"""
        print("\n" + "="*60)
        print("🔥 HermesNexus Smoke Tests - 系统健康检查")
        print("="*60)
        cls.start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        """Smoke测试完成"""
        elapsed_time = time.time() - cls.start_time
        print("\n" + "="*60)
        print(f"✅ Smoke Tests 完成 - 耗时: {elapsed_time:.2f}秒")
        print("="*60)

    def setUp(self):
        """每个测试前的设置"""
        # 创建临时数据库
        self.temp_dir = tempfile.mkdtemp(prefix="smoke_test_")
        self.db_path = os.path.join(self.temp_dir, "smoke.db")

        # 初始化数据库
        self.db = SQLiteBackend(db_path=self.db_path)
        self.db.initialize()
        self.db.create_tables()  # 创建数据库表

        # 初始化服务
        self.asset_service = AssetService(database=self.db)
        self.task_service = TaskService(database=self.db)
        self.audit_service = AuditService(database=self.db)
        self.auth_manager = AuthManager()

    def tearDown(self):
        """清理临时资源"""
        import shutil
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_01_database_health(self):
        """测试1: 数据库健康检查"""
        print("\n[1/6] 🗄️  数据库健康检查...")

        # 检查数据库连接
        self.assertIsNotNone(self.db, "数据库连接应该存在")

        # 检查数据库文件是否创建
        self.assertTrue(os.path.exists(self.db_path), "数据库文件应该存在")

        # 检查基本表是否创建
        session = self.db._get_session()
        try:
            # 简单查询验证表存在
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result.fetchall()]
            self.assertIn('assets', tables, "assets表应该存在")
            self.assertIn('tasks', tables, "tasks表应该存在")
            self.assertIn('audit_logs', tables, "audit_logs表应该存在")
            print("   ✓ 数据库连接正常")
            print(f"   ✓ 数据表已创建: {', '.join(tables)}")
        finally:
            session.close()

    def test_02_asset_service_health(self):
        """测试2: 资产服务健康检查"""
        print("\n[2/6] 📦 资产服务健康检查...")

        # 创建测试资产
        test_asset = Asset(
            asset_id="smoke-asset-001",
            name="Smoke测试资产",
            asset_type=AssetType.LINUX_HOST,
            status=AssetStatus.ACTIVE,
            description="用于Smoke测试的资产"
        )

        # 创建资产
        created_asset = self.asset_service.create_asset(test_asset)
        self.assertIsNotNone(created_asset, "资产创建应该成功")

        # 查询资产
        retrieved_asset = self.asset_service.get_asset("smoke-asset-001")
        self.assertIsNotNone(retrieved_asset, "资产查询应该成功")
        self.assertEqual(retrieved_asset.name, "Smoke测试资产")

        # 统计检查
        stats = self.asset_service.get_statistics()
        self.assertEqual(stats['total_assets'], 1, "应该有1个资产")

        print("   ✓ 资产创建成功")
        print("   ✓ 资产查询成功")
        print("   ✓ 统计功能正常")

    def test_03_task_service_health(self):
        """测试3: 任务服务健康检查"""
        print("\n[3/6] ⚙️  任务服务健康检查...")

        # 先创建资产
        asset = Asset(
            asset_id="smoke-asset-002",
            name="Smoke任务资产",
            asset_type=AssetType.LINUX_HOST,
            status=AssetStatus.ACTIVE
        )
        self.asset_service.create_asset(asset)

        # 创建测试任务
        test_task = Task(
            task_id="smoke-task-001",
            name="Smoke测试任务",
            task_type=TaskType.BASIC_EXEC,
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            target_asset_id="smoke-asset-002",
            command="echo 'smoke test'",
            timeout=30,
            created_by="smoke-test",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # 创建任务
        created_task = self.task_service.create_task(test_task)
        self.assertIsNotNone(created_task, "任务创建应该成功")

        # 查询任务
        retrieved_task = self.task_service.get_task("smoke-task-001")
        self.assertIsNotNone(retrieved_task, "任务查询应该成功")

        # 任务状态变更测试
        updated_task = self.task_service.assign_node_to_task("smoke-task-001", "smoke-node-001")
        self.assertEqual(updated_task.status, TaskStatus.ASSIGNED, "任务分配应该成功")

        print("   ✓ 任务创建成功")
        print("   ✓ 任务查询成功")
        print("   ✓ 任务状态变更成功")

    def test_04_audit_service_health(self):
        """测试4: 审计服务健康检查"""
        print("\n[4/6] 📋 审计服务健康检查...")

        # 创建审计日志请求
        from shared.models.audit import AuditLogCreateRequest

        audit_request = AuditLogCreateRequest(
            action=AuditAction.ASSET_REGISTERED,
            category=AuditCategory.ASSET,
            level=EventLevel.INFO,
            actor="smoke-test-user",
            target_type="asset",
            target_id="smoke-asset-003",
            message="Smoke测试审计日志"
        )

        # 插入审计日志
        audit_log = self.audit_service.log_action(audit_request)

        # 查询审计日志
        retrieved_log = self.audit_service.get_audit_log(audit_log.audit_id)
        self.assertIsNotNone(retrieved_log, "审计日志查询应该成功")

        # 列表查询
        logs = self.audit_service.list_audit_logs(limit=10)
        self.assertGreater(len(logs), 0, "应该有审计日志")

        print("   ✓ 审计日志创建成功")
        print("   ✓ 审计日志查询成功")
        print(f"   ✓ 当前审计日志数量: {len(logs)}")

    def test_05_auth_service_health(self):
        """测试5: 认证服务健康检查"""
        print("\n[5/6] 🔐 认证服务健康检查...")

        # Token创建和验证
        # 创建Token
        token = self.auth_manager.create_token(
            user_id="smoke-user-001",
            username="smokeuser",
            role="operator",
            permissions=["asset.read", "task.read"]
        )
        self.assertIsNotNone(token, "Token创建应该成功")

        # 验证Token
        validated_user = self.auth_manager.validate_token(token)
        self.assertIsNotNone(validated_user, "Token验证应该成功")
        self.assertEqual(validated_user['user_id'], 'smoke-user-001')

        # API Key创建和验证
        api_key = self.auth_manager.create_api_key(
            user_id="smoke-user-002",
            name="smoke-api-key"
        )
        self.assertIsNotNone(api_key, "API Key创建应该成功")

        validated_key = self.auth_manager.validate_api_key(api_key)
        self.assertIsNotNone(validated_key, "API Key验证应该成功")

        print("   ✓ Token创建和验证成功")
        print("   ✓ API Key创建和验证成功")
        print("   ✓ 认证服务运行正常")

    def test_06_integration_health(self):
        """测试6: 集成健康检查"""
        print("\n[6/6] 🔗 集成健康检查...")

        # 创建完整的业务流程
        # 1. 创建资产
        asset = Asset(
            asset_id="smoke-integration-asset",
            name="集成测试资产",
            asset_type=AssetType.LINUX_HOST,
            status=AssetStatus.ACTIVE
        )
        self.asset_service.create_asset(asset)

        # 2. 创建任务
        task = Task(
            task_id="smoke-integration-task",
            name="集成测试任务",
            task_type=TaskType.BASIC_EXEC,
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            target_asset_id="smoke-integration-asset",
            command="echo 'integration smoke test'",
            timeout=30,
            created_by="smoke-integration-test",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.task_service.create_task(task)

        # 3. 验证集成关系
        asset_logs = self.audit_service.query_by_asset("smoke-integration-asset")
        task_logs = self.audit_service.query_by_task("smoke-integration-task")

        self.assertGreater(len(asset_logs), 0, "应该有资产相关的审计日志")
        self.assertGreater(len(task_logs), 0, "应该有任务相关的审计日志")

        # 4. 验证数据一致性
        retrieved_asset = self.asset_service.get_asset("smoke-integration-asset")
        retrieved_task = self.task_service.get_task("smoke-integration-task")

        self.assertEqual(retrieved_task.target_asset_id, retrieved_asset.asset_id, "任务应该关联到正确的资产")

        print("   ✓ 资产-任务关联正确")
        print("   ✓ 审计追踪完整")
        print("   ✓ 数据一致性验证通过")

    def test_performance_baseline(self):
        """性能基线检查"""
        print("\n[⚡] 性能基线检查...")

        # 测试批量操作性能
        start_time = time.time()

        # 批量创建10个资产
        for i in range(10):
            asset = Asset(
                asset_id=f"smoke-perf-{i:03d}",
                name=f"性能测试资产-{i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE
            )
            self.asset_service.create_asset(asset)

        creation_time = time.time() - start_time

        # 批量查询性能
        start_time = time.time()
        all_assets = self.asset_service.list_assets()
        query_time = time.time() - start_time

        self.assertGreaterEqual(len(all_assets), 10, "应该至少有10个资产")
        self.assertLess(creation_time, 5.0, "批量创建应该在5秒内完成")
        self.assertLess(query_time, 1.0, "批量查询应该在1秒内完成")

        print(f"   ✓ 批量创建10个资产耗时: {creation_time:.3f}秒")
        print(f"   ✓ 批量查询耗时: {query_time:.3f}秒")
        print("   ✓ 性能基线检查通过")


class TestSmokeQuickCheck(unittest.TestCase):
    """快速检查 - 最关键的功能验证"""

    def setUp(self):
        """快速设置"""
        self.temp_dir = tempfile.mkdtemp(prefix="quick_smoke_")
        self.db_path = os.path.join(self.temp_dir, "quick.db")
        self.db = SQLiteBackend(db_path=self.db_path)
        self.db.initialize()
        self.db.create_tables()  # 创建数据库表

        self.asset_service = AssetService(database=self.db)
        self.task_service = TaskService(database=self.db)

    def tearDown(self):
        """快速清理"""
        import shutil
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_critical_path_only(self):
        """只测试最关键的路径"""
        print("\n[🚀] 快速关键路径检查...")

        # 1. 数据库可用
        self.assertIsNotNone(self.db)

        # 2. 能创建资产
        asset = self.asset_service.create_asset(Asset(
            asset_id="quick-asset",
            name="快速检查资产",
            asset_type=AssetType.LINUX_HOST,
            status=AssetStatus.ACTIVE
        ))
        self.assertIsNotNone(asset)

        # 3. 能创建任务
        task = self.task_service.create_task(Task(
            task_id="quick-task",
            name="快速检查任务",
            task_type=TaskType.BASIC_EXEC,
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            target_asset_id="quick-asset",
            command="echo 'quick'",
            timeout=30,
            created_by="quick",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ))
        self.assertIsNotNone(task)

        print("   ✓ 数据库: OK")
        print("   ✓ 资产服务: OK")
        print("   ✓ 任务服务: OK")
        print("   ✅ 快速检查通过 - 系统核心功能正常")


def run_smoke_tests():
    """运行Smoke测试的主函数"""
    print("\n" + "="*70)
    print("🔥 HermesNexus Smoke Tests - 快速系统健康检查")
    print("="*70)
    print("这些测试在5分钟内验证系统核心功能")
    print("如果Smoke测试失败，不要继续其他测试")
    print("="*70)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加健康检查测试
    suite.addTests(loader.loadTestsFromTestCase(TestSmokeHealthCheck))

    # 添加快速检查测试
    suite.addTests(loader.loadTestsFromTestCase(TestSmokeQuickCheck))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出结果
    print("\n" + "="*70)
    if result.wasSuccessful():
        print("✅ Smoke Tests 全部通过 - 系统健康")
        print("="*70)
        return 0
    else:
        print("❌ Smoke Tests 失败 - 系统存在问题")
        print("="*70)
        print(f"失败数: {len(result.failures)}")
        print(f"错误数: {len(result.errors)}")
        return 1


if __name__ == "__main__":
    exit_code = run_smoke_tests()
    sys.exit(exit_code)
