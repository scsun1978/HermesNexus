"""
HermesNexus Phase 3 - 审批API
提供审批流程的HTTP API接口
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Header
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# 导入审批相关模型和服务
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.models.approval import (
    ApprovalRequest,
    ApprovalDecision,
    ApprovalComment,
    ApprovalStatus,
    ApprovalPriority,
    ApprovalStatistics,
)
from shared.services.approval_service import get_approval_service
from shared.security.node_auth_middleware import require_node_auth
from shared.security.permission_checker import require_permission
from shared.models.permission import ActionType, ResourceType, PermissionContext
from shared.models.node import NodeIdentity

# 创建API路由器
router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


# 认证依赖函数（简化版，实际应基于JWT Token）
async def get_current_user(
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
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
    # 实际实现中需要调用node_auth_middleware中的认证逻辑
    try:
        # 去掉Bearer前缀
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

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
def check_approval_permission(action: str):
    """
    检查审批操作权限的依赖工厂函数

    Args:
        action: 操作类型

    Returns:
        依赖函数
    """

    def permission_dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        """
        实际的权限检查函数

        Args:
            current_user: 当前用户信息

        Raises:
            HTTPException: 权限不足时抛出403
        """
        # 检查用户是否有审批权限
        allowed_roles = ["tenant_admin", "super_admin", "operator"]

        # 对于查看操作，允许所有已认证用户
        if action == "view":
            return current_user

        # 对于审批操作，需要特定角色
        if action == "approve":
            if not any(role in current_user.get("roles", []) for role in allowed_roles):
                raise HTTPException(status_code=403, detail="权限不足：需要审批权限")

        # 对于创建请求，所有已认证用户都可以
        if action == "create":
            return current_user

        return current_user

    return permission_dependency
    # 检查用户是否有审批权限
    allowed_roles = ["tenant_admin", "super_admin", "operator"]

    # 对于查看操作，允许所有已认证用户
    if action == "view":
        return current_user

    # 对于审批操作，需要特定角色
    if action == "approve":
        if not any(role in current_user.get("roles", []) for role in allowed_roles):
            raise HTTPException(status_code=403, detail="权限不足：需要审批权限")

    # 对于创建请求，所有已认证用户都可以
    if action == "create":
        return current_user

    return current_user


# 请求/响应模型
class CreateApprovalRequest(BaseModel):
    """创建审批请求模型"""

    title: str = Field(..., description="审批标题", min_length=1, max_length=200)
    description: str = Field(..., description="审批描述", min_length=1, max_length=1000)
    requester_id: str = Field(..., description="申请人ID")
    requester_name: str = Field(..., description="申请人姓名")
    operation_type: str = Field(..., description="操作类型")
    resource_type: str = Field(..., description="资源类型")
    target_operation: dict = Field(..., description="目标操作详情")
    risk_level: str = Field(..., description="风险等级")
    approver_role: str = Field(..., description="审批人角色")
    resource_id: Optional[str] = Field(None, description="资源ID")
    priority: str = Field(default="medium", description="优先级")
    timeout_seconds: Optional[int] = Field(None, description="超时时间（秒）")
    metadata: Optional[dict] = Field(default=None, description="附加元数据")


class SubmitApprovalRequest(BaseModel):
    """提交审批请求模型"""

    request_id: str = Field(..., description="请求ID")


class MakeApprovalDecision(BaseModel):
    """审批决策模型"""

    decision: str = Field(..., description="决策结果: approve/reject")
    reason: str = Field(..., description="决策理由", min_length=1, max_length=500)
    approver_id: str = Field(..., description="审批人ID")
    approver_name: str = Field(..., description="审批人姓名")


class WithdrawApprovalRequest(BaseModel):
    """撤回审批请求模型"""

    request_id: str = Field(..., description="请求ID")
    withdrawer_id: str = Field(..., description="撤回人ID")
    withdrawer_name: str = Field(..., description="撤回人姓名")
    reason: str = Field(..., description="撤回理由", min_length=1, max_length=500)


class AddApprovalComment(BaseModel):
    """添加审批评论模型"""

    request_id: str = Field(..., description="请求ID")
    content: str = Field(..., description="评论内容", min_length=1, max_length=500)
    author_id: str = Field(..., description="评论人ID")
    author_name: str = Field(..., description="评论人姓名")
    is_internal: bool = Field(default=False, description="是否为内部评论")


# API端点实现


@router.post("/requests", response_model=ApprovalRequest)
async def create_approval_request(
    request_data: CreateApprovalRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    创建审批请求

    创建一个新的审批请求，初始状态为DRAFT（草案）
    需要认证
    """
    try:
        # 补充申请人信息
        request_data.requester_id = current_user["user_id"]
        request_data.requester_name = current_user["user_name"]

        service = get_approval_service()

        # 转换优先级
        priority = ApprovalPriority(request_data.priority)

        # 创建审批请求
        request = service.create_request(
            title=request_data.title,
            description=request_data.description,
            requester_id=request_data.requester_id,
            requester_name=request_data.requester_name,
            operation_type=request_data.operation_type,
            resource_type=request_data.resource_type,
            target_operation=request_data.target_operation,
            risk_level=request_data.risk_level,
            approver_role=request_data.approver_role,
            resource_id=request_data.resource_id,
            priority=priority,
            timeout_seconds=request_data.timeout_seconds,
            metadata=request_data.metadata,
        )

        return request

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建审批请求失败: {str(e)}")


