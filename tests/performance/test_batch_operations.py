"""
批量操作性能测试 - 验证优化效果
测试单个操作 vs 批量操作的性能差异
"""

import unittest
import tempfile
import os
import time
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database.sqlite_backend import SQLiteBackend
from shared.dao.asset_dao import AssetDAO
from shared.dao.task_dao import TaskDAO
from shared.dao.audit_dao import AuditDAO
from shared.models.asset import Asset, AssetType, AssetStatus
from shared.models.task import Task, TaskType, TaskStatus, TaskPriority
from shared.models.audit import AuditLog, AuditAction, AuditCategory, EventLevel


class TestBatchOperationsPerformance(unittest.TestCase):
    """批量操作性能测试"""

    @classmethod
    def setUpClass(cls):
        """测试初始化"""
        print("\n" + "=" * 70)
        print("⚡ 批量操作性能测试 - 验证优化效果")
        print("=" * 70)

    def setUp(self):
        """每个测试前的设置"""
        # 创建临时数据库
        self.temp_dir = tempfile.mkdtemp(prefix="batch_perf_test_")
        self.db_path = os.path.join(self.temp_dir, "batch_perf.db")

        # 初始化数据库
        self.db = SQLiteBackend(db_path=self.db_path)
        self.db.initialize()
        self.db.create_tables()

        # 创建DAO实例
        self.asset_dao = AssetDAO(database=self.db)
        self.task_dao = TaskDAO(database=self.db)
        self.audit_dao = AuditDAO(database=self.db)

    def tearDown(self):
        """清理临时资源"""
        import shutil

        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_asset_batch_insert_performance(self):
        """测试资产批量插入性能"""
        print("\n📦 资产批量插入性能测试...")

        # 测试单个插入性能
        print("  🔸 测试单个插入10个资产...")
        single_insert_times = []
        for i in range(10):
            asset = Asset(
                asset_id=f"single-asset-{i:04d}",
                name=f"单个插入资产-{i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE,
                description="单个插入测试",
            )

            start = time.time()
            self.asset_dao.insert(asset)
            elapsed = time.time() - start
            single_insert_times.append(elapsed)

        single_total = sum(single_insert_times)
        single_avg = sum(single_insert_times) / len(single_insert_times)

        print(f"     单个插入总耗时: {single_total:.3f}秒")
        print(f"     单个插入平均耗时: {single_avg*1000:.3f}毫秒")

        # 测试批量插入性能
        print("  🔹 测试批量插入10个资产...")
        batch_assets = []
        for i in range(10, 20):
            asset = Asset(
                asset_id=f"batch-asset-{i:04d}",
                name=f"批量插入资产-{i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE,
                description="批量插入测试",
            )
            batch_assets.append(asset)

        start = time.time()
        self.asset_dao.insert_batch(batch_assets)
        batch_total = time.time() - start
        batch_avg = batch_total / len(batch_assets)

        print(f"     批量插入总耗时: {batch_total:.3f}秒")
        print(f"     批量插入平均耗时: {batch_avg*1000:.3f}毫秒")

        # 计算性能提升
        speedup = single_total / batch_total if batch_total > 0 else float("inf")
        improvement = ((single_total - batch_total) / single_total) * 100 if single_total > 0 else 0

        print(f"  📈 性能提升: {speedup:.1f}x ({improvement:.1f}%)")

        # 验证性能提升
        self.assertGreater(speedup, 1.5, "批量插入应该至少快1.5倍")
        print("  ✅ 批量插入性能测试通过")

    def test_asset_batch_query_performance(self):
        """测试资产批量查询性能"""
        print("\n🔍 资产批量查询性能测试...")

        # 先插入50个资产
        print("  🔸 准备测试数据...")
        assets = []
        for i in range(50):
            asset = Asset(
                asset_id=f"query-test-asset-{i:04d}",
                name=f"查询测试资产-{i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE,
                description="查询测试",
            )
            assets.append(asset)

        self.asset_dao.insert_batch(assets)

        # 测试单个查询性能
        print("  🔸 测试单个查询10个资产...")
        single_query_times = []
        test_ids = [f"query-test-asset-{i:04d}" for i in range(10)]

        for asset_id in test_ids:
            start = time.time()
            self.asset_dao.select_by_id(asset_id)
            elapsed = time.time() - start
            single_query_times.append(elapsed)

        single_total = sum(single_query_times)
        single_avg = sum(single_query_times) / len(single_query_times)

        print(f"     单个查询总耗时: {single_total:.3f}秒")
        print(f"     单个查询平均耗时: {single_avg*1000:.3f}毫秒")

        # 测试批量查询性能
        print("  🔹 测试批量查询10个资产...")
        start = time.time()
        batch_results = self.asset_dao.select_by_ids(test_ids)
        batch_total = time.time() - start
        batch_avg = batch_total / len(test_ids)

        print(f"     批量查询总耗时: {batch_total:.3f}秒")
        print(f"     批量查询平均耗时: {batch_avg*1000:.3f}毫秒")
        print(f"     查询结果数: {len(batch_results)}")

        # 计算性能提升
        speedup = single_total / batch_total if batch_total > 0 else float("inf")
        improvement = ((single_total - batch_total) / single_total) * 100 if single_total > 0 else 0

        print(f"  📈 性能提升: {speedup:.1f}x ({improvement:.1f}%)")

        # 验证批量查询结果
        self.assertEqual(len(batch_results), len(test_ids), "应该查询到所有资产")
        self.assertGreater(speedup, 2.0, "批量查询应该至少快2倍")
        print("  ✅ 批量查询性能测试通过")

    def test_task_batch_operations_performance(self):
        """测试任务批量操作性能"""
        print("\n⚙️ 任务批量操作性能测试...")

        # 先创建一些资产作为关联
        assets = []
        for i in range(5):
            asset = Asset(
                asset_id=f"task-test-asset-{i}",
                name=f"任务测试资产-{i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE,
            )
            assets.append(asset)
        self.asset_dao.insert_batch(assets)

        # 测试任务批量插入
        print("  🔹 测试批量插入20个任务...")
        tasks = []
        for i in range(20):
            task = Task(
                task_id=f"batch-task-{i:04d}",
                name=f"批量插入任务-{i}",
                task_type=TaskType.BASIC_EXEC,
                status=TaskStatus.PENDING,
                priority=TaskPriority.NORMAL,
                target_asset_id=f"task-test-asset-{i % 5}",
                command="echo 'batch task'",
                timeout=30,
                created_by="performance-test",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            tasks.append(task)

        start = time.time()
        self.task_dao.insert_batch(tasks)
        batch_time = time.time() - start

        print(f"     批量插入20个任务耗时: {batch_time:.3f}秒")
        print(f"     平均每个任务: {(batch_time/20)*1000:.3f}毫秒")

        # 测试任务批量查询
        print("  🔹 测试批量查询10个任务...")
        task_ids = [f"batch-task-{i:04d}" for i in range(10)]

        start = time.time()
        queried_tasks = self.task_dao.select_by_ids(task_ids)
        query_time = time.time() - start

        print(f"     批量查询10个任务耗时: {query_time:.3f}秒")
        print(f"     查询结果数: {len(queried_tasks)}")

        self.assertEqual(len(queried_tasks), len(task_ids), "应该查询到所有任务")
        print("  ✅ 任务批量操作性能测试通过")

    def test_audit_batch_insert_performance(self):
        """测试审计日志批量插入性能"""
        print("\n📋 审计日志批量插入性能测试...")

        # 测试批量插入100条审计日志
        print("  🔹 测试批量插入100条审计日志...")
        audit_logs = []
        for i in range(100):
            audit_log = AuditLog(
                audit_id=f"batch-audit-{i:04d}",
                action=AuditAction.TASK_CREATED,
                category=AuditCategory.TASK,
                level=EventLevel.INFO,
                actor="performance-test",
                target_type="task",
                target_id=f"batch-task-{i:04d}",
                message=f"审计日志 {i}",
            )
            audit_logs.append(audit_log)

        start = time.time()
        self.audit_dao.insert_batch(audit_logs)
        batch_time = time.time() - start

        print(f"     批量插入100条审计日志耗时: {batch_time:.3f}秒")
        print(f"     平均每条日志: {(batch_time/100)*1000:.3f}毫秒")
        print(f"     吞吐量: {100/batch_time:.1f} logs/sec")

        # 验证插入性能
        throughput = 100 / batch_time
        self.assertGreater(throughput, 50, "应该至少达到50 logs/sec的吞吐量")
        print("  ✅ 审计日志批量插入性能测试通过")

    def test_mixed_batch_operations(self):
        """测试混合批量操作场景"""
        print("\n🔄 混合批量操作场景测试...")

        # 场景1: 批量创建资产和相关任务
        print("  🔹 场景1: 批量创建5个资产及其相关任务...")

        start = time.time()
        # 批量创建资产
        assets = []
        for i in range(5):
            asset = Asset(
                asset_id=f"mixed-asset-{i}",
                name=f"混合测试资产-{i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE,
            )
            assets.append(asset)
        self.asset_dao.insert_batch(assets)

        # 批量创建任务
        tasks = []
        for i in range(5):
            task = Task(
                task_id=f"mixed-task-{i}",
                name=f"混合测试任务-{i}",
                task_type=TaskType.BASIC_EXEC,
                status=TaskStatus.PENDING,
                priority=TaskPriority.NORMAL,
                target_asset_id=f"mixed-asset-{i}",
                command="echo 'mixed test'",
                timeout=30,
                created_by="mixed-test",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            tasks.append(task)
        self.task_dao.insert_batch(tasks)

        # 批量创建审计日志
        audit_logs = []
        for i in range(5):
            audit_log = AuditLog(
                audit_id=f"mixed-audit-{i}",
                action=AuditAction.TASK_CREATED,
                category=AuditCategory.TASK,
                level=EventLevel.INFO,
                actor="mixed-test",
                target_type="task",
                target_id=f"mixed-task-{i}",
                message=f"混合测试审计日志 {i}",
            )
            audit_logs.append(audit_log)
        self.audit_dao.insert_batch(audit_logs)

        total_time = time.time() - start

        print(f"     总耗时: {total_time:.3f}秒")
        print(f"     创建了: {len(assets)}个资产, {len(tasks)}个任务, {len(audit_logs)}条审计日志")

        # 验证所有数据都创建成功
        queried_assets = self.asset_dao.select_by_ids([a.asset_id for a in assets])
        queried_tasks = self.task_dao.select_by_ids([t.task_id for t in tasks])

        self.assertEqual(len(queried_assets), len(assets), "所有资产应该创建成功")
        self.assertEqual(len(queried_tasks), len(tasks), "所有任务应该创建成功")

        print("  ✅ 混合批量操作场景测试通过")


def run_performance_tests():
    """运行性能测试的主函数"""
    print("\n" + "=" * 70)
    print("🚀 HermesNexus 批量操作性能测试")
    print("=" * 70)
    print("测试目标: 验证批量操作相对单个操作的性能提升")
    print("=" * 70)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestBatchOperationsPerformance)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出结果
    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print("✅ 批量操作性能测试全部通过")
        print("=" * 70)
        print("📈 性能优化效果验证:")
        print("  - 批量插入性能显著提升")
        print("  - 批量查询避免N+1问题")
        print("  - 数据库往返次数大幅减少")
        print("=" * 70)
        return 0
    else:
        print("❌ 批量操作性能测试失败")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = run_performance_tests()
    sys.exit(exit_code)
