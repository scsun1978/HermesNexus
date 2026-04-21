"""
HermesNexus Phase 4 Day 2 性能基线测试
建立性能基线，确保系统性能符合生产要求
"""

import unittest
import tempfile
import os
import time
import statistics
from pathlib import Path
from datetime import datetime, timezone

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
import sys
sys.path.insert(0, str(project_root))

from shared.database.sqlite_backend import SQLiteBackend
from shared.services.asset_service import AssetService
from shared.services.task_service import TaskService
from shared.services.audit_service import AuditService
from shared.models.asset import Asset, AssetType, AssetStatus
from shared.models.task import Task, TaskType, TaskStatus, TaskPriority
from shared.models.audit import AuditAction, AuditCategory, EventLevel


class TestPerformanceBaseline(unittest.TestCase):
    """性能基线测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = self.temp_db.name

        # 初始化数据库和服务
        self.db = SQLiteBackend(self.db_path)
        self.db.initialize()

        self.asset_service = AssetService(database=self.db)
        self.task_service = TaskService(database=self.db)
        self.audit_service = AuditService(database=self.db)

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_asset_service_performance_baseline(self):
        """资产服务性能基线测试"""
        print(f"\n🚀 资产服务性能基线测试")

        # 测试1: 批量创建资产性能
        start_time = time.time()
        asset_count = 100

        for i in range(asset_count):
            asset = Asset(
                asset_id=f"perf-asset-{i:04d}",
                name=f"Performance Test Asset {i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.REGISTERED,
                description="Performance baseline test asset"
            )
            self.asset_service.create_asset(asset)

        creation_time = time.time() - start_time
        assets_per_second = asset_count / creation_time

        print(f"  📊 创建 {asset_count} 个资产耗时: {creation_time:.3f}秒")
        print(f"  📈 创建速率: {assets_per_second:.1f} 资产/秒")

        # 性能基线要求
        self.assertLess(creation_time, 5.0, "批量创建资产应在5秒内完成")
        self.assertGreater(assets_per_second, 20, "创建速率应大于20资产/秒")

        # 测试2: 查询性能
        start_time = time.time()

        assets = self.asset_service.list_assets()

        query_time = time.time() - start_time
        query_rate = asset_count / query_time if query_time > 0 else float('inf')

        print(f"  📊 查询 {asset_count} 个资产耗时: {query_time:.3f}秒")
        print(f"  📈 查询速率: {query_rate:.1f} 资产/秒")

        # 性能基线要求
        self.assertLess(query_time, 1.0, "资产查询应在1秒内完成")
        self.assertGreater(query_rate, 100, "查询速率应大于100资产/秒")

        # 测试3: 单个资产查询性能
        start_time = time.time()

        asset = self.asset_service.get_asset("perf-asset-0050")

        single_query_time = time.time() - start_time

        print(f"  📊 单个资产查询耗时: {single_query_time*1000:.2f}毫秒")

        # 性能基线要求
        self.assertLess(single_query_time, 0.1, "单个资产查询应在100毫秒内完成")
        self.assertIsNotNone(asset, "应能查询到资产")

        print(f"✅ 资产服务性能基线测试通过")

    def test_task_service_performance_baseline(self):
        """任务服务性能基线测试"""
        print(f"\n🚀 任务服务性能基线测试")

        # 先创建一些资产作为任务目标
        for i in range(10):
            asset = Asset(
                asset_id=f"perf-task-asset-{i}",
                name=f"Task Target {i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE
            )
            self.asset_service.create_asset(asset)

        # 测试1: 批量创建任务性能
        start_time = time.time()
        task_count = 50

        for i in range(task_count):
            task = Task(
                task_id=f"perf-task-{i:04d}",
                name=f"Performance Test Task {i}",
                task_type=TaskType.BASIC_EXEC,
                status=TaskStatus.PENDING,
                priority=TaskPriority.NORMAL,
                target_asset_id=f"perf-task-asset-{i % 10}",
                command="echo 'performance test'",
                created_by="performance_test"
            )
            self.task_service.create_task(task)

        creation_time = time.time() - start_time
        tasks_per_second = task_count / creation_time

        print(f"  📊 创建 {task_count} 个任务耗时: {creation_time:.3f}秒")
        print(f"  📈 创建速率: {tasks_per_second:.1f} 任务/秒")

        # 性能基线要求
        self.assertLess(creation_time, 3.0, "批量创建任务应在3秒内完成")
        self.assertGreater(tasks_per_second, 15, "创建速率应大于15任务/秒")

        # 测试2: 任务查询性能
        start_time = time.time()

        tasks = self.task_service.list_tasks()

        query_time = time.time() - start_time
        query_rate = task_count / query_time if query_time > 0 else float('inf')

        print(f"  📊 查询 {task_count} 个任务耗时: {query_time:.3f}秒")
        print(f"  📈 查询速率: {query_rate:.1f} 任务/秒")

        # 性能基线要求
        self.assertLess(query_time, 1.0, "任务查询应在1秒内完成")
        self.assertGreater(query_rate, 50, "查询速率应大于50任务/秒")

        # 测试3: 任务状态更新性能
        start_time = time.time()

        for i in range(10):
            task = self.task_service.get_task(f"perf-task-{i:04d}")
            task.status = TaskStatus.ASSIGNED
            self.task_service.update_task(task)

        update_time = time.time() - start_time
        update_rate = 10 / update_time if update_time > 0 else float('inf')

        print(f"  📊 更新10个任务状态耗时: {update_time:.3f}秒")
        print(f"  📈 更新速率: {update_rate:.1f} 任务/秒")

        # 性能基线要求
        self.assertLess(update_time, 1.0, "批量状态更新应在1秒内完成")
        self.assertGreater(update_rate, 10, "更新速率应大于10任务/秒")

        print(f"✅ 任务服务性能基线测试通过")

    def test_audit_service_performance_baseline(self):
        """审计服务性能基线测试"""
        print(f"\n🚀 审计服务性能基线测试")

        # 测试1: 批量创建审计日志性能
        start_time = time.time()
        audit_count = 200

        for i in range(audit_count):
            audit = self.audit_service.log_event(
                action=AuditAction.TASK_CREATED,
                category=AuditCategory.TASK,
                level=EventLevel.INFO,
                actor="performance_test",
                target_type="task",
                target_id=f"perf-task-{i}",
                message=f"Performance test audit log {i}",
                details={"test": True, "index": i}
            )

        creation_time = time.time() - start_time
        audits_per_second = audit_count / creation_time

        print(f"  📊 创建 {audit_count} 条审计日志耗时: {creation_time:.3f}秒")
        print(f"  📈 创建速率: {audits_per_second:.1f} 日志/秒")

        # 性能基线要求
        self.assertLess(creation_time, 2.0, "批量创建审计日志应在2秒内完成")
        self.assertGreater(audits_per_second, 100, "创建速率应大于100日志/秒")

        # 测试2: 审计日志查询性能
        start_time = time.time()

        stats = self.audit_service.get_audit_stats()

        query_time = time.time() - start_time

        print(f"  📊 获取审计统计耗时: {query_time*1000:.2f}毫秒")

        # 性能基线要求
        self.assertLess(query_time, 0.5, "统计查询应在500毫秒内完成")
        self.assertEqual(stats.total_events, audit_count, "统计应包含所有审计日志")

        # 测试3: 审计日志过滤查询性能
        start_time = time.time()

        filtered_logs = self.audit_service.query_by_task("perf-task-50", limit=10)

        query_time = time.time() - start_time

        print(f"  📊 过滤查询审计日志耗时: {query_time*1000:.2f}毫秒")

        # 性能基线要求
        self.assertLess(query_time, 0.3, "过滤查询应在300毫秒内完成")
        self.assertGreaterEqual(len(filtered_logs), 1, "应能查询到相关审计日志")

        print(f"✅ 审计服务性能基线测试通过")

    def test_concurrent_operations_performance(self):
        """并发操作性能测试"""
        print(f"\n🚀 并发操作性能测试")

        import threading
        import queue

        results = queue.Queue()
        num_threads = 10
        operations_per_thread = 10

        def worker(thread_id):
            """工作线程"""
            thread_results = []
            start_time = time.time()

            for i in range(operations_per_thread):
                op_start = time.time()

                # 执行操作
                asset = Asset(
                    asset_id=f"concurrent-asset-{thread_id}-{i}",
                    name=f"Concurrent Asset {thread_id}-{i}",
                    asset_type=AssetType.LINUX_HOST,
                    status=AssetStatus.REGISTERED
                )
                self.asset_service.create_asset(asset)

                op_time = time.time() - op_start
                thread_results.append(op_time * 1000)  # 转换为毫秒

            thread_time = time.time() - start_time
            results.put({
                'thread_id': thread_id,
                'thread_time': thread_time,
                'operation_times': thread_results
            })

        # 启动并发线程
        start_time = time.time()

        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        total_time = time.time() - start_time
        total_operations = num_threads * operations_per_thread
        ops_per_second = total_operations / total_time

        # 分析结果
        all_operation_times = []
        while not results.empty():
            result = results.get()
            all_operation_times.extend(result['operation_times'])

        avg_op_time = statistics.mean(all_operation_times)
        max_op_time = max(all_operation_times)
        min_op_time = min(all_operation_times)

        print(f"  📊 并发操作总数: {total_operations}")
        print(f"  📊 总耗时: {total_time:.3f}秒")
        print(f"  📈 总吞吐量: {ops_per_second:.1f} 操作/秒")
        print(f"  📊 平均操作耗时: {avg_op_time:.2f}毫秒")
        print(f"  📊 最大操作耗时: {max_op_time:.2f}毫秒")
        print(f"  📊 最小操作耗时: {min_op_time:.2f}毫秒")

        # 性能基线要求
        self.assertLess(total_time, 5.0, "并发操作应在5秒内完成")
        self.assertGreater(ops_per_second, 20, "并发吞吐量应大于20操作/秒")
        self.assertLess(avg_op_time, 200, "平均操作耗时应小于200毫秒")

        print(f"✅ 并发操作性能测试通过")


class TestSystemResourceBaseline(unittest.TestCase):
    """系统资源使用基线测试"""

    def test_memory_usage_baseline(self):
        """内存使用基线测试"""
        print(f"\n🚀 内存使用基线测试")

        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            rss_mb = memory_info.rss / 1024 / 1024  # 常驻内存
            vms_mb = memory_info.vms / 1024 / 1024  # 虚拟内存

            print(f"  📊 RSS内存: {rss_mb:.1f} MB")
            print(f"  📊 VMS内存: {vms_mb:.1f} MB")

            # 性能基线要求
            self.assertLess(rss_mb, 200, "RSS内存应小于200MB")
            self.assertLess(vms_mb, 500, "VMS内存应小于500MB")

            print(f"✅ 内存使用基线测试通过")

        except ImportError:
            self.skipTest("psutil未安装，跳过内存测试")

    def test_cpu_efficiency_baseline(self):
        """CPU效率基线测试"""
        print(f"\n🚀 CPU效率基线测试")

        try:
            import psutil
            import time

            # 测试CPU使用效率 - 执行密集计算
            process = psutil.Process()

            # 测量空闲时的CPU使用
            time.sleep(0.1)
            idle_cpu = process.cpu_percent(interval=0.1)

            # 执行一些工作
            start_time = time.time()
            work_start_cpu = process.cpu_percent()

            # 执行计算密集工作
            result = sum(i * i for i in range(10000))

            work_time = time.time() - start_time
            work_cpu = process.cpu_percent(interval=0.1)

            print(f"  📊 空闲CPU: {idle_cpu}%")
            print(f"  📊 工作CPU: {work_cpu}%")
            print(f"  📊 工作耗时: {work_time*1000:.2f}毫秒")
            print(f"  📊 计算结果: {result}")

            # 性能基线要求
            self.assertLess(work_time, 1.0, "计算工作应在1秒内完成")
            self.assertLess(idle_cpu, 20, "空闲CPU使用应小于20%")

            print(f"✅ CPU效率基线测试通过")

        except ImportError:
            self.skipTest("psutil未安装，跳过CPU测试")


if __name__ == '__main__':
    # 运行性能基线测试
    print("🚀 开始HermesNexus性能基线测试")
    print("=" * 50)

    # 运行测试
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试用例
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceBaseline))
    suite.addTests(loader.loadTestsFromTestCase(TestSystemResourceBaseline))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出总结
    print("\n" + "=" * 50)
    print("📊 性能基线测试总结")
    print(f"  运行测试数: {result.testsRun}")
    print(f"  成功数: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  失败数: {len(result.failures)}")
    print(f"  错误数: {len(result.errors)}")

    if result.wasSuccessful():
        print("✅ 所有性能基线测试通过")
    else:
        print("❌ 部分性能基线测试失败")

    print("=" * 50)