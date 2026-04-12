"""
HermesNexus Phase 2 - 统一枚举定义

本模块定义所有状态枚举和错误码，供 cloud 和 edge 共享使用。
禁止在此文件之外定义重复或冲突的枚举值。
"""

from enum import Enum
from typing import Dict, Any


# =============================================================================
# Asset 相关枚举
# =============================================================================

class AssetType(str, Enum):
    """资产类型定义"""
    EDGE_NODE = "edge_node"        # 边缘节点
    LINUX_HOST = "linux_host"      # Linux 主机
    NETWORK_DEVICE = "network_device"  # 网络设备
    IOT_DEVICE = "iot_device"      # IoT 设备


class AssetStatus(str, Enum):
    """资产状态"""
    REGISTERED = "registered"      # 已注册，未关联运行节点
    ACTIVE = "active"              # 活跃，有运行节点在线
    INACTIVE = "inactive"          # 非活跃，运行节点离线
    DECOMMISSIONED = "decommissioned"  # 已退役

    def can_transition_to(self, new_status: 'AssetStatus') -> bool:
        """检查状态转换是否合法"""
        valid_transitions = {
            AssetStatus.REGISTERED: [AssetStatus.ACTIVE, AssetStatus.DECOMMISSIONED],
            AssetStatus.ACTIVE: [AssetStatus.INACTIVE, AssetStatus.DECOMMISSIONED],
            AssetStatus.INACTIVE: [AssetStatus.ACTIVE, AssetStatus.DECOMMISSIONED],
            AssetStatus.DECOMMISSIONED: [],  # 终态
        }
        return new_status in valid_transitions.get(self, [])


# =============================================================================
# Node 相关枚举
# =============================================================================

class NodeStatus(str, Enum):
    """运行节点状态"""
    REGISTERED = "registered"      # 已注册，首次连接
    ONLINE = "online"              # 在线，可接收任务
    BUSY = "busy"                  # 忙碌，正在执行任务
    OFFLINE = "offline"            # 离线，心跳超时
    DEGRADED = "degraded"          # 降级，部分功能不可用

    def can_transition_to(self, new_status: 'NodeStatus') -> bool:
        """检查状态转换是否合法"""
        valid_transitions = {
            NodeStatus.REGISTERED: [NodeStatus.ONLINE, NodeStatus.OFFLINE],
            NodeStatus.ONLINE: [NodeStatus.BUSY, NodeStatus.OFFLINE, NodeStatus.DEGRADED],
            NodeStatus.BUSY: [NodeStatus.ONLINE, NodeStatus.OFFLINE, NodeStatus.DEGRADED],
            NodeStatus.OFFLINE: [NodeStatus.ONLINE, NodeStatus.DEGRADED],
            NodeStatus.DEGRADED: [NodeStatus.ONLINE, NodeStatus.OFFLINE],
        }
        return new_status in valid_transitions.get(self, [])


# =============================================================================
# Task 相关枚举
# =============================================================================

class TaskType(str, Enum):
    """任务类型"""
    BASIC_EXEC = "basic_exec"      # 基础命令执行
    SCRIPT_TRANSFER = "script_transfer"  # 脚本传输执行
    FILE_TRANSFER = "file_transfer"      # 文件传输
    SYSTEM_INFO = "system_info"    # 系统信息查询


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"            # 待调度
    ASSIGNED = "assigned"          # 已分配给节点
    RUNNING = "running"            # 执行中
    SUCCEEDED = "succeeded"        # 成功完成
    COMPLETED = "succeeded"        # 兼容旧测试/旧API
    FAILED = "failed"              # 执行失败
    TIMEOUT = "timeout"            # 执行超时
    CANCELLED = "cancelled"        # 已取消

    @classmethod
    def _missing_(cls, value):
        if value == "completed":
            return cls.SUCCEEDED
        return super()._missing_(value)

    def can_transition_to(self, new_status: 'TaskStatus') -> bool:
        """检查状态转换是否合法"""
        valid_transitions = {
            TaskStatus.PENDING: [TaskStatus.ASSIGNED, TaskStatus.CANCELLED],
            TaskStatus.ASSIGNED: [TaskStatus.RUNNING, TaskStatus.CANCELLED],
            TaskStatus.RUNNING: [TaskStatus.SUCCEEDED, TaskStatus.FAILED,
                                  TaskStatus.TIMEOUT, TaskStatus.CANCELLED],
            TaskStatus.SUCCEEDED: [],  # 终态
            TaskStatus.FAILED: [],     # 终态
            TaskStatus.TIMEOUT: [],    # 终态
            TaskStatus.CANCELLED: [],  # 终态
        }
        return new_status in valid_transitions.get(self, [])

    def is_terminal(self) -> bool:
        """是否为终态"""
        return self in [TaskStatus.SUCCEEDED, TaskStatus.FAILED,
                       TaskStatus.TIMEOUT, TaskStatus.CANCELLED]


