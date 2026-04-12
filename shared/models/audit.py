"""
HermesNexus Phase 2/3 - Audit Log Model
审计日志数据模型

Phase 2: 基础审计日志功能
Phase 3: 扩展安全审计字段和统一规范
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


# ===== Phase 3: 统一安全审计扩展 =====

class ActorType(str, Enum):
    """操作者类型枚举（Phase 3扩展）"""
    USER = "user"  # 人类用户
    NODE = "node"  # 边缘节点
    SYSTEM = "system"  # 系统自动
    SERVICE = "service"  # 服务账号
    API_CLIENT = "api_client"  # API客户端


class SecurityEventType(str, Enum):
    """安全事件类型枚举（Phase 3扩展）"""
    # 认证事件
    AUTH_TOKEN_ISSUED = "auth_token_issued"
    AUTH_TOKEN_VALIDATED = "auth_token_validated"
    AUTH_TOKEN_REFRESHED = "auth_token_refreshed"
    AUTH_TOKEN_EXPIRED = "auth_token_expired"
    NODE_AUTHENTICATED = "node_authenticated"
    NODE_BINDING = "node_binding"
    NODE_UNBINDING = "node_unbinding"

    # 授权事件
    PERMISSION_CHECK = "permission_check"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"

    # 审批事件
    APPROVAL_REQUEST_CREATED = "approval_request_created"
    APPROVAL_REQUEST_SUBMITTED = "approval_request_submitted"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_EXPIRED = "approval_expired"

    # 回滚事件
    ROLLBACK_PLAN_CREATED = "rollback_plan_created"
    ROLLBACK_PLAN_EXECUTED = "rollback_plan_executed"
    ROLLBACK_STEP_STARTED = "rollback_step_started"
    ROLLBACK_STEP_COMPLETED = "rollback_step_completed"
    ROLLBACK_STEP_FAILED = "rollback_step_failed"
    ROLLBACK_COMPLETED = "rollback_completed"
    ROLLBACK_FAILED = "rollback_failed"

    # 故障恢复事件
    FAILURE_DETECTED = "failure_detected"
    FAILURE_CLASSIFIED = "failure_classified"
    RECOVERY_PLAN_CREATED = "recovery_plan_created"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_COMPLETED = "recovery_completed"
    RECOVERY_FAILED = "recovery_failed"
    MANUAL_INTERVENTION_REQUIRED = "manual_intervention_required"


class ActionResult(str, Enum):
    """操作结果枚举（Phase 3扩展）"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class RiskLevel(str, Enum):
    """风险等级枚举（Phase 3扩展）"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityAuditLog(BaseModel):
    """统一安全审计日志模型（Phase 3扩展）

    基于Phase 2的AuditLog模型，增加安全审计专用字段
    与原有AuditLog模型保持兼容性
    """

    # 基础字段（继承自AuditLog）
    audit_id: str = Field(..., description="审计记录ID")
    action: AuditAction = Field(..., description="审计动作类型")
    category: AuditCategory = Field(..., description="审计分类")
    level: EventLevel = Field(default=EventLevel.INFO, description="事件级别")

    # Phase 3 扩展字段
    security_event_type: Optional[SecurityEventType] = Field(None, description="安全事件类型")
    result: ActionResult = Field(default=ActionResult.SUCCESS, description="操作结果")
    risk_level: Optional[RiskLevel] = Field(None, description="风险等级")

    # 操作者信息（扩展）
    actor: str = Field(..., description="操作发起者")
    actor_type: ActorType = Field(default=ActorType.USER, description="操作者类型")
    tenant_id: Optional[str] = Field(None, description="租户ID")

    # 目标信息（扩展）
    target_type: str = Field(..., description="目标对象类型")
    target_id: Optional[str] = Field(None, description="目标对象ID")
    resource_type: Optional[str] = Field(None, description="资源类型")

    # 关联信息（扩展）
    related_task_id: Optional[str] = Field(None, description="关联的任务ID")
    related_node_id: Optional[str] = Field(None, description="关联的节点ID")
    related_asset_id: Optional[str] = Field(None, description="关联的资产ID")
    approval_id: Optional[str] = Field(None, description="关联的审批ID")
    rollback_plan_id: Optional[str] = Field(None, description="关联的回滚计划ID")
    failure_id: Optional[str] = Field(None, description="关联的故障ID")
    recovery_plan_id: Optional[str] = Field(None, description="关联的恢复计划ID")

    # 事件详情（扩展）
    details: Dict[str, Any] = Field(default_factory=dict, description="事件详细信息")
    message: str = Field(..., description="事件描述消息")
    error_message: Optional[str] = Field(None, description="错误信息")
    stack_trace: Optional[str] = Field(None, description="错误堆栈")

    # 变更追踪（新增）
    changes: Optional[Dict[str, Any]] = Field(None, description="变更内容")
    old_values: Optional[Dict[str, Any]] = Field(None, description="变更前的值")
    new_values: Optional[Dict[str, Any]] = Field(None, description="变更后的值")

    # 上下文信息（扩展）
    ip_address: Optional[str] = Field(None, description="操作发起IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")
    request_id: Optional[str] = Field(None, description="请求ID")
    correlation_id: Optional[str] = Field(None, description="关联ID")
    session_id: Optional[str] = Field(None, description="会话ID")

    # 性能和监控字段（新增）
    duration_ms: Optional[int] = Field(None, description="操作耗时（毫秒）")
    memory_usage_mb: Optional[float] = Field(None, description="内存使用（MB）")
    cpu_usage_percent: Optional[float] = Field(None, description="CPU使用率（%）")

    # 时间戳
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="事件时间戳")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="记录创建时间")

    class Config:
        json_schema_extra = {
            "example": {
                "audit_id": "audit-20240416-001",
                "action": AuditAction.APPROVAL_GRANTED,
                "category": AuditCategory.SECURITY,
                "level": EventLevel.INFO,
                "security_event_type": SecurityEventType.APPROVAL_GRANTED,
                "result": ActionResult.SUCCESS,
                "risk_level": RiskLevel.MEDIUM,
                "actor": "admin-001",
                "actor_type": ActorType.USER,
                "tenant_id": "tenant-001",
                "target_type": "approval_request",
                "target_id": "approval-001",
                "approval_id": "approval-001",
                "message": "批准高风险操作请求",
                "details": {
                    "operation_type": "config_change",
                    "resource_type": "config",
                    "risk_level": "medium"
                },
                "ip_address": "192.168.1.100",
                "request_id": "req-001",
                "correlation_id": "corr-001",
                "duration_ms": 125
            }
        }


class SecurityEvent(BaseModel):
    """安全事件告警模型（Phase 3新增）"""

    event_id: str = Field(..., description="安全事件ID")
    security_event_type: SecurityEventType = Field(..., description="安全事件类型")
    severity: RiskLevel = Field(..., description="严重程度")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="事件时间")

    # 事件详情
    title: str = Field(..., description="事件标题")
    description: str = Field(..., description="事件描述")
    affected_resources: List[str] = Field(default_factory=list, description="受影响的资源")

    # 攻击者信息
    attacker_id: Optional[str] = Field(None, description="攻击者ID")
    attacker_ip: Optional[str] = Field(None, description="攻击者IP")
    attack_vector: Optional[str] = Field(None, description="攻击向量")

    # 防护信息
    defense_mechanism: Optional[str] = Field(None, description="防护机制")
    blocking_action: Optional[str] = Field(None, description="阻断动作")

    # 响应信息
    response_status: str = Field(default="detected", description="响应状态")
    response_actions: List[str] = Field(default_factory=list, description="已采取的响应动作")

    # 上下文
    context: Dict[str, Any] = Field(default_factory=dict, description="事件上下文")
    correlation_id: Optional[str] = Field(None, description="关联ID")
    related_audit_logs: List[str] = Field(default_factory=list, description="相关审计日志ID")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "security-20240416-001",
                "security_event_type": SecurityEventType.PERMISSION_DENIED,
                "severity": RiskLevel.HIGH,
                "title": "检测到权限绕过尝试",
                "description": "用户user-001尝试访问无权限的资源node-002",
                "attacker_id": "user-001",
                "attacker_ip": "192.168.1.100",
                "attack_vector": "privilege_escalation",
                "defense_mechanism": "rbac",
                "blocking_action": "access_blocked",
                "response_status": "blocked"
            }
        }


class ComplianceReport(BaseModel):
    """合规报告模型（Phase 3新增）"""

    report_id: str = Field(..., description="报告ID")
    report_type: str = Field(..., description="报告类型")
    period_start: datetime = Field(..., description="报告期间开始时间")
    period_end: datetime = Field(..., description="报告期间结束时间")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="生成时间")

    # 统计信息
    total_events: int = Field(..., description="总事件数")
    events_by_type: Dict[str, int] = Field(default_factory=dict, description="按类型统计")
    events_by_severity: Dict[str, int] = Field(default_factory=dict, description="按严重程度统计")
    events_by_actor: Dict[str, int] = Field(default_factory=dict, description="按操作者统计")

    # 安全指标
    auth_success_rate: float = Field(..., description="认证成功率")
    auth_failure_count: int = Field(..., description="认证失败次数")
    approval_success_rate: float = Field(..., description="审批成功率")
    rollback_success_rate: float = Field(..., description="回滚成功率")
    incident_count: int = Field(default=0, description="安全事件数量")

    # 合规检查
    compliance_checks: List[Dict[str, Any]] = Field(default_factory=list, description="合规检查结果")
    compliance_score: float = Field(..., description="合规评分（0-100）")
    compliance_status: str = Field(..., description="合规状态")

    # 建议
    recommendations: List[str] = Field(default_factory=list, description="改进建议")

    class Config:
        json_schema_extra = {
            "example": {
                "report_id": "compliance-20240416-001",
                "report_type": "monthly_security_report",
                "period_start": "2026-04-01T00:00:00Z",
                "period_end": "2026-04-30T23:59:59Z",
                "total_events": 15420,
                "auth_success_rate": 0.98,
                "auth_failure_count": 308,
                "approval_success_rate": 0.92,
                "rollback_success_rate": 0.95,
                "incident_count": 3,
                "compliance_score": 92.5,
                "compliance_status": "compliant"
            }
        }


class AuditStatisticsExtended(BaseModel):
    """审计统计模型（Phase 3扩展）"""

    # 总体统计
    total_events: int = Field(..., description="总事件数")
    events_by_type: Dict[str, int] = Field(default_factory=dict, description="按类型统计")
    events_by_result: Dict[str, int] = Field(default_factory=dict, description="按结果统计")
    events_by_risk_level: Dict[str, int] = Field(default_factory=dict, description="按风险等级统计")

    # 时间统计
    events_by_hour: Dict[str, int] = Field(default_factory=dict, description="按小时统计")
    events_by_day: Dict[str, int] = Field(default_factory=dict, description="按天统计")

    # 操作者统计
    top_actors: List[Dict[str, Any]] = Field(default_factory=list, description="最活跃的操作者")
    actors_by_type: Dict[str, int] = Field(default_factory=dict, description="按操作者类型统计")

    # 资源统计
    most_accessed_resources: List[Dict[str, Any]] = Field(default_factory=list, description="访问最多的资源")

    # 安全统计
    failed_auth_count: int = Field(default=0, description="认证失败次数")
    permission_denied_count: int = Field(default=0, description="权限拒绝次数")
    security_events_count: int = Field(default=0, description="安全事件数量")

    # 性能统计
    avg_duration_ms: float = Field(default=0.0, description="平均操作耗时")
    max_duration_ms: float = Field(default=0.0, description="最大操作耗时")

    class Config:
        json_schema_extra = {
            "example": {
                "total_events": 15420,
                "events_by_type": {
                    "auth_login": 5200,
                    "permission_check": 3200,
                    "approval_granted": 1500,
                    "rollback_completed": 720
                },
                "events_by_result": {
                    "success": 14850,
                    "failure": 520,
                    "timeout": 50
                },
                "failed_auth_count": 308,
                "permission_denied_count": 95,
                "security_events_count": 12,
                "avg_duration_ms": 125.5
            }
        }


# 审计字段常量定义（Phase 3新增）
class AuditFields:
    """审计字段常量"""

    # 必填字段
    REQUIRED_FIELDS = [
        "audit_id",
        "action",
        "category",
        "timestamp",
        "actor",
        "actor_type",
        "target_type",
        "message"
    ]

    # 推荐字段
    RECOMMENDED_FIELDS = [
        "tenant_id",
        "target_id",
        "resource_type",
        "result",
        "ip_address",
        "request_id",
        "correlation_id"
    ]

    # 敏感操作字段
    SENSITIVE_OPERATION_FIELDS = [
        "security_event_type",
        "risk_level",
        "changes",
        "old_values",
        "new_values",
        "approval_id",
        "rollback_plan_id"
    ]

    # 性能监控字段
    PERFORMANCE_FIELDS = [
        "duration_ms",
        "memory_usage_mb",
        "cpu_usage_percent"
    ]


# 审计事件优先级定义（Phase 3新增）
class AuditPriority:
    """审计事件优先级"""

    # 关键事件（需要实时告警）
    CRITICAL_EVENTS = [
        AuditAction.AUTH_DENIED,
        SecurityEventType.PERMISSION_DENIED,
        SecurityEventType.APPROVAL_REJECTED,
        SecurityEventType.ROLLBACK_FAILED,
        SecurityEventType.RECOVERY_FAILED,
        SecurityEventType.MANUAL_INTERVENTION_REQUIRED,
        AuditAction.SYSTEM_ERROR
    ]

    # 重要事件（需要记录和分析）
    IMPORTANT_EVENTS = [
        AuditAction.USER_LOGIN,
        SecurityEventType.AUTH_TOKEN_ISSUED,
        AuditAction.NODE_REGISTERED,
        SecurityEventType.APPROVAL_GRANTED,
        SecurityEventType.ROLLBACK_PLAN_CREATED,
        SecurityEventType.FAILURE_DETECTED
    ]

    # 一般事件（正常记录）
    NORMAL_EVENTS = [
        AuditAction.USER_LOGOUT,
        SecurityEventType.AUTH_TOKEN_VALIDATED,
        SecurityEventType.PERMISSION_CHECK
    ]
