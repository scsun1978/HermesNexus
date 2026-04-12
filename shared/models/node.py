"""
HermesNexus Phase 3 - 节点身份模型
节点身份、认证和生命周期管理
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field, validator


class NodeStatus(str, Enum):
    """节点状态"""

    UNREGISTERED = "unregistered"  # 未注册
    REGISTERING = "registering"  # 注册中
    REGISTERED = "registered"  # 已注册
    ACTIVE = "active"  # 活跃
    INACTIVE = "inactive"  # 非活跃
    SUSPENDED = "suspended"  # 暂停
    DEREGISTERED = "deregistered"  # 已注销
    FAILED = "failed"  # 失败

    def can_transition_to(self, new_status: "NodeStatus") -> bool:
        """检查状态转换是否合法"""
        valid_transitions = {
            NodeStatus.UNREGISTERED: [NodeStatus.REGISTERING, NodeStatus.REGISTERED],
            NodeStatus.REGISTERING: [NodeStatus.REGISTERED, NodeStatus.FAILED],
            NodeStatus.REGISTERED: [
                NodeStatus.ACTIVE,
                NodeStatus.INACTIVE,
                NodeStatus.DEREGISTERED,
            ],
            NodeStatus.ACTIVE: [
                NodeStatus.INACTIVE,
                NodeStatus.SUSPENDED,
                NodeStatus.DEREGISTERED,
            ],
            NodeStatus.INACTIVE: [NodeStatus.ACTIVE, NodeStatus.DEREGISTERED],
            NodeStatus.SUSPENDED: [NodeStatus.ACTIVE, NodeStatus.DEREGISTERED],
            NodeStatus.FAILED: [NodeStatus.REGISTERING, NodeStatus.DEREGISTERED],
            NodeStatus.DEREGISTERED: [],
        }
        return new_status in valid_transitions.get(self, [])


class NodeType(str, Enum):
    """节点类型"""

    PHYSICAL = "physical"  # 物理机
    VIRTUAL_MACHINE = "vm"  # 虚拟机
    CONTAINER = "container"  # 容器
    EDGE_DEVICE = "edge"  # 边缘设备


class NodeIdentity(BaseModel):
    """节点身份模型"""

    # 基本身份信息
    node_id: str = Field(..., description="节点唯一ID")
    node_name: str = Field(..., description="节点显示名称")
    node_type: NodeType = Field(..., description="节点类型")

    # 多租户信息
    tenant_id: str = Field(..., description="租户ID")
    region_id: str = Field(..., description="区域ID")

    # 认证信息
    auth_token: Optional[str] = Field(None, description="当前认证Token")
    token_expires_at: Optional[datetime] = Field(None, description="Token过期时间")
    public_key: Optional[str] = Field(None, description="公钥(用于mTLS)")

    # 能力信息
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="能力清单")
    max_concurrent_tasks: int = Field(3, ge=1, le=100, description="最大并发任务数")

    # 状态信息
    status: NodeStatus = Field(default=NodeStatus.UNREGISTERED, description="节点状态")
    registered_at: Optional[datetime] = Field(None, description="注册时间")
    last_heartbeat: Optional[datetime] = Field(None, description="最后心跳时间")

    # 关联关系
    managed_devices: List[str] = Field(default_factory=list, description="管理的设备ID列表")
    assigned_tasks: List[str] = Field(default_factory=list, description="分配的任务ID列表")

    # 元数据
    description: Optional[str] = Field(None, description="节点描述")
    location: Optional[str] = Field(None, description="物理位置")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    node_metadata: Dict[str, Any] = Field(default_factory=dict, description="自定义元数据")

    # 审计信息
    created_by: Optional[str] = Field(None, description="创建者")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="更新时间"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "node_id": "node-001",
                "node_name": "data-center-1-node-1",
                "node_type": "physical",
                "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_expires_at": "2026-04-13T10:00:00Z",
                "capabilities": {
                    "protocols": ["ssh", "http"],
                    "max_tasks": 5,
                    "resources": {"cpu": 16, "memory": "64GB"},
                },
                "max_concurrent_tasks": 3,
                "status": "active",
                "registered_at": "2026-04-12T10:00:00Z",
                "last_heartbeat": "2026-04-12T15:30:00Z",
                "managed_devices": ["device-001", "device-002"],
                "assigned_tasks": ["task-001"],
                "description": "生产环境节点1",
                "location": "Beijing Data Center 1",
                "tags": ["production", "linux"],
                "created_by": "admin",
            }
        }

    @validator("node_id")
    def validate_node_id(cls, v):
        """验证节点ID格式"""
        if not v or len(v.strip()) == 0:
            raise ValueError("node_id cannot be empty")
        return v.strip()

    def is_token_valid(self) -> bool:
        """检查Token是否有效"""
        if not self.auth_token or not self.token_expires_at:
            return False
        return datetime.now(timezone.utc) < self.token_expires_at

    def is_active(self) -> bool:
        """检查节点是否活跃"""
        if self.status != NodeStatus.ACTIVE:
            return False
        if not self.last_heartbeat:
            return False
        # 心跳超时时间：5分钟
        heartbeat_timeout = timedelta(minutes=5)
        return datetime.now(timezone.utc) - self.last_heartbeat < heartbeat_timeout

    def can_accept_tasks(self) -> bool:
        """检查节点是否可以接受新任务"""
        if not self.is_active():
            return False
        if len(self.assigned_tasks) >= self.max_concurrent_tasks:
            return False
        return True


class NodeRegistrationRequest(BaseModel):
    """节点注册请求"""

    node_id: str = Field(..., description="节点ID")
    node_name: str = Field(..., description="节点名称")
    node_type: NodeType = Field(..., description="节点类型")
    description: Optional[str] = Field(None, description="节点描述")

    # 能力信息
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="能力清单")
    max_concurrent_tasks: int = Field(3, ge=1, le=100, description="最大并发任务数")

    # 位置和元数据
    location: Optional[str] = Field(None, description="物理位置")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    node_metadata: Dict[str, Any] = Field(default_factory=dict, description="自定义元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "node_id": "node-001",
                "node_name": "data-center-1-node-1",
                "node_type": "physical",
                "description": "生产环境节点1",
                "capabilities": {
                    "protocols": ["ssh", "http"],
                    "max_tasks": 5,
                    "resources": {"cpu": 16, "memory": "64GB"},
                },
                "max_concurrent_tasks": 3,
                "location": "Beijing Data Center 1",
                "tags": ["production", "linux"],
            }
        }


class NodeHeartbeatRequest(BaseModel):
    """节点心跳请求"""

    node_id: str = Field(..., description="节点ID")
    status: NodeStatus = Field(..., description="当前状态")

    # 状态信息
    active_tasks: int = Field(0, ge=0, description="当前活跃任务数")
    cpu_usage: float = Field(0.0, ge=0.0, le=100.0, description="CPU使用率")
    memory_usage: float = Field(0.0, ge=0.0, le=100.0, description="内存使用率")

    # 能力状态
    available_slots: int = Field(0, ge=0, description="可用任务槽位数")

    # 错误信息
    error_message: Optional[str] = Field(None, description="错误消息")

    class Config:
        json_schema_extra = {
            "example": {
                "node_id": "node-001",
                "status": "active",
                "active_tasks": 2,
                "cpu_usage": 45.5,
                "memory_usage": 62.3,
                "available_slots": 1,
            }
        }


class NodeTokenInfo(BaseModel):
    """节点Token信息"""

    token: str = Field(..., description="JWT Token")
    node_id: str = Field(..., description="节点ID")
    expires_at: datetime = Field(..., description="过期时间")
    permissions: List[str] = Field(default_factory=list, description="权限列表")
    issued_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="颁发时间"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "node_id": "node-001",
                "expires_at": "2026-04-13T10:00:00Z",
                "permissions": ["task.execute", "task.report", "heartbeat"],
                "issued_at": "2026-04-12T10:00:00Z",
            }
        }


# 节点权限定义
class NodePermission(str, Enum):
    """节点权限"""

    TASK_EXECUTE = "task.execute"  # 执行任务
    TASK_REPORT = "task.report"  # 上报结果
    HEARTBEAT = "heartbeat"  # 心跳上报
    STATUS_REPORT = "status.report"  # 状态上报
    ERROR_REPORT = "error.report"  # 错误上报


class NodeCapabilities(BaseModel):
    """节点能力模型"""

    # 支持的协议
    protocols: List[str] = Field(default_factory=list, description="支持的协议")

    # 任务执行能力
    max_concurrent_tasks: int = Field(3, ge=1, le=100, description="最大并发任务数")
    supported_task_types: List[str] = Field(default_factory=list, description="支持的任务类型")

    # 系统资源
    cpu_cores: Optional[int] = Field(None, description="CPU核心数")
    memory_gb: Optional[float] = Field(None, description="内存大小(GB)")
    disk_gb: Optional[float] = Field(None, description="磁盘大小(GB)")

    # 网络能力
    network_bandwidth_mbps: Optional[int] = Field(None, description="网络带宽")
    network_latency_ms: Optional[int] = Field(None, description="网络延迟")

    class Config:
        json_schema_extra = {
            "example": {
                "protocols": ["ssh", "http", "https"],
                "max_concurrent_tasks": 5,
                "supported_task_types": [
                    "basic_exec",
                    "script_transfer",
                    "file_transfer",
                ],
                "cpu_cores": 16,
                "memory_gb": 64.0,
                "disk_gb": 1000.0,
                "network_bandwidth_mbps": 1000,
                "network_latency_ms": 5,
            }
        }
