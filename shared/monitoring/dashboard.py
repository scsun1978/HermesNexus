"""
HermesNexus 监控面板
提供系统状态可视化和告警展示
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

from shared.monitoring.metrics import (
    MetricsCollector,
    MetricType,
    MetricCategory,
    get_metrics_collector,
)
from shared.monitoring.alerts import AlertManager, AlertSeverity, get_alert_manager


class MonitoringDashboard:
    """监控面板"""

    def __init__(self):
        self.metrics_collector = get_metrics_collector()
        self.alert_manager = get_alert_manager()

    def get_system_overview(self) -> Dict[str, Any]:
        """获取系统概览"""
        system_metrics = self.metrics_collector.collect_system_metrics()
        alert_summary = self.alert_manager.get_alert_summary()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system_health": self._calculate_system_health(
                system_metrics, alert_summary
            ),
            "resource_usage": {
                "cpu": {
                    "usage_percent": system_metrics.get("cpu_usage_percent", 0),
                    "status": self._get_resource_status(
                        system_metrics.get("cpu_usage_percent", 0), 80, 95
                    ),
                },
                "memory": {
                    "usage_percent": system_metrics.get("memory_usage_percent", 0),
                    "status": self._get_resource_status(
                        system_metrics.get("memory_usage_percent", 0), 85, 95
                    ),
                },
                "disk": {
                    "usage_percent": system_metrics.get("disk_usage_percent", 0),
                    "status": self._get_resource_status(
                        system_metrics.get("disk_usage_percent", 0), 80, 90
                    ),
                },
            },
            "alerts": {
                "total": alert_summary["total_active_alerts"],
                "critical": alert_summary["critical_count"],
                "high": alert_summary["high_count"],
                "medium": alert_summary["medium_count"],
                "low": alert_summary["low_count"],
            },
        }

    def get_application_performance(self) -> Dict[str, Any]:
        """获取应用性能数据"""
        metrics_summary = self.metrics_collector.get_metric_summary()

        # 提取API性能数据
        api_metrics = {}
        if "api_request_duration_summary" in metrics_summary["metrics"]:
            duration_summary = metrics_summary["metrics"][
                "api_request_duration_summary"
            ]
            if "default" in duration_summary:
                api_metrics = {
                    "avg_response_time_ms": duration_summary["default"].get("avg", 0),
                    "p95_response_time_ms": duration_summary["default"].get("p95", 0),
                    "p99_response_time_ms": duration_summary["default"].get("p99", 0),
                }

        # 提取数据库性能数据
        db_metrics = {}
        if "db_query_duration_summary" in metrics_summary["metrics"]:
            db_summary = metrics_summary["metrics"]["db_query_duration_summary"]
            if "default" in db_summary:
                db_metrics = {
                    "avg_query_time_ms": db_summary["default"].get("avg", 0),
                    "p95_query_time_ms": db_summary["default"].get("p95", 0),
                }

        # 计算错误率
        total_requests = metrics_summary["metrics"].get("api_request_count", {})
        error_requests = metrics_summary["metrics"].get("api_request_errors", {})

        total_count = sum(total_requests.values()) if total_requests else 0
        total_errors = sum(error_requests.values()) if error_requests else 0
        error_rate = (total_errors / total_count * 100) if total_count > 0 else 0

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "api_performance": api_metrics,
            "database_performance": db_metrics,
            "error_rate": error_rate,
            "total_requests": total_count,
            "total_errors": total_errors,
        }

    def get_business_metrics(self) -> Dict[str, Any]:
        """获取业务指标"""
        metrics_summary = self.metrics_collector.get_metric_summary()
        metrics = metrics_summary["metrics"]

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "assets": {
                "total_count": metrics.get("asset_total_count", {}).get("default", 0),
                "online_count": metrics.get("asset_online_count", {}).get("default", 0),
                "online_rate": self._calculate_online_rate(metrics),
            },
            "tasks": {
                "total_count": metrics.get("task_total_count", {}).get("default", 0),
                "success_rate": self._calculate_success_rate(metrics),
                "failure_count": metrics.get("task_failure_count", {}).get(
                    "default", 0
                ),
            },
            "nodes": {
                "online_count": metrics.get("node_online_count", {}).get("default", 0)
            },
        }

    def get_alerts_panel(self) -> Dict[str, Any]:
        """获取告警面板"""
        active_alerts = self.alert_manager.get_active_alerts()

        # 按严重级别分组
        critical_alerts = [
            a for a in active_alerts if a.severity == AlertSeverity.CRITICAL
        ]
        high_alerts = [a for a in active_alerts if a.severity == AlertSeverity.HIGH]
        medium_alerts = [a for a in active_alerts if a.severity == AlertSeverity.MEDIUM]
        low_alerts = [a for a in active_alerts if a.severity == AlertSeverity.LOW]

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_count": len(active_alerts),
            "alerts": {
                "critical": [self._alert_to_dict(a) for a in critical_alerts],
                "high": [self._alert_to_dict(a) for a in high_alerts],
                "medium": [self._alert_to_dict(a) for a in medium_alerts],
                "low": [self._alert_to_dict(a) for a in low_alerts],
            },
            "summary": self.alert_manager.get_alert_summary(),
        }

    def generate_dashboard_report(self) -> str:
        """生成监控面板报告"""
        overview = self.get_system_overview()
        app_perf = self.get_application_performance()
        business = self.get_business_metrics()
        alerts_panel = self.get_alerts_panel()

        report = []
        report.append("=" * 70)
        report.append("HermesNexus 监控面板")
        report.append("=" * 70)
        report.append(f"生成时间: {overview['timestamp']}")
        report.append("")

        # 系统健康度
        report.append("🏥 系统健康度: " + overview["system_health"])
        report.append("")

        # 资源使用情况
        report.append("📊 资源使用情况:")
        resources = overview["resource_usage"]
        for resource_name, resource_data in resources.items():
            usage = resource_data["usage_percent"]
            status = resource_data["status"]
            status_emoji = (
                "🟢" if status == "normal" else "🟡" if status == "warning" else "🔴"
            )
            report.append(f"  {resource_name.upper()}: {usage:.1f}% {status_emoji}")
        report.append("")

        # 应用性能
        report.append("⚡ 应用性能:")
        api_perf = app_perf["api_performance"]
        if api_perf:
            report.append(
                f"  平均响应时间: {api_perf.get('avg_response_time_ms', 0):.1f}ms"
            )
            report.append(
                f"  P95响应时间: {api_perf.get('p95_response_time_ms', 0):.1f}ms"
            )
            report.append(
                f"  P99响应时间: {api_perf.get('p99_response_time_ms', 0):.1f}ms"
            )
        report.append(f"  错误率: {app_perf['error_rate']:.2f}%")
        report.append("")

        # 业务指标
        report.append("💼 业务指标:")
        assets = business["assets"]
        tasks = business["tasks"]
        report.append(f"  资产总数: {assets['total_count']}")
        report.append(
            f"  在线资产: {assets['online_count']} ({assets['online_rate']:.1f}%)"
        )
        report.append(f"  任务总数: {tasks['total_count']}")
        report.append(f"  任务成功率: {tasks['success_rate']:.1f}%")
        report.append("")

        # 告警情况
        alerts = alerts_panel["alerts"]
        if alerts_panel["total_count"] > 0:
            report.append("🚨 活跃告警:")
            for severity in ["critical", "high", "medium", "low"]:
                severity_alerts = alerts[severity]
                if severity_alerts:
                    report.append(f"  {severity.upper()} ({len(severity_alerts)}):")
                    for alert in severity_alerts[:3]:  # 只显示前3个
                        report.append(f"    - {alert['message']}")
            report.append("")
        else:
            report.append("✅ 无活跃告警")
            report.append("")

        report.append("=" * 70)

        return "\n".join(report)

    def _calculate_system_health(
        self, system_metrics: Dict[str, Any], alert_summary: Dict[str, Any]
    ) -> str:
        """计算系统健康度"""
        # 检查资源使用情况
        cpu_usage = system_metrics.get("cpu_usage_percent", 0)
        memory_usage = system_metrics.get("memory_usage_percent", 0)
        disk_usage = system_metrics.get("disk_usage_percent", 0)

        resource_issues = sum([cpu_usage > 80, memory_usage > 85, disk_usage > 80])

        # 检查告警情况
        critical_alerts = alert_summary.get("critical_count", 0)
        high_alerts = alert_summary.get("high_count", 0)

        if critical_alerts > 0 or resource_issues >= 2:
            return "🔴 异常"
        elif high_alerts > 0 or resource_issues == 1:
            return "🟡 警告"
        else:
            return "🟢 正常"

    def _get_resource_status(
        self, usage: float, warning_threshold: float, critical_threshold: float
    ) -> str:
        """获取资源状态"""
        if usage > critical_threshold:
            return "critical"
        elif usage > warning_threshold:
            return "warning"
        else:
            return "normal"

    def _calculate_online_rate(self, metrics: Dict[str, Any]) -> float:
        """计算资产在线率"""
        total_count = metrics.get("asset_total_count", {}).get("default", 0)
        online_count = metrics.get("asset_online_count", {}).get("default", 0)
        return (online_count / total_count * 100) if total_count > 0 else 0

    def _calculate_success_rate(self, metrics: Dict[str, Any]) -> float:
        """计算任务成功率"""
        total_count = metrics.get("task_total_count", {}).get("default", 0)
        failure_count = metrics.get("task_failure_count", {}).get("default", 0)
        success_count = total_count - failure_count
        return (success_count / total_count * 100) if total_count > 0 else 100

    def _alert_to_dict(self, alert: Any) -> Dict[str, Any]:
        """将告警对象转换为字典"""
        return {
            "rule_name": alert.rule_name,
            "severity": alert.severity.value,
            "category": alert.category.value,
            "message": alert.message,
            "current_value": alert.current_value,
            "threshold": alert.threshold,
            "triggered_at": alert.triggered_at.isoformat(),
            "metric_name": alert.metric_name,
            "suggestion": alert.suggestion,
            "labels": alert.labels,
        }


# 全局监控面板实例
_global_dashboard = None


def get_monitoring_dashboard() -> MonitoringDashboard:
    """获取全局监控面板"""
    global _global_dashboard
    if _global_dashboard is None:
        _global_dashboard = MonitoringDashboard()
    return _global_dashboard
