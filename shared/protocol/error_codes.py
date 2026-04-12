"""
错误码定义

定义系统中的机器可读错误码，便于错误追踪和自动化处理
"""

from enum import Enum
from typing import Optional, Dict, Any


class ErrorCode(str, Enum):
    """错误码枚举"""

    # 通用错误 (1000-1999)
    UNKNOWN_ERROR = "ERR_1000"
    INVALID_REQUEST = "ERR_1001"
    UNAUTHORIZED = "ERR_1002"
    FORBIDDEN = "ERR_1003"
    RESOURCE_NOT_FOUND = "ERR_1004"
    TIMEOUT = "ERR_1005"
    RATE_LIMIT_EXCEEDED = "ERR_1006"

    # 节点相关错误 (2000-2999)
    NODE_NOT_FOUND = "ERR_2000"
    NODE_REGISTRATION_FAILED = "ERR_2001"
    NODE_HEARTBEAT_FAILED = "ERR_2002"
    NODE_OFFLINE = "ERR_2003"
    NODE_MAINTENANCE = "ERR_2004"

    # 任务相关错误 (3000-3999)
    TASK_NOT_FOUND = "ERR_3000"
    TASK_CREATION_FAILED = "ERR_3001"
    TASK_EXECUTION_FAILED = "ERR_3002"
    TASK_TIMEOUT = "ERR_3003"
    TASK_CANCELLED = "ERR_3004"
    INVALID_TASK_TYPE = "ERR_3005"
    INVALID_TASK_PARAMETERS = "ERR_3006"

    # 设备相关错误 (4000-4999)
    DEVICE_NOT_FOUND = "ERR_4000"
    DEVICE_CONNECTION_FAILED = "ERR_4001"
    DEVICE_AUTHENTICATION_FAILED = "ERR_4002"
    DEVICE_OFFLINE = "ERR_4003"
    UNSUPPORTED_DEVICE_TYPE = "ERR_4004"
    UNSUPPORTED_PROTOCOL = "ERR_4005"

    # SSH执行器错误 (5000-5999)
    SSH_CONNECTION_FAILED = "ERR_5000"
    SSH_AUTHENTICATION_FAILED = "ERR_5001"
    SSH_COMMAND_FAILED = "ERR_5002"
    SSH_TIMEOUT = "ERR_5003"
    SSH_CHANNEL_CLOSED = "ERR_5004"
    INVALID_SSH_CREDENTIALS = "ERR_5005"

    # 数据库错误 (6000-6999)
    DATABASE_ERROR = "ERR_6000"
    DATABASE_CONNECTION_FAILED = "ERR_6001"
    DATABASE_QUERY_FAILED = "ERR_6002"
    DUPLICATE_RECORD = "ERR_6003"


class ErrorDetail:
    """错误详情类"""

    def __init__(
        self, code: ErrorCode, message: str, details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error_code": self.code.value,
            "error_message": self.message,
            "details": self.details,
        }


# 预定义的常见错误
COMMON_ERRORS = {
    ErrorCode.NODE_NOT_FOUND: ErrorDetail(
        ErrorCode.NODE_NOT_FOUND,
        "指定的节点不存在",
        {"suggestion": "请检查节点ID是否正确"},
    ),
    ErrorCode.TASK_NOT_FOUND: ErrorDetail(
        ErrorCode.TASK_NOT_FOUND,
        "指定的任务不存在",
        {"suggestion": "请检查任务ID是否正确"},
    ),
    ErrorCode.DEVICE_NOT_FOUND: ErrorDetail(
        ErrorCode.DEVICE_NOT_FOUND,
        "指定的设备不存在",
        {"suggestion": "请检查设备ID是否正确"},
    ),
    ErrorCode.SSH_CONNECTION_FAILED: ErrorDetail(
        ErrorCode.SSH_CONNECTION_FAILED,
        "SSH连接失败",
        {"suggestion": "请检查主机地址、端口和网络连接"},
    ),
    ErrorCode.TASK_TIMEOUT: ErrorDetail(
        ErrorCode.TASK_TIMEOUT,
        "任务执行超时",
        {"suggestion": "请增加超时时间或检查设备状态"},
    ),
}
