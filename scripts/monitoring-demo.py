#!/usr/bin/env python3
"""
监控面板演示脚本
展示HermesNexus监控与告警系统的使用
"""

import sys
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.monitoring.metrics import MetricsCollector, get_metrics_collector
from shared.monitoring.alerts import AlertManager, get_alert_manager
from shared.monitoring.dashboard import MonitoringDashboard, get_monitoring_dashboard


def simulate_api_traffic(collector: MetricsCollector, duration: int = 60):
    """模拟API流量"""
    print("📡 模拟API流量...")

    endpoints = [
        ("/api/assets", "GET"),
        ("/api/assets", "POST"),
        ("/api/tasks", "GET"),
        ("/api/tasks", "POST"),
        ("/api/audit-logs", "GET"),
    ]

    start_time = time.time()
    request_count = 0

    while time.time() - start_time < duration:
        # 随机选择端点和状态
        endpoint, method = random.choice(endpoints)

        # 模拟响应时间 (10ms - 500ms)
        response_time = random.uniform(0.01, 0.5)

        # 模拟状态码 (95%成功, 5%失败)
        status = "200" if random.random() > 0.05 else "500"

        # 记录API请求
        collector.record_api_request(endpoint, method, status, response_time)

        # 模拟数据库查询
        db_operation = random.choice(["select", "insert", "update"])
        db_table = random.choice(["assets", "tasks", "audit_logs"])
        db_query_time = random.uniform(0.001, 0.1)
        collector.record_db_query(db_operation, db_table, db_query_time)

        request_count += 1

        # 每10个请求输出一次进度
        if request_count % 10 == 0:
            print(f"  已生成 {request_count} 个请求...")

        time.sleep(0.1)  # 间隔100ms

    print(f"  ✅ 总共生成 {request_count} 个API请求")


def simulate_system_metrics(collector: MetricsCollector):
    """模拟系统指标"""
    print("📊 模拟系统指标...")

    # 记录系统指标
    system_metrics = collector.collect_system_metrics()

    # 记录业务指标
    collector.record_gauge("asset_total_count", 150.0)
    collector.record_gauge("asset_online_count", 135.0)
    collector.record_gauge("task_total_count", 85.0)
    collector.record_counter("task_failure_count", 3.0)

    collector.record_gauge("node_online_count", 12.0)

    print("  ✅ 系统指标已记录")


def demonstrate_monitoring():
    """演示监控功能"""
    print("\n" + "="*70)
    print("🚀 HermesNexus 监控系统演示")
    print("="*70)

    # 初始化监控组件
    dashboard = get_monitoring_dashboard()
    alert_manager = get_alert_manager()
    metrics_collector = get_metrics_collector()

    print("\n📋 演示步骤:")
    print("  1. 生成模拟流量数据")
    print("  2. 采集系统指标")
    print("  3. 检查告警规则")
    print("  4. 显示监控面板")
    print("")

    # 步骤1: 生成模拟流量
    simulate_system_metrics(metrics_collector)
    simulate_api_traffic(metrics_collector, duration=30)  # 30秒模拟

    # 步骤2: 检查告警
    print("\n🚨 检查告警规则...")
    metrics_summary = metrics_collector.get_metric_summary()
    new_alerts = alert_manager.check_metrics(metrics_summary["metrics"])

    if new_alerts:
        print(f"  ✅ 触发了 {len(new_alerts)} 个新告警")
        for alert in new_alerts:
            print(f"     - {alert.rule_name}: {alert.message}")
    else:
        print("  ✅ 未触发告警")

    # 步骤3: 显示监控面板
    print("\n📊 监控面板:")
    print(dashboard.generate_dashboard_report())

    # 步骤4: 显示详细数据
    print("\n📈 详细数据展示:")

    overview = dashboard.get_system_overview()
    print(f"\n系统健康度: {overview['system_health']}")

    print("\n资源使用详情:")
    for resource_name, resource_data in overview['resource_usage'].items():
        print(f"  {resource_name.upper()}:")
        print(f"    使用率: {resource_data['usage_percent']:.1f}%")
        print(f"    状态: {resource_data['status']}")

    app_perf = dashboard.get_application_performance()
    print(f"\n应用性能:")
    print(f"  总请求数: {app_perf['total_requests']}")
    print(f"  总错误数: {app_perf['total_errors']}")
    print(f"  错误率: {app_perf['error_rate']:.2f}%")

    alerts_panel = dashboard.get_alerts_panel()
    print(f"\n告警状态:")
    print(f"  活跃告警数: {alerts_panel['total_count']}")
    print(f"  严重告警: {alerts_panel['summary']['critical_count']}")
    print(f"  高级告警: {alerts_panel['summary']['high_count']}")

    print("\n" + "="*70)
    print("✅ 监控系统演示完成")
    print("="*70)
    print("\n💡 监控系统功能:")
    print("  - 实时指标采集")
    print("  - 智能告警规则")
    print("  - 可视化监控面板")
    print("  - 多维度数据分析")
    print("\n🔧 下一步:")
    print("  - 集成到实际运行环境")
    print("  - 配置告警通知方式")
    print("  - 扩展监控指标覆盖")
    print("  - 优化告警规则阈值")


def create_monitoring_report():
    """创建监控报告"""
    print("\n📝 生成监控报告...")

    dashboard = get_monitoring_dashboard()

    # 生成监控面板报告
    report = dashboard.generate_dashboard_report()

    # 保存报告到文件
    report_path = "docs/monitoring/monitoring-report.md"
    import os
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# HermesNexus 监控报告\n\n")
        f.write(f"**生成时间**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
        f.write("## 监控面板数据\n\n")
        f.write(report)

    print(f"  ✅ 监控报告已生成: {report_path}")

    # 生成告警规则文档
    alert_rules_path = "docs/monitoring/alert-rules.md"
    with open(alert_rules_path, "w", encoding="utf-8") as f:
        f.write("# HermesNexus 告警规则文档\n\n")
        f.write(f"**更新时间**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")

        f.write("## 系统资源告警\n\n")
        f.write("| 规则名称 | 阈值 | 时间窗口 | 严重级别 |\n")
        f.write("|----------|------|----------|----------|\n")
        for rule in alert_manager.rules[:3]:  # 只显示前3个规则
            f.write(f"| {rule.name} | {rule.threshold} | {rule.time_window}s | {rule.severity.value} |\n")

    print(f"  ✅ 告警规则文档已生成: {alert_rules_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HermesNexus 监控系统演示")
    parser.add_argument("--demo", action="store_true", help="运行监控演示")
    parser.add_argument("--report", action="store_true", help="生成监控报告")
    parser.add_argument("--full", action="store_true", help="完整演示和报告")

    args = parser.parse_args()

    if args.full or not (args.demo or args.report):
        # 完整演示
        demonstrate_monitoring()
        create_monitoring_report()
    elif args.demo:
        demonstrate_monitoring()
    elif args.report:
        create_monitoring_report()