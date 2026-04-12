"""
性能基线分析工具 - Week 4 Day 1
用于识别系统性能瓶颈，确定优化优先级
"""

import os
import sys
import time
import tempfile
import statistics
from pathlib import Path
from typing import Dict, List, Any, Callable
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


class PerformanceAnalyzer:
    """性能分析器"""

    def __init__(self):
        self.results = {}
        self.temp_dir = None
        self.db = None

    def setup(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp(prefix="perf_analysis_")
        db_path = os.path.join(self.temp_dir, "analysis.db")
        self.db = SQLiteBackend(db_path=db_path)
        self.db.initialize()
        self.db.create_tables()

        return self.db

    def cleanup(self):
        """清理测试环境"""
        import shutil
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def measure_operation(self, name: str, operation: Callable, iterations: int = 100) -> Dict[str, Any]:
        """
        测量操作性能

        Args:
            name: 操作名称
            operation: 要测量的操作函数
            iterations: 迭代次数

        Returns:
            性能统计数据
        """
        times = []
        errors = 0

        for i in range(iterations):
            start = time.time()
            try:
                operation(i)
                elapsed = time.time() - start
                times.append(elapsed)
            except Exception as e:
                errors += 1
                print(f"  ❌ {name} 第{i+1}次迭代失败: {e}")

        if not times:
            return {
                "name": name,
                "iterations": iterations,
                "errors": errors,
                "success_rate": 0.0,
                "avg": 0,
                "min": 0,
                "max": 0,
                "median": 0,
                "p95": 0,
                "p99": 0,
                "total": 0
            }

        sorted_times = sorted(times)
        total_time = sum(times)

        return {
            "name": name,
            "iterations": iterations,
            "errors": errors,
            "success_rate": (iterations - errors) / iterations,
            "avg": statistics.mean(times),
            "min": min(times),
            "max": max(times),
            "median": statistics.median(times),
            "p95": sorted_times[int(len(sorted_times) * 0.95)] if len(sorted_times) >= 20 else sorted_times[-1],
            "p99": sorted_times[int(len(sorted_times) * 0.99)] if len(sorted_times) >= 100 else sorted_times[-1],
            "total": total_time,
            "throughput": iterations / total_time if total_time > 0 else 0
        }

    def analyze_database_operations(self):
        """分析数据库操作性能"""
        print("\n📊 数据库操作性能分析")

        db = self.setup()
        asset_dao = AssetDAO(database=db)
        task_dao = TaskDAO(database=db)
        audit_dao = AuditDAO(database=db)

        results = {}

        # 1. Asset 插入性能
        print("  🔍 分析资产插入性能...")
        def insert_asset(i):
            asset = Asset(
                asset_id=f"analysis-asset-{i:04d}",
                name=f"分析资产-{i}",
                asset_type=AssetType.LINUX_HOST,
                status=AssetStatus.ACTIVE,
                description="性能分析测试"
            )
            asset_dao.insert(asset)

        results["asset_insert"] = self.measure_operation("资产插入", insert_asset, 100)

        # 2. Asset 查询性能 (通过ID)
        print("  🔍 分析资产查询性能...")
        def query_asset(i):
            asset = asset_dao.select_by_id(f"analysis-asset-{i:04d}")
            if asset is None:
                raise ValueError(f"资产 analysis-asset-{i:04d} 未找到")

        results["asset_query_by_id"] = self.measure_operation("资产查询(通过ID)", query_asset, 100)

        # 3. Asset 列表查询性能
        print("  🔍 分析资产列表查询性能...")
        def list_assets(i):
            assets = asset_dao.list(limit=50)
            if len(assets) == 0:
                raise ValueError("资产列表为空")

        results["asset_list"] = self.measure_operation("资产列表查询", list_assets, 50)

        # 4. Asset 更新性能
        print("  🔍 分析资产更新性能...")
        def update_asset(i):
            asset = asset_dao.select_by_id(f"analysis-asset-{i%50:04d}")
            asset.status = AssetStatus.INACTIVE
            asset_dao.update(asset)

        results["asset_update"] = self.measure_operation("资产更新", update_asset, 50)

        # 5. Task 插入性能
        print("  🔍 分析任务插入性能...")
        def insert_task(i):
            task = Task(
                task_id=f"analysis-task-{i:04d}",
                name=f"分析任务-{i}",
                task_type=TaskType.BASIC_EXEC,
                status=TaskStatus.PENDING,
                priority=TaskPriority.NORMAL,
                target_asset_id=f"analysis-asset-{i%100:04d}",
                command="echo 'analysis'",
                timeout=30,
                created_by="performance-analysis",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            task_dao.insert(task)

        results["task_insert"] = self.measure_operation("任务插入", insert_task, 100)

        # 6. Task 查询性能
        print("  🔍 分析任务查询性能...")
        def query_task(i):
            task = task_dao.select_by_id(f"analysis-task-{i:04d}")
            if task is None:
                raise ValueError(f"任务 analysis-task-{i:04d} 未找到")

        results["task_query_by_id"] = self.measure_operation("任务查询(通过ID)", query_task, 100)

        # 7. Audit Log 插入性能
        print("  🔍 分析审计日志插入性能...")
        def insert_audit(i):
            audit_log = AuditLog(
                audit_id=f"analysis-audit-{i:04d}",
                action=AuditAction.TASK_CREATED,
                category=AuditCategory.TASK,
                level=EventLevel.INFO,
                actor="performance-analysis",
                target_type="task",
                target_id=f"analysis-task-{i:04d}",
                message=f"审计日志 {i}"
            )
            audit_dao.insert(audit_log)

        results["audit_insert"] = self.measure_operation("审计日志插入", insert_audit, 100)

        # 8. 批量插入性能测试
        print("  🔍 分析批量插入性能...")
        def batch_insert_assets():
            assets = []
            for i in range(50):
                asset = Asset(
                    asset_id=f"batch-asset-{i:04d}",
                    name=f"批量资产-{i}",
                    asset_type=AssetType.LINUX_HOST,
                    status=AssetStatus.ACTIVE,
                    description="批量插入测试"
                )
                assets.append(asset)

            start = time.time()
            for asset in assets:
                asset_dao.insert(asset)
            elapsed = time.time() - start

            return {
                "name": "批量插入50个资产",
                "iterations": 50,
                "errors": 0,
                "success_rate": 1.0,
                "avg": elapsed / 50,
                "min": elapsed / 50,
                "max": elapsed / 50,
                "median": elapsed / 50,
                "p95": elapsed / 50,
                "p99": elapsed / 50,
                "total": elapsed,
                "throughput": 50 / elapsed if elapsed > 0 else 0
            }

        results["batch_insert_50"] = batch_insert_assets()

        self.cleanup()
        return results

    def identify_bottlenecks(self, results: Dict[str, Any]):
        """识别性能瓶颈"""
        print("\n🔍 性能瓶颈识别")

        bottlenecks = []

        # 按平均耗时排序
        sorted_ops = sorted(results.items(), key=lambda x: x[1]["avg"], reverse=True)

        print("\n  📉 操作耗时排名 (按平均时间):")
        for i, (name, stats) in enumerate(sorted_ops, 1):
            print(f"    {i}. {name}:")
            print(f"       平均: {stats['avg']*1000:.3f}ms")
            print(f"       P95:  {stats['p95']*1000:.3f}ms")
            print(f"       P99:  {stats['p99']*1000:.3f}ms")
            print(f"       吞吐: {stats['throughput']:.1f} ops/sec")

            # 识别潜在瓶颈
            if stats['avg'] > 0.1:  # 超过100ms认为是慢操作
                bottlenecks.append({
                    "operation": name,
                    "issue": "平均耗时过长",
                    "value": f"{stats['avg']*1000:.3f}ms",
                    "priority": "HIGH" if stats['avg'] > 0.5 else "MEDIUM"
                })

            if stats['p99'] / stats['avg'] > 10:  # P99远超平均值，说明有长尾延迟
                bottlenecks.append({
                    "operation": name,
                    "issue": "长尾延迟严重",
                    "value": f"P99是平均值的{stats['p99']/stats['avg']:.1f}倍",
                    "priority": "MEDIUM"
                })

            if stats['success_rate'] < 0.95:  # 成功率低于95%
                bottlenecks.append({
                    "operation": name,
                    "issue": "可靠性问题",
                    "value": f"成功率{stats['success_rate']*100:.1f}%",
                    "priority": "HIGH"
                })

        return bottlenecks

    def generate_optimization_recommendations(self, bottlenecks: List[Dict[str, Any]]):
        """生成优化建议"""
        print("\n💡 优化建议:")

        recommendations = []

        for bottleneck in bottlenecks:
            operation = bottleneck["operation"]
            issue = bottleneck["issue"]
            priority = bottleneck["priority"]

            if "insert" in operation and "耗时" in issue:
                recommendations.append({
                    "target": operation,
                    "action": "批量插入优化",
                    "details": [
                        "使用批量插入代替单条插入",
                        "考虑数据库事务批处理",
                        "优化数据库连接池配置"
                    ],
                    "priority": priority,
                    "expected_improvement": "50-70%"
                })

            elif "query" in operation and "耗时" in issue:
                recommendations.append({
                    "target": operation,
                    "action": "查询优化",
                    "details": [
                        "添加合适的数据库索引",
                        "优化查询语句，避免全表扫描",
                        "考虑查询结果缓存"
                    ],
                    "priority": priority,
                    "expected_improvement": "30-50%"
                })

            elif "长尾" in issue:
                recommendations.append({
                    "target": operation,
                    "action": "长尾延迟优化",
                    "details": [
                        "检查是否有锁竞争",
                        "优化内存使用",
                        "考虑异步处理"
                    ],
                    "priority": priority,
                    "expected_improvement": "40-60%"
                })

        return recommendations

    def run_analysis(self):
        """运行完整的性能分析"""
        print("🚀 开始性能基线分析")

        # 1. 分析数据库操作
        results = self.analyze_database_operations()

        # 2. 识别瓶颈
        bottlenecks = self.identify_bottlenecks(results)

        # 3. 生成优化建议
        recommendations = self.generate_optimization_recommendations(bottlenecks)

        # 4. 生成分析报告
        self.generate_report(results, bottlenecks, recommendations)

        return {
            "results": results,
            "bottlenecks": bottlenecks,
            "recommendations": recommendations
        }

    def generate_report(self, results: Dict[str, Any], bottlenecks: List[Dict[str, Any]], recommendations: List[Dict[str, Any]]):
        """生成分析报告"""
        report_path = "tests/performance/baseline_analysis_report.md"

        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# HermesNexus 性能基线分析报告\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("**分析范围**: 数据库操作性能基线\n\n")

            f.write("## 📊 性能基线数据\n\n")

            # 操作性能表
            f.write("### 数据库操作性能\n\n")
            f.write("| 操作 | 平均耗时 | P95耗时 | P99耗时 | 吞吐量 | 成功率 |\n")
            f.write("|------|----------|---------|---------|--------|--------|\n")

            for name, stats in results.items():
                f.write(f"| {stats['name']} | {stats['avg']*1000:.3f}ms | {stats['p95']*1000:.3f}ms | {stats['p99']*1000:.3f}ms | {stats['throughput']:.1f} ops/s | {stats['success_rate']*100:.1f}% |\n")

            f.write("\n## 🔍 识别的性能瓶颈\n\n")

            if bottlenecks:
                f.write("| 操作 | 问题 | 数值 | 优先级 |\n")
                f.write("|------|------|------|--------|\n")
                for b in bottlenecks:
                    f.write(f"| {b['operation']} | {b['issue']} | {b['value']} | {b['priority']} |\n")
            else:
                f.write("✅ 未发现明显性能瓶颈\n")

            f.write("\n## 💡 优化建议\n\n")

            if recommendations:
                for i, rec in enumerate(recommendations, 1):
                    f.write(f"### {i}. {rec['target']} - {rec['action']} (优先级: {rec['priority']})\n\n")
                    f.write(f"**预期改善**: {rec['expected_improvement']}\n\n")
                    f.write("**具体措施**:\n")
                    for detail in rec['details']:
                        f.write(f"- {detail}\n")
                    f.write("\n")
            else:
                f.write("✅ 当前性能表现良好，暂无优化建议\n")

            f.write("\n## 📋 下一步行动\n\n")
            f.write("基于上述分析，建议按以下优先级进行性能优化：\n\n")

            if recommendations:
                high_priority = [r for r in recommendations if r['priority'] == 'HIGH']
                medium_priority = [r for r in recommendations if r['priority'] == 'MEDIUM']

                if high_priority:
                    f.write("### 🔥 高优先级 (本周处理)\n")
                    for i, rec in enumerate(high_priority, 1):
                        f.write(f"{i}. **{rec['target']}**: {rec['action']}\n")
                    f.write("\n")

                if medium_priority:
                    f.write("### 🟡 中优先级 (下周处理)\n")
                    for i, rec in enumerate(medium_priority, 1):
                        f.write(f"{i}. **{rec['target']}**: {rec['action']}\n")
                    f.write("\n")
            else:
                f.write("当前系统性能良好，可以继续功能开发\n")

        print(f"\n📝 分析报告已生成: {report_path}")


if __name__ == "__main__":
    analyzer = PerformanceAnalyzer()
    analysis_results = analyzer.run_analysis()

    print("\n✅ 性能基线分析完成")
    print(f"  📊 测试操作数: {len(analysis_results['results'])}")
    print(f"  🔍 发现瓶颈: {len(analysis_results['bottlenecks'])}")
    print(f"  💡 优化建议: {len(analysis_results['recommendations'])}")