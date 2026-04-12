"""
HermesNexus Phase 2 - Audit Service (Database Version)
审计日志业务逻辑层 - 数据库版本
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import math
from shared.models.audit import (
    AuditLog, AuditLogCreateRequest,
    AuditLogQueryParams, AuditLogListResponse, AuditStats,
    AuditAction, AuditCategory, EventLevel
)
from shared.dao.audit_dao import AuditDAO


class AuditService:
    """审计日志服务 - 数据库版本"""

    def __init__(self, database=None):
        """
        初始化审计服务

        Args:
            database: 数据库实例
        """
        self.database = database

        # 如果有数据库，使用DAO；否则使用内存存储
        if database:
            self.audit_dao = AuditDAO(database)
            self._audit_logs: Optional[List[AuditLog]] = None
            self._index_by_task: Optional[Dict[str, List[str]]] = None
            self._index_by_node: Optional[Dict[str, List[str]]] = None
            self._index_by_asset: Optional[Dict[str, List[str]]] = None
        else:
            self.audit_dao = None
            self._audit_logs: List[AuditLog] = []
            self._index_by_task: Dict[str, List[str]] = {}
            self._index_by_node: Dict[str, List[str]] = {}
            self._index_by_asset: Dict[str, List[str]] = {}

    def log_action(self, request: AuditLogCreateRequest) -> AuditLog:
        """
        记录审计日志

        Args:
            request: 审计日志创建请求

        Returns:
            创建的审计日志
        """
        audit_id = f"audit-{uuid.uuid4().hex[:8]}"

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
            created_at=datetime.utcnow(),
        )

        if self.audit_dao:
            saved = self.audit_dao.insert(audit_log)
        else:
            self._audit_logs.append(audit_log)
            if audit_log.target_type == "task" and audit_log.target_id:
                self._index_by_task.setdefault(audit_log.target_id, []).append(audit_id)
            elif audit_log.target_type == "node" and audit_log.target_id:
                self._index_by_node.setdefault(audit_log.target_id, []).append(audit_id)
            elif audit_log.target_type == "asset" and audit_log.target_id:
                self._index_by_asset.setdefault(audit_log.target_id, []).append(audit_id)
            saved = audit_log

        return saved

    def get_audit_log(self, audit_id: str) -> Optional[AuditLog]:
        """
        获取审计日志详情

        Args:
            audit_id: 审计日志ID

        Returns:
            审计日志对象，如果不存在则返回None
        """
        if self.audit_dao:
            return self.audit_dao.select_by_id(audit_id)
        else:
            for log in self._audit_logs:
                if log.audit_id == audit_id:
                    return log
            return None

    def list_audit_logs(self, params: AuditLogQueryParams = None, limit: int = None, filters: Dict[str, Any] = None, **kwargs):
        """
        查询审计日志列表

        Args:
            params: 查询参数；如果不提供则直接返回日志列表

        Returns:
            审计日志列表或列表响应
        """
        if params is None:
            if self.audit_dao:
                logs = self.audit_dao.list(filters=filters or {}, limit=limit)
            else:
                logs = list(self._audit_logs)
                if filters:
                    # 兼容简单字典过滤
                    for key, value in filters.items():
                        logs = [log for log in logs if getattr(log, key, None) == value]
                if limit is not None:
                    logs = logs[:limit]
            return logs

        filters = {}
        if params.action:
            filters["action"] = params.action
        if params.category:
            filters["category"] = params.category
        if params.level:
            filters["level"] = params.level
        if params.actor:
            filters["actor"] = params.actor
        if params.target_type:
            filters["target_type"] = params.target_type
        if params.target_id:
            filters["target_id"] = params.target_id
        if params.related_task_id:
            filters["related_task_id"] = params.related_task_id
        if params.related_node_id:
            filters["related_node_id"] = params.related_node_id
        if params.related_asset_id:
            filters["related_asset_id"] = params.related_asset_id
        if params.start_time:
            filters["start_time"] = params.start_time
        if params.end_time:
            filters["end_time"] = params.end_time
        if params.search:
            filters["search"] = params.search

        if self.audit_dao:
            audit_logs = self.audit_dao.list(
                filters=filters,
                limit=params.page_size,
                offset=(params.page - 1) * params.page_size,
                order_by=(f"-{params.sort_by}" if params.sort_order == "desc" else params.sort_by)
            )
            total = self.audit_dao.count(filters)
        else:
            audit_logs = self._audit_logs
            total = len(audit_logs)

        total_pages = math.ceil(total / params.page_size) if params.page_size else 0
        return AuditLogListResponse(
            audit_logs=audit_logs,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    def get_audit_stats(self) -> AuditStats:
        """
        获取审计统计信息

        Returns:
            审计统计信息
        """
        if self.audit_dao:
            total = self.audit_dao.count({})
            category_stats = {category.value: self.audit_dao.count({"category": category}) for category in AuditCategory}
            level_stats = {level.value: self.audit_dao.count({"level": level}) for level in EventLevel}
            action_stats = {action.value: self.audit_dao.count({"action": action}) for action in AuditAction}
        else:
            audit_logs = self._audit_logs
            total = len(audit_logs)
            category_stats = {}
            level_stats = {}
            action_stats = {}
            for log in audit_logs:
                category_stats[log.category.value] = category_stats.get(log.category.value, 0) + 1
                level_stats[log.level.value] = level_stats.get(log.level.value, 0) + 1
                action_stats[log.action.value] = action_stats.get(log.action.value, 0) + 1

        last_hour = datetime.utcnow() - timedelta(hours=1)
        last_day = datetime.utcnow() - timedelta(days=1)
        last_week = datetime.utcnow() - timedelta(days=7)
        if self.audit_dao:
            events_last_hour = self.audit_dao.count({"start_time": last_hour})
            events_last_day = self.audit_dao.count({"start_time": last_day})
            events_last_week = self.audit_dao.count({"start_time": last_week})
            error_events = self.audit_dao.count({"level": EventLevel.ERROR})
            critical_events = self.audit_dao.count({"level": EventLevel.CRITICAL})
        else:
            events_last_hour = sum(1 for log in audit_logs if log.created_at >= last_hour)
            events_last_day = sum(1 for log in audit_logs if log.created_at >= last_day)
            events_last_week = sum(1 for log in audit_logs if log.created_at >= last_week)
            error_events = level_stats.get(EventLevel.ERROR.value, 0)
            critical_events = level_stats.get(EventLevel.CRITICAL.value, 0)

        return AuditStats(
            total_events=total,
            by_category=category_stats,
            by_action=action_stats,
            by_level=level_stats,
            events_last_hour=events_last_hour,
            events_last_day=events_last_day,
            events_last_week=events_last_week,
            error_events=error_events,
            critical_events=critical_events,
        )

    def query_by_task(self, task_id: str, limit: int = None) -> List[AuditLog]:
        """
        查询特定任务的审计日志

        Args:
            task_id: 任务ID
            limit: 返回数量限制

        Returns:
            审计日志列表
        """
        if self.audit_dao:
            return self.audit_dao.query_by_task(task_id, limit)
        else:
            audits = []
            for log in sorted(self._audit_logs, key=lambda item: item.created_at, reverse=True):
                meta = log.details or {}
                if (
                    (log.target_type == "task" and log.target_id == task_id)
                    or log.related_task_id == task_id
                    or meta.get("related_task_id") == task_id
                    or meta.get("task_id") == task_id
                ):
                    audits.append(log)
            return audits[:limit] if limit else audits

    def query_by_node(self, node_id: str, limit: int = None) -> List[AuditLog]:
        """
        查询特定节点的审计日志

        Args:
            node_id: 节点ID
            limit: 返回数量限制

        Returns:
            审计日志列表
        """
        if self.audit_dao:
            return self.audit_dao.query_by_node(node_id, limit)
        else:
            audits = []
            for log in sorted(self._audit_logs, key=lambda item: item.created_at, reverse=True):
                meta = log.details or {}
                if (
                    (log.target_type == "node" and log.target_id == node_id)
                    or log.related_node_id == node_id
                    or meta.get("related_node_id") == node_id
                    or meta.get("node_id") == node_id
                ):
                    audits.append(log)
            return audits[:limit] if limit else audits

    def query_by_asset(self, asset_id: str, limit: int = None) -> List[AuditLog]:
        """
        查询特定资产的审计日志

        Args:
            asset_id: 资产ID
            limit: 返回数量限制

        Returns:
            审计日志列表
        """
        if self.audit_dao:
            return self.audit_dao.query_by_asset(asset_id, limit)
        else:
            audits = []
            for log in sorted(self._audit_logs, key=lambda item: item.created_at, reverse=True):
                meta = log.details or {}
                if (
                    (log.target_type == "asset" and log.target_id == asset_id)
                    or log.related_asset_id == asset_id
                    or meta.get("related_asset_id") == asset_id
                    or meta.get("target_asset_id") == asset_id
                    or meta.get("asset_id") == asset_id
                ):
                    audits.append(log)
            return audits[:limit] if limit else audits


# 便捷函数
def log_task_created(task_id: str, actor: str, task_data: Dict[str, Any]) -> AuditLog:
    """记录任务创建日志"""
    return AuditLog(
        audit_id=f"audit-{uuid.uuid4().hex[:8]}",
        action=AuditAction.TASK_CREATED,
        category=AuditCategory.TASK,
        level=EventLevel.INFO,
        actor=actor,
        target_type="task",
        target_id=task_id,
        message=f"Task created: {task_data.get('name', task_id)}",
        details=task_data,
        created_at=datetime.utcnow()
    )

def log_task_succeeded(task_id: str, actor: str, result: Dict[str, Any]) -> AuditLog:
    """记录任务成功日志"""
    return AuditLog(
        audit_id=f"audit-{uuid.uuid4().hex[:8]}",
        action=AuditAction.TASK_SUCCEEDED,
        category=AuditCategory.TASK,
        level=EventLevel.INFO,
        actor=actor,
        target_type="task",
        target_id=task_id,
        message=f"Task succeeded: {task_id}",
        details=result,
        created_at=datetime.utcnow()
    )

def log_task_failed(task_id: str, actor: str, error: str) -> AuditLog:
    """记录任务失败日志"""
    return AuditLog(
        audit_id=f"audit-{uuid.uuid4().hex[:8]}",
        action=AuditAction.TASK_FAILED,
        category=AuditCategory.TASK,
        level=EventLevel.ERROR,
        actor=actor,
        target_type="task",
        target_id=task_id,
        message=f"Task failed: {task_id}",
        details={"error": error},
        created_at=datetime.utcnow()
    )


# 全局服务实例（用于简单的单例模式）
_audit_service_instance = None


def get_audit_service(database=None):
    """
    获取审计服务实例（单例模式）

    Args:
        database: 数据库实例（首次调用时提供）

    Returns:
        AuditService 实例
    """
    global _audit_service_instance
    if _audit_service_instance is None:
        _audit_service_instance = AuditService(database=database)
    elif database is not None and _audit_service_instance.database is None:
        # 如果首次创建时没有数据库，但后续提供了数据库，则重新创建
        _audit_service_instance = AuditService(database=database)
    return _audit_service_instance
