"""
HermesNexus Phase 3 - 审批服务
实现审批流程的核心业务逻辑
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from shared.models.approval import (
    ApprovalRequest, ApprovalDecision, ApprovalComment, ApprovalStatus,
    ApprovalPriority, ApprovalStatistics, ApprovalConfig,
    ApprovalStateTransition
)
from shared.models.permission import RiskLevel, ActionType, ResourceType


class ApprovalService:
    """审批服务 - 审批流程核心逻辑"""

    def __init__(self, config: Optional[ApprovalConfig] = None):
        """
        初始化审批服务

        Args:
            config: 审批配置
        """
        self.config = config or ApprovalConfig()

        # 审批请求存储（生产环境应使用数据库）
        self._requests: Dict[str, ApprovalRequest] = {}

        # 审批决策存储
        self._decisions: Dict[str, List[ApprovalDecision]] = {}

        # 审批评论存储
        self._comments: Dict[str, List[ApprovalComment]] = {}

    def create_request(
        self,
        title: str,
        description: str,
        requester_id: str,
        requester_name: str,
        operation_type: str,
        resource_type: str,
        target_operation: Dict[str, Any],
        risk_level: str,
        approver_role: str,
        resource_id: Optional[str] = None,
        priority: ApprovalPriority = ApprovalPriority.MEDIUM,
        timeout_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ApprovalRequest:
        """
        创建审批请求

        Args:
            title: 审批标题
            description: 审批描述
            requester_id: 申请人ID
            requester_name: 申请人姓名
            operation_type: 操作类型
            resource_type: 资源类型
            target_operation: 目标操作详情
            risk_level: 风险等级
            approver_role: 审批人角色
            resource_id: 资源ID
            priority: 优先级
            timeout_seconds: 超时时间
            metadata: 附加元数据

        Returns:
            审批请求对象
        """
        # 生成请求ID
        request_id = f"approval-{uuid.uuid4().hex[:8]}"

        # 计算过期时间
        timeout = timeout_seconds or self.config.default_timeout_seconds
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=timeout)

        # 创建审批请求
        request = ApprovalRequest(
            request_id=request_id,
            title=title,
            description=description,
            requester_id=requester_id,
            requester_name=requester_name,
            approver_role=approver_role,
            operation_type=operation_type,
            resource_type=resource_type,
            resource_id=resource_id,
            target_operation=target_operation,
            risk_level=risk_level,
            priority=priority,
            status=ApprovalStatus.DRAFT,
            timeout_seconds=timeout,
            expires_at=expires_at,
            metadata=metadata or {}
        )

        # 保存请求
        self._requests[request_id] = request

        return request

    def submit_request(self, request_id: str) -> ApprovalRequest:
        """
        提交审批请求

        Args:
            request_id: 请求ID

        Returns:
            更新后的审批请求

        Raises:
            ValueError: 请求不存在或状态不允许提交
        """
        request = self._get_request(request_id)

        # 检查状态转换
        if not ApprovalStateTransition.can_transition(request.status, ApprovalStatus.PENDING):
            raise ValueError(f"当前状态 {request.status} 不允许提交")

        # 更新状态
        request.status = ApprovalStatus.PENDING
        request.submitted_at = datetime.now(timezone.utc)
        request.updated_at = datetime.now(timezone.utc)

        # 保存更新
        self._requests[request_id] = request

        # 创建审计日志（这里简化处理）
        # audit_log_id = self._create_audit_log(request, "submit")

        return request

    def make_decision(
        self,
        request_id: str,
        decision: str,
        reason: str,
        approver_id: str,
        approver_name: str
    ) -> ApprovalRequest:
        """
        进行审批决策

        Args:
            request_id: 请求ID
            decision: 决策结果 (approve/reject)
            reason: 决策理由
            approver_id: 审批人ID
            approver_name: 审批人姓名

        Returns:
            更新后的审批请求

        Raises:
            ValueError: 请求不存在或状态不允许决策
        """
        request = self._get_request(request_id)

        # 检查状态
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"当前状态 {request.status} 不允许审批决策")

        # 验证决策值
        valid_decisions = ["approve", "reject"]
        if decision not in valid_decisions:
            raise ValueError(f"无效的决策值: {decision}，必须是: {valid_decisions}")

        # 确定目标状态
        target_status = ApprovalStatus.APPROVED if decision == "approve" else ApprovalStatus.REJECTED

        # 更新请求状态
        request.status = target_status
        request.decision = decision
        request.decision_reason = reason
        request.approver_id = approver_id
        request.approver_name = approver_name
        request.decided_at = datetime.now(timezone.utc)
        request.updated_at = datetime.now(timezone.utc)

        # 保存更新
        self._requests[request_id] = request

        # 创建决策记录
        decision_record = ApprovalDecision(
            decision_id=f"decision-{uuid.uuid4().hex[:8]}",
            request_id=request_id,
            decision=decision,
            reason=reason,
            approver_id=approver_id,
            approver_name=approver_name,
            decided_at=datetime.now(timezone.utc)
        )

        # 保存决策
        if request_id not in self._decisions:
            self._decisions[request_id] = []
        self._decisions[request_id].append(decision_record)

        # 创建审计日志
        # self._create_audit_log(request, "decision", decision_record)

        return request

    def withdraw_request(
        self,
        request_id: str,
        withdrawer_id: str,
        withdrawer_name: str,
        reason: str
    ) -> ApprovalRequest:
        """
        撤回审批请求

        Args:
            request_id: 请求ID
            withdrawer_id: 撤回人ID
            withdrawer_name: 撤回人姓名
            reason: 撤回理由

        Returns:
            更新后的审批请求

        Raises:
            ValueError: 请求不存在或状态不允许撤回
        """
        request = self._get_request(request_id)

        # 检查状态转换
        if not ApprovalStateTransition.can_transition(request.status, ApprovalStatus.WITHDRAWN):
            raise ValueError(f"当前状态 {request.status} 不允许撤回")

        # 更新状态
        request.status = ApprovalStatus.WITHDRAWN
        request.decision_reason = f"撤回理由: {reason}"
        request.updated_at = datetime.now(timezone.utc)

        # 保存更新
        self._requests[request_id] = request

        # 创建审计日志
        # self._create_audit_log(request, "withdraw", {"reason": reason})

        return request

    def cancel_request(self, request_id: str) -> ApprovalRequest:
        """
        取消审批请求（仅草案状态）

        Args:
            request_id: 请求ID

        Returns:
            更新后的审批请求

        Raises:
            ValueError: 请求不存在或状态不允许取消
        """
        request = self._get_request(request_id)

        # 只有草案状态可以取消
        if request.status != ApprovalStatus.DRAFT:
            raise ValueError(f"当前状态 {request.status} 不允许取消")

        # 更新状态
        request.status = ApprovalStatus.CANCELLED
        request.updated_at = datetime.now(timezone.utc)

        # 保存更新
        self._requests[request_id] = request

        return request

    def check_timeout(self) -> List[str]:
        """
        检查并处理超时的审批请求

        Returns:
            超时的请求ID列表
        """
        if not self.config.auto_expire_enabled:
            return []

        now = datetime.now(timezone.utc)
        timeout_requests = []

        for request_id, request in self._requests.items():
            # 只处理审批中的请求
            if request.status == ApprovalStatus.PENDING:
                # 检查是否超时
                if request.expires_at and now > request.expires_at:
                    # 更新状态为过期
                    request.status = ApprovalStatus.EXPIRED
                    request.updated_at = now
                    timeout_requests.append(request_id)

        return timeout_requests

    def add_comment(
        self,
        request_id: str,
        content: str,
        author_id: str,
        author_name: str,
        is_internal: bool = False
    ) -> ApprovalComment:
        """
        添加审批评论

        Args:
            request_id: 请求ID
            content: 评论内容
            author_id: 评论人ID
            author_name: 评论人姓名
            is_internal: 是否为内部评论

        Returns:
            审批评论对象

        Raises:
            ValueError: 请求不存在
        """
        # 确保请求存在
        self._get_request(request_id)

        # 创建评论
        comment = ApprovalComment(
            comment_id=f"comment-{uuid.uuid4().hex[:8]}",
            request_id=request_id,
            content=content,
            author_id=author_id,
            author_name=author_name,
            is_internal=is_internal,
            created_at=datetime.now(timezone.utc)
        )

        # 保存评论
        if request_id not in self._comments:
            self._comments[request_id] = []
        self._comments[request_id].append(comment)

        return comment

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """
        获取审批请求

        Args:
            request_id: 请求ID

        Returns:
            审批请求对象，如果不存在则返回None
        """
        return self._requests.get(request_id)

    def list_requests(
        self,
        status: Optional[ApprovalStatus] = None,
        requester_id: Optional[str] = None,
        approver_id: Optional[str] = None,
        priority: Optional[ApprovalPriority] = None,
        limit: int = 100
    ) -> List[ApprovalRequest]:
        """
        列出审批请求

        Args:
            status: 审批状态过滤
            requester_id: 申请人过滤
            approver_id: 审批人过滤
            priority: 优先级过滤
            limit: 返回数量限制

        Returns:
            审批请求列表
        """
        requests = list(self._requests.values())

        # 应用过滤条件
        if status:
            requests = [r for r in requests if r.status == status]
        if requester_id:
            requests = [r for r in requests if r.requester_id == requester_id]
        if approver_id:
            requests = [r for r in requests if r.approver_id == approver_id]
        if priority:
            requests = [r for r in requests if r.priority == priority]

        # 按创建时间倒序排序
        requests.sort(key=lambda x: x.created_at, reverse=True)

        # 限制返回数量
        return requests[:limit]

    def get_decisions(self, request_id: str) -> List[ApprovalDecision]:
        """
        获取审批决策历史

        Args:
            request_id: 请求ID

        Returns:
            审批决策列表
        """
        return self._decisions.get(request_id, [])

    def get_comments(self, request_id: str) -> List[ApprovalComment]:
        """
        获取审批评论

        Args:
            request_id: 请求ID

        Returns:
            审批评论列表
        """
        return self._comments.get(request_id, [])

    def get_statistics(self) -> ApprovalStatistics:
        """
        获取审批统计信息

        Returns:
            审批统计对象
        """
        requests = list(self._requests.values())

        # 基础统计
        total = len(requests)
        pending = sum(1 for r in requests if r.status == ApprovalStatus.PENDING)
        approved = sum(1 for r in requests if r.status == ApprovalStatus.APPROVED)
        rejected = sum(1 for r in requests if r.status == ApprovalStatus.REJECTED)
        expired = sum(1 for r in requests if r.status == ApprovalStatus.EXPIRED)

        # 时间统计
        approval_times = []
        for request in requests:
            if request.decided_at and request.submitted_at:
                time_diff = (request.decided_at - request.submitted_at).total_seconds()
                approval_times.append(time_diff)

        if approval_times:
            avg_time = sum(approval_times) / len(approval_times)
            max_time = max(approval_times)
            min_time = min(approval_times)
        else:
            avg_time = 0.0
            max_time = 0.0
            min_time = 0.0

        # 分类统计
        by_priority = {}
        by_risk_level = {}
        by_operation_type = {}

        for request in requests:
            # 按优先级统计
            priority_str = request.priority.value
            by_priority[priority_str] = by_priority.get(priority_str, 0) + 1

            # 按风险等级统计
            by_risk_level[request.risk_level] = by_risk_level.get(request.risk_level, 0) + 1

            # 按操作类型统计
            by_operation_type[request.operation_type] = by_operation_type.get(request.operation_type, 0) + 1

        return ApprovalStatistics(
            total_requests=total,
            pending_requests=pending,
            approved_requests=approved,
            rejected_requests=rejected,
            expired_requests=expired,
            avg_approval_time_seconds=avg_time,
            max_approval_time_seconds=max_time,
            min_approval_time_seconds=min_time,
            by_priority=by_priority,
            by_risk_level=by_risk_level,
            by_operation_type=by_operation_type
        )

    def _get_request(self, request_id: str) -> ApprovalRequest:
        """获取审批请求（不存在时抛出异常）"""
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"审批请求不存在: {request_id}")
        return request


# 全局审批服务实例（延迟初始化）
_global_approval_service: Optional[ApprovalService] = None


def get_approval_service() -> ApprovalService:
    """获取全局审批服务实例"""
    global _global_approval_service
    if _global_approval_service is None:
        _global_approval_service = ApprovalService()
    return _global_approval_service


def create_approval_service(config: ApprovalConfig) -> ApprovalService:
    """
    创建自定义审批服务

    Args:
        config: 审批配置

    Returns:
        审批服务实例
    """
    return ApprovalService(config=config)