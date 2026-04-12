"""
HermesNexus Phase 2 - Audit Log Model
审计日志数据模型
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field, root_validator


class AuditAction(str, Enum):
    """审计动作类型"""
    # Task lifecycle
    TASK_CREATED = "task_created"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_SUCCEEDED = "task_succeeded"
    TASK_FAILED = "task_failed"
    TASK_TIMEOUT = "task_timeout"
    TASK_CANCELLED = "task_cancelled"
    TASK_RETRY = "task_retry"

    # Auth/security events
    AUTH_SUCCESS = "auth_success"
    AUTH_DENIED = "auth_denied"

    # Node lifecycle
    NODE_REGISTERED = "node_registered"
    NODE_ONLINE = "node_online"
    NODE_OFFLINE = "node_offline"
    NODE_HEARTBEAT = "node_heartbeat"
    NODE_DISCONNECTED = "node_disconnected"

    # Asset lifecycle
    ASSET_REGISTERED = "asset_registered"
    ASSET_UPDATED = "asset_updated"
    ASSET_DECOMMISSIONED = "asset_decommissioned"
    ASSET_ASSOCIATED = "asset_associated"
    ASSET_DISSOCIATED = "asset_dissociated"

    # System events
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"
    SYSTEM_ERROR = "system_error"
    SYSTEM_WARNING = "system_warning"

    # User actions
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_ACTION = "user_action"


class EventLevel(str, Enum):
    """事件级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditCategory(str, Enum):
    """审计分类"""
    TASK = "task"              # 任务相关
    NODE = "node"              # 节点相关
    ASSET = "asset"            # 资产相关
    SYSTEM = "system"          # 系统相关
    SECURITY = "security"      # 安全相关
    USER = "user"              # 用户相关


class AuditLog(BaseModel):
    """审计日志模型"""
    audit_id: str = Field(..., description="审计日志唯一标识")
    action: AuditAction = Field(..., description="审计动作类型")
    category: AuditCategory = Field(..., description="审计分类")
    level: EventLevel = Field(default=EventLevel.INFO, description="事件级别")

    # 操作者信息
    actor: str = Field(..., description="操作发起者")
    actor_type: str = Field(default="user", description="操作者类型: user, system, node")

    # 目标信息
    target_type: str = Field(..., description="目标对象类型: task, node, asset, system")
    target_id: Optional[str] = Field(None, description="目标对象ID")

    # 关联信息
    related_task_id: Optional[str] = Field(None, description="关联的任务ID")
    related_node_id: Optional[str] = Field(None, description="关联的节点ID")
    related_asset_id: Optional[str] = Field(None, description="关联的资产ID")

    # 事件详情
    details: Dict[str, Any] = Field(default_factory=dict, description="事件详细信息")
    message: str = Field(..., description="事件描述消息")

    # 上下文信息
    ip_address: Optional[str] = Field(None, description="操作发起IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")
    request_id: Optional[str] = Field(None, description="请求ID")

    # 时间戳
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="事件时间戳")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="记录创建时间")

    class Config:
        json_schema_extra = {
            "example": {
                "audit_id": "audit-001",
                "action": "task_created",
                "category": "task",
                "level": "info",
                "actor": "admin",
                "actor_type": "user",
                "target_type": "task",
                "target_id": "task-001",
                "related_task_id": "task-001",
                "details": {
                    "task_name": "系统信息查询",
                    "task_type": "basic_exec",
                    "target_asset": "asset-001"
                },
                "message": "创建任务: 系统信息查询",
                "ip_address": "192.168.1.100",
                "request_id": "req-001",
                "timestamp": "2026-04-12T15:30:00Z"
            }
        }


class AuditLogCreateRequest(BaseModel):
    """审计日志创建请求"""
    action: AuditAction = Field(..., description="审计动作类型")
    category: AuditCategory = Field(..., description="审计分类")
    level: EventLevel = Field(default=EventLevel.INFO, description="事件级别")

    # 操作者信息
    actor: str = Field(..., description="操作发起者")
    actor_type: str = Field(default="user", description="操作者类型")

    # 目标信息
    target_type: str = Field(..., description="目标对象类型")
    target_id: Optional[str] = Field(None, description="目标对象ID")

    # 关联信息
    related_task_id: Optional[str] = Field(None, description="关联的任务ID")
    related_node_id: Optional[str] = Field(None, description="关联的节点ID")
    related_asset_id: Optional[str] = Field(None, description="关联的资产ID")

    # 事件详情
    details: Dict[str, Any] = Field(default_factory=dict, description="事件详细信息")
    message: str = Field(..., description="事件描述消息")

    # 上下文信息
    ip_address: Optional[str] = Field(None, description="操作发起IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")
    request_id: Optional[str] = Field(None, description="请求ID")

    @root_validator(pre=True)
    def _compat_metadata_alias(cls, values):
        if isinstance(values, dict) and "details" not in values and "metadata" in values:
            values["details"] = values.pop("metadata")
        return values

    class Config:
        json_schema_extra = {
            "example": {
                "action": "task_created",
                "category": "task",
                "level": "info",
                "actor": "admin",
                "target_type": "task",
                "target_id": "task-001",
                "message": "创建任务: 系统信息查询",
                "details": {
                    "task_name": "系统信息查询"
                }
            }
        }


