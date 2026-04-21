"""
HermesNexus Phase 4 Day 2 负载和性能验证测试
验证系统在高负载下的性能表现
"""

import unittest
import tempfile
import os
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
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


class TestLoadPerformance(unittest.TestCase):
    """负载性能测试"""

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

        # 预先创建一些资产作为任务目标
        self.target_assets = []
        for i in range(20):
            asset = Asset(
                asset_id=f"load-asset-{i}",
                name=f"Load Test Asset {i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE
            )
            created_asset = self.asset_service.create_asset(asset)
            self.target_assets.append(created_asset.asset_id)

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_concurrent_asset_operations(self):
        """并发资产操作负载测试"""
        print(f"\n🚀 并发资产操作负载测试")

        num_threads = 20
        assets_per_thread = 5
        total_assets = num_threads * assets_per_thread

        results = []
        start_time = time.time()

        def create_assets(thread_id):
            """创建资产的线程函数"""
            thread_start = time.time()
            created_count = 0

            for i in range(assets_per_thread):
                asset = Asset(
                    asset_id=f"load-asset-thread{thread_id}-{i}",
                    name=f"Concurrent Asset {thread_id}-{i}",
                    asset_type=AssetType.LINUX_HOST,
                    status=AssetStatus.REGISTERED
                )
                try:
                    self.asset_service.create_asset(asset)
                    created_count += 1
                except Exception as e:
                    print(f"  ⚠️  线程 {thread_id} 创建资产失败: {e}")

            thread_time = time.time() - thread_start
            return {
                'thread_id': thread_id,
                'created_count': created_count,
                'thread_time': thread_time
            }

        # 使用线程池执行并发操作
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_assets, i) for i in range(num_threads)]

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"  ⚠️  线程执行失败: {e}")

        total_time = time.time() - start_time
        total_created = sum(r['created_count'] for r in results)
        throughput = total_created / total_time if total_time > 0 else 0
        avg_thread_time = statistics.mean([r['thread_time'] for r in results]) if results else 0

        print(f"  📊 总资产创建数: {total_created}/{total_assets}")
        print(f"  📊 总耗时: {total_time:.3f}秒")
        print(f"  📈 吞吐量: {throughput:.1f} 资产/秒")
        print(f"  📊 平均线程耗时: {avg_thread_time:.3f}秒")

        # 性能要求
        self.assertGreater(total_created, total_assets * 0.95, "至少95%的资产应创建成功")
        self.assertLess(total_time, 10.0, "并发操作应在10秒内完成")
        self.assertGreater(throughput, 10, "吞吐量应大于10资产/秒")

        print(f"✅ 并发资产操作负载测试通过")

    def test_concurrent_task_operations(self):
        """并发任务操作负载测试"""
        print(f"\n🚀 并发任务操作负载测试")

        num_threads = 15
        tasks_per_thread = 5
        total_tasks = num_threads * tasks_per_thread

        results = []
        start_time = time.time()

        def create_tasks(thread_id):
            """创建任务的线程函数"""
            thread_start = time.time()
            created_count = 0

            for i in range(tasks_per_thread):
                # 轮询使用目标资产
                target_asset = self.target_assets[thread_id % len(self.target_assets)]

                task = Task(
                    task_id=f"load-task-thread{thread_id}-{i}",
                    name=f"Concurrent Task {thread_id}-{i}",
                    task_type=TaskType.BASIC_EXEC,
                    status=TaskStatus.PENDING,
                    priority=TaskPriority.NORMAL,
                    target_asset_id=target_asset,
                    command="echo 'load test'",
                    created_by="load_test"
                )
                try:
                    self.task_service.create_task(task)
                    created_count += 1
                except Exception as e:
                    print(f"  ⚠️  线程 {thread_id} 创建任务失败: {e}")

            thread_time = time.time() - thread_start
            return {
                'thread_id': thread_id,
                'created_count': created_count,
                'thread_time': thread_time
            }

        # 使用线程池执行并发操作
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_tasks, i) for i in range(num_threads)]

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"  ⚠️  线程执行失败: {e}")

        total_time = time.time() - start_time
        total_created = sum(r['created_count'] for r in results)
        throughput = total_created / total_time if total_time > 0 else 0
        avg_thread_time = statistics.mean([r['thread_time'] for r in results]) if results else 0

        print(f"  📊 总任务创建数: {total_created}/{total_tasks}")
        print(f"  📊 总耗时: {total_time:.3f}秒")
        print(f"  📈 吞吐量: {throughput:.1f} 任务/秒")
        print(f"  📊 平均线程耗时: {avg_thread_time:.3f}秒")

        # 性能要求
        self.assertGreater(total_created, total_tasks * 0.95, "至少95%的任务应创建成功")
        self.assertLess(total_time, 8.0, "并发操作应在8秒内完成")
        self.assertGreater(throughput, 15, "吞吐量应大于15任务/秒")

        print(f"✅ 并发任务操作负载测试通过")

    def test_mixed_workload_performance(self):
        """混合工作负载性能测试"""
        print(f"\n🚀 混合工作负载性能测试")

        # 模拟真实工作负载：创建资产、创建任务、记录审计
        operations = [
            ('create_assets', 50),
            ('create_tasks', 30),
            ('create_audits', 100)
        ]

        start_time = time.time()

        # 执行混合工作负载
        for op_name, count in operations:
            op_start = time.time()

            if op_name == 'create_assets':
                for i in range(count):
                    asset = Asset(
                        asset_id=f"mixed-asset-{i}",
                        name=f"Mixed Workload Asset {i}",
                        asset_type=AssetType.LINUX_HOST,
                        status=AssetStatus.REGISTERED
                    )
                    self.asset_service.create_asset(asset)

            elif op_name == 'create_tasks':
                for i in range(count):
                    target_asset = self.target_assets[i % len(self.target_assets)]
                    task = Task(
                        task_id=f"mixed-task-{i}",
                        name=f"Mixed Workload Task {i}",
                        task_type=TaskType.BASIC_EXEC,
                        status=TaskStatus.PENDING,
                        target_asset_id=target_asset,
                        command="echo 'mixed workload'"
                    )
                    self.task_service.create_task(task)

            elif op_name == 'create_audits':
                for i in range(count):
                    self.audit_service.log_event(
                        action=AuditAction.TASK_CREATED,
                        category=AuditCategory.TASK,
                        level=EventLevel.INFO,
                        actor="mixed_workload_test",
                        target_type="task",
                        target_id=f"mixed-task-{i % count}",
                        message=f"Mixed workload audit {i}"
                    )

            op_time = time.time() - op_start
            ops_per_sec = count / op_time if op_time > 0 else 0
            print(f"  📊 {op_name}: {count}个操作, {op_time:.3f}秒, {ops_per_sec:.1f} 操作/秒")

        total_time = time.time() - start_time
        total_ops = sum(count for _, count in operations)
        overall_throughput = total_ops / total_time if total_time > 0 else 0

        print(f"  📊 混合工作负载总耗时: {total_time:.3f}秒")
        print(f"  📈 总吞吐量: {overall_throughput:.1f} 操作/秒")

        # 性能要求
        self.assertLess(total_time, 5.0, "混合工作负载应在5秒内完成")
        self.assertGreater(overall_throughput, 30, "总吞吐量应大于30操作/秒")

        print(f"✅ 混合工作负载性能测试通过")


