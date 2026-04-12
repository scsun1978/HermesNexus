"""
HermesNexus Phase 3 - 审批流模型
定义审批流程的数据结构和状态机
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ApprovalStatus(str, Enum):
    """审批状态枚举"""

    DRAFT = "draft"  # 草案状态
    PENDING = "pending"  # 审批中
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已拒绝
    WITHDRAWN = "withdrawn"  # 已撤回
    EXPIRED = "expired"  # 已过期
    CANCELLED = "cancelled"  # 已取消


class ApprovalPriority(str, Enum):
    """审批优先级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ApprovalRequest(BaseModel):
    """审批请求模型"""

    # 基本信息
    request_id: str = Field(..., description="审批请求ID")
    title: str = Field(..., description="审批标题")
    description: str = Field(..., description="审批描述")

    # 申请人信息
    requester_id: str = Field(..., description="申请人ID")
    requester_name: str = Field(..., description="申请人姓名")
    requester_type: str = Field(default="human", description="申请人类型")

    # 审批人信息
    approver_id: Optional[str] = Field(None, description="审批人ID")
    approver_name: Optional[str] = Field(None, description="审批人姓名")
    approver_role: str = Field(..., description="审批人角色")

    # 操作信息
    operation_type: str = Field(..., description="操作类型")
    resource_type: str = Field(..., description="资源类型")
    resource_id: Optional[str] = Field(None, description="资源ID")
    target_operation: Dict[str, Any] = Field(..., description="目标操作详情")

    # 风险信息
    risk_level: str = Field(..., description="风险等级")
    risk_reason: str = Field(default="", description="风险评估理由")

    # 优先级和状态
    priority: ApprovalPriority = Field(
        default=ApprovalPriority.MEDIUM, description="优先级"
    )
    status: ApprovalStatus = Field(default=ApprovalStatus.DRAFT, description="审批状态")

    # 时间信息
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="更新时间"
    )
    submitted_at: Optional[datetime] = Field(None, description="提交时间")
    decided_at: Optional[datetime] = Field(None, description="决策时间")

    # 超时设置
    timeout_seconds: int = Field(default=86400, description="超时时间（秒），默认24小时")
    expires_at: Optional[datetime] = Field(None, description="过期时间")

    # 决策信息
    decision: Optional[str] = Field(None, description="决策结果: approve/reject")
    decision_reason: Optional[str] = Field(None, description="决策理由")

    # 附加信息
    tags: List[str] = Field(default_factory=list, description="标签")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")

    # 审计信息
    audit_log_id: Optional[str] = Field(None, description="审计日志ID")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "approval-001",
                "title": "删除生产服务器",
                "description": "需要删除一台生产环境的服务器",
                "requester_id": "user-001",
                "requester_name": "张三",
                "requester_type": "human",
                "approver_id": "admin-001",
                "approver_name": "李四",
                "approver_role": "tenant_admin",
                "operation_type": "delete",
                "resource_type": "asset",
                "resource_id": "server-prod-001",
                "target_operation": {
                    "action": "delete",
                    "confirmation": "确认删除生产服务器server-prod-001",
                },
                "risk_level": "high",
                "risk_reason": "删除生产环境设备属于高风险操作",
                "priority": "high",
                "status": "pending",
                "timeout_seconds": 86400,
            }
        }


class ApprovalDecision(BaseModel):
    """审批决策模型"""

    # 基本信息
    decision_id: str = Field(..., description="决策ID")
    request_id: str = Field(..., description="审批请求ID")

    # 决策信息
    decision: str = Field(..., description="决策结果: approve/reject")
    reason: str = Field(..., description="决策理由")
    approver_id: str = Field(..., description="审批人ID")
    approver_name: str = Field(..., description="审批人姓名")

    # 决策时间
    decided_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="决策时间"
    )

    # 附加信息
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "decision_id": "decision-001",
                "request_id": "approval-001",
                "decision": "approve",
                "reason": "已确认删除操作的安全性，批准执行",
                "approver_id": "admin-001",
                "approver_name": "李四",
            }
        }


class ApprovalComment(BaseModel):
    """审批评论模型"""

    # 基本信息
    comment_id: str = Field(..., description="评论ID")
    request_id: str = Field(..., description="审批请求ID")

    # 评论内容
    content: str = Field(..., description="评论内容")
    author_id: str = Field(..., description="评论人ID")
    author_name: str = Field(..., description="评论人姓名")
    author_type: str = Field(default="human", description="评论人类型")

    # 评论时间
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="评论时间"
    )

    # 附加信息
    is_internal: bool = Field(default=False, description="是否为内部评论")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "comment_id": "comment-001",
                "request_id": "approval-001",
                "content": "请确认是否已做好数据备份",
                "author_id": "user-002",
                "author_name": "王五",
                "author_type": "human",
                "is_internal": False,
            }
        }


