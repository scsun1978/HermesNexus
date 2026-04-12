"""
HermesNexus Phase 2 - Audit Service
审计日志业务逻辑层
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
from shared.models.audit import (
    AuditLog,
    AuditLogCreateRequest,
    AuditLogQueryParams,
    AuditLogListResponse,
    AuditStats,
    AuditAction,
    AuditCategory,
    EventLevel,
)


class AuditService:
    """审计日志服务"""

    def __init__(self, database=None):
        """
        初始化审计服务

        Args:
            database: 数据库实例（可以是 SQLAlchemy, SQLite 等）
        """
        self.database = database
        self._audit_logs: List[AuditLog] = []  # 内存存储（Phase 2 MVP）
        self._index_by_task: Dict[str, List[str]] = {}  # 任务ID索引
        self._index_by_node: Dict[str, List[str]] = {}  # 节点ID索引
        self._index_by_asset: Dict[str, List[str]] = {}  # 资产ID索引

    def log_action(self, request: AuditLogCreateRequest) -> AuditLog:
        """
        记录审计日志

        Args:
            request: 审计日志创建请求

        Returns:
            创建的审计日志
        """
        # 生成审计ID
        audit_id = f"audit-{uuid.uuid4().hex[:8]}"

        # 创建审计日志对象
        audit_log = AuditLog(
            audit_id=audit_id,
            action=request.action,
            category=request.category,
            level=request.level,
            actor=request.actor,
            actor_type=request.actor_type,
            target_type=request.target_type,
            target_id=request.target_id,
            related_task_id=request.related_task_id,
            related_node_id=request.related_node_id,
            related_asset_id=request.related_asset_id,
            details=request.details or {},
            message=request.message,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            request_id=request.request_id,
            timestamp=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )

        # 保存审计日志
        self._audit_logs.append(audit_log)

        # 更新索引
        if request.related_task_id:
            if request.related_task_id not in self._index_by_task:
                self._index_by_task[request.related_task_id] = []
            self._index_by_task[request.related_task_id].append(audit_id)

        if request.related_node_id:
            if request.related_node_id not in self._index_by_node:
                self._index_by_node[request.related_node_id] = []
            self._index_by_node[request.related_node_id].append(audit_id)

        if request.related_asset_id:
            if request.related_asset_id not in self._index_by_asset:
                self._index_by_asset[request.related_asset_id] = []
            self._index_by_asset[request.related_asset_id].append(audit_id)

        return audit_log

    def query_logs(self, params: AuditLogQueryParams) -> AuditLogListResponse:
        """
        查询审计日志

        Args:
            params: 查询参数

        Returns:
            审计日志列表响应
        """
        # 获取所有审计日志
        logs = list(self._audit_logs)

        # 应用过滤
        if params.action:
            logs = [log for log in logs if log.action == params.action]

        if params.category:
            logs = [log for log in logs if log.category == params.category]

        if params.level:
            logs = [log for log in logs if log.level == params.level]

        if params.actor:
            logs = [log for log in logs if log.actor == params.actor]

        if params.target_type:
            logs = [log for log in logs if log.target_type == params.target_type]

        if params.target_id:
            logs = [log for log in logs if log.target_id == params.target_id]

        if params.related_task_id:
            logs = [
                log for log in logs if log.related_task_id == params.related_task_id
            ]

        if params.related_node_id:
            logs = [
                log for log in logs if log.related_node_id == params.related_node_id
            ]

        if params.related_asset_id:
            logs = [
                log for log in logs if log.related_asset_id == params.related_asset_id
            ]

        if params.search:
            search_lower = params.search.lower()
            logs = [
                log
                for log in logs
                if search_lower in log.message.lower()
                or any(search_lower in str(v).lower() for v in log.details.values())
            ]

        if params.start_time:
            logs = [log for log in logs if log.timestamp >= params.start_time]

        if params.end_time:
            logs = [log for log in logs if log.timestamp <= params.end_time]

        # 排序
        reverse = params.sort_order == "desc"
        if hasattr(AuditLog, params.sort_by):
            logs.sort(key=lambda log: getattr(log, params.sort_by), reverse=reverse)

        # 分页
        total = len(logs)
        start = (params.page - 1) * params.page_size
        end = start + params.page_size
        paged_logs = logs[start:end]

        total_pages = (total + params.page_size - 1) // params.page_size

        return AuditLogListResponse(
            total=total,
            audit_logs=paged_logs,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    def get_logs_by_task(self, task_id: str, limit: int = 100) -> List[AuditLog]:
        """
        获取任务相关的审计日志

        Args:
            task_id: 任务ID
            limit: 最大返回数量

        Returns:
            审计日志列表
        """
        audit_ids = self._index_by_task.get(task_id, [])
        logs = [log for log in self._audit_logs if log.audit_id in audit_ids]

        # 按时间排序
        logs.sort(key=lambda log: log.timestamp, reverse=True)

        return logs[:limit]

    def get_logs_by_node(self, node_id: str, limit: int = 100) -> List[AuditLog]:
        """
        获取节点相关的审计日志

        Args:
            node_id: 节点ID
            limit: 最大返回数量

        Returns:
            审计日志列表
        """
        audit_ids = self._index_by_node.get(node_id, [])
        logs = [log for log in self._audit_logs if log.audit_id in audit_ids]

        # 按时间排序
        logs.sort(key=lambda log: log.timestamp, reverse=True)

        return logs[:limit]

    def get_logs_by_asset(self, asset_id: str, limit: int = 100) -> List[AuditLog]:
        """
        获取资产相关的审计日志

        Args:
            asset_id: 资产ID
            limit: 最大返回数量

        Returns:
            审计日志列表
        """
        audit_ids = self._index_by_asset.get(asset_id, [])
        logs = [log for log in self._audit_logs if log.audit_id in audit_ids]

        # 按时间排序
        logs.sort(key=lambda log: log.timestamp, reverse=True)

        return logs[:limit]

    def get_audit_stats(self) -> AuditStats:
        """
        获取审计统计信息

        Returns:
            审计统计信息
        """
        logs = self._audit_logs
        now = datetime.utcnow()

        # 按分类统计
        by_category: Dict[str, int] = {}
        for category in AuditCategory:
            count = sum(1 for log in logs if log.category == category)
            by_category[category.value] = count

        # 按动作统计
        by_action: Dict[str, int] = {}
        for action in AuditAction:
            count = sum(1 for log in logs if log.action == action)
            if count > 0:  # 只包含有记录的动作
                by_action[action.value] = count

        # 按级别统计
        by_level: Dict[str, int] = {}
        for level in EventLevel:
            count = sum(1 for log in logs if log.level == level)
            by_level[level.value] = count

        # 时间范围统计
        events_last_hour = sum(
            1 for log in logs if log.timestamp >= now - timedelta(hours=1)
        )
        events_last_day = sum(
            1 for log in logs if log.timestamp >= now - timedelta(days=1)
        )
        events_last_week = sum(
            1 for log in logs if log.timestamp >= now - timedelta(weeks=1)
        )

        # 错误统计
        error_events = sum(
            1 for log in logs if log.level in [EventLevel.ERROR, EventLevel.CRITICAL]
        )
        critical_events = sum(1 for log in logs if log.level == EventLevel.CRITICAL)

        return AuditStats(
            total_events=len(logs),
            by_category=by_category,
            by_action=by_action,
            by_level=by_level,
            events_last_hour=events_last_hour,
            events_last_day=events_last_day,
            events_last_week=events_last_week,
            error_events=error_events,
            critical_events=critical_events,
        )

    def export_logs(self, params: AuditLogExportRequest) -> str:
        """
        导出审计日志

        Args:
            params: 导出请求

        Returns:
            导出的内容
        """
        # 构建查询参数
        query_params = AuditLogQueryParams(
            start_time=params.start_time,
            end_time=params.end_time,
            category=params.category,
            level=params.level,
            page=1,
            page_size=params.limit,
            sort_by="timestamp",
            sort_order="desc",
        )

        # 查询日志
        result = self.query_logs(query_params)
        logs = result.audit_logs

        # 根据格式导出
        if params.format == "json":
            import json

            return json.dumps([log.dict() for log in logs], indent=2, default=str)
        elif params.format == "csv":
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # 写入标题行
            writer.writerow(
                [
                    "审计ID",
                    "动作",
                    "分类",
                    "级别",
                    "操作者",
                    "目标类型",
                    "目标ID",
                    "关联任务",
                    "关联节点",
                    "关联资产",
                    "消息",
                    "时间戳",
                ]
            )

            # 写入数据行
            for log in logs:
                writer.writerow(
                    [
                        log.audit_id,
                        log.action.value,
                        log.category.value,
                        log.level.value,
                        log.actor,
                        log.target_type,
                        log.target_id or "",
                        log.related_task_id or "",
                        log.related_node_id or "",
                        log.related_asset_id or "",
                        log.message,
                        log.timestamp.isoformat(),
                    ]
                )

            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {params.format}")


# 全局服务实例（Phase 2 MVP 使用内存存储）
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """获取全局审计服务实例"""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service


# 便捷函数：记录常用事件
def log_task_created(
    task_id: str, task_name: str, actor: str, details: Dict[str, Any] = None
):
    """记录任务创建事件"""
    service = get_audit_service()
    return service.log_action(
        AuditLogCreateRequest(
            action=AuditAction.TASK_CREATED,
            category=AuditCategory.TASK,
            level=EventLevel.INFO,
            actor=actor,
            target_type="task",
            target_id=task_id,
            related_task_id=task_id,
            message=f"创建任务: {task_name}",
            details=details or {},
        )
    )


def log_task_succeeded(
    task_id: str,
    task_name: str,
    node_id: str,
    actor: str,
    details: Dict[str, Any] = None,
):
    """记录任务成功事件"""
    service = get_audit_service()
    return service.log_action(
        AuditLogCreateRequest(
            action=AuditAction.TASK_SUCCEEDED,
            category=AuditCategory.TASK,
            level=EventLevel.INFO,
            actor=actor,
            actor_type="node",
            target_type="task",
            target_id=task_id,
            related_task_id=task_id,
            related_node_id=node_id,
            message=f"任务执行成功: {task_name}",
            details=details or {},
        )
    )


def log_task_failed(
    task_id: str,
    task_name: str,
    node_id: str,
    error_message: str,
    actor: str,
    details: Dict[str, Any] = None,
):
    """记录任务失败事件"""
    service = get_audit_service()
    return service.log_action(
        AuditLogCreateRequest(
            action=AuditAction.TASK_FAILED,
            category=AuditCategory.TASK,
            level=EventLevel.ERROR,
            actor=actor,
            actor_type="node",
            target_type="task",
            target_id=task_id,
            related_task_id=task_id,
            related_node_id=node_id,
            message=f"任务执行失败: {task_name}",
            details={"error_message": error_message, **(details or {})},
        )
    )


def log_node_online(
    node_id: str, node_name: str, actor: str, details: Dict[str, Any] = None
):
    """记录节点上线事件"""
    service = get_audit_service()
    return service.log_action(
        AuditLogCreateRequest(
            action=AuditAction.NODE_ONLINE,
            category=AuditCategory.NODE,
            level=EventLevel.INFO,
            actor=actor,
            actor_type="node",
            target_type="node",
            target_id=node_id,
            related_node_id=node_id,
            message=f"节点上线: {node_name}",
            details=details or {},
        )
    )


def log_node_offline(
    node_id: str, node_name: str, actor: str, details: Dict[str, Any] = None
):
    """记录节点离线事件"""
    service = get_audit_service()
    return service.log_action(
        AuditLogCreateRequest(
            action=AuditAction.NODE_OFFLINE,
            category=AuditCategory.NODE,
            level=EventLevel.WARNING,
            actor=actor,
            actor_type="system",
            target_type="node",
            target_id=node_id,
            related_node_id=node_id,
            message=f"节点离线: {node_name}",
            details=details or {},
        )
    )