# =============================================================================
# Audit 相关枚举
# =============================================================================

class AuditAction(str, Enum):
    """审计动作类型"""
    # Task lifecycle
    TASK_CREATED = "task_created"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_SUCCEEDED = "task_succeeded"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"

    # Node lifecycle
    NODE_REGISTERED = "node_registered"
    NODE_ONLINE = "node_online"
    NODE_OFFLINE = "node_offline"
    NODE_HEARTBEAT = "node_heartbeat"

    # Asset lifecycle
    ASSET_REGISTERED = "asset_registered"
    ASSET_UPDATED = "asset_updated"
    ASSET_DECOMMISSIONED = "asset_decommissioned"


class EventLevel(str, Enum):
    """事件级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# =============================================================================
# 错误码定义
# =============================================================================

class ErrorCodeCategory(str, Enum):
    """错误分类"""
    VALIDATION_ERROR = "validation_error"  # 输入验证失败
    NOT_FOUND = "not_found"               # 资源不存在
    CONFLICT = "conflict"                 # 状态冲突
    RATE_LIMIT = "rate_limit"             # 超出配额
    INTERNAL_ERROR = "internal_error"     # 内部错误


class ErrorCode(str, Enum):
    """具体错误码"""
    # Asset errors (ASSET_xxx)
    ASSET_NOT_FOUND = "ASSET_001"
    ASSET_ALREADY_EXISTS = "ASSET_002"
    ASSET_INVALID_TYPE = "ASSET_003"
    ASSET_INVALID_STATE_TRANSITION = "ASSET_004"

    # Node errors (NODE_xxx)
    NODE_NOT_FOUND = "NODE_001"
    NODE_OFFLINE = "NODE_002"
    NODE_BUSY = "NODE_003"
    NODE_HEARTBEAT_TIMEOUT = "NODE_004"
    NODE_ALREADY_REGISTERED = "NODE_005"

    # Task errors (TASK_xxx)
    TASK_NOT_FOUND = "TASK_001"
    TASK_INVALID_TARGET = "TASK_002"
    TASK_TIMEOUT = "TASK_003"
    TASK_EXECUTION_FAILED = "TASK_004"
    TASK_CANCELLED = "TASK_005"
    TASK_INVALID_STATE_TRANSITION = "TASK_006"

    # Validation errors (VAL_xxx)
    VAL_MISSING_REQUIRED_FIELD = "VAL_001"
    VAL_INVALID_ENUM_VALUE = "VAL_002"
    VAL_INVALID_JSON_FORMAT = "VAL_003"
    VAL_INVALID_PARAMETER = "VAL_004"

    # Rate limit errors (RATE_xxx)
    RATE_TOO_MANY_REQUESTS = "RATE_001"
    RATE_TASK_LIMIT_EXCEEDED = "RATE_002"

    # Internal errors (INT_xxx)
    INT_DATABASE_ERROR = "INT_001"
    INT_INTERNAL_SERVICE_ERROR = "INT_002"
    INT_UPSTREAM_SERVICE_ERROR = "INT_003"

    def get_category(self) -> ErrorCodeCategory:
        """获取错误码所属分类"""
        prefix = self.value.split('_')[0]
        mapping = {
            'ASSET': ErrorCodeCategory.NOT_FOUND,
            'NODE': ErrorCodeCategory.NOT_FOUND,
            'TASK': ErrorCodeCategory.NOT_FOUND,
            'VAL': ErrorCodeCategory.VALIDATION_ERROR,
            'RATE': ErrorCodeCategory.RATE_LIMIT,
            'INT': ErrorCodeCategory.INTERNAL_ERROR,
        }
        return mapping.get(prefix, ErrorCodeCategory.INTERNAL_ERROR)

    def to_dict(self, details: Dict[str, Any] = None, request_id: str = None) -> Dict[str, Any]:
        """转换为标准错误响应格式"""
        from datetime import datetime

        return {
            "error": {
                "code": self.value,
                "category": self.get_category().value,
                "message": self._get_default_message(),
                "details": details or {},
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "request_id": request_id or "N/A"
            }
        }

    def _get_default_message(self) -> str:
        """获取默认错误消息"""
        messages = {
            # Asset errors
            ErrorCode.ASSET_NOT_FOUND: "Asset not found",
            ErrorCode.ASSET_ALREADY_EXISTS: "Asset already exists",
            ErrorCode.ASSET_INVALID_TYPE: "Invalid asset type",
            ErrorCode.ASSET_INVALID_STATE_TRANSITION: "Invalid asset state transition",

            # Node errors
            ErrorCode.NODE_NOT_FOUND: "Node not found",
            ErrorCode.NODE_OFFLINE: "Node is offline",
            ErrorCode.NODE_BUSY: "Node is busy",
            ErrorCode.NODE_HEARTBEAT_TIMEOUT: "Node heartbeat timeout",
            ErrorCode.NODE_ALREADY_REGISTERED: "Node already registered",

            # Task errors
            ErrorCode.TASK_NOT_FOUND: "Task not found",
            ErrorCode.TASK_INVALID_TARGET: "Invalid target node for task",
            ErrorCode.TASK_TIMEOUT: "Task execution timeout",
            ErrorCode.TASK_EXECUTION_FAILED: "Task execution failed",
            ErrorCode.TASK_CANCELLED: "Task was cancelled",
            ErrorCode.TASK_INVALID_STATE_TRANSITION: "Invalid task state transition",

            # Validation errors
            ErrorCode.VAL_MISSING_REQUIRED_FIELD: "Missing required field",
            ErrorCode.VAL_INVALID_ENUM_VALUE: "Invalid enum value",
            ErrorCode.VAL_INVALID_JSON_FORMAT: "Invalid JSON format",
            ErrorCode.VAL_INVALID_PARAMETER: "Invalid parameter",

            # Rate limit errors
            ErrorCode.RATE_TOO_MANY_REQUESTS: "Too many requests",
            ErrorCode.RATE_TASK_LIMIT_EXCEEDED: "Task limit exceeded",

            # Internal errors
            ErrorCode.INT_DATABASE_ERROR: "Database error",
            ErrorCode.INT_INTERNAL_SERVICE_ERROR: "Internal service error",
            ErrorCode.INT_UPSTREAM_SERVICE_ERROR: "Upstream service error",
        }
        return messages.get(self, "Unknown error")


# =============================================================================
# 常用工具函数
# =============================================================================

def validate_state_transition(
    current_status: Enum,
    new_status: Enum,
    entity_type: str = "entity"
) -> None:
    """
    验证状态转换是否合法

    Args:
        current_status: 当前状态
        new_status: 目标状态
        entity_type: 实体类型（用于错误消息）

    Raises:
        ValueError: 如果状态转换不合法
    """
    if not current_status.can_transition_to(new_status):
        raise ValueError(
            f"Invalid {entity_type} state transition: "
            f"{current_status.value} -> {new_status.value}"
        )


def create_error_response(
    error_code: ErrorCode,
    details: Dict[str, Any] = None,
    request_id: str = None
) -> Dict[str, Any]:
    """
    创建标准错误响应

    Args:
        error_code: 错误码
        details: 错误详情
        request_id: 请求ID

    Returns:
        标准错误响应字典
    """
    return error_code.to_dict(details=details, request_id=request_id)
