"""
HermesNexus 监控指标定义
定义系统、应用、业务层面的关键指标
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List
from datetime import datetime
from collections import defaultdict
import time
import psutil


class MetricType(str, Enum):
    """指标类型"""

    COUNTER = "counter"  # 计数器，单调递增
    GAUGE = "gauge"  # 仪表盘，可增可减
    HISTOGRAM = "histogram"  # 直方图，分布统计
    SUMMARY = "summary"  # 摘要，统计信息


class MetricCategory(str, Enum):
    """指标分类"""

    SYSTEM = "system"  # 系统资源指标
    APPLICATION = "application"  # 应用性能指标
    BUSINESS = "business"  # 业务指标
    DATABASE = "database"  # 数据库指标


@dataclass
class MetricDefinition:
    """指标定义"""

    name: str  # 指标名称
    type: MetricType  # 指标类型
    category: MetricCategory  # 指标分类
    description: str  # 指标描述
    unit: str  # 单位
    labels: List[str]  # 标签维度


# 系统资源指标定义
SYSTEM_METRICS = {
    # CPU相关
    "cpu_usage_percent": MetricDefinition(
        name="cpu_usage_percent",
        type=MetricType.GAUGE,
        category=MetricCategory.SYSTEM,
        description="CPU使用率",
        unit="%",
        labels=["host", "core"],
    ),
    # 内存相关
    "memory_usage_percent": MetricDefinition(
        name="memory_usage_percent",
        type=MetricType.GAUGE,
        category=MetricCategory.SYSTEM,
        description="内存使用率",
        unit="%",
        labels=["host"],
    ),
    "memory_used_bytes": MetricDefinition(
        name="memory_used_bytes",
        type=MetricType.GAUGE,
        category=MetricCategory.SYSTEM,
        description="已使用内存字节数",
        unit="bytes",
        labels=["host"],
    ),
    "memory_available_bytes": MetricDefinition(
        name="memory_available_bytes",
        type=MetricType.GAUGE,
        category=MetricCategory.SYSTEM,
        description="可用内存字节数",
        unit="bytes",
        labels=["host"],
    ),
    # 磁盘相关
    "disk_usage_percent": MetricDefinition(
        name="disk_usage_percent",
        type=MetricType.GAUGE,
        category=MetricCategory.SYSTEM,
        description="磁盘使用率",
        unit="%",
        labels=["host", "mount_point"],
    ),
    "disk_used_bytes": MetricDefinition(
        name="disk_used_bytes",
        type=MetricType.GAUGE,
        category=MetricCategory.SYSTEM,
        description="已使用磁盘字节数",
        unit="bytes",
        labels=["host", "mount_point"],
    ),
    "disk_io_read_bytes": MetricDefinition(
        name="disk_io_read_bytes",
        type=MetricType.COUNTER,
        category=MetricCategory.SYSTEM,
        description="磁盘读取字节数",
        unit="bytes",
        labels=["host", "device"],
    ),
    "disk_io_write_bytes": MetricDefinition(
        name="disk_io_write_bytes",
        type=MetricType.COUNTER,
        category=MetricCategory.SYSTEM,
        description="磁盘写入字节数",
        unit="bytes",
        labels=["host", "device"],
    ),
    # 网络相关
    "network_bytes_sent": MetricDefinition(
        name="network_bytes_sent",
        type=MetricType.COUNTER,
        category=MetricCategory.SYSTEM,
        description="网络发送字节数",
        unit="bytes",
        labels=["host", "interface"],
    ),
    "network_bytes_recv": MetricDefinition(
        name="network_bytes_recv",
        type=MetricType.COUNTER,
        category=MetricCategory.SYSTEM,
        description="网络接收字节数",
        unit="bytes",
        labels=["host", "interface"],
    ),
}


# 应用性能指标定义
APPLICATION_METRICS = {
    # API相关
    "api_request_count": MetricDefinition(
        name="api_request_count",
        type=MetricType.COUNTER,
        category=MetricCategory.APPLICATION,
        description="API请求总数",
        unit="requests",
        labels=["endpoint", "method", "status"],
    ),
    "api_request_duration": MetricDefinition(
        name="api_request_duration",
        type=MetricType.HISTOGRAM,
        category=MetricCategory.APPLICATION,
        description="API请求耗时",
        unit="ms",
        labels=["endpoint", "method"],
    ),
    "api_request_errors": MetricDefinition(
        name="api_request_errors",
        type=MetricType.COUNTER,
        category=MetricCategory.APPLICATION,
        description="API错误总数",
        unit="errors",
        labels=["endpoint", "method", "error_type"],
    ),
    # 数据库相关
    "db_query_count": MetricDefinition(
        name="db_query_count",
        type=MetricType.COUNTER,
        category=MetricCategory.APPLICATION,
        description="数据库查询总数",
        unit="queries",
        labels=["operation", "table"],
    ),
    "db_query_duration": MetricDefinition(
        name="db_query_duration",
        type=MetricType.HISTOGRAM,
        category=MetricCategory.APPLICATION,
        description="数据库查询耗时",
        unit="ms",
        labels=["operation", "table"],
    ),
    "db_connection_pool_size": MetricDefinition(
        name="db_connection_pool_size",
        type=MetricType.GAUGE,
        category=MetricCategory.APPLICATION,
        description="数据库连接池大小",
        unit="connections",
        labels=["pool_type"],
    ),
    # 任务相关
    "task_processing_duration": MetricDefinition(
        name="task_processing_duration",
        type=MetricType.HISTOGRAM,
        category=MetricCategory.APPLICATION,
        description="任务处理耗时",
        unit="ms",
        labels=["task_type", "status"],
    ),
    "task_queue_size": MetricDefinition(
        name="task_queue_size",
        type=MetricType.GAUGE,
        category=MetricCategory.APPLICATION,
        description="任务队列大小",
        unit="tasks",
        labels=["queue_name", "priority"],
    ),
}


# 业务指标定义
BUSINESS_METRICS = {
    # 资产相关
    "asset_total_count": MetricDefinition(
        name="asset_total_count",
        type=MetricType.GAUGE,
        category=MetricCategory.BUSINESS,
        description="资产总数",
        unit="assets",
        labels=["asset_type", "status"],
    ),
    "asset_online_count": MetricDefinition(
        name="asset_online_count",
        type=MetricType.GAUGE,
        category=MetricCategory.BUSINESS,
        description="在线资产数",
        unit="assets",
        labels=["asset_type"],
    ),
    # 任务相关
    "task_total_count": MetricDefinition(
        name="task_total_count",
        type=MetricType.GAUGE,
        category=MetricCategory.BUSINESS,
        description="任务总数",
        unit="tasks",
        labels=["task_type", "status"],
    ),
    "task_success_rate": MetricDefinition(
        name="task_success_rate",
        type=MetricType.GAUGE,
        category=MetricCategory.BUSINESS,
        description="任务成功率",
        unit="%",
        labels=["task_type", "time_window"],
    ),
    "task_failure_count": MetricDefinition(
        name="task_failure_count",
        type=MetricType.COUNTER,
        category=MetricCategory.BUSINESS,
        description="任务失败总数",
        unit="failures",
        labels=["task_type", "failure_reason"],
    ),
    # 节点相关
    "node_online_count": MetricDefinition(
        name="node_online_count",
        type=MetricType.GAUGE,
        category=MetricCategory.BUSINESS,
        description="在线节点数",
        unit="nodes",
        labels=["node_type", "region"],
    ),
    "node_heartbeat_delay": MetricDefinition(
        name="node_heartbeat_delay",
        type=MetricType.HISTOGRAM,
        category=MetricCategory.BUSINESS,
        description="节点心跳延迟",
        unit="ms",
        labels=["node_id", "region"],
    ),
}


class MetricsCollector:
    """指标采集器"""

    def __init__(self):
        self.metrics = defaultdict(lambda: defaultdict(float))
        self.histograms = defaultdict(lambda: defaultdict(list))
        self.start_time = time.time()

    def collect_system_metrics(self) -> Dict[str, Any]:
        """采集系统指标"""
        metrics = {}

        try:
            # CPU指标
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics["cpu_usage_percent"] = cpu_percent

            # 内存指标
            memory = psutil.virtual_memory()
            metrics["memory_usage_percent"] = memory.percent
            metrics["memory_used_bytes"] = memory.used
            metrics["memory_available_bytes"] = memory.available

            # 磁盘指标
            disk = psutil.disk_usage("/")
            metrics["disk_usage_percent"] = disk.percent
            metrics["disk_used_bytes"] = disk.used

            # 网络指标
            net_io = psutil.net_io_counters()
            metrics["network_bytes_sent"] = net_io.bytes_sent
            metrics["network_bytes_recv"] = net_io.bytes_recv

        except Exception as e:
            print(f"系统指标采集失败: {e}")

        return metrics

    def record_counter(
        self, name: str, value: float = 1.0, labels: Dict[str, str] = None
    ):
        """记录计数器指标"""
        label_key = self._make_label_key(labels)
        self.metrics[name][label_key] += value

    def record_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """记录仪表盘指标"""
        label_key = self._make_label_key(labels)
        self.metrics[name][label_key] = value

    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """记录直方图指标"""
        label_key = self._make_label_key(labels)
        self.histograms[name][label_key].append(value)

    def record_api_request(
        self, endpoint: str, method: str, status: str, duration: float
    ):
        """记录API请求"""
        # 请求计数
        self.record_counter(
            "api_request_count",
            1.0,
            {"endpoint": endpoint, "method": method, "status": status},
        )

        # 请求耗时
        self.record_histogram(
            "api_request_duration",
            duration * 1000,
            {"endpoint": endpoint, "method": method},  # 转换为毫秒
        )

        # 错误计数
        if status != "200":
            self.record_counter(
                "api_request_errors",
                1.0,
                {"endpoint": endpoint, "method": method, "error_type": "http_error"},
            )

    def record_db_query(self, operation: str, table: str, duration: float):
        """记录数据库查询"""
        # 查询计数
        self.record_counter(
            "db_query_count", 1.0, {"operation": operation, "table": table}
        )

        # 查询耗时
        self.record_histogram(
            "db_query_duration",
            duration * 1000,
            {"operation": operation, "table": table},
        )

    def get_metric_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        summary = {
            "collection_time": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - self.start_time,
            "metrics": {},
        }

        # 汇总计数器和仪表盘指标
        for metric_name, label_data in self.metrics.items():
            summary["metrics"][metric_name] = dict(label_data)

        # 汇总直方图指标
        for metric_name, label_data in self.histograms.items():
            summary["metrics"][f"{metric_name}_summary"] = {}
            for label_key, values in label_data.items():
                if values:
                    sorted_values = sorted(values)
                    summary["metrics"][f"{metric_name}_summary"][label_key] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "p50": sorted_values[len(sorted_values) // 2],
                        "p95": (
                            sorted_values[int(len(sorted_values) * 0.95)]
                            if len(sorted_values) >= 20
                            else sorted_values[-1]
                        ),
                        "p99": (
                            sorted_values[int(len(sorted_values) * 0.99)]
                            if len(sorted_values) >= 100
                            else sorted_values[-1]
                        ),
                    }

        return summary

    def _make_label_key(self, labels: Dict[str, str] = None) -> str:
        """创建标签键"""
        if not labels:
            return "default"

        sorted_items = sorted(labels.items())
        return ",".join([f"{k}={v}" for k, v in sorted_items])


# 全局指标采集器实例
_global_collector = None


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标采集器"""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector
