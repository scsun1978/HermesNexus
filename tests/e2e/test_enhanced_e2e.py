"""
增强的E2E测试 - 具有失败诊断和详细输出

在端到端测试中，当测试失败时提供详细的诊断信息
"""

import unittest
import tempfile
import os
import traceback
import sys
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database.sqlite_backend import SQLiteBackend
from shared.services.asset_service import AssetService
from shared.services.task_service import TaskService
from shared.services.audit_service import AuditService
from shared.security.auth_manager import AuthManager
from shared.models.asset import Asset, AssetType, AssetStatus
from shared.models.task import (
    Task,
    TaskType,
    TaskStatus,
    TaskPriority,
    TaskExecutionResult,
)
from shared.models.audit import AuditAction, EventLevel


class E2ETestResult:
    """E2E测试结果记录器"""

    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = time.time()
        self.checkpoints = []
        self.errors = []
        self.warnings = []
        self.success = False

    def add_checkpoint(self, name: str, details: str = ""):
        """添加检查点"""
        self.checkpoints.append(
            {"name": name, "details": details, "timestamp": time.time()}
        )

    def add_error(self, error: str, details: str = ""):
        """添加错误"""
        self.errors.append(
            {
                "error": error,
                "details": details,
                "timestamp": time.time(),
                "traceback": traceback.format_exc(),
            }
        )

    def add_warning(self, warning: str, details: str = ""):
        """添加警告"""
        self.warnings.append(
            {"warning": warning, "details": details, "timestamp": time.time()}
        )

    def finish(self, success: bool = True):
        """完成测试"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success

    def generate_report(self) -> str:
        """生成测试报告"""
        report = []
        report.append(f"\n{'='*60}")
        report.append(f"E2E测试报告: {self.test_name}")
        report.append(f"{'='*60}")

        # 测试结果
        status = "✅ 通过" if self.success else "❌ 失败"
        report.append(f"状态: {status}")
        report.append(f"耗时: {self.duration:.2f}秒")

        # 检查点
        if self.checkpoints:
            report.append(f"\n检查点 ({len(self.checkpoints)}):")
            for i, cp in enumerate(self.checkpoints, 1):
                elapsed = cp["timestamp"] - self.start_time
                report.append(f"  {i}. {cp['name']} (+{elapsed:.2f}s)")
                if cp["details"]:
                    report.append(f"     详情: {cp['details']}")

        # 警告
        if self.warnings:
            report.append(f"\n⚠️  警告 ({len(self.warnings)}):")
            for warning in self.warnings:
                report.append(f"  - {warning['warning']}")
                if warning["details"]:
                    report.append(f"    {warning['details']}")

        # 错误
        if self.errors:
            report.append(f"\n❌ 错误 ({len(self.errors)}):")
            for error in self.errors:
                report.append(f"  - {error['error']}")
                if error["details"]:
                    report.append(f"    详情: {error['details']}")
                if error["traceback"]:
                    report.append(f"    堆栈:\n{error['traceback']}")

        report.append(f"{'='*60}\n")
        return "\n".join(report)


class EnhancedE2ETest(unittest.TestCase):
    """增强的E2E测试基类"""

    def setUp(self):
        """测试设置"""
        self.test_result = E2ETestResult(self._testMethodName)
        self.temp_dir = None
        self.db = None
        self.services = {}

        try:
            # 创建临时环境
            self.temp_dir = tempfile.mkdtemp(prefix="e2e_test_")
            self.db_path = os.path.join(self.temp_dir, "e2e.db")

            # 初始化数据库
            self.db = SQLiteBackend(db_path=self.db_path)
            self.db.initialize()
            self.db.create_tables()  # 创建数据库表
            self.test_result.add_checkpoint("环境初始化", f"临时数据库: {self.db_path}")

            # 初始化服务
            self.services["asset"] = AssetService(database=self.db)
            self.services["task"] = TaskService(database=self.db)
            self.services["audit"] = AuditService(database=self.db)
            self.services["auth"] = AuthManager()
            self.test_result.add_checkpoint("服务初始化", "所有服务已创建")

        except Exception as e:
            self.test_result.add_error("环境设置失败", str(e))
            self.test_result.finish(False)
            self.fail(self.test_result.generate_report())

    def tearDown(self):
        """测试清理"""
        try:
            # 如果测试失败，保留临时文件用于诊断
            if not self._outcome.errors and not self._outcome.failures:
                self._cleanup_temp_files()
            else:
                self.test_result.add_warning(
                    "临时文件保留", f"由于测试失败，临时文件已保留在: {self.temp_dir}"
                )

            # 生成测试报告
            success = not (self._outcome.errors or self._outcome.failures)
            self.test_result.finish(success)

            # 如果测试失败，打印详细报告
            if not success:
                print(self.test_result.generate_report())

        except Exception as e:
            print(f"清理过程中出错: {e}")

    def _cleanup_temp_files(self):
        """清理临时文件"""
        import shutil

        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                self.test_result.add_warning("清理失败", str(e))


class TestCompleteWorkflowE2E(EnhancedE2ETest):
    """完整工作流E2E测试"""

    def test_complete_user_workflow(self):
        """测试完整的用户工作流"""
        try:
            # Step 1: 用户登录
            self.test_result.add_checkpoint("用户认证")
            user_info = {
                "user_id": "e2e-user-001",
                "username": "e2euser",
                "role": "operator",
                "permissions": ["asset.read", "asset.write", "task.read", "task.write"],
            }
            token = self.services["auth"].create_token(user_info)
            self.assertIsNotNone(token, "Token创建应该成功")

            # Step 2: 创建资产
            self.test_result.add_checkpoint("创建资产")
            asset = Asset(
                asset_id="e2e-asset-001",
                name="E2E测试资产",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE,
                description="端到端测试资产",
                created_by="e2e-user-001",  # 添加created_by字段
            )
            created_asset = self.services["asset"].create_asset(
                asset, created_by="e2e-user-001"
            )
            self.assertIsNotNone(created_asset)
            self.assertEqual(created_asset.asset_id, "e2e-asset-001")

            # Step 3: 创建任务
            self.test_result.add_checkpoint("创建任务")
            task = Task(
                task_id="e2e-task-001",
                name="E2E测试任务",
                task_type=TaskType.BASIC_EXEC,
                status=TaskStatus.PENDING,
                priority=TaskPriority.NORMAL,
                target_asset_id="e2e-asset-001",
                command="uptime && free -h && df -h",
                timeout=60,
                description="系统信息收集任务",
                created_by="e2e-user-001",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            created_task = self.services["task"].create_task(task)
            self.assertIsNotNone(created_task)

            # Step 4: 任务分配
            self.test_result.add_checkpoint("任务分配")
            assigned_task = self.services["task"].assign_node_to_task(
                "e2e-task-001", "e2e-node-001"
            )
            self.assertEqual(assigned_task.status, TaskStatus.ASSIGNED)

            # Step 5: 任务执行
            self.test_result.add_checkpoint("任务执行")
            running_task = self.services["task"].start_task(
                "e2e-task-001", "e2e-node-001"
            )
            self.assertEqual(running_task.status, TaskStatus.RUNNING)
            self.assertIsNotNone(running_task.started_at)

            # Step 6: 任务完成
            self.test_result.add_checkpoint("任务完成")
            result = TaskExecutionResult(
                exit_code=0,
                stdout="load average: 0.01, 0.02, 0.05\nMem: 16G total",
                stderr="",
                completed_at=datetime.utcnow(),
            )
            completed_task = self.services["task"].complete_task("e2e-task-001", result)
            self.assertEqual(completed_task.status, TaskStatus.COMPLETED)
            self.assertIsNotNone(completed_task.completed_at)

            # Step 7: 验证审计追踪
            self.test_result.add_checkpoint("审计追踪验证")
            audit_logs = self.services["audit"].query_by_asset("e2e-asset-001")
            self.assertGreater(len(audit_logs), 0, "应该有审计日志")

            # 验证审计日志完整性
            actions = [log.action for log in audit_logs]
            self.assertIn(AuditAction.ASSET_REGISTERED, actions)
            self.assertIn(AuditAction.TASK_CREATED, actions)

            # Step 8: 查询和统计
            self.test_result.add_checkpoint("数据查询")
            all_assets = self.services["asset"].list_assets()
            all_tasks = self.services["task"].list_tasks()

            self.assertGreaterEqual(len(all_assets), 1)
            self.assertGreaterEqual(len(all_tasks), 1)

            # Step 9: 资产状态更新
            self.test_result.add_checkpoint("状态更新")
            updated_asset = Asset(
                asset_id="e2e-asset-001",
                name="E2E测试资产",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.INACTIVE,  # 状态变更
                description="维护中",
                meta_data={"location": "data-center-1"},
            )
            self.services["asset"].update_asset(updated_asset)

            retrieved_asset = self.services["asset"].get_asset("e2e-asset-001")
            self.assertEqual(retrieved_asset.status, AssetStatus.INACTIVE)

            # Step 10: 数据一致性验证
            self.test_result.add_checkpoint("数据一致性验证")
            stats = self.services["asset"].get_statistics()
            self.assertEqual(stats["total_assets"], 1)

            print("\n✅ 完整工作流测试通过")

        except Exception as e:
            self.test_result.add_error("工作流测试失败", str(e))
            raise

    def test_error_handling_workflow(self):
        """测试错误处理工作流"""
        try:
            self.test_result.add_checkpoint("错误处理测试开始")

            # 创建资产
            asset = Asset(
                asset_id="e2e-error-asset",
                name="错误测试资产",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE,
            )
            self.services["asset"].create_asset(asset)

            # 创建会失败的任务
            task = Task(
                task_id="e2e-error-task",
                name="会失败的任务",
                task_type=TaskType.BASIC_EXEC,
                status=TaskStatus.PENDING,
                priority=TaskPriority.NORMAL,
                target_asset_id="e2e-error-asset",
                command="exit 1",  # 故意失败
                timeout=30,
                created_by="e2e-error-test",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.services["task"].create_task(task)

            # 执行任务
            self.services["task"].assign_node_to_task("e2e-error-task", "error-node")
            self.services["task"].start_task("e2e-error-task", "error-node")

            # 标记任务失败
            result = TaskExecutionResult(
                exit_code=1,
                stdout="",
                stderr="Command failed",
                completed_at=datetime.utcnow(),
            )
            failed_task = self.services["task"].complete_task("e2e-error-task", result)

            # 验证失败状态
            self.assertEqual(failed_task.status, TaskStatus.FAILED)

            # 验证错误审计日志
            audit_logs = self.services["audit"].query_by_task("e2e-error-task")
            error_logs = [log for log in audit_logs if log.level == EventLevel.ERROR]
            self.assertGreater(len(error_logs), 0, "应该有错误级别的审计日志")

            self.test_result.add_checkpoint("错误处理验证完成")
            print("\n✅ 错误处理工作流测试通过")

        except Exception as e:
            self.test_result.add_error("错误处理测试失败", str(e))
            raise

    def test_concurrent_users_workflow(self):
        """测试并发用户工作流"""
        try:
            self.test_result.add_checkpoint("并发用户测试开始")

            # 模拟3个并发用户
            users = [
                {"user_id": "e2e-concurrent-1", "username": "user1"},
                {"user_id": "e2e-concurrent-2", "username": "user2"},
                {"user_id": "e2e-concurrent-3", "username": "user3"},
            ]

            # 每个用户创建资产和任务
            for user in users:
                # 创建资产（传递created_by参数）
                asset = Asset(
                    asset_id=f"e2e-asset-{user['user_id']}",
                    name=f"{user['username']}'s asset",
                    asset_type=AssetType.LINUX_HOST,
                    status=AssetStatus.ACTIVE,
                    created_by=user["user_id"],  # 添加created_by字段
                )
                self.services["asset"].create_asset(asset, created_by=user["user_id"])

                # 创建任务
                task = Task(
                    task_id=f"e2e-task-{user['user_id']}",
                    name=f"{user['username']}'s task",
                    task_type=TaskType.BASIC_EXEC,
                    status=TaskStatus.PENDING,
                    priority=TaskPriority.NORMAL,
                    target_asset_id=f"e2e-asset-{user['user_id']}",
                    command=f"echo '{user['username']}'",
                    timeout=30,
                    created_by=user["user_id"],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                self.services["task"].create_task(task)

            # 验证数据隔离和一致性
            all_assets = self.services["asset"].list_assets()
            all_tasks = self.services["task"].list_tasks()

            self.assertEqual(len(all_assets), 3, "应该有3个资产")
            self.assertEqual(len(all_tasks), 3, "应该有3个任务")

            # 验证每个用户的资源
            for user in users:
                user_assets = [a for a in all_assets if a.created_by == user["user_id"]]
                user_tasks = [t for t in all_tasks if t.created_by == user["user_id"]]

                self.assertEqual(
                    len(user_assets), 1, f"{user['username']}应该有1个资产"
                )
                self.assertEqual(len(user_tasks), 1, f"{user['username']}应该有1个任务")

            self.test_result.add_checkpoint("并发用户验证完成")
            print("\n✅ 并发用户工作流测试通过")

        except Exception as e:
            self.test_result.add_error("并发用户测试失败", str(e))
            raise


class TestSystemDiagnosticsE2E(EnhancedE2ETest):
    """系统诊断E2E测试"""

    def test_database_diagnostics(self):
        """数据库诊断"""
        try:
            self.test_result.add_checkpoint("数据库诊断开始")

            # 测试数据库连接
            session = self.db._get_session()
            self.assertIsNotNone(session)

            # 检查表结构
            from sqlalchemy import text

            result = session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in result.fetchall()]

            self.assertIn("assets", tables)
            self.assertIn("tasks", tables)
            self.assertIn("audit_logs", tables)

            # 检查索引
            result = session.execute(
                text("SELECT name FROM sqlite_master WHERE type='index'")
            )
            indexes = [row[0] for row in result.fetchall()]

            self.test_result.add_checkpoint(
                "数据库结构检查", f"表: {len(tables)}, 索引: {len(indexes)}"
            )

            session.close()

        except Exception as e:
            self.test_result.add_error("数据库诊断失败", str(e))
            raise

    def test_service_diagnostics(self):
        """服务诊断"""
        try:
            self.test_result.add_checkpoint("服务诊断开始")

            # 测试每个服务的健康状态
            services_to_check = ["asset", "task", "audit"]

            for service_name in services_to_check:
                service = self.services[service_name]

                # 创建测试数据
                if service_name == "asset":
                    test_entity = Asset(
                        asset_id="diagnostic-asset",
                        name="诊断资产",
                        asset_type=AssetType.LINUX_HOST,
                        status=AssetStatus.ACTIVE,
                    )
                    created = service.create_asset(test_entity)
                    retrieved = service.get_asset("diagnostic-asset")

                elif service_name == "task":
                    # 先创建依赖的资产
                    asset = Asset(
                        asset_id="diagnostic-task-asset",
                        name="诊断任务资产",
                        asset_type=AssetType.LINUX_HOST,
                        status=AssetStatus.ACTIVE,
                    )
                    self.services["asset"].create_asset(asset)

                    test_entity = Task(
                        task_id="diagnostic-task",
                        name="诊断任务",
                        task_type=TaskType.BASIC_EXEC,
                        status=TaskStatus.PENDING,
                        priority=TaskPriority.NORMAL,
                        target_asset_id="diagnostic-task-asset",
                        command="echo 'diagnostic'",
                        timeout=30,
                        created_by="diagnostic",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    created = service.create_task(test_entity)
                    retrieved = service.get_task("diagnostic-task")

                self.assertIsNotNone(created, f"{service_name}服务创建应该成功")
                self.assertIsNotNone(retrieved, f"{service_name}服务查询应该成功")

            self.test_result.add_checkpoint("服务诊断完成")

        except Exception as e:
            self.test_result.add_error("服务诊断失败", str(e))
            raise


if __name__ == "__main__":
    # 运行增强的E2E测试
    unittest.main(verbosity=2)