@router.post("/requests/submit", response_model=ApprovalRequest)
async def submit_approval_request(
    submit_data: SubmitApprovalRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    提交审批请求

    将审批请求从DRAFT状态提交到PENDING状态，开始审批流程
    需要认证
    """
    try:
        service = get_approval_service()

        # 权限检查：只有申请人能提交自己的请求
        request = service.get_request(submit_data.request_id)
        if not request:
            raise HTTPException(
                status_code=404, detail=f"审批请求不存在: {submit_data.request_id}"
            )

        if request.requester_id != current_user["user_id"]:
            raise HTTPException(
                status_code=403, detail="权限不足：只能提交自己创建的审批请求"
            )

        # 提交请求
        request = service.submit_request(submit_data.request_id)

        return request

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交审批请求失败: {str(e)}")


@router.post("/requests/decision", response_model=ApprovalRequest)
async def make_approval_decision(
    decision_data: MakeApprovalDecision,
    current_user: Dict[str, Any] = Depends(check_approval_permission("approve")),
):
    """
    进行审批决策

    对审批请求进行批准或拒绝决策
    需要认证+审批权限
    """
    try:
        # 补充审批人信息
        decision_data.approver_id = current_user["user_id"]
        decision_data.approver_name = current_user["user_name"]

        service = get_approval_service()

        # 进行决策
        request = service.make_decision(
            request_id=decision_data.request_id,
            decision=decision_data.decision,
            reason=decision_data.reason,
            approver_id=decision_data.approver_id,
            approver_name=decision_data.approver_name,
        )

        return request

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"审批决策失败: {str(e)}")


@router.post("/requests/withdraw", response_model=ApprovalRequest)
async def withdraw_approval_request(
    withdraw_data: WithdrawApprovalRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    撤回审批请求

    申请人可以撤回审批请求
    需要认证
    """
    try:
        # 补充撤回人信息
        withdraw_data.withdrawer_id = current_user["user_id"]
        withdraw_data.withdrawer_name = current_user["user_name"]

        service = get_approval_service()

        # 权限检查：只有申请人能撤回自己的请求
        request = service.get_request(withdraw_data.request_id)
        if not request:
            raise HTTPException(
                status_code=404, detail=f"审批请求不存在: {withdraw_data.request_id}"
            )

        if request.requester_id != current_user["user_id"]:
            raise HTTPException(
                status_code=403, detail="权限不足：只能撤回自己创建的审批请求"
            )

        # 撤回请求
        request = service.withdraw_request(
            request_id=withdraw_data.request_id,
            withdrawer_id=withdraw_data.withdrawer_id,
            withdrawer_name=withdraw_data.withdrawer_name,
            reason=withdraw_data.reason,
        )

        return request

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"撤回审批请求失败: {str(e)}")


