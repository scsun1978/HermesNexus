"""
性能基线测试 - 建立系统性能基准

测试目标：
1. 建立数据库查询性能基线
2. 识别最慢的DAO操作
3. 评估系统容量和瓶颈
4. 为优化提供数据支持
"""

import unittest
import tempfile
import os
import time
import sys
import statistics
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database.sqlite_backend import SQLiteBackend
from shared.services.asset_service import AssetService
from shared.services.task_service import TaskService
from shared.services.audit_service import AuditService
from shared.dao.asset_dao import AssetDAO
from shared.dao.task_dao import TaskDAO
from shared.dao.audit_dao import AuditDAO
from shared.models.asset import Asset, AssetType, AssetStatus
from shared.models.task import Task, TaskType, TaskStatus, TaskPriority
from shared.models.audit import AuditLog, AuditAction, AuditCategory, EventLevel


class PerformanceMetric:
    """性能指标记录"""

    def __init__(self, name: str):
        self.name = name
        self.times = []
        self.count = 0
        self.errors = 0

    def start(self):
        """开始计时"""
        return time.time()

    def end(self, start_time: float, success: bool = True):
        """结束计时"""
        duration = time.time() - start_time
        self.times.append(duration)
        self.count += 1
        if not success:
            self.errors += 1
        return duration

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.times:
            return {
                "name": self.name,
                "count": 0,
                "errors": 0,
                "avg": 0,
                "min": 0,
                "max": 0,
                "median": 0,
                "p95": 0,
                "p99": 0,
            }

        sorted_times = sorted(self.times)
        return {
            "name": self.name,
            "count": self.count,
            "errors": self.errors,
            "avg": statistics.mean(self.times),
            "min": min(self.times),
            "max": max(self.times),
            "median": statistics.median(self.times),
            "p95": (
                sorted_times[int(len(sorted_times) * 0.95)]
                if len(sorted_times) >= 20
                else sorted_times[-1]
            ),
            "p99": (
                sorted_times[int(len(sorted_times) * 0.99)]
                if len(sorted_times) >= 100
                else sorted_times[-1]
            ),
        }


