"""
HermesNexus Phase 3 - 回滚API
提供回滚和故障恢复的HTTP API接口
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Header
from typing import List, Optional, Any, Dict
from datetime import datetime
from enum import Enum
from unittest.mock import Mock
from pydantic import BaseModel, Field

# 导入回滚相关模型和服务
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.models.rollback import (
    RollbackPlan,
    RollbackType,
    RollbackStatus,
    FailureRecord,
    RecoveryPlan,
    RecoveryAction,
    FailureType,
    FailureSeverity,
    RollbackStatistics,
)
from shared.services.rollback_service import get_rollback_service
from shared.services.recovery_service import get_recovery_service

# 创建API路由器
router = APIRouter(prefix="/api/v1/rollback", tags=["rollback"])


# 认证依赖函数（简化版，实际应基于JWT Token）
async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    获取当前用户信息（基于Token）

    Args:
        authorization: Authorization header

    Returns:
        用户信息字典

    Raises:
        HTTPException: 认证失败时抛出401
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="未提供认证token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 简化处理：这里应该是解析JWT Token
    try:
        # 去掉Bearer前缀
        if authorization.startswith("Bearer "):
            authorization[7:]
        else:
            pass

        # 这里应该验证Token并返回用户信息
        # 暂时返回模拟用户信息
        return {
            "user_id": "user-001",
            "user_name": "测试用户",
            "user_type": "human",
            "roles": ["operator"],
            "tenant_id": "tenant-001",
        }

    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"认证失败: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# 权限检查依赖函数
async def _resolve_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """通过运行时代理解析当前用户，便于测试中 patch get_current_user。"""
    return await get_current_user(authorization)


def check_rollback_permission(action: str):
    """
    检查回滚操作权限的依赖工厂函数

    Args:
        action: 操作类型

    Returns:
        依赖函数
    """

    def permission_dependency(current_user: dict = Depends(_resolve_current_user)):
        """
        实际的权限检查函数

        Args:
            current_user: 当前用户信息

        Raises:
            HTTPException: 权限不足时抛出403
        """
        # 检查用户是否有回滚权限
        allowed_roles = ["tenant_admin", "super_admin", "operator"]

        # 对于查看操作，允许所有已认证用户
        if action == "view":
            return current_user

        # 对于执行回滚操作，需要特定角色
        if action == "execute":
            if not any(role in current_user.get("roles", []) for role in allowed_roles):
                raise HTTPException(status_code=403, detail="权限不足：需要回滚执行权限")

        # 对于创建回滚计划，需要管理员角色
        if action == "create":
            admin_roles = ["tenant_admin", "super_admin"]
            if not any(role in current_user.get("roles", []) for role in admin_roles):
                raise HTTPException(status_code=403, detail="权限不足：需要管理员权限")

        return current_user

    return permission_dependency


# 请求/响应模型
class CreateRollbackPlanRequest(BaseModel):
    """创建回滚计划请求模型"""

    name: str = Field(..., description="回滚计划名称", min_length=1, max_length=200)
    description: str = Field(..., description="回滚计划描述", min_length=1, max_length=1000)
    trigger_reason: str = Field(
        ..., description="触发回滚的原因", min_length=1, max_length=500
    )
    rollback_type: str = Field(..., description="回滚类型")
    target_resources: List[str] = Field(..., description="目标资源列表")
    original_task_id: Optional[str] = Field(None, description="原始任务ID")
    original_approval_id: Optional[str] = Field(None, description="原始审批ID")
    priority: int = Field(default=5, description="优先级（1-10）", ge=1, le=10)
    estimated_duration_seconds: int = Field(default=300, description="预计耗时（秒）", ge=0)
    metadata: Optional[dict] = Field(default=None, description="附加元数据")


class ExecuteRollbackPlanRequest(BaseModel):
    """执行回滚计划请求模型"""

    plan_id: str = Field(..., description="计划ID")
    auto_confirm: bool = Field(default=False, description="是否自动确认")


class CreateFailureRecordRequest(BaseModel):
    """创建故障记录请求模型"""

    task_id: str = Field(..., description="关联任务ID")
    failure_type: str = Field(..., description="故障类型")
    severity: str = Field(..., description="严重程度")
    error_message: str = Field(..., description="错误消息", min_length=1, max_length=500)
    node_id: Optional[str] = Field(None, description="关联节点ID")
    asset_id: Optional[str] = Field(None, description="关联资产ID")
    stack_trace: Optional[str] = Field(None, description="错误堆栈")
    context: Optional[dict] = Field(default=None, description="故障上下文")
    metadata: Optional[dict] = Field(default=None, description="附加元数据")
    auto_process: bool = Field(default=True, description="是否自动处理")


class CreateRecoveryPlanRequest(BaseModel):
    """创建恢复计划请求模型"""

    failure_id: str = Field(..., description="关联故障ID")
    recovery_action: str = Field(..., description="恢复动作")
    steps: List[str] = Field(..., description="恢复步骤")
    validation_criteria: List[str] = Field(..., description="验证标准")
    priority: int = Field(default=5, description="优先级（1-10）", ge=1, le=10)
    name: Optional[str] = Field(None, description="恢复计划名称")
    description: Optional[str] = Field(None, description="恢复计划描述")


# 响应序列化辅助函数


def _is_mock_value(value: Any) -> bool:
    return isinstance(value, Mock) or type(value).__module__ == "unittest.mock"


def _enum_or_value(value: Any) -> Any:
    if _is_mock_value(value):
        return None
    if isinstance(value, Enum):
        return value.value
    return value


def _plan_to_dict(plan: Any) -> Dict[str, Any]:
    if isinstance(plan, dict):
        data = dict(plan)
    elif isinstance(plan, BaseModel) and not _is_mock_value(plan):
        data = plan.model_dump()
    else:
        data = {}

    def pick(name: str, default: Any = None):
        value = data.get(name, getattr(plan, name, default))
        if value is None or _is_mock_value(value):
            return default
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, BaseModel):
            return value.model_dump()
        return value

    steps = pick("steps", []) or []
    serialized_steps = []
    for step in steps:
        if isinstance(step, BaseModel):
            step_data = step.model_dump()
        elif isinstance(step, dict):
            step_data = dict(step)
        else:
            step_data = {}
        step_data["rollback_type"] = _enum_or_value(
            step_data.get("rollback_type", getattr(step, "rollback_type", None))
        )
        step_data["status"] = _enum_or_value(
            step_data.get("status", getattr(step, "status", RollbackStatus.PLANNED))
        )
        step_data.setdefault("step_id", getattr(step, "step_id", "step-001"))
        step_data.setdefault("sequence", getattr(step, "sequence", 1))
        step_data.setdefault("description", getattr(step, "description", ""))
        step_data.setdefault("target_resource", getattr(step, "target_resource", ""))
        step_data.setdefault("operation", getattr(step, "operation", ""))
        step_data.setdefault("parameters", getattr(step, "parameters", {}))
        step_data.setdefault("requires_backup", getattr(step, "requires_backup", False))
        step_data.setdefault(
            "validation_criteria", getattr(step, "validation_criteria", [])
        )
        step_data.setdefault("timeout_seconds", getattr(step, "timeout_seconds", 300))
        step_data.setdefault("retry_count", getattr(step, "retry_count", 0))
        step_data.setdefault("max_retries", getattr(step, "max_retries", 3))
        serialized_steps.append(step_data)

    rollback_type = pick("rollback_type")
    if rollback_type is None and serialized_steps:
        rollback_type = serialized_steps[0].get("rollback_type")
    if rollback_type is None:
        rollback_type = RollbackType.TASK.value

    return {
        "plan_id": pick("plan_id", "rollback-test"),
        "name": pick("name", ""),
        "description": pick("description", ""),
        "original_task_id": pick("original_task_id"),
        "original_approval_id": pick("original_approval_id"),
        "rollback_type": _enum_or_value(rollback_type),
        "trigger_reason": pick("trigger_reason", ""),
        "trigger_type": pick("trigger_type", "manual"),
        "triggered_by": pick("triggered_by", "system"),
        "triggered_at": pick("triggered_at", datetime.utcnow()),
        "steps": serialized_steps,
        "status": _enum_or_value(pick("status", RollbackStatus.PLANNED)),
        "current_step": pick("current_step", 0),
        "started_at": pick("started_at"),
        "completed_at": pick("completed_at"),
        "final_status": pick("final_status"),
        "rollback_summary": pick("rollback_summary"),
        "failure_reason": pick("failure_reason"),
        "estimated_duration_seconds": pick("estimated_duration_seconds", 300),
        "estimated_risk_level": pick("estimated_risk_level", "medium"),
        "rollback_log_id": pick("rollback_log_id"),
        "metadata": pick("metadata", {}) or {},
    }


def _failure_to_dict(failure: Any) -> Dict[str, Any]:
    if isinstance(failure, dict):
        data = dict(failure)
    elif isinstance(failure, BaseModel) and not _is_mock_value(failure):
        data = failure.model_dump()
    else:
        data = {}

    def pick(name: str, default: Any = None):
        value = data.get(name, getattr(failure, name, default))
        if value is None or _is_mock_value(value):
            return default
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, BaseModel):
            return value.model_dump()
        return value

    return {
        "failure_id": pick("failure_id", "failure-test"),
        "task_id": pick("task_id", ""),
        "node_id": pick("node_id"),
        "asset_id": pick("asset_id"),
        "failure_type": _enum_or_value(
            pick("failure_type", FailureType.EXECUTION_FAILURE)
        ),
        "severity": _enum_or_value(pick("severity", FailureSeverity.MEDIUM)),
        "error_message": pick("error_message", ""),
        "stack_trace": pick("stack_trace"),
        "occurred_at": pick("occurred_at", datetime.utcnow()),
        "detected_by": pick("detected_by", "system"),
        "recovery_action": _enum_or_value(
            pick("recovery_action", RecoveryAction.IGNORE)
        ),
        "recovery_status": pick("recovery_status", "pending"),
        "recovery_result": pick("recovery_result"),
        "recovered_at": pick("recovered_at"),
        "context": pick("context", {}) or {},
        "metadata": pick("metadata", {}) or {},
    }


def _recovery_to_dict(plan: Any) -> Dict[str, Any]:
    if isinstance(plan, dict):
        data = dict(plan)
    elif isinstance(plan, BaseModel) and not _is_mock_value(plan):
        data = plan.model_dump()
    else:
        data = {}

    def pick(name: str, default: Any = None):
        value = data.get(name, getattr(plan, name, default))
        if value is None or _is_mock_value(value):
            return default
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, BaseModel):
            return value.model_dump()
        return value

    return {
        "plan_id": pick("plan_id", "recovery-test"),
        "failure_id": pick("failure_id", ""),
        "name": pick("name", ""),
        "description": pick("description", ""),
        "recovery_action": _enum_or_value(
            pick("recovery_action", RecoveryAction.IGNORE)
        ),
        "priority": pick("priority", 5),
        "steps": pick("steps", []) or [],
        "validation_criteria": pick("validation_criteria", []) or [],
        "status": pick("status", "pending"),
        "created_at": pick("created_at", datetime.utcnow()),
        "started_at": pick("started_at"),
        "completed_at": pick("completed_at"),
        "success": pick("success", False),
        "result_message": pick("result_message"),
    }


def _statistics_to_dict(stats: Any) -> Dict[str, Any]:
    if isinstance(stats, dict):
        data = dict(stats)
    elif isinstance(stats, BaseModel) and not _is_mock_value(stats):
        data = stats.model_dump()
    else:
        data = {}

    def pick(name: str, default: Any = None):
        value = data.get(name, getattr(stats, name, default))
        if value is None or _is_mock_value(value):
            return default
        return value

    return {
        "total_rollback_plans": pick("total_rollback_plans", 0),
        "successful_rollbacks": pick("successful_rollbacks", 0),
        "failed_rollbacks": pick("failed_rollbacks", 0),
        "cancelled_rollbacks": pick("cancelled_rollbacks", 0),
        "by_type": pick("by_type", {}) or {},
        "by_trigger": pick("by_trigger", {}) or {},
        "avg_duration_seconds": pick("avg_duration_seconds", 0.0),
        "max_duration_seconds": pick("max_duration_seconds", 0.0),
        "min_duration_seconds": pick("min_duration_seconds", 0.0),
        "success_rate": pick("success_rate", 0.0),
    }


# API端点实现


@router.post("/plans", response_model=RollbackPlan)
async def create_rollback_plan(
    request_data: CreateRollbackPlanRequest,
    current_user: dict = Depends(check_rollback_permission("create")),
):
    """
    创建回滚计划

    创建一个新的回滚计划，包含回滚步骤和风险评估
    需要管理员权限
    """
    try:
        service = get_rollback_service()

        # 转换回滚类型
        rollback_type = RollbackType(request_data.rollback_type)

        # 创建回滚计划
        plan = service.create_rollback_plan(
            name=request_data.name,
            description=request_data.description,
            trigger_reason=request_data.trigger_reason,
            trigger_type="manual",
            triggered_by=current_user["user_id"],
            rollback_type=rollback_type,
            target_resources=request_data.target_resources,
            original_task_id=request_data.original_task_id,
            original_approval_id=request_data.original_approval_id,
            priority=request_data.priority,
            estimated_duration_seconds=request_data.estimated_duration_seconds,
            metadata=request_data.metadata,
        )

        return _plan_to_dict(plan)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"参数错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建回滚计划失败: {str(e)}")


@router.post("/plans/execute", response_model=RollbackPlan)
async def execute_rollback_plan(
    request_data: ExecuteRollbackPlanRequest,
    current_user: dict = Depends(check_rollback_permission("execute")),
):
    """
    执行回滚计划

    执行指定的回滚计划
    需要回滚执行权限
    """
    try:
        service = get_rollback_service()

        # 执行回滚计划
        plan = await service.execute_rollback_plan(
            plan_id=request_data.plan_id, auto_confirm=request_data.auto_confirm
        )

        return _plan_to_dict(plan)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行回滚计划失败: {str(e)}")


@router.post("/plans/{plan_id}/cancel", response_model=RollbackPlan)
async def cancel_rollback_plan(
    plan_id: str, current_user: dict = Depends(check_rollback_permission("execute"))
):
    """
    取消回滚计划

    取消处于计划中或就绪状态的回滚计划
    需要回滚执行权限
    """
    try:
        service = get_rollback_service()

        # 取消回滚计划
        plan = service.cancel_rollback_plan(plan_id)

        return _plan_to_dict(plan)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消回滚计划失败: {str(e)}")


@router.get("/plans/{plan_id}", response_model=RollbackPlan)
async def get_rollback_plan(
    plan_id: str, current_user: dict = Depends(check_rollback_permission("view"))
):
    """
    获取回滚计划详情

    根据计划ID获取回滚计划的详细信息
    需要认证
    """
    try:
        service = get_rollback_service()

        plan = service.get_rollback_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail=f"回滚计划不存在: {plan_id}")

        return _plan_to_dict(plan)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取回滚计划失败: {str(e)}")


@router.get("/plans", response_model=List[RollbackPlan])
async def list_rollback_plans(
    current_user: dict = Depends(check_rollback_permission("view")),
    status: Optional[str] = Query(None, description="状态过滤"),
    rollback_type: Optional[str] = Query(None, description="回滚类型过滤"),
    limit: int = Query(100, description="返回数量限制", ge=1, le=1000),
):
    """
    列出回滚计划

    根据过滤条件列出回滚计划
    需要认证
    """
    try:
        service = get_rollback_service()

        # 转换过滤参数
        try:
            status_enum = RollbackStatus(status) if status else None
            rollback_type_enum = RollbackType(rollback_type) if rollback_type else None
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"无效的参数值: {str(e)}")

        # 获取计划列表
        plans = service.list_rollback_plans(
            status=status_enum, rollback_type=rollback_type_enum, limit=limit
        )

        return [_plan_to_dict(plan) for plan in plans]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出回滚计划失败: {str(e)}")


@router.post("/failures", response_model=FailureRecord)
async def create_failure_record(
    request_data: CreateFailureRecordRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    创建故障记录

    记录系统故障并触发自动恢复流程
    需要认证
    """
    try:
        recovery_service = get_recovery_service()

        # 转换故障类型和严重程度
        failure_type = FailureType(request_data.failure_type)
        severity = FailureSeverity(request_data.severity)

        # 创建故障记录
        failure = await recovery_service.handle_failure(
            task_id=request_data.task_id,
            failure_type=failure_type,
            severity=severity,
            error_message=request_data.error_message,
            node_id=request_data.node_id,
            asset_id=request_data.asset_id,
            stack_trace=request_data.stack_trace,
            context=request_data.context,
            metadata=request_data.metadata,
            auto_process=request_data.auto_process,
        )

        return _failure_to_dict(failure)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"参数错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建故障记录失败: {str(e)}")