class ApprovalStatistics(BaseModel):
    """审批统计模型"""

    # 总体统计
    total_requests: int = Field(..., description="总请求数")
    pending_requests: int = Field(..., description="待审批请求数")
    approved_requests: int = Field(..., description="已批准请求数")
    rejected_requests: int = Field(..., description="已拒绝请求数")
    expired_requests: int = Field(..., description="已过期请求数")

    # 时间统计
    avg_approval_time_seconds: float = Field(..., description="平均审批时间（秒）")
    max_approval_time_seconds: float = Field(..., description="最长审批时间（秒）")
    min_approval_time_seconds: float = Field(..., description="最短审批时间（秒）")

    # 分类统计
    by_priority: Dict[str, int] = Field(default_factory=dict, description="按优先级分类统计")
    by_risk_level: Dict[str, int] = Field(default_factory=dict, description="按风险等级分类统计")
    by_operation_type: Dict[str, int] = Field(
        default_factory=dict, description="按操作类型分类统计"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total_requests": 100,
                "pending_requests": 15,
                "approved_requests": 70,
                "rejected_requests": 12,
                "expired_requests": 3,
                "avg_approval_time_seconds": 3600,
                "max_approval_time_seconds": 86400,
                "min_approval_time_seconds": 300,
                "by_priority": {"low": 20, "medium": 50, "high": 25, "urgent": 5},
                "by_risk_level": {"low": 30, "medium": 40, "high": 30},
                "by_operation_type": {
                    "delete": 15,
                    "restart": 10,
                    "update": 50,
                    "create": 25,
                },
            }
        }


class ApprovalConfig(BaseModel):
    """审批配置模型"""

    # 默认配置
    default_timeout_seconds: int = Field(default=86400, description="默认超时时间（秒）")
    default_approver_role: str = Field(default="tenant_admin", description="默认审批人角色")

    # 自动处理规则
    auto_expire_enabled: bool = Field(default=True, description="是否启用自动过期")
    auto_withdraw_enabled: bool = Field(default=False, description="是否启用自动撤回")

    # 通知配置
    notification_enabled: bool = Field(default=True, description="是否启用通知")
    notification_channels: List[str] = Field(
        default_factory=lambda: ["email", "web"], description="通知渠道"
    )

    # 审批规则
    approval_rules: Dict[str, Any] = Field(default_factory=dict, description="审批规则配置")

    # 工作时间配置
    work_hours_only: bool = Field(default=False, description="仅在工作时间处理审批")
    work_hours_start: str = Field(default="09:00", description="工作开始时间")
    work_hours_end: str = Field(default="18:00", description="工作结束时间")
    work_days: List[int] = Field(
        default_factory=lambda: [1, 2, 3, 4, 5], description="工作日（1-7，1=周一）"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "default_timeout_seconds": 86400,
                "default_approver_role": "tenant_admin",
                "auto_expire_enabled": True,
                "auto_withdraw_enabled": False,
                "notification_enabled": True,
                "notification_channels": ["email", "web"],
                "approval_rules": {
                    "high_risk_requires_approval": True,
                    "multi_level_approval": False,
                },
                "work_hours_only": False,
                "work_hours_start": "09:00",
                "work_hours_end": "18:00",
                "work_days": [1, 2, 3, 4, 5],
            }
        }


# 状态转换规则
class ApprovalStateTransition:
    """审批状态转换规则"""

    # 允许的状态转换
    ALLOWED_TRANSITIONS = {
        ApprovalStatus.DRAFT: [ApprovalStatus.PENDING, ApprovalStatus.CANCELLED],
        ApprovalStatus.PENDING: [
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.WITHDRAWN,
            ApprovalStatus.EXPIRED,
        ],
        ApprovalStatus.APPROVED: [],  # 终态
        ApprovalStatus.REJECTED: [],  # 终态
        ApprovalStatus.WITHDRAWN: [],  # 终态
        ApprovalStatus.EXPIRED: [],  # 终态
        ApprovalStatus.CANCELLED: [],  # 终态
    }

    @classmethod
    def can_transition(
        cls, from_status: ApprovalStatus, to_status: ApprovalStatus
    ) -> bool:
        """
        检查是否可以进行状态转换

        Args:
            from_status: 当前状态
            to_status: 目标状态

        Returns:
            是否可以转换
        """
        allowed_transitions = cls.ALLOWED_TRANSITIONS.get(from_status, [])
        return to_status in allowed_transitions

    @classmethod
    def get_valid_transitions(cls, from_status: ApprovalStatus) -> List[ApprovalStatus]:
        """
        获取当前状态的所有有效转换

        Args:
            from_status: 当前状态

        Returns:
            有效转换列表
        """
        return cls.ALLOWED_TRANSITIONS.get(from_status, [])

    @classmethod
    def is_terminal_state(cls, status: ApprovalStatus) -> bool:
        """
        检查是否为终态

        Args:
            status: 审批状态

        Returns:
            是否为终态
        """
        return len(cls.ALLOWED_TRANSITIONS.get(status, [])) == 0