class AuditLogQueryParams(BaseModel):
    """审计日志查询参数"""
    action: Optional[AuditAction] = Field(None, description="按动作类型过滤")
    category: Optional[AuditCategory] = Field(None, description="按分类过滤")
    level: Optional[EventLevel] = Field(None, description="按级别过滤")
    actor: Optional[str] = Field(None, description="按操作者过滤")
    target_type: Optional[str] = Field(None, description="按目标类型过滤")
    target_id: Optional[str] = Field(None, description="按目标ID过滤")
    related_task_id: Optional[str] = Field(None, description="按关联任务过滤")
    related_node_id: Optional[str] = Field(None, description="按关联节点过滤")
    related_asset_id: Optional[str] = Field(None, description="按关联资产过滤")
    search: Optional[str] = Field(None, description="搜索关键词（消息、详情）")

    # 时间范围过滤
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")

    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(50, ge=1, le=500, description="每页大小")
    sort_by: str = Field("timestamp", description="排序字段")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="排序方向")

    class Config:
        json_schema_extra = {
            "example": {
                "category": "task",
                "level": "error",
                "start_time": "2026-04-12T00:00:00Z",
                "end_time": "2026-04-12T23:59:59Z",
                "page": 1,
                "page_size": 50
            }
        }


class AuditLogListResponse(BaseModel):
    """审计日志列表响应"""
    total: int = Field(..., description="总数量")
    audit_logs: List[AuditLog] = Field(..., description="审计日志列表")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    total_pages: int = Field(..., description="总页数")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 5000,
                "audit_logs": [],
                "page": 1,
                "page_size": 50,
                "total_pages": 100
            }
        }


class AuditStats(BaseModel):
    """审计统计信息"""
    total_events: int = Field(..., description="总事件数")
    by_category: Dict[str, int] = Field(default_factory=dict, description="按分类统计")
    by_action: Dict[str, int] = Field(default_factory=dict, description="按动作统计")
    by_level: Dict[str, int] = Field(default_factory=dict, description="按级别统计")

    # 时间范围统计
    events_last_hour: int = Field(..., description="最近1小时事件数")
    events_last_day: int = Field(..., description="最近1天事件数")
    events_last_week: int = Field(..., description="最近1周事件数")

    # 错误统计
    error_events: int = Field(..., description="错误事件数")
    critical_events: int = Field(..., description="严重错误事件数")

    class Config:
        json_schema_extra = {
            "example": {
                "total_events": 50000,
                "by_category": {
                    "task": 30000,
                    "node": 10000,
                    "asset": 5000,
                    "system": 3000,
                    "security": 1500,
                    "user": 500
                },
                "by_action": {
                    "task_created": 15000,
                    "task_succeeded": 12000,
                    "task_failed": 2000,
                    "node_heartbeat": 8000
                },
                "by_level": {
                    "info": 40000,
                    "warning": 8000,
                    "error": 1500,
                    "critical": 500
                },
                "events_last_hour": 1000,
                "events_last_day": 15000,
                "events_last_week": 50000,
                "error_events": 2000,
                "critical_events": 500
            }
        }


class AuditExportRequest(BaseModel):
    """审计日志导出请求"""
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    category: Optional[AuditCategory] = Field(None, description="审计分类")
    level: Optional[EventLevel] = Field(None, description="事件级别")
    format: str = Field("json", description="导出格式: json, csv")
    limit: int = Field(10000, ge=1, le=100000, description="最大导出数量")

    class Config:
        json_schema_extra = {
            "example": {
                "start_time": "2026-04-12T00:00:00Z",
                "end_time": "2026-04-12T23:59:59Z",
                "category": "task",
                "level": "error",
                "format": "json",
                "limit": 10000
            }
        }