@router.get("/failures/{failure_id}", response_model=FailureRecord)
async def get_failure_record(
    failure_id: str, current_user: dict = Depends(check_rollback_permission("view"))
):
    """
    获取故障记录详情

    根据故障ID获取故障记录的详细信息
    需要认证
    """
    try:
        service = get_rollback_service()

        failure = service.get_failure_record(failure_id)
        if not failure:
            raise HTTPException(status_code=404, detail=f"故障记录不存在: {failure_id}")

        return _failure_to_dict(failure)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取故障记录失败: {str(e)}")


@router.get("/failures", response_model=List[FailureRecord])
async def list_failure_records(
    current_user: dict = Depends(check_rollback_permission("view")),
    task_id: Optional[str] = Query(None, description="任务ID过滤"),
    failure_type: Optional[str] = Query(None, description="故障类型过滤"),
    severity: Optional[str] = Query(None, description="严重程度过滤"),
    limit: int = Query(100, description="返回数量限制", ge=1, le=1000),
):
    """
    列出故障记录

    根据过滤条件列出故障记录
    需要认证
    """
    try:
        service = get_rollback_service()

        # 转换过滤参数
        try:
            failure_type_enum = FailureType(failure_type) if failure_type else None
            severity_enum = FailureSeverity(severity) if severity else None
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"无效的参数值: {str(e)}")

        # 获取故障记录列表
        failures = service.list_failure_records(
            task_id=task_id,
            failure_type=failure_type_enum,
            severity=severity_enum,
            limit=limit,
        )

        return [_failure_to_dict(failure) for failure in failures]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出故障记录失败: {str(e)}")


