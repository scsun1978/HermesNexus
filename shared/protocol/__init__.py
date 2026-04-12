"""
共享协议模块

包含云边通信的消息定义、错误码规范
"""

from .messages import (
    MessageType,
    BaseMessage,
    HeartbeatMessage,
    TaskMessage,
    ResultMessage,
    ErrorMessage,
    RegisterMessage,
    DeviceStatusMessage
)

from .error_codes import (
    ErrorCode,
    ErrorDetail,
    COMMON_ERRORS
)

__all__ = [
    "MessageType",
    "BaseMessage",
    "HeartbeatMessage",
    "TaskMessage",
    "ResultMessage",
    "ErrorMessage",
    "RegisterMessage",
    "DeviceStatusMessage",
    "ErrorCode",
    "ErrorDetail",
    "COMMON_ERRORS"
]
