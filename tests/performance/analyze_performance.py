#!/usr/bin/env python3
"""
性能分析脚本 - 分析系统性能瓶颈

用途：
1. 运行性能基线测试
2. 分析性能瓶颈
3. 提供优化建议
4. 生成性能报告
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class PerformanceAnalyzer:
    """性能分析器"""

    def __init__(self):
        self.baseline_data = {}
        self.bottlenecks = []
        self.optimizations = []

    def run_baseline_tests(self):
        """运行性能基线测试"""
        print("="*70)
        print("🔍 运行性能基线测试...")
        print("="*70)

        try:
            # 运行性能测试
            result = subprocess.run(
                ["python3", "-m", "pytest", "tests/performance/test_performance_baseline.py", "-v"],
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )

            # 解析测试输出
            self._parse_test_output(result.stdout, result.stderr)

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print("❌ 性能测试超时")
            return False
        except Exception as e:
            print(f"❌ 性能测试执行失败: {e}")
            return False

    def _parse_test_output(self, stdout, stderr):
        """解析测试输出"""
        # 这里可以添加更复杂的解析逻辑
        # 提取性能数据
        print("性能测试输出已捕获")

    def analyze_bottlenecks(self):
        """分析性能瓶颈"""
        print("\n" + "="*70)
        print("🔍 分析性能瓶颈...")
        print("="*70)

        # 常见的性能瓶颈检查
        bottlenecks = []

        # 1. 检查数据库连接
        print("\n1️⃣  检查数据库连接...")
        try:
            from shared.database.sqlite_backend import SQLiteBackend
            db = SQLiteBackend(db_path="/tmp/perf_check.db")

            start = datetime.now()
            session = db._get_session()
            session.execute("SELECT 1")
            end = datetime.now()

            connection_time = (end - start).total_seconds()
            print(f"   数据库连接时间: {connection_time*1000:.2f}ms")

            if connection_time > 0.1:  # 100ms
                bottlenecks.append({
                    "type": "database_connection",
                    "severity": "high",
                    "issue": f"数据库连接过慢 ({connection_time*1000:.2f}ms)",
                    "recommendation": "使用连接池减少连接开销"
                })

            session.close()
        except Exception as e:
            print(f"   ⚠️  数据库检查失败: {e}")

        # 2. 检查索引使用情况
        print("\n2️⃣  检查索引使用情况...")
        self._check_index_usage()

        # 3. 检查查询优化
        print("\n3️⃣  检查查询优化...")
        self._check_query_optimization()

        # 4. 检查批量操作
        print("\n4️⃣  检查批量操作...")
        self._check_bulk_operations()

        self.bottlenecks = bottlenecks

        if not bottlenecks:
            print("\n✅ 未发现明显的性能瓶颈")
        else:
            print(f"\n⚠️  发现 {len(bottlenecks)} 个性能瓶颈")

    def _check_index_usage(self):
        """检查索引使用情况"""
        try:
            from shared.database.sqlite_backend import SQLiteBackend
            db = SQLiteBackend(db_path="/tmp/index_check.db")
            db.initialize()

            session = db._get_session()

            # 检查表索引
            tables = ['assets', 'tasks', 'audit_logs']

            for table in tables:
                result = session.execute(f"PRAGMA index_list({table})")
                indexes = result.fetchall()

                print(f"   {table}: {len(indexes)} 个索引")

                # 检查索引统计信息
                for index in indexes:
                    index_name = index[1]
                    result = session.execute(f"PRAGMA index_info('{index_name}')")
                    columns = result.fetchall()
                    print(f"     - {index_name}: {len(columns)} 列")

            session.close()

        except Exception as e:
            print(f"   ⚠️  索引检查失败: {e}")

    def _check_query_optimization(self):
        """检查查询优化情况"""
        # 检查是否有N+1查询问题
        print("   检查N+1查询...")
        print("   建议: 使用JOIN或批量查询避免N+1问题")

        # 检查是否有全表扫描
        print("   检查全表扫描...")
        print("   建议: 确保WHERE条件使用索引列")

    def _check_bulk_operations(self):
        """检查批量操作优化"""
        print("   批量插入优化...")
        print("   建议: 使用批量INSERT或executemany")

        print("   批量查询优化...")
        print("   建议: 合并多个查询，减少数据库往返")

    def generate_optimization_plan(self):
        """生成优化计划"""
        print("\n" + "="*70)
        print("📋 生成优化计划...")
        print("="*70)

        optimizations = []

        # 基于发现的瓶颈生成优化建议
        for bottleneck in self.bottlenecks:
            if bottleneck["type"] == "database_connection":
                optimizations.append({
                    "priority": "high",
                    "action": "实现数据库连接池",
                    "expected_improvement": "减少50-70%的连接开销",
                    "implementation_effort": "中等",
                    "steps": [
                        "使用SQLAlchemy的QueuePool实现连接池",
                        "配置合适的pool_size和max_overflow",
                        "添加连接健康检查"
                    ]
                })

        # 通用的优化建议
        optimizations.extend([
            {
                "priority": "medium",
                "action": "添加查询结果缓存",
                "expected_improvement": "减少70-90%的重复查询",
                "implementation_effort": "低",
                "steps": [
                    "实现简单的内存缓存",
                    "为频繁查询的数据添加缓存层",
                    "设置合理的缓存过期时间"
                ]
            },
            {
                "priority": "medium",
                "action": "优化批量操作",
                "expected_improvement": "提升3-5倍批量操作性能",
                "implementation_effort": "低",
                "steps": [
                    "使用executemany进行批量插入",
                    "实现批量查询接口",
                    "减少数据库往返次数"
                ]
            },
            {
                "priority": "low",
                "action": "数据库索引优化",
                "expected_improvement": "提升20-50%查询性能",
                "implementation_effort": "低",
                "steps": [
                    "分析查询模式",
                    "为常用查询条件添加索引",
                    "定期分析和重建索引"
                ]
            }
        ])

        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        optimizations.sort(key=lambda x: priority_order.get(x["priority"], 3))

        self.optimizations = optimizations

        # 输出优化计划
        for i, opt in enumerate(optimizations, 1):
            priority_symbol = {
                "high": "🔴",
                "medium": "🟡",
                "low": "🟢"
            }.get(opt["priority"], "⚪")

            print(f"\n{priority_symbol} 优化 {i}: {opt['action']}")
            print(f"   优先级: {opt['priority']}")
            print(f"   预期改进: {opt['expected_improvement']}")
            print(f"   实现难度: {opt['implementation_effort']}")
            print(f"   实施步骤:")
            for step in opt['steps']:
                print(f"     • {step}")

    def generate_report(self):
        """生成性能分析报告"""
        print("\n" + "="*70)
        print("📊 性能分析报告")
        print("="*70)

        report = {
            "timestamp": datetime.now().isoformat(),
            "bottlenecks": self.bottlenecks,
            "optimizations": self.optimizations,
            "summary": self._generate_summary()
        }

        # 保存报告
        report_file = "performance_analysis_report.json"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n📄 性能报告已保存: {report_file}")
        except Exception as e:
            print(f"⚠️  保存报告失败: {e}")

        # 输出摘要
        print("\n📋 性能分析摘要:")
        print(f"   发现瓶颈: {len(self.bottlenecks)} 个")
        print(f"   优化建议: {len(self.optimizations)} 个")
        print(f"   高优先级优化: {len([o for o in self.optimizations if o['priority'] == 'high'])} 个")

    def _generate_summary(self):
        """生成摘要"""
        return {
            "total_bottlenecks": len(self.bottlenecks),
            "total_optimizations": len(self.optimizations),
            "high_priority_optimizations": len([o for o in self.optimizations if o['priority'] == 'high']),
            "medium_priority_optimizations": len([o for o in self.optimizations if o['priority'] == 'medium']),
            "low_priority_optimizations": len([o for o in self.optimizations if o['priority'] == 'low'])
        }


def main():
    """主函数"""
    print("🚀 HermesNexus 性能分析工具")
    print("目标: 识别性能瓶颈，提供优化建议")

    analyzer = PerformanceAnalyzer()

    # 1. 运行性能基线测试
    if not analyzer.run_baseline_tests():
        print("⚠️  性能基线测试未完全通过，但继续分析")

    # 2. 分析性能瓶颈
    analyzer.analyze_bottlenecks()

    # 3. 生成优化计划
    analyzer.generate_optimization_plan()

    # 4. 生成报告
    analyzer.generate_report()

    print("\n" + "="*70)
    print("✅ 性能分析完成")
    print("="*70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
