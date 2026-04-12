"""
核心数据模型定义

使用 Pydantic 定义数据验证模型
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, field_serializer
import uuid

from .enums import (
    NodeStatus,
    DeviceType,
    DeviceProtocol,
    DeviceStatus,
    JobStatus,
    JobType,
    TaskType,
    TaskPriority,
    EventType,
    EventLevel,
    UserRole,
    AuditAction,
)


def get_utc_now() -> datetime:
    """获取当前UTC时间的辅助函数"""
    return datetime.now(timezone.utc)


class Node(BaseModel):
    """节点模型"""

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    location: Optional[str] = None
    status: NodeStatus = NodeStatus.OFFLINE
    tags: List[str] = Field(default_factory=list)
    last_heartbeat: Optional[datetime] = None
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    @field_serializer("last_heartbeat", "created_at", "updated_at")
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        return dt.isoformat()


class Device(BaseModel):
    """设备模型"""

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    type: DeviceType
    protocol: DeviceProtocol
    host: str = Field(..., min_length=1)
    port: Optional[int] = None
    credentials: Dict[str, Any] = Field(default_factory=dict)
    status: DeviceStatus = DeviceStatus.UNKNOWN
    node_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_seen: Optional[datetime] = None
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    @field_serializer("last_seen", "created_at", "updated_at")
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        return dt.isoformat()


class Job(BaseModel):
    """任务模型"""

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    type: JobType
    status: JobStatus = JobStatus.PENDING
    target_device_id: str = Field(..., min_length=1)
    target_device_name: Optional[str] = None
    task_type: TaskType = TaskType.EXEC
    command: Optional[str] = None
    script: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: int = 300
    retry_times: int = 0
    max_retries: int = 3
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @field_serializer("created_at", "updated_at", "started_at", "completed_at")
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        return dt.isoformat()


class Event(BaseModel):
    """事件模型"""

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str = Field(..., min_length=1, max_length=255)
    type: EventType
    level: EventLevel = EventLevel.INFO
    source: str = Field(..., min_length=1)
    source_type: str = "node"  # node, device, cloud, system
    title: Optional[str] = None
    message: str = Field(..., min_length=1)
    data: Dict[str, Any] = Field(default_factory=dict)
    related_job_id: Optional[str] = None
    related_device_id: Optional[str] = None
    related_node_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=get_utc_now)

    @field_serializer("timestamp")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()


class User(BaseModel):
    """用户模型"""

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=5, max_length=255)
    password_hash: str = Field(..., min_length=1)
    role: UserRole = UserRole.VIEWER
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    @field_validator("email")
    def email_format(cls, v):
        """验证邮箱格式"""
        if "@" not in v:
            raise ValueError("邮箱格式不正确")
        return v

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()


class AuditLog(BaseModel):
    """审计日志模型"""

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    action: AuditAction
    actor: str = Field(..., min_length=1)
    actor_type: str = "user"  # user, system, node
    resource_type: Optional[str] = None  # node, device, job, event
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=get_utc_now)

    @field_serializer("timestamp")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()
