#!/usr/bin/env python3
"""
压力测试脚本 - 验证系统在高负载下的表现
测试Week 4性能优化的实际效果
"""

import unittest
import tempfile
import os
import time
import sys
import statistics
import threading
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.database.sqlite_backend import SQLiteBackend
from shared.dao.asset_dao import AssetDAO
from shared.dao.task_dao import TaskDAO
from shared.dao.audit_dao import AuditDAO
from shared.services.asset_service import AssetService
from shared.services.task_service import TaskService
from shared.services.audit_service import AuditService
from shared.models.asset import Asset, AssetType, AssetStatus
from shared.models.task import Task, TaskType, TaskStatus, TaskPriority
from shared.models.audit import AuditLog, AuditAction, AuditCategory, EventLevel


class StressTestResult:
    """压力测试结果"""

    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = time.time()
        self.operations = 0
        self.errors = 0
        self.timings = []
        self.concurrency = 0

    def record_operation(self, duration: float, success: bool):
        """记录操作"""
        self.operations += 1
        if success:
            self.timings.append(duration)
        else:
            self.errors += 1

    def get_summary(self) -> Dict[str, Any]:
        """获取测试摘要"""
        if not self.timings:
            return {
                "test_name": self.test_name,
                "operations": self.operations,
                "errors": self.errors,
                "success_rate": 0.0,
                "avg_time": 0,
                "min_time": 0,
                "max_time": 0,
                "median_time": 0,
                "p95_time": 0,
                "p99_time": 0,
                "throughput": 0,
                "duration": 0,
            }

        sorted_times = sorted(self.timings)
        duration = time.time() - self.start_time

        return {
            "test_name": self.test_name,
            "operations": self.operations,
            "errors": self.errors,
            "success_rate": ((self.operations - self.errors) / self.operations) * 100,
            "avg_time": statistics.mean(self.timings),
            "min_time": min(self.timings),
            "max_time": max(self.timings),
            "median_time": statistics.median(self.timings),
            "p95_time": (
                sorted_times[int(len(sorted_times) * 0.95)]
                if len(sorted_times) >= 20
                else sorted_times[-1]
            ),
            "p99_time": (
                sorted_times[int(len(sorted_times) * 0.99)]
                if len(sorted_times) >= 100
                else sorted_times[-1]
            ),
            "throughput": self.operations / duration if duration > 0 else 0,
            "duration": duration,
        }