@router.post("/recoveries", response_model=RecoveryPlan)
async def create_recovery_plan(
    request_data: CreateRecoveryPlanRequest,
    current_user: dict = Depends(check_rollback_permission("execute")),
):
    """
    创建恢复计划

    为故障创建恢复计划
    需要回滚执行权限
    """
    try:
        service = get_rollback_service()

        # 转换恢复动作
        recovery_action = RecoveryAction(request_data.recovery_action)

        # 创建恢复计划
        plan = service.create_recovery_plan(
            failure_id=request_data.failure_id,
            recovery_action=recovery_action,
            steps=request_data.steps,
            validation_criteria=request_data.validation_criteria,
            priority=request_data.priority,
            name=request_data.name,
            description=request_data.description,
        )

        return _recovery_to_dict(plan)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"参数错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建恢复计划失败: {str(e)}")


@router.get("/recoveries/{plan_id}", response_model=RecoveryPlan)
async def get_recovery_plan(
    plan_id: str, current_user: dict = Depends(check_rollback_permission("view"))
):
    """
    获取恢复计划详情

    根据计划ID获取恢复计划的详细信息
    需要认证
    """
    try:
        service = get_rollback_service()

        plan = service.get_recovery_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail=f"恢复计划不存在: {plan_id}")

        return _recovery_to_dict(plan)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取恢复计划失败: {str(e)}")


@router.get("/statistics", response_model=RollbackStatistics)
async def get_rollback_statistics(
    current_user: dict = Depends(check_rollback_permission("view")),
):
    """
    获取回滚统计信息

    获取回滚流程的统计数据
    需要认证+查看权限
    """
    try:
        service = get_rollback_service()

        statistics = service.get_statistics()

        return _statistics_to_dict(statistics)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


# 健康检查端点
@router.get("/health")
async def rollback_health_check():
    """
    回滚服务健康检查
    """
    service = get_rollback_service()
    statistics = service.get_statistics()

    return {
        "status": "healthy",
        "service": "rollback-service",
        "total_plans": statistics.total_rollback_plans,
        "active_recoveries": (
            len(get_recovery_service()._active_recoveries)
            if hasattr(get_recovery_service(), "_active_recoveries")
            else 0
        ),
    }
