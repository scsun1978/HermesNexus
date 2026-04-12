"""
HermesNexus Phase 3 - 回滚模型
定义回滚和恢复相关的数据结构
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class RollbackType(str, Enum):
    """回滚类型枚举"""
    CONFIG = "config"  # 配置回滚
    SERVICE = "service"  # 服务回滚
    DEVICE = "device"  # 设备回滚
    TASK = "task"  # 任务回滚


class RollbackStatus(str, Enum):
    """回滚状态枚举"""
    PLANNED = "planned"  # 计划中
    PREPARING = "preparing"  # 准备中
    READY = "ready"  # 就绪
    EXECUTING = "executing"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消
    PARTIAL = "partial"  # 部分完成


class RollbackStep(BaseModel):
    """回滚步骤模型"""

    # 基本信息
    step_id: str = Field(..., description="步骤ID")
    sequence: int = Field(..., description="执行顺序")
    description: str = Field(..., description="步骤描述")

    # 回滚操作
    rollback_type: RollbackType = Field(..., description="回滚类型")
    target_resource: str = Field(..., description="目标资源")
    operation: str = Field(..., description="回滚操作")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="操作参数")

    # 执行信息
    status: RollbackStatus = Field(default=RollbackStatus.PLANNED, description="步骤状态")
    executed_at: Optional[datetime] = Field(None, description="执行时间")
    result: Optional[str] = Field(None, description="执行结果")
    error_message: Optional[str] = Field(None, description="错误信息")

    # 安全信息
    requires_backup: bool = Field(default=True, description="是否需要备份")
    backup_location: Optional[str] = Field(None, description="备份位置")
    validation_criteria: List[str] = Field(default_factory=list, description="验证标准")

    # 超时控制
    timeout_seconds: int = Field(default=300, description="超时时间（秒）")
    retry_count: int = Field(default=0, description="重试次数")
    max_retries: int = Field(default=3, description="最大重试次数")

    class Config:
        json_schema_extra = {
            "example": {
                "step_id": "step-001",
                "sequence": 1,
                "description": "回滚配置文件",
                "rollback_type": "config",
                "target_resource": "/etc/app/config.json",
                "operation": "restore_backup",
                "parameters": {
                    "backup_path": "/backup/config.json.bak"
                },
                "status": "planned",
                "requires_backup": True,
                "validation_criteria": ["config_exists", "config_valid"],
                "timeout_seconds": 60
            }
        }


class RollbackPlan(BaseModel):
    """回滚计划模型"""

    # 基本信息
    plan_id: str = Field(..., description="计划ID")
    name: str = Field(..., description="回滚计划名称")
    description: str = Field(..., description="回滚计划描述")

    # 关联信息
    original_task_id: Optional[str] = Field(None, description="原始任务ID")
    original_approval_id: Optional[str] = Field(None, description="原始审批ID")

    # 回滚类型
    rollback_type: RollbackType = Field(..., description="回滚类型")

    # 触发信息
    trigger_reason: str = Field(..., description="触发回滚的原因")
    trigger_type: str = Field(..., description="触发类型: auto/manual")
    triggered_by: str = Field(..., description="触发人ID")
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="触发时间")

    # 回滚步骤
    steps: List[RollbackStep] = Field(..., description="回滚步骤列表")

    # 状态信息
    status: RollbackStatus = Field(default=RollbackStatus.PLANNED, description="回滚状态")
    current_step: int = Field(default=0, description="当前执行步骤")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")

    # 结果信息
    final_status: Optional[str] = Field(None, description="最终状态")
    rollback_summary: Optional[str] = Field(None, description="回滚摘要")
    failure_reason: Optional[str] = Field(None, description="失败原因")

    # 风险控制
    estimated_duration_seconds: int = Field(..., description="预计耗时（秒）")
    estimated_risk_level: str = Field(default="medium", description="预计风险等级")

    # 审计信息
    rollback_log_id: Optional[str] = Field(None, description="回滚日志ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "rollback-001",
                "name": "配置回滚计划",
                "description": "回滚配置文件变更",
                "original_task_id": "task-001",
                "trigger_reason": "审批拒绝，需要回滚配置变更",
                "trigger_type": "auto",
                "triggered_by": "system",
                "triggered_at": "2026-04-15T10:30:00Z",
                "steps": [
                    {
                        "step_id": "step-001",
                        "sequence": 1,
                        "description": "停止受影响的服务",
                        "rollback_type": "service",
                        "target_resource": "core-api",
                        "operation": "stop",
                        "status": "planned"
                    },
                    {
                        "step_id": "step-002",
                        "sequence": 2,
                        "description": "恢复配置文件",
                        "rollback_type": "config",
                        "target_resource": "/etc/app/config.json",
                        "operation": "restore_backup",
                        "status": "planned"
                    }
                ],
                "status": "planned",
                "current_step": 0,
                "estimated_duration_seconds": 300,
                "estimated_risk_level": "low"
            }
        }


class FailureType(str, Enum):
    """故障类型枚举"""
    EXECUTION_FAILURE = "execution_failure"  # 执行失败
    VALIDATION_FAILURE = "validation_failure"  # 验证失败
    TIMEOUT_FAILURE = "timeout_failure"  # 超时失败
    DEPENDENCY_FAILURE = "dependency_failure"  # 依赖失败
    CONFIGURATION_ERROR = "configuration_error"  # 配置错误
    NETWORK_FAILURE = "network_failure"  # 网络故障
    RESOURCE_EXHAUSTION = "resource_exhaustion"  # 资源耗尽
    APPROVAL_REJECTED = "approval_rejected"  # 审批拒绝
    MANUAL_TRIGGER = "manual_trigger"  # 人工触发


class FailureSeverity(str, Enum):
    """故障严重程度"""
    LOW = "low"  # 低影响，不影响业务
    MEDIUM = "medium"  # 中等影响，部分功能受影响
    HIGH = "high"  # 高影响，核心功能受影响
    CRITICAL = "critical"  # 严重影响，业务中断


class RecoveryAction(str, Enum):
    """恢复动作枚举"""
    RETRY = "retry"  # 重试
    ROLLBACK = "rollback"  # 回滚
    SKIP = "skip"  # 跳过
    ESCALATE = "escalate"  # 升级处理
    MANUAL_INTERVENTION = "manual_intervention"  # 人工介入
    IGNORE = "ignore"  # 忽略


class FailureRecord(BaseModel):
    """故障记录模型"""

    # 基本信息
    failure_id: str = Field(..., description="故障ID")
    task_id: str = Field(..., description="关联任务ID")
    node_id: Optional[str] = Field(None, description="关联节点ID")
    asset_id: Optional[str] = Field(None, description="关联资产ID")

    # 故障信息
    failure_type: FailureType = Field(..., description="故障类型")
    severity: FailureSeverity = Field(..., description="严重程度")
    error_message: str = Field(..., description="错误消息")
    stack_trace: Optional[str] = Field(None, description="错误堆栈")

    # 发生信息
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="发生时间")
    detected_by: str = Field(default="system", description="检测方式")

    # 处理信息
    recovery_action: RecoveryAction = Field(..., description="恢复动作")
    recovery_status: str = Field(default="pending", description="恢复状态")
    recovery_result: Optional[str] = Field(None, description="恢复结果")
    recovered_at: Optional[datetime] = Field(None, description="恢复时间")

    # 附加信息
    context: Dict[str, Any] = Field(default_factory=dict, description="故障上下文")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "failure_id": "failure-001",
                "task_id": "task-001",
                "node_id": "node-001",
                "failure_type": "execution_failure",
                "severity": "high",
                "error_message": "Connection timeout",
                "occurred_at": "2026-04-15T10:30:00Z",
                "recovery_action": "retry",
                "recovery_status": "pending"
            }
        }


class RecoveryPlan(BaseModel):
    """恢复计划模型"""

    # 基本信息
    plan_id: str = Field(..., description="计划ID")
    failure_id: str = Field(..., description="关联故障ID")
    name: str = Field(..., description="恢复计划名称")
    description: str = Field(..., description="恢复计划描述")

    # 恢复策略
    recovery_action: RecoveryAction = Field(..., description="恢复动作")
    priority: int = Field(default=5, description="优先级（1-10，数字越小优先级越高）")

    # 执行步骤
    steps: List[str] = Field(..., description="恢复步骤")
    validation_criteria: List[str] = Field(..., description="验证标准")

    # 状态信息
    status: str = Field(default="pending", description="恢复状态")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")

    # 结果信息
    success: bool = Field(default=False, description="是否成功")
    result_message: Optional[str] = Field(None, description="结果消息")

    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "recovery-001",
                "failure_id": "failure-001",
                "name": "重试失败任务",
                "description": "重试连接超时的任务",
                "recovery_action": "retry",
                "priority": 5,
                "steps": [
                    "检查网络连接",
                    "重试任务执行",
                    "验证执行结果"
                ],
                "validation_criteria": ["任务成功完成"],
                "status": "pending"
            }
        }


class RollbackStatistics(BaseModel):
    """回滚统计模型"""

    # 总体统计
    total_rollback_plans: int = Field(..., description="总回滚计划数")
    successful_rollbacks: int = Field(..., description="成功回滚数")
    failed_rollbacks: int = Field(..., description="失败回滚数")
    cancelled_rollbacks: int = Field(..., description="取消回滚数")

    # 分类统计
    by_type: Dict[str, int] = Field(default_factory=dict, description="按类型统计")
    by_trigger: Dict[str, int] = Field(default_factory=dict, description="按触发原因统计")

    # 时间统计
    avg_duration_seconds: float = Field(..., description="平均回滚耗时")
    max_duration_seconds: float = Field(..., description="最长回滚耗时")
    min_duration_seconds: float = Field(..., description="最短回滚耗时")

    # 成功率统计
    success_rate: float = Field(..., description="回滚成功率")

    class Config:
        json_schema_extra = {
            "example": {
                "total_rollback_plans": 100,
                "successful_rollbacks": 85,
                "failed_rollbacks": 10,
                "cancelled_rollbacks": 5,
                "by_type": {
                    "config": 40,
                    "service": 30,
                    "device": 20,
                    "task": 10
                },
                "avg_duration_seconds": 180,
                "success_rate": 0.85
            }
        }


# 回滚步骤类型常量
class RollbackStepTypes:
    """回滚步骤类型常量"""

    # 配置回滚步骤
    BACKUP_CONFIG = "backup_config"
    RESTORE_CONFIG = "restore_config"
    VERIFY_CONFIG = "verify_config"

    # 服务回滚步骤
    STOP_SERVICE = "stop_service"
    START_SERVICE = "start_service"
    RESTART_SERVICE = "restart_service"
    DEPLOY_VERSION = "deploy_version"

    # 设备回滚步骤
    BACKUP_DEVICE = "backup_device"
    RESTORE_DEVICE = "restore_device"
    REBOOT_DEVICE = "reboot_device"

    # 任务回滚步骤
    RESET_TASK_STATUS = "reset_task_status"
    COMPENSATE_OPERATION = "compensate_operation"
    NOTIFY_USER = "notify_user"


# 故障处理策略常量
class FailureHandlingStrategies:
    """故障处理策略常量"""

    # 立即重试策略
    IMMEDIATE_RETRY = {
        "failure_types": [FailureType.NETWORK_FAILURE, FailureType.TIMEOUT_FAILURE],
        "action": RecoveryAction.RETRY,
        "max_attempts": 3,
        "backoff_seconds": 5
    }

    # 延迟重试策略
    DELAYED_RETRY = {
        "failure_types": [FailureType.DEPENDENCY_FAILURE, FailureType.RESOURCE_EXHAUSTION],
        "action": RecoveryAction.RETRY,
        "max_attempts": 5,
        "backoff_seconds": 30
    }

    # 直接回滚策略
    IMMEDIATE_ROLLBACK = {
        "failure_types": [FailureType.APPROVAL_REJECTED, FailureType.CONFIGURATION_ERROR],
        "action": RecoveryAction.ROLLBACK,
        "rollback_plan": "default"
    }

    # 升级处理策略
    ESCALATE_STRATEGY = {
        "failure_types": [FailureType.EXECUTION_FAILURE, FailureType.VALIDATION_FAILURE],
        "action": RecoveryAction.ESCALATE,
        "escalation_level": "operator"
    }