class TestStressPerformance(unittest.TestCase):
    """压力测试"""

    @classmethod
    def setUpClass(cls):
        """压力测试初始化"""
        print("\n" + "=" * 70)
        print("🔥 HermesNexus 压力测试 - 验证性能优化效果")
        print("=" * 70)

    def setUp(self):
        """每个测试前的设置"""
        # 创建临时数据库
        self.temp_dir = tempfile.mkdtemp(prefix="stress_test_")
        self.db_path = os.path.join(self.temp_dir, "stress.db")

        # 初始化数据库
        self.db = SQLiteBackend(db_path=self.db_path)
        self.db.initialize()
        self.db.create_tables()

        # 初始化DAO
        self.asset_dao = AssetDAO(database=self.db)
        self.task_dao = TaskDAO(database=self.db)
        self.audit_dao = AuditDAO(database=self.db)

    def tearDown(self):
        """清理临时资源"""
        import shutil

        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_01_concurrent_asset_operations(self):
        """测试1: 并发资产操作压力测试"""
        print("\n[1/4] 📦 并发资产操作压力测试...")

        # 先插入100个资产作为基础数据
        print("  📋 准备基础数据...")
        base_assets = []
        for i in range(100):
            asset = Asset(
                asset_id=f"stress-asset-{i:04d}",
                name=f"压力测试资产-{i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE,
                description="压力测试基础数据",
            )
            base_assets.append(asset)

        self.asset_dao.insert_batch(base_assets)
        print(f"  ✅ 基础数据准备完成: {len(base_assets)}个资产")

        # 并发读取测试
        print("  🔥 并发读取测试...")
        result = StressTestResult("并发资产读取")

        def read_asset(asset_id):
            start = time.time()
            try:
                asset = self.asset_dao.select_by_id(asset_id)
                duration = time.time() - start
                result.record_operation(duration, asset is not None)
                return asset
            except Exception as e:
                result.record_operation(0, False)
                print(f"    ❌ 读取失败 {asset_id}: {e}")
                return None

        # 使用5个并发线程执行读取
        test_ids = [f"stress-asset-{i:04d}" for i in range(50)]
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(read_asset, aid) for aid in test_ids]
            for future in as_completed(futures):
                future.result()

        summary = result.get_summary()
        print(f"  📊 读取测试结果:")
        print(f"     操作数: {summary['operations']}")
        print(f"     成功率: {summary['success_rate']:.1f}%")
        print(f"     吞吐量: {summary['throughput']:.1f} ops/sec")
        print(f"     P95耗时: {summary['p95_time']*1000:.2f}ms")
        print(f"     P99耗时: {summary['p99_time']*1000:.2f}ms")

        # 验证性能要求
        self.assertGreater(summary["success_rate"], 99.0, "读取成功率应该>99%")
        self.assertGreater(summary["throughput"], 100.0, "吞吐量应该>100 ops/sec")

        print("  ✅ 并发读取压力测试通过")

    def test_02_batch_vs_single_performance(self):
        """测试2: 批量操作 vs 单个操作性能对比"""
        print("\n[2/4] ⚡ 批量操作 vs 单个操作性能对比...")

        # 测试单个插入
        print("  📊 测试单个插入50个资产...")
        single_result = StressTestResult("单个插入")

        for i in range(50):
            asset = Asset(
                asset_id=f"single-perf-{i:04d}",
                name=f"单个插入性能测试-{i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE,
            )

            start = time.time()
            try:
                self.asset_dao.insert(asset)
                duration = time.time() - start
                single_result.record_operation(duration, True)
            except Exception as e:
                single_result.record_operation(0, False)
                print(f"    ❌ 插入失败: {e}")

        single_summary = single_result.get_summary()

        # 测试批量插入
        print("  📊 测试批量插入50个资产...")
        batch_result = StressTestResult("批量插入")

        batch_assets = []
        for i in range(50):
            asset = Asset(
                asset_id=f"batch-perf-{i:04d}",
                name=f"批量插入性能测试-{i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE,
            )
            batch_assets.append(asset)

        start = time.time()
        try:
            self.asset_dao.insert_batch(batch_assets)
            duration = time.time() - start
            batch_result.record_operation(duration, True)
        except Exception as e:
            batch_result.record_operation(0, False)
            print(f"    ❌ 批量插入失败: {e}")

        batch_summary = batch_result.get_summary()

        # 性能对比
        print("  📈 性能对比:")
        print(f"     单个插入总耗时: {single_summary['duration']:.3f}秒")
        print(f"     批量插入总耗时: {batch_summary['duration']:.3f}秒")
        print(
            f"     性能提升: {single_summary['duration'] / batch_summary['duration']:.1f}x"
        )
        print(
            f"     时间节省: {((single_summary['duration'] - batch_summary['duration']) / single_summary['duration']) * 100:.1f}%"
        )

        # 验证批量操作的性能优势
        speedup = single_summary["duration"] / batch_summary["duration"]
        self.assertGreater(speedup, 1.5, "批量插入应该至少快1.5倍")

        print("  ✅ 批量操作性能对比测试通过")

    def test_03_high_load_query_performance(self):
        """测试3: 高负载查询性能测试"""
        print("\n[3/4] 🔍 高负载查询性能测试...")

        # 准备大量测试数据
        print("  📋 准备测试数据...")
        test_assets = []
        for i in range(200):
            asset = Asset(
                asset_id=f"query-stress-{i:04d}",
                name=f"查询压力测试-{i}",
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
                description="查询压力测试",
            )
            test_assets.append(asset)

        self.asset_dao.insert_batch(test_assets)
        print(f"  ✅ 测试数据准备完成: {len(test_assets)}个资产")

        # 测试不同查询的性能
        print("  🔥 测试列表查询性能...")
        result = StressTestResult("列表查询压力测试")

        iterations = 50
        for i in range(iterations):
            start = time.time()
            try:
                # 执行带过滤条件的列表查询
                assets = self.asset_dao.list(
                    filters={"asset_type": AssetType.LINUX_HOST}, limit=50
                )
                duration = time.time() - start
                result.record_operation(duration, len(assets) > 0)
            except Exception as e:
                result.record_operation(0, False)
                print(f"    ❌ 查询失败: {e}")

        summary = result.get_summary()
        print(f"  📊 查询性能结果:")
        print(f"     查询次数: {summary['operations']}")
        print(f"     成功率: {summary['success_rate']:.1f}%")
        print(f"     平均耗时: {summary['avg_time']*1000:.2f}ms")
        print(f"     P95耗时: {summary['p95_time']*1000:.2f}ms")
        print(f"     查询吞吐: {summary['throughput']:.1f} queries/sec")

        # 验证查询性能
        self.assertGreater(summary["success_rate"], 99.0, "查询成功率应该>99%")
        self.assertLess(summary["p95_time"] * 1000, 100.0, "P95查询时间应该<100ms")

        print("  ✅ 高负载查询性能测试通过")

    def test_04_mixed_workload_stability(self):
        """测试4: 混合工作负载稳定性测试"""
        print("\n[4/4) 🔄 混合工作负载稳定性测试...")

        result = StressTestResult("混合工作负载")

        def worker_operation(worker_id: int):
            """工作线程操作"""
            ops_completed = 0

            for i in range(10):  # 每个线程执行10次操作
                # 创建资产
                asset = Asset(
                    asset_id=f"mixed-worker-{worker_id}-{i:04d}",
                    name=f"混合测试资产-{worker_id}-{i}",
                    asset_type=AssetType.LINUX_HOST,
                    status=AssetStatus.ACTIVE,
                )

                start = time.time()
                try:
                    self.asset_dao.insert(asset)
                    duration = time.time() - start
                    result.record_operation(duration, True)
                    ops_completed += 1
                except Exception as e:
                    result.record_operation(0, False)

            return ops_completed

        # 使用10个并发工作线程
        print("  🔥 启动10个并发工作线程...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker_operation, i) for i in range(10)]
            completed_ops = [future.result() for future in as_completed(futures)]

        summary = result.get_summary()
        print(f"  📊 混合工作负载结果:")
        print(f"     总操作数: {summary['operations']}")
        print(f"     成功操作: {summary['operations'] - summary['errors']}")
        print(f"     失败操作: {summary['errors']}")
        print(f"     成功率: {summary['success_rate']:.1f}%")
        print(f"     总耗时: {summary['duration']:.3f}秒")
        print(f"     系统吞吐: {summary['throughput']:.1f} ops/sec")

        # 验证系统稳定性
        self.assertEqual(summary["operations"], 100, "应该完成100个操作")
        self.assertGreaterEqual(summary["success_rate"], 95.0, "成功率应该>=95%")
        self.assertGreater(summary["throughput"], 50.0, "吞吐量应该>50 ops/sec")

        print("  ✅ 混合工作负载稳定性测试通过")


def generate_stress_test_report():
    """生成压力测试报告"""
    print("\n📝 生成压力测试报告...")

    report_path = "tests/performance/stress-test-report.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# HermesNexus 压力测试报告\n\n")
        f.write(
            f"**生成时间**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        )
        f.write("## 测试目的\n\n")
        f.write(
            "验证Week 4性能优化在实际高负载场景下的效果，确保系统在压力下稳定运行。\n\n"
        )

        f.write("## 测试场景\n\n")
        f.write("### 1. 并发资产操作压力测试\n")
        f.write("- 测试并发读取性能\n")
        f.write("- 验证批量查询效果\n")
        f.write("- 预期: 高并发下仍保持良好性能\n\n")

        f.write("### 2. 批量操作 vs 单个操作对比\n")
        f.write("- 对比单个插入和批量插入性能\n")
        f.write("- 验证性能提升效果\n")
        f.write("- 预期: 批量操作明显快于单个操作\n\n")

        f.write("### 3. 高负载查询性能测试\n")
        f.write("- 测试大数据量查询性能\n")
        f.write("- 验证索引优化效果\n")
        f.write("- 预期: 查询时间保持稳定\n\n")

        f.write("### 4. 混合工作负载稳定性测试\n")
        f.write("- 模拟真实并发场景\n")
        f.write("- 验证系统稳定性\n")
        f.write("- 预期: 高成功率，无明显性能下降\n\n")

        f.write("## 性能指标\n\n")
        f.write("| 指标 | 目标值 | 说明 |\n")
        f.write("|------|--------|------|\n")
        f.write("| 并发读取成功率 | >99% | 高并发下保持高成功率 |\n")
        f.write("| 批量操作性能提升 | >1.5x | 批量操作至少快1.5倍 |\n")
        f.write("| 查询P95响应时间 | <100ms | 95%的查询在100ms内完成 |\n")
        f.write("| 混合工作负载成功率 | >=95% | 并发场景下保持高成功率 |\n")
        f.write("| 系统吞吐量 | >50 ops/sec | 每秒处理50+操作 |\n\n")

        f.write("## 验收标准\n\n")
        f.write("- [ ] 所有压力测试通过\n")
        f.write("- [ ] 性能指标达到预期目标\n")
        f.write("- [ ] 无内存泄漏或资源泄漏\n")
        f.write("- [ ] 系统在高负载下稳定运行\n")
        f.write("- [ ] 性能优化效果得到验证\n")

    print(f"  ✅ 压力测试报告已生成: {report_path}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🚀 HermesNexus 压力测试执行")
    print("=" * 70)

    # 运行压力测试
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestStressPerformance)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 生成报告
    generate_stress_test_report()

    # 输出最终结果
    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print("✅ 压力测试全部通过")
        print("=" * 70)
        print("📈 Week 4 性能优化验证完成")
        print("  - 批量操作性能提升得到验证")
        print("  - 高负载下系统稳定性良好")
        print("  - 查询性能符合预期目标")
        print("=" * 70)
        exit_code = 0
    else:
        print("❌ 压力测试存在失败")
        print("=" * 70)
        exit_code = 1

    sys.exit(exit_code)
