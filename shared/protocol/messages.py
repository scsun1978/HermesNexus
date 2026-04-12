"""
云边通信消息定义

定义云端和边缘节点之间的消息格式
"""

from enum import Enum
from typing import Optional, Any, Dict, List
from datetime import datetime, timezone
from dataclasses import dataclass, field
import json
import uuid


class MessageType(str, Enum):
    """消息类型枚举"""

    # 边缘 → 云端
    HEARTBEAT = "heartbeat"  # 心跳消息
    REGISTER = "register"  # 节点注册
    TASK_RESULT = "task_result"  # 任务执行结果
    ERROR = "error"  # 错误报告
    DEVICE_STATUS = "device_status"  # 设备状态上报

    # 云端 → 边缘
    TASK_ASSIGN = "task_assign"  # 任务分配
    CONFIG_UPDATE = "config_update"  # 配置更新
    SHUTDOWN = "shutdown"  # 关闭指令
    HEARTBEAT_ACK = "heartbeat_ack"  # 心跳确认
    TASK_CANCEL = "task_cancel"  # 任务取消


@dataclass
class BaseMessage:
    """消息基类"""

    type: MessageType
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    node_id: Optional[str] = None
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(
            {
                "type": self.type.value,
                "timestamp": self.timestamp,
                "node_id": self.node_id,
                "message_id": self.message_id,
                "data": self.to_dict(),
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        raise NotImplementedError


@dataclass
class HeartbeatMessage(BaseMessage):
    """心跳消息"""

    type: MessageType = MessageType.HEARTBEAT
    status: str = "online"
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_tasks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "active_tasks": self.active_tasks,
        }


@dataclass
class TaskMessage(BaseMessage):
    """任务消息"""

    type: MessageType = MessageType.TASK_ASSIGN
    task_id: str = ""
    job_id: str = ""  # 关联的作业ID
    task_type: str = ""  # exec, script, file_transfer
    target_device: str = ""
    target_host: str = ""  # 目标主机地址
    target_port: int = 22  # 目标端口
    command: str = ""  # 要执行的命令
    script: str = ""  # 要执行的脚本
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 300
    priority: int = 5
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    created_by: str = "system"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "job_id": self.job_id,
            "task_type": self.task_type,
            "target_device": self.target_device,
            "target_host": self.target_host,
            "target_port": self.target_port,
            "command": self.command,
            "script": self.script,
            "parameters": self.parameters,
            "timeout": self.timeout,
            "priority": self.priority,
            "retry_policy": self.retry_policy,
            "created_by": self.created_by,
        }


@dataclass
class ResultMessage(BaseMessage):
    """任务结果消息"""

    type: MessageType = MessageType.TASK_RESULT
    task_id: str = ""
    job_id: str = ""
    status: str = "success"  # success, failed, timeout, cancelled
    output: Any = None
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    error: Optional[str] = None
    error_code: Optional[str] = None
    execution_time: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "job_id": self.job_id,
            "status": self.status,
            "output": self.output,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "error": self.error,
            "error_code": self.error_code,
            "execution_time": self.execution_time,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }


@dataclass
class RegisterMessage(BaseMessage):
    """节点注册消息"""

    type: MessageType = MessageType.REGISTER
    node_id: str = ""
    node_name: str = ""
    node_type: str = "edge"
    capabilities: Dict[str, Any] = field(default_factory=dict)
    version: str = "0.1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "node_type": self.node_type,
            "capabilities": self.capabilities,
            "version": self.version,
        }


@dataclass
class ErrorMessage(BaseMessage):
    """错误消息"""

    type: MessageType = MessageType.ERROR
    error_code: str = ""
    error_message: str = ""
    error_category: str = "general"  # general, network, execution, system
    context: Dict[str, Any] = field(default_factory=dict)
    retry_able: bool = False
    retry_after: Optional[int] = None  # 秒

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "error_message": self.error_message,
            "error_category": self.error_category,
            "context": self.context,
            "retry_able": self.retry_able,
            "retry_after": self.retry_after,
        }


@dataclass
class DeviceStatusMessage(BaseMessage):
    """设备状态消息"""

    type: MessageType = MessageType.DEVICE_STATUS
    device_id: str = ""
    status: str = "unknown"  # online, offline, error
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "status": self.status,
            "metrics": self.metrics,
        }
