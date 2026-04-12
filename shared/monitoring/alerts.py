"""
HermesNexus 告警规则定义
定义告警阈值、严重级别和通知策略
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta


class AlertSeverity(str, Enum):
    """告警严重级别"""

    CRITICAL = "critical"  # 严重，需要立即处理
    HIGH = "high"  # 高级，需要尽快处理
    MEDIUM = "medium"  # 中级，需要关注
    LOW = "low"  # 低级，可以延后处理
    INFO = "info"  # 信息，仅供了解


class AlertCategory(str, Enum):
    """告警分类"""

    SYSTEM_RESOURCE = "system_resource"  # 系统资源告警
    APPLICATION_PERF = "application_perf"  # 应用性能告警
    BUSINESS_ANOMALY = "business_anomaly"  # 业务异常告警
    DATABASE_ISSUE = "database_issue"  # 数据库问题告警
    SECURITY = "security"  # 安全告警


@dataclass
class AlertRule:
    """告警规则"""

    name: str  # 告警规则名称
    metric_name: str  # 监控指标名称
    severity: AlertSeverity  # 严重级别
    category: AlertCategory  # 告警分类
    condition: str  # 告警条件表达式
    threshold: float  # 阈值
    time_window: int  # 时间窗口(秒)
    description: str  # 告警描述
    suggestion: str  # 处理建议


# 系统资源告警规则
SYSTEM_ALERT_RULES = [
    AlertRule(
        name="高CPU使用率",
        metric_name="cpu_usage_percent",
        severity=AlertSeverity.HIGH,
        category=AlertCategory.SYSTEM_RESOURCE,
        condition="greater_than",
        threshold=80.0,
        time_window=300,  # 5分钟
        description="CPU使用率持续超过80%",
        suggestion="1. 检查是否有进程异常占用CPU\n2. 考虑扩容或负载均衡\n3. 查看是否有异常任务执行",
    ),
    AlertRule(
        name="严重CPU使用率",
        metric_name="cpu_usage_percent",
        severity=AlertSeverity.CRITICAL,
        category=AlertCategory.SYSTEM_RESOURCE,
        condition="greater_than",
        threshold=95.0,
        time_window=120,  # 2分钟
        description="CPU使用率持续超过95%",
        suggestion="1. 立即检查系统进程状态\n2. 考虑重启服务或扩容\n3. 检查是否有死循环或异常进程",
    ),
    AlertRule(
        name="高内存使用率",
        metric_name="memory_usage_percent",
        severity=AlertSeverity.HIGH,
        category=AlertCategory.SYSTEM_RESOURCE,
        condition="greater_than",
        threshold=85.0,
        time_window=300,
        description="内存使用率持续超过85%",
        suggestion="1. 检查内存泄漏问题\n2. 重启高内存占用的服务\n3. 考虑增加系统内存",
    ),
    AlertRule(
        name="严重内存使用率",
        metric_name="memory_usage_percent",
        severity=AlertSeverity.CRITICAL,
        category=AlertCategory.SYSTEM_RESOURCE,
        condition="greater_than",
        threshold=95.0,
        time_window=120,
        description="内存使用率持续超过95%",
        suggestion="1. 立即重启相关服务\n2. 检查是否有内存泄漏\n3. 考虑紧急扩容",
    ),
    AlertRule(
        name="磁盘空间不足",
        metric_name="disk_usage_percent",
        severity=AlertSeverity.HIGH,
        category=AlertCategory.SYSTEM_RESOURCE,
        condition="greater_than",
        threshold=90.0,
        time_window=60,
        description="磁盘使用率超过90%",
        suggestion="1. 清理日志文件和临时文件\n2. 归档或删除旧数据\n3. 扩容磁盘存储",
    ),
]


# 应用性能告警规则
APPLICATION_ALERT_RULES = [
    AlertRule(
        name="API错误率过高",
        metric_name="api_request_errors",
        severity=AlertSeverity.HIGH,
        category=AlertCategory.APPLICATION_PERF,
        condition="error_rate_high",
        threshold=0.05,  # 5%错误率
        time_window=300,
        description="API错误率超过5%",
        suggestion="1. 检查应用日志中的错误信息\n2. 查看是否有依赖服务异常\n3. 验证数据库连接状态",
    ),
    AlertRule(
        name="API响应时间过长",
        metric_name="api_request_duration_p95",
        severity=AlertSeverity.MEDIUM,
        category=AlertCategory.APPLICATION_PERF,
        condition="greater_than",
        threshold=2000.0,  # 2秒
        time_window=300,
        description="API P95响应时间超过2秒",
        suggestion="1. 分析慢查询日志\n2. 优化数据库查询\n3. 考虑增加缓存",
    ),
    AlertRule(
        name="数据库连接池耗尽",
        metric_name="db_connection_pool_size",
        severity=AlertSeverity.CRITICAL,
        category=AlertCategory.APPLICATION_PERF,
        condition="pool_exhausted",
        threshold=0.9,  # 90%使用率
        time_window=60,
        description="数据库连接池使用率超过90%",
        suggestion="1. 检查是否有连接泄漏\n2. 增加连接池大小\n3. 优化长时间运行的查询",
    ),
]


# 业务异常告警规则
BUSINESS_ALERT_RULES = [
    AlertRule(
        name="任务失败率过高",
        metric_name="task_failure_count",
        severity=AlertSeverity.HIGH,
        category=AlertCategory.BUSINESS_ANOMALY,
        condition="failure_rate_high",
        threshold=0.10,  # 10%失败率
        time_window=600,  # 10分钟
        description="任务失败率超过10%",
        suggestion="1. 查看失败任务的错误日志\n2. 检查目标资产状态\n3. 验证网络连通性",
    ),
    AlertRule(
        name="节点离线",
        metric_name="node_online_count",
        severity=AlertSeverity.HIGH,
        category=AlertCategory.BUSINESS_ANOMALY,
        condition="count_decrease",
        threshold=0.5,  # 减少50%
        time_window=300,
        description="在线节点数量突然减少",
        suggestion="1. 检查网络连接状态\n2. 查看节点服务状态\n3. 通知相关运维人员",
    ),
    AlertRule(
        name="资产离线率过高",
        metric_name="asset_online_count",
        severity=AlertSeverity.MEDIUM,
        category=AlertCategory.BUSINESS_ANOMALY,
        condition="rate_low",
        threshold=0.80,  # 在线率低于80%
        time_window=600,
        description="资产在线率低于80%",
        suggestion="1. 查看离线资产列表\n2. 检查网络连通性\n3. 分析离线原因",
    ),
]


@dataclass
class Alert:
    """告警实例"""

    rule_name: str  # 触发的规则名称
    severity: AlertSeverity  # 严重级别
    category: AlertCategory  # 告警分类
    message: str  # 告警消息
    current_value: float  # 当前值
    threshold: float  # 阈值
    triggered_at: datetime  # 触发时间
    metric_name: str  # 指标名称
    suggestion: str  # 处理建议
    labels: Dict[str, str]  # 标签信息
    resolved: bool = False  # 是否已解决
    resolved_at: Optional[datetime] = None  # 解决时间


class AlertManager:
    """告警管理器"""

    def __init__(self):
        self.active_alerts = {}  # 活跃告警 {rule_name: Alert}
        self.alert_history = []  # 告警历史
        self.rules = SYSTEM_ALERT_RULES + APPLICATION_ALERT_RULES + BUSINESS_ALERT_RULES

    def check_metrics(self, metrics: Dict[str, Any]) -> List[Alert]:
        """检查指标并触发告警"""
        new_alerts = []

        for rule in self.rules:
            metric_value = self._get_metric_value(metrics, rule.metric_name)

            if metric_value is None:
                continue

            if self._should_trigger_alert(rule, metric_value, metrics):
                alert = Alert(
                    rule_name=rule.name,
                    severity=rule.severity,
                    category=rule.category,
                    message=f"{rule.description}: 当前值 {metric_value}",
                    current_value=metric_value,
                    threshold=rule.threshold,
                    triggered_at=datetime.utcnow(),
                    metric_name=rule.metric_name,
                    suggestion=rule.suggestion,
                    labels={},
                )

                new_alerts.append(alert)
                self.active_alerts[rule.name] = alert

        return new_alerts

    def resolve_alert(self, rule_name: str):
        """解决告警"""
        if rule_name in self.active_alerts:
            alert = self.active_alerts[rule_name]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            self.alert_history.append(alert)
            del self.active_alerts[rule_name]

    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())

    def get_alert_summary(self) -> Dict[str, Any]:
        """获取告警摘要"""
        active_alerts = self.get_active_alerts()

        # 按严重级别统计
        severity_count = {}
        for alert in active_alerts:
            severity_count[alert.severity.value] = (
                severity_count.get(alert.severity.value, 0) + 1
            )

        # 按分类统计
        category_count = {}
        for alert in active_alerts:
            category_count[alert.category.value] = (
                category_count.get(alert.category.value, 0) + 1
            )

        return {
            "total_active_alerts": len(active_alerts),
            "severity_distribution": severity_count,
            "category_distribution": category_count,
            "critical_count": severity_count.get("critical", 0),
            "high_count": severity_count.get("high", 0),
            "medium_count": severity_count.get("medium", 0),
            "low_count": severity_count.get("low", 0),
        }

    def _get_metric_value(
        self, metrics: Dict[str, Any], metric_name: str
    ) -> Optional[float]:
        """获取指标值"""
        # 直接获取指标值
        if metric_name in metrics:
            return float(metrics[metric_name])

        # 处理摘要指标
        if f"{metric_name}_summary" in metrics:
            summary = metrics[f"{metric_name}_summary"]
            if isinstance(summary, dict) and "default" in summary:
                if "avg" in summary["default"]:
                    return float(summary["default"]["avg"])
                if "count" in summary["default"]:
                    return float(summary["default"]["count"])

        return None

    def _should_trigger_alert(
        self, rule: AlertRule, value: float, metrics: Dict[str, Any]
    ) -> bool:
        """判断是否应该触发告警"""
        if rule.condition == "greater_than":
            return value > rule.threshold
        elif rule.condition == "less_than":
            return value < rule.threshold
        elif rule.condition == "error_rate_high":
            # 计算错误率
            total_requests = metrics.get("api_request_count", 1)
            error_requests = metrics.get("api_request_errors", 0)
            error_rate = error_requests / total_requests if total_requests > 0 else 0
            return error_rate > rule.threshold
        elif rule.condition == "pool_exhausted":
            # 检查连接池使用率
            pool_size = value
            max_pool_size = 100  # 假设最大连接池大小
            return pool_size / max_pool_size > rule.threshold
        else:
            return False


# 全局告警管理器实例
_global_alert_manager = None


def get_alert_manager() -> AlertManager:
    """获取全局告警管理器"""
    global _global_alert_manager
    if _global_alert_manager is None:
        _global_alert_manager = AlertManager()
    return _global_alert_manager
