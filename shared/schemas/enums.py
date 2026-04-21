"""
共享枚举定义

定义系统中使用的所有枚举类型
"""

from enum import Enum


class NodeStatus(str, Enum):
    """节点状态"""

    UNREGISTERED = "unregistered"
    REGISTERING = "registering"
    REGISTERED = "registered"
    ONLINE = "online"
    OFFLINE = "offline"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class DeviceType(str, Enum):
    """设备类型"""

    EDGE_NODE = "edge_node"
    LINUX_HOST = "linux_host"
    NETWORK_DEVICE = "network_device"
    IOT_DEVICE = "iot_device"


class DeviceProtocol(str, Enum):
    """设备协议"""

    SSH = "ssh"
    SNMP = "snmp"
    HTTP = "http"
    MODBUS = "modbus"


class DeviceStatus(str, Enum):
    """设备状态"""

    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    ERROR = "error"


class JobStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """任务类型"""

    INSPECTION = "inspection"
    RESTART = "restart"
    BASIC_EXEC = "basic_exec"
    UPGRADE = "upgrade"
    ROLLBACK = "rollback"
    SCRIPT = "script"
    FILE_TRANSFER = "file_transfer"


class TaskType(str, Enum):
    """任务执行类型"""

    EXEC = "exec"  # 执行单条命令
    SCRIPT = "script"  # 执行脚本
    FILE_TRANSFER = "file_transfer"  # 文件传输
    SYSTEM = "system"  # 系统操作


class TaskPriority(str, Enum):
    """任务优先级"""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class EventType(str, Enum):
    """事件类型"""

    NODE_REGISTERED = "node_registered"
    NODE_HEARTBEAT = "node_heartbeat"
    NODE_OFFLINE = "node_offline"
    JOB_CREATED = "job_created"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    DEVICE_DISCOVERED = "device_discovered"
    DEVICE_OFFLINE = "device_offline"
    ERROR = "error"
    WARNING = "warning"


class EventLevel(str, Enum):
    """事件级别"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class UserRole(str, Enum):
    """用户角色"""

    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class AuditAction(str, Enum):
    """审计操作类型"""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"
    EXECUTE = "execute"
    CANCEL = "cancel"
    LOGIN = "login"
    LOGOUT = "logout"
    DEPLOY = "deploy"
    CONFIG_CHANGE = "config_change"