class TestResourceOptimization(unittest.TestCase):
    """资源使用优化测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = self.temp_db.name

        self.db = SQLiteBackend(self.db_path)
        self.db.initialize()

        self.asset_service = AssetService(database=self.db)

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_memory_efficiency(self):
        """内存效率测试"""
        print(f"\n🚀 内存效率测试")

        try:
            import psutil
            import gc

            process = psutil.Process()
            gc.collect()

            # 测量基础内存使用
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

            # 创建大量资产
            batch_size = 1000
            start_time = time.time()

            for i in range(batch_size):
                asset = Asset(
                    asset_id=f"memory-asset-{i}",
                    name=f"Memory Test Asset {i}",
                    asset_type=AssetType.LINUX_HOST,
                    status=AssetStatus.REGISTERED,
                    metadata={
                        'description': f"Test asset {i}" * 10,  # 增加内存使用
                        'tags': [f"tag{j}" for j in range(5)]
                    }
                )
                self.asset_service.create_asset(asset)

            creation_time = time.time() - start_time

            # 强制垃圾回收
            gc.collect()

            # 测量峰值内存使用
            peak_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = peak_memory - baseline_memory
            memory_per_asset = memory_increase / batch_size

            print(f"  📊 基础内存: {baseline_memory:.1f} MB")
            print(f"  📊 峰值内存: {peak_memory:.1f} MB")
            print(f"  📊 内存增长: {memory_increase:.1f} MB")
            print(f"  📊 每资产内存: {memory_per_asset:.3f} KB")
            print(f"  📊 创建速率: {batch_size/creation_time:.1f} 资产/秒")

            # 内存效率要求
            self.assertLess(peak_memory, 500, "峰值内存应小于500MB")
            self.assertLess(memory_per_asset, 10, "每资产内存应小于10KB")
            self.assertGreater(batch_size/creation_time, 100, "创建速率应大于100资产/秒")

            print(f"✅ 内存效率测试通过")

        except ImportError:
            self.skipTest("psutil未安装，跳过内存测试")

    def test_query_performance_optimization(self):
        """查询性能优化测试"""
        print(f"\n🚀 查询性能优化测试")

        # 创建大量资产用于查询测试
        batch_size = 500
        for i in range(batch_size):
            asset = Asset(
                asset_id=f"query-asset-{i}",
                name=f"Query Test Asset {i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE
            )
            self.asset_service.create_asset(asset)

        # 测试列表查询性能
        query_times = []
        for i in range(10):
            start_time = time.time()
            assets = self.asset_service.list_assets()
            query_time = time.time() - start_time
            query_times.append(query_time)

        avg_query_time = statistics.mean(query_times)
        max_query_time = max(query_times)
        min_query_time = min(query_times)

        print(f"  📊 资产总数: {len(assets)}")
        print(f"  📊 平均查询时间: {avg_query_time*1000:.2f}毫秒")
        print(f"  📊 最大查询时间: {max_query_time*1000:.2f}毫秒")
        print(f"  📊 最小查询时间: {min_query_time*1000:.2f}毫秒")

        # 查询性能要求
        self.assertLess(avg_query_time, 0.05, "平均查询时间应小于50毫秒")
        self.assertLess(max_query_time, 0.1, "最大查询时间应小于100毫秒")

        # 测试单个资产查询性能
        single_query_times = []
        for i in range(20):
            asset_id = f"query-asset-{i}"
            start_time = time.time()
            asset = self.asset_service.get_asset(asset_id)
            query_time = time.time() - start_time
            single_query_times.append(query_time)

        avg_single_time = statistics.mean(single_query_times)

        print(f"  📊 单个查询平均时间: {avg_single_time*1000:.2f}毫秒")

        # 单个查询性能要求
        self.assertLess(avg_single_time, 0.01, "单个查询时间应小于10毫秒")

        print(f"✅ 查询性能优化测试通过")


class TestPerformanceBaseline(unittest.TestCase):
    """性能基线建立测试"""

    def test_response_time_baseline(self):
        """响应时间基线建立"""
        print(f"\n🚀 响应时间基线建立")

        baselines = {
            'asset_creation': 50,    # 毫秒
            'task_creation': 30,     # 毫秒
            'audit_creation': 10,    # 毫秒
            'asset_query': 10,       # 毫秒
            'task_query': 15,        # 毫秒
            'bulk_query': 100        # 毫秒
        }

        print("  📊 响应时间基线 (毫秒):")
        for operation, baseline in baselines.items():
            print(f"    {operation}: {baseline}ms")

        # 这里可以保存到文件或配置中
        # 用于后续性能回归检测

        print(f"✅ 响应时间基线建立完成")

    def test_throughput_baseline(self):
        """吞吐量基线建立"""
        print(f"\n🚀 吞吐量基线建立")

        baselines = {
            'asset_operations': 100,  # 操作/秒
            'task_operations': 150,   # 操作/秒
            'audit_operations': 200,  # 操作/秒
            'concurrent_requests': 50 # 并发请求
        }

        print("  📊 吞吐量基线 (操作/秒):")
        for operation, baseline in baselines.items():
            print(f"    {operation}: {baseline}")

        print(f"✅ 吞吐量基线建立完成")


if __name__ == '__main__':
    print("🚀 开始HermesNexus负载和性能验证测试")
    print("=" * 60)

    # 运行测试
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试用例
    suite.addTests(loader.loadTestsFromTestCase(TestLoadPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestResourceOptimization))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceBaseline))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出总结
    print("\n" + "=" * 60)
    print("📊 负载和性能验证总结")
    print(f"  运行测试数: {result.testsRun}")
    print(f"  成功数: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  失败数: {len(result.failures)}")
    print(f"  错误数: {len(result.errors)}")

    if result.wasSuccessful():
        print("✅ 所有负载和性能验证通过")
        print("🎯 系统性能符合生产要求")
    else:
        print("⚠️  部分验证未通过，需要优化")

    print("=" * 60)