@router.delete("/requests/{request_id}", response_model=ApprovalRequest)
async def cancel_approval_request(
    request_id: str, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    取消审批请求

    取消处于DRAFT状态的审批请求
    需要认证
    """
    try:
        service = get_approval_service()

        # 权限检查：只有申请人能取消自己的请求
        request = service.get_request(request_id)
        if not request:
            raise HTTPException(status_code=404, detail=f"审批请求不存在: {request_id}")

        if request.requester_id != current_user["user_id"]:
            raise HTTPException(
                status_code=403, detail="权限不足：只能取消自己创建的审批请求"
            )

        # 取消请求
        request = service.cancel_request(request_id)

        return request

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消审批请求失败: {str(e)}")


@router.get("/requests/{request_id}", response_model=ApprovalRequest)
async def get_approval_request(
    request_id: str,
    current_user: Dict[str, Any] = Depends(check_approval_permission("view")),
):
    """
    获取审批请求详情

    根据请求ID获取审批请求的详细信息
    需要认证
    """
    try:
        service = get_approval_service()

        request = service.get_request(request_id)
        if not request:
            raise HTTPException(status_code=404, detail=f"审批请求不存在: {request_id}")

        # 权限检查：用户只能查看自己相关的审批请求（除非是管理员）
        user_roles = current_user.get("roles", [])
        if "admin" not in user_roles and "super_admin" not in user_roles:
            if (
                request.requester_id != current_user["user_id"]
                and request.approver_id != current_user["user_id"]
            ):
                raise HTTPException(
                    status_code=403, detail="权限不足：只能查看自己相关的审批请求"
                )

        return request

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取审批请求失败: {str(e)}")


@router.get("/requests", response_model=List[ApprovalRequest])
async def list_approval_requests(
    current_user: Dict[str, Any] = Depends(get_current_user),
    status: Optional[str] = Query(None, description="审批状态过滤"),
    requester_id: Optional[str] = Query(None, description="申请人ID过滤"),
    approver_id: Optional[str] = Query(None, description="审批人ID过滤"),
    priority: Optional[str] = Query(None, description="优先级过滤"),
    limit: int = Query(100, description="返回数量限制", ge=1, le=1000),
):
    """
    列出审批请求

    根据过滤条件列出审批请求
    需要认证
    """
    try:
        service = get_approval_service()

        # 转换过滤参数（如果参数无效，抛出ValueError）
        try:
            status_enum = ApprovalStatus(status) if status else None
            priority_enum = ApprovalPriority(priority) if priority else None
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"无效的参数值: {str(e)}")

        # 获取请求列表
        requests = service.list_requests(
            status=status_enum,
            requester_id=requester_id,
            approver_id=approver_id,
            priority=priority_enum,
            limit=limit,
        )

        return requests

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出审批请求失败: {str(e)}")


@router.post("/comments", response_model=ApprovalComment)
async def add_approval_comment(
    comment_data: AddApprovalComment,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    添加审批评论

    为审批请求添加评论
    需要认证
    """
    try:
        # 补充评论人信息
        comment_data.author_id = current_user["user_id"]
        comment_data.author_name = current_user["user_name"]

        service = get_approval_service()

        # 添加评论
        comment = service.add_comment(
            request_id=comment_data.request_id,
            content=comment_data.content,
            author_id=comment_data.author_id,
            author_name=comment_data.author_name,
            is_internal=comment_data.is_internal,
        )

        return comment

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加评论失败: {str(e)}")


@router.get("/requests/{request_id}/comments", response_model=List[ApprovalComment])
async def get_approval_comments(
    request_id: str, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取审批评论

    获取审批请求的所有评论
    需要认证
    """
    try:
        service = get_approval_service()

        comments = service.get_comments(request_id)

        return comments

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取评论失败: {str(e)}")


@router.get("/requests/{request_id}/decisions", response_model=List[ApprovalDecision])
async def get_approval_decisions(
    request_id: str, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取审批决策历史

    获取审批请求的所有决策记录
    需要认证
    """
    try:
        service = get_approval_service()

        decisions = service.get_decisions(request_id)

        return decisions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取决策历史失败: {str(e)}")


@router.get("/statistics", response_model=ApprovalStatistics)
async def get_approval_statistics(
    current_user: Dict[str, Any] = Depends(check_approval_permission("view")),
):
    """
    获取审批统计信息

    获取审批流程的统计数据
    需要认证+查看权限
    """
    try:
        service = get_approval_service()

        statistics = service.get_statistics()

        return statistics

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.post("/admin/check-timeout")
async def check_approval_timeout():
    """
    检查审批超时

    检查并处理超时的审批请求（管理接口）
    """
    try:
        service = get_approval_service()

        timeout_requests = service.check_timeout()

        return {
            "message": f"处理了 {len(timeout_requests)} 个超时请求",
            "timeout_requests": timeout_requests,
            "count": len(timeout_requests),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查超时失败: {str(e)}")


# 健康检查端点
@router.get("/health")
async def approval_health_check():
    """
    审批服务健康检查
    """
    service = get_approval_service()
    statistics = service.get_statistics()

    return {
        "status": "healthy",
        "service": "approval-service",
        "total_requests": statistics.total_requests,
        "pending_requests": statistics.pending_requests,
    }
