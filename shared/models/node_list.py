"""
HermesNexus v1.2 - 节点列表查询模型
支持分页、筛选、批量查询的节点列表功能
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class NodeQueryFilter(str, Enum):
    """节点查询过滤器类型"""

    STATUS = "status"  # 状态筛选
    NODE_TYPE = "node_type"  # 节点类型筛选
    TAGS = "tags"  # 标签筛选
    LOCATION = "location"  # 位置筛选
    SEARCH = "search"  # 全文搜索
    HEARTBEAT_AFTER = "heartbeat_after"  # 心跳时间筛选
    HEARTBEAT_BEFORE = "heartbeat_before"  # 心跳时间筛选
    CREATED_AFTER = "created_after"  # 创建时间筛选
    CREATED_BEFORE = "created_before"  # 创建时间筛选
    CAPABILITIES = "capabilities"  # 能力筛选
    ACTIVE_TASKS = "active_tasks"  # 活跃任务数筛选


class NodeSortField(str, Enum):
    """节点排序字段"""

    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    NODE_NAME = "node_name"
    LAST_HEARTBEAT = "last_heartbeat"
    STATUS = "status"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"


class SortOrder(str, Enum):
    """排序方向"""

    ASC = "asc"  # 升序
    DESC = "desc"  # 降序


class NodeListRequest(BaseModel):
    """节点列表查询请求"""

    # 分页参数
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")

    # 筛选参数
    filters: Dict[str, Any] = Field(default_factory=dict, description="筛选条件")
    status: Optional[List[str]] = Field(None, description="状态列表")
    node_type: Optional[str] = Field(None, description="节点类型")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    location: Optional[str] = Field(None, description="位置")
    search: Optional[str] = Field(None, description="搜索关键词")

    # 时间范围筛选
    heartbeat_after: Optional[str] = Field(None, description="心跳时间之后(ISO格式)")
    heartbeat_before: Optional[str] = Field(None, description="心跳时间之前(ISO格式)")
    created_after: Optional[str] = Field(None, description="创建时间之后(ISO格式)")
    created_before: Optional[str] = Field(None, description="创建时间之前(ISO格式)")

    # 排序参数
    sort_by: NodeSortField = Field(NodeSortField.CREATED_AT, description="排序字段")
    sort_order: SortOrder = Field(SortOrder.DESC, description="排序方向")

    # 扩展参数
    include_heartbeat_stats: bool = Field(False, description="是否包含心跳统计")
    include_task_summary: bool = Field(False, description="是否包含任务摘要")
    include_audit_summary: bool = Field(False, description="是否包含审计摘要")

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 20,
                "status": ["active", "registered"],
                "node_type": "physical",
                "tags": ["production", "linux"],
                "search": "data-center-1",
                "sort_by": "last_heartbeat",
                "sort_order": "desc",
                "include_heartbeat_stats": True,
                "include_task_summary": True,
            }
        }


class NodeStatusSummary(BaseModel):
    """节点状态摘要"""

    is_online: bool = Field(..., description="是否在线")
    is_active: bool = Field(..., description="是否活跃")
    can_accept_tasks: bool = Field(..., description="是否能接受任务")
    health_status: str = Field(..., description="健康状态: healthy, degraded, error, unknown")
    last_heartbeat_age_seconds: Optional[int] = Field(None, description="最后心跳距现在的秒数")
    heartbeat_timeout_seconds: int = Field(300, description="心跳超时秒数")

    class Config:
        json_schema_extra = {
            "example": {
                "is_online": True,
                "is_active": True,
                "can_accept_tasks": True,
                "health_status": "healthy",
                "last_heartbeat_age_seconds": 45,
                "heartbeat_timeout_seconds": 300,
            }
        }


class NodeHeartbeatStats(BaseModel):
    """节点心跳统计"""

    total_heartbeats: int = Field(0, description="总心跳次数")
    successful_heartbeats: int = Field(0, description="成功心跳次数")
    failed_heartbeats: int = Field(0, description="失败心跳次数")
    avg_heartbeat_interval_seconds: Optional[float] = Field(None, description="平均心跳间隔(秒)")
    last_successful_heartbeat: Optional[str] = Field(None, description="最后成功心跳时间")
    last_failed_heartbeat: Optional[str] = Field(None, description="最后失败心跳时间")

    class Config:
        json_schema_extra = {
            "example": {
                "total_heartbeats": 1524,
                "successful_heartbeats": 1520,
                "failed_heartbeats": 4,
                "avg_heartbeat_interval_seconds": 58.5,
                "last_successful_heartbeat": "2026-04-15T10:30:00Z",
                "last_failed_heartbeat": "2026-04-15T08:15:00Z",
            }
        }


class NodeTaskSummary(BaseModel):
    """节点任务摘要"""

    total_tasks: int = Field(0, description="总任务数")
    running_tasks: int = Field(0, description="运行中任务数")
    completed_tasks: int = Field(0, description="已完成任务数")
    failed_tasks: int = Field(0, description="失败任务数")
    current_task_load: int = Field(0, description="当前任务负载")
    max_concurrent_tasks: int = Field(3, description="最大并发任务数")
    task_utilization_percent: float = Field(0.0, description="任务利用率百分比")
    recent_task_ids: List[str] = Field(default_factory=list, description="最近任务ID列表")

    class Config:
        json_schema_extra = {
            "example": {
                "total_tasks": 156,
                "running_tasks": 2,
                "completed_tasks": 148,
                "failed_tasks": 6,
                "current_task_load": 2,
                "max_concurrent_tasks": 3,
                "task_utilization_percent": 66.7,
                "recent_task_ids": ["task-001", "task-002", "task-003"],
            }
        }


class NodeAuditSummary(BaseModel):
    """节点审计摘要"""

    total_audit_logs: int = Field(0, description="总审计日志数")
    recent_errors: int = Field(0, description="最近错误数")
    recent_warnings: int = Field(0, description="最近警告数")
    last_error: Optional[str] = Field(None, description="最后错误信息")
    last_error_time: Optional[str] = Field(None, description="最后错误时间")
    last_audit_log: Optional[str] = Field(None, description="最后审计日志时间")
    recent_audit_activities: List[str] = Field(default_factory=list, description="最近审计活动")

    class Config:
        json_schema_extra = {
            "example": {
                "total_audit_logs": 892,
                "recent_errors": 2,
                "recent_warnings": 5,
                "last_error": "SSH connection timeout",
                "last_error_time": "2026-04-15T09:45:00Z",
                "last_audit_log": "2026-04-15T10:30:00Z",
                "recent_audit_activities": [
                    "task.exec.success",
                    "heartbeat.received",
                    "task.started",
                ],
            }
        }


class NodeListResponse(BaseModel):
    """节点列表响应"""

    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="节点列表")
    total: int = Field(0, description="总节点数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页数量")
    total_pages: int = Field(0, description="总页数")
    has_next: bool = Field(False, description="是否有下一页")
    has_prev: bool = Field(False, description="是否有上一页")

    # 汇总信息
    status_summary: Dict[str, int] = Field(default_factory=dict, description="状态摘要统计")
    health_summary: Dict[str, int] = Field(default_factory=dict, description="健康状态摘要统计")

    class Config:
        json_schema_extra = {
            "example": {
                "nodes": [],
                "total": 45,
                "page": 1,
                "page_size": 20,
                "total_pages": 3,
                "has_next": True,
                "has_prev": False,
                "status_summary": {
                    "active": 30,
                    "inactive": 10,
                    "registered": 3,
                    "failed": 2,
                },
                "health_summary": {
                    "healthy": 28,
                    "degraded": 5,
                    "error": 2,
                    "unknown": 10,
                },
            }
        }


class BatchNodeRequest(BaseModel):
    """批量节点查询请求"""

    node_ids: List[str] = Field(..., description="节点ID列表", min_items=1, max_items=100)
    include_heartbeat_stats: bool = Field(False, description="是否包含心跳统计")
    include_task_summary: bool = Field(False, description="是否包含任务摘要")
    include_audit_summary: bool = Field(False, description="是否包含审计摘要")

    class Config:
        json_schema_extra = {
            "example": {
                "node_ids": ["node-001", "node-002", "node-003"],
                "include_heartbeat_stats": True,
                "include_task_summary": True,
                "include_audit_summary": False,
            }
        }


class BatchNodeResponse(BaseModel):
    """批量节点查询响应"""

    nodes: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="节点详情字典，key为node_id")
    found_nodes: int = Field(0, description="找到的节点数")
    missing_nodes: List[str] = Field(default_factory=list, description="未找到的节点ID列表")

    class Config:
        json_schema_extra = {
            "example": {
                "nodes": {"node-001": {}, "node-002": {}},
                "found_nodes": 2,
                "missing_nodes": ["node-003"],
            }
        }