class TestDatabasePerformanceBaseline(unittest.TestCase):
    """数据库性能基线测试"""

    @classmethod
    def setUpClass(cls):
        """性能测试初始化"""
        print("\n" + "=" * 70)
        print("⚡ HermesNexus 性能基线测试")
        print("=" * 70)
        cls.start_time = time.time()
        cls.metrics = {}

    @classmethod
    def tearDownClass(cls):
        """生成性能报告"""
        elapsed_time = time.time() - cls.start_time
        print("\n" + "=" * 70)
        print(f"⚡ 性能测试完成 - 总耗时: {elapsed_time:.2f}秒")
        print("=" * 70)

        # 输出性能基线报告
        cls._generate_performance_report()

    def setUp(self):
        """每个测试前的设置"""
        # 创建临时数据库
        self.temp_dir = tempfile.mkdtemp(prefix="perf_test_")
        self.db_path = os.path.join(self.temp_dir, "perf.db")

        # 初始化数据库
        self.db = SQLiteBackend(db_path=self.db_path)
        self.db.initialize()
        self.db.create_tables()  # 创建数据库表

        # 创建DAO实例
        self.asset_dao = AssetDAO(database=self.db)
        self.task_dao = TaskDAO(database=self.db)
        self.audit_dao = AuditDAO(database=self.db)

    def tearDown(self):
        """清理临时资源"""
        import shutil

        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_01_asset_crud_performance(self):
        """测试1: 资产CRUD性能"""
        print("\n[1/6] 📦 资产CRUD性能测试...")

        metric = PerformanceMetric("资产CRUD")

        # 测试插入性能
        insert_times = []
        for i in range(100):
            start = metric.start()
            try:
                asset = Asset(
                    asset_id=f"perf-asset-{i:04d}",
                    name=f"性能测试资产-{i}",
                    asset_type=AssetType.LINUX_HOST,
                    status=AssetStatus.ACTIVE,
                    description="性能测试",
                )
                self.asset_dao.insert(asset)
                metric.end(start, True)
                insert_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"资产插入失败: {e}")

        # 测试查询性能
        query_times = []
        for i in range(100):
            start = metric.start()
            try:
                asset = self.asset_dao.select_by_id(f"perf-asset-{i:04d}")
                self.assertIsNotNone(asset)
                metric.end(start, True)
                query_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"资产查询失败: {e}")

        # 测试列表查询性能
        list_times = []
        for _ in range(20):
            start = metric.start()
            try:
                assets = self.asset_dao.list(limit=50)
                metric.end(start, True)
                list_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"资产列表查询失败: {e}")

        # 测试更新性能
        update_times = []
        for i in range(50):
            start = metric.start()
            try:
                asset = self.asset_dao.select_by_id(f"perf-asset-{i:04d}")
                asset.status = AssetStatus.INACTIVE
                self.asset_dao.update(asset)
                metric.end(start, True)
                update_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"资产更新失败: {e}")

        # 测试删除性能
        delete_times = []
        for i in range(50, 100):
            start = metric.start()
            try:
                self.asset_dao.delete(f"perf-asset-{i:04d}")
                metric.end(start, True)
                delete_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"资产删除失败: {e}")

        # 记录性能指标
        self.metrics["asset_insert"] = statistics.mean(insert_times)
        self.metrics["asset_query"] = statistics.mean(query_times)
        self.metrics["asset_list"] = statistics.mean(list_times)
        self.metrics["asset_update"] = statistics.mean(update_times)
        self.metrics["asset_delete"] = statistics.mean(delete_times)

        # 输出结果
        print(f"   插入性能: {statistics.mean(insert_times)*1000:.2f}ms (平均)")
        print(f"   查询性能: {statistics.mean(query_times)*1000:.2f}ms (平均)")
        print(f"   列表性能: {statistics.mean(list_times)*1000:.2f}ms (平均)")
        print(f"   更新性能: {statistics.mean(update_times)*1000:.2f}ms (平均)")
        print(f"   删除性能: {statistics.mean(delete_times)*1000:.2f}ms (平均)")

        self.__class__.metrics["asset_crud"] = metric.get_stats()

    def test_02_task_crud_performance(self):
        """测试2: 任务CRUD性能"""
        print("\n[2/6] ⚙️  任务CRUD性能测试...")

        metric = PerformanceMetric("任务CRUD")

        # 先创建一些资产用于关联
        for i in range(10):
            asset = Asset(
                asset_id=f"perf-task-asset-{i}",
                name=f"任务测试资产-{i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE,
            )
            self.asset_dao.insert(asset)

        # 测试任务插入性能
        insert_times = []
        for i in range(100):
            start = metric.start()
            try:
                task = Task(
                    task_id=f"perf-task-{i:04d}",
                    name=f"性能测试任务-{i}",
                    task_type=TaskType.BASIC_EXEC,
                    status=TaskStatus.PENDING,
                    priority=TaskPriority.NORMAL,
                    target_asset_id=f"perf-task-asset-{i % 10}",
                    command="echo 'performance test'",
                    timeout=30,
                    created_by="perf-test",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                self.task_dao.insert(task)
                metric.end(start, True)
                insert_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"任务插入失败: {e}")

        # 测试任务查询性能
        query_times = []
        for i in range(100):
            start = metric.start()
            try:
                task = self.task_dao.select_by_id(f"perf-task-{i:04d}")
                self.assertIsNotNone(task)
                metric.end(start, True)
                query_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"任务查询失败: {e}")

        # 测试任务列表查询性能
        list_times = []
        for _ in range(20):
            start = metric.start()
            try:
                tasks = self.task_dao.list(limit=50)
                metric.end(start, True)
                list_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"任务列表查询失败: {e}")

        # 测试任务更新性能
        update_times = []
        for i in range(50):
            start = metric.start()
            try:
                task = self.task_dao.select_by_id(f"perf-task-{i:04d}")
                task.status = TaskStatus.ASSIGNED
                task.target_node_id = f"perf-node-{i}"
                self.task_dao.update(task)
                metric.end(start, True)
                update_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"任务更新失败: {e}")

        # 记录性能指标
        self.metrics["task_insert"] = statistics.mean(insert_times)
        self.metrics["task_query"] = statistics.mean(query_times)
        self.metrics["task_list"] = statistics.mean(list_times)
        self.metrics["task_update"] = statistics.mean(update_times)

        print(f"   插入性能: {statistics.mean(insert_times)*1000:.2f}ms (平均)")
        print(f"   查询性能: {statistics.mean(query_times)*1000:.2f}ms (平均)")
        print(f"   列表性能: {statistics.mean(list_times)*1000:.2f}ms (平均)")
        print(f"   更新性能: {statistics.mean(update_times)*1000:.2f}ms (平均)")

        self.__class__.metrics["task_crud"] = metric.get_stats()

    def test_03_audit_log_performance(self):
        """测试3: 审计日志性能"""
        print("\n[3/6] 📋 审计日志性能测试...")

        metric = PerformanceMetric("审计日志")

        # 测试审计日志插入性能
        insert_times = []
        for i in range(200):
            start = metric.start()
            try:
                audit_log = AuditLog(
                    audit_id=f"perf-audit-{i:04d}",
                    action=AuditAction.ASSET_REGISTERED,
                    category=AuditCategory.ASSET,
                    level=EventLevel.INFO,
                    actor="perf-test-user",
                    target_type="asset",
                    target_id=f"perf-audit-asset-{i}",
                    message=f"性能测试审计日志 {i}",
                )
                self.audit_dao.insert(audit_log)
                metric.end(start, True)
                insert_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"审计日志插入失败: {e}")

        # 测试审计日志查询性能
        query_times = []
        for i in range(50):
            start = metric.start()
            try:
                audit = self.audit_dao.select_by_id(f"perf-audit-{i:04d}")
                self.assertIsNotNone(audit)
                metric.end(start, True)
                query_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"审计日志查询失败: {e}")

        # 测试审计日志列表查询性能
        list_times = []
        for _ in range(20):
            start = metric.start()
            try:
                audits = self.audit_dao.list(limit=100)
                metric.end(start, True)
                list_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"审计日志列表查询失败: {e}")

        # 测试按目标查询性能
        target_query_times = []
        for i in range(20):
            start = metric.start()
            try:
                audits = self.audit_dao.query_by_asset(
                    f"perf-audit-asset-{i}", limit=10
                )
                metric.end(start, True)
                target_query_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"按目标查询失败: {e}")

        # 记录性能指标
        self.metrics["audit_insert"] = statistics.mean(insert_times)
        self.metrics["audit_query"] = statistics.mean(query_times)
        self.metrics["audit_list"] = statistics.mean(list_times)
        self.metrics["audit_target_query"] = statistics.mean(target_query_times)

        print(f"   插入性能: {statistics.mean(insert_times)*1000:.2f}ms (平均)")
        print(f"   查询性能: {statistics.mean(query_times)*1000:.2f}ms (平均)")
        print(f"   列表性能: {statistics.mean(list_times)*1000:.2f}ms (平均)")
        print(f"   按目标查询: {statistics.mean(target_query_times)*1000:.2f}ms (平均)")

        self.__class__.metrics["audit_log"] = metric.get_stats()

    def test_04_complex_query_performance(self):
        """测试4: 复杂查询性能"""
        print("\n[4/6] 🔍 复杂查询性能测试...")

        metric = PerformanceMetric("复杂查询")

        # 准备测试数据
        for i in range(50):
            asset = Asset(
                asset_id=f"complex-asset-{i}",
                name=f"复杂查询资产-{i}",
                asset_type=[
                    AssetType.LINUX_HOST,
                    AssetType.NETWORK_DEVICE,
                    AssetType.IOT_DEVICE,
                ][i % 3],
                status=[
                    AssetStatus.ACTIVE,
                    AssetStatus.INACTIVE,
                    AssetStatus.DECOMMISSIONED,
                ][i % 3],
                description="复杂查询测试",
            )
            self.asset_dao.insert(asset)

        # 测试带过滤条件的查询性能
        filter_times = []
        for _ in range(30):
            start = metric.start()
            try:
                assets = self.asset_dao.list(
                    filters={"asset_type": AssetType.LINUX_HOST}, limit=50
                )
                metric.end(start, True)
                filter_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"过滤查询失败: {e}")

        # 测试排序查询性能
        sort_times = []
        for _ in range(30):
            start = metric.start()
            try:
                assets = self.asset_dao.list(order_by="-created_at", limit=50)
                metric.end(start, True)
                sort_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"排序查询失败: {e}")

        # 测试分页查询性能
        pagination_times = []
        for offset in range(0, 100, 10):
            start = metric.start()
            try:
                assets = self.asset_dao.list(limit=10, offset=offset)
                metric.end(start, True)
                pagination_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"分页查询失败: {e}")

        # 测试统计查询性能
        count_times = []
        for _ in range(20):
            start = metric.start()
            try:
                count = self.asset_dao.count()
                metric.end(start, True)
                count_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"统计查询失败: {e}")

        print(f"   过滤查询: {statistics.mean(filter_times)*1000:.2f}ms (平均)")
        print(f"   排序查询: {statistics.mean(sort_times)*1000:.2f}ms (平均)")
        print(f"   分页查询: {statistics.mean(pagination_times)*1000:.2f}ms (平均)")
        print(f"   统计查询: {statistics.mean(count_times)*1000:.2f}ms (平均)")

        self.__class__.metrics["complex_query"] = metric.get_stats()

    def test_05_bulk_operations_performance(self):
        """测试5: 批量操作性能"""
        print("\n[5/6] 📦 批量操作性能测试...")

        metric = PerformanceMetric("批量操作")

        # 测试批量插入性能
        bulk_insert_times = []
        for batch in range(5):
            start = metric.start()
            try:
                for i in range(20):
                    asset = Asset(
                        asset_id=f"bulk-asset-{batch}-{i}",
                        name=f"批量插入资产-{batch}-{i}",
                        asset_type=AssetType.LINUX_HOST,
                        status=AssetStatus.ACTIVE,
                    )
                    self.asset_dao.insert(asset)
                metric.end(start, True)
                bulk_insert_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"批量插入失败: {e}")

        # 测试批量查询性能
        bulk_query_times = []
        for _ in range(10):
            start = metric.start()
            try:
                assets = self.asset_dao.list(limit=100)
                self.assertGreaterEqual(len(assets), 100)
                metric.end(start, True)
                bulk_query_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)
                self.fail(f"批量查询失败: {e}")

        print(f"   批量插入 (20个): {statistics.mean(bulk_insert_times)*1000:.2f}ms (平均)")
        print(f"   批量查询 (100个): {statistics.mean(bulk_query_times)*1000:.2f}ms (平均)")

        self.__class__.metrics["bulk_operations"] = metric.get_stats()

    def test_06_concurrent_operations_performance(self):
        """测试6: 并发操作性能"""
        print("\n[6/6] 🔄 并发操作性能测试...")

        metric = PerformanceMetric("并发操作")

        # 模拟并发读写场景
        read_times = []
        write_times = []

        # 混合读写测试
        for i in range(50):
            # 写入
            start = metric.start()
            try:
                asset = Asset(
                    asset_id=f"concurrent-asset-{i}",
                    name=f"并发测试资产-{i}",
                    asset_type=AssetType.LINUX_HOST,
                    status=AssetStatus.ACTIVE,
                )
                self.asset_dao.insert(asset)
                metric.end(start, True)
                write_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)

            # 读取
            start = metric.start()
            try:
                asset = self.asset_dao.select_by_id(f"concurrent-asset-{i}")
                self.assertIsNotNone(asset)
                metric.end(start, True)
                read_times.append(time.time() - start)
            except Exception as e:
                metric.end(start, False)

        print(f"   写入性能: {statistics.mean(write_times)*1000:.2f}ms (平均)")
        print(f"   读取性能: {statistics.mean(read_times)*1000:.2f}ms (平均)")

        self.__class__.metrics["concurrent"] = metric.get_stats()

    @classmethod
    def _generate_performance_report(cls):
        """生成性能基线报告"""
        print("\n" + "=" * 70)
        print("📊 性能基线报告")
        print("=" * 70)

        if not hasattr(cls, "metrics") or not cls.metrics:
            print("没有性能数据")
            return

        # 输出各模块性能基线
        for metric_name, metric_data in cls.metrics.items():
            if isinstance(metric_data, dict) and "avg" in metric_data:
                print(f"\n{metric_data['name']}:")
                print(f"  调用次数: {metric_data['count']}")
                print(f"  平均耗时: {metric_data['avg']*1000:.2f}ms")
                print(f"  最小耗时: {metric_data['min']*1000:.2f}ms")
                print(f"  最大耗时: {metric_data['max']*1000:.2f}ms")
                print(f"  中位数: {metric_data['median']*1000:.2f}ms")
                print(f"  P95: {metric_data['p95']*1000:.2f}ms")
                print(f"  P99: {metric_data['p99']*1000:.2f}ms")

        # 性能基线总结
        print("\n" + "=" * 70)
        print("🎯 性能基线总结")
        print("=" * 70)

        # 识别最慢的操作
        slow_operations = []
        for key, value in cls.metrics.items():
            if isinstance(value, (int, float)):
                slow_operations.append((key, value))

        slow_operations.sort(key=lambda x: x[1], reverse=True)

        if slow_operations:
            print("\n最慢的操作 (Top 5):")
            for i, (operation, time_ms) in enumerate(slow_operations[:5], 1):
                print(f"  {i}. {operation}: {time_ms*1000:.2f}ms")

        print("\n性能建议:")
        print("  - 所有平均响应时间应 < 100ms")
        print("  - P95 响应时间应 < 200ms")
        print("  - P99 响应时间应 < 500ms")
        print("  - 批量操作应优化为 < 50ms/条")

        print("\n" + "=" * 70)


if __name__ == "__main__":
    # 运行性能基线测试
    unittest.main(verbosity=2)
