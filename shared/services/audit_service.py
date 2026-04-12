"""
HermesNexus Phase 2 - Audit Service (Database Version)
审计日志业务逻辑层 - 数据库版本
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import uuid
import math
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
            created_at=datetime.now(timezone.utc),
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
                self._index_by_asset.setdefault(audit_log.target_id, []).append(
                    audit_id
                )
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

    def list_audit_logs(
        self,
        params: AuditLogQueryParams = None,
        limit: int = None,
        filters: Dict[str, Any] = None,
        **kwargs,
    ):
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
                order_by=(
                    f"-{params.sort_by}"
                    if params.sort_order == "desc"
                    else params.sort_by
                ),
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
            category_stats = {
                category.value: self.audit_dao.count({"category": category})
                for category in AuditCategory
            }
            level_stats = {
                level.value: self.audit_dao.count({"level": level})
                for level in EventLevel
            }
            action_stats = {
                action.value: self.audit_dao.count({"action": action})
                for action in AuditAction
            }
        else:
            audit_logs = self._audit_logs
            total = len(audit_logs)
            category_stats = {}
            level_stats = {}
            action_stats = {}
            for log in audit_logs:
                category_stats[log.category.value] = (
                    category_stats.get(log.category.value, 0) + 1
                )
                level_stats[log.level.value] = level_stats.get(log.level.value, 0) + 1
                action_stats[log.action.value] = (
                    action_stats.get(log.action.value, 0) + 1
                )

        last_hour = datetime.now(timezone.utc) - timedelta(hours=1)
        last_day = datetime.now(timezone.utc) - timedelta(days=1)
        last_week = datetime.now(timezone.utc) - timedelta(days=7)
        if self.audit_dao:
            events_last_hour = self.audit_dao.count({"start_time": last_hour})
            events_last_day = self.audit_dao.count({"start_time": last_day})
            events_last_week = self.audit_dao.count({"start_time": last_week})
            error_events = self.audit_dao.count({"level": EventLevel.ERROR})
            critical_events = self.audit_dao.count({"level": EventLevel.CRITICAL})
        else:
            events_last_hour = sum(
                1 for log in audit_logs if log.created_at >= last_hour
            )
            events_last_day = sum(1 for log in audit_logs if log.created_at >= last_day)
            events_last_week = sum(
                1 for log in audit_logs if log.created_at >= last_week
            )
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
            for log in sorted(
                self._audit_logs, key=lambda item: item.created_at, reverse=True
            ):
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
            for log in sorted(
                self._audit_logs, key=lambda item: item.created_at, reverse=True
            ):
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
            for log in sorted(
                self._audit_logs, key=lambda item: item.created_at, reverse=True
            ):
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
        created_at=datetime.now(timezone.utc),
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
        created_at=datetime.now(timezone.utc),
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
        created_at=datetime.now(timezone.utc),
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


# ===== Phase 3: 统一安全审计扩展 =====


class SecurityAuditService:
    """安全审计服务 - Phase 3扩展"""

    def __init__(self, base_audit_service=None):
        """
        初始化安全审计服务

        Args:
            base_audit_service: 基础审计服务实例
        """
        self.base_audit_service = base_audit_service

        # 安全审计日志存储
        self._security_audit_logs = {}
        self._security_events = {}

        # 审计统计缓存
        self._statistics_cache = None
        self._cache_expiry = None

    def create_security_audit_log(self, **kwargs) -> "SecurityAuditLog":
        """
        创建安全审计日志

        这个方法提供了一个简化的接口来创建安全审计日志
        """
        from shared.models.audit import SecurityAuditLog

        audit_id = f"audit-{uuid.uuid4().hex[:8]}"
        kwargs["audit_id"] = audit_id

        # 确保timestamp存在
        if "timestamp" not in kwargs:
            kwargs["timestamp"] = datetime.now(timezone.utc)

        # 创建安全审计日志
        audit_log = SecurityAuditLog(**kwargs)
        self._security_audit_logs[audit_id] = audit_log

        # 同时记录到基础审计服务
        if self.base_audit_service:
            try:
                # 转换为Phase 2的AuditLog格式
                base_request = self._convert_to_base_audit_log(audit_log)
                self.base_audit_service.log_action(base_request)
            except Exception as e:
                # 如果转换失败，只记录错误，不影响主流程
                print(f"Warning: Failed to log to base audit service: {e}")

        return audit_log

    def _convert_to_base_audit_log(self, security_audit_log):
        """将安全审计日志转换为Phase 2的审计日志格式"""
        from shared.models.audit import AuditLogCreateRequest

        return AuditLogCreateRequest(
            action=security_audit_log.action,
            category=security_audit_log.category,
            level=security_audit_log.level,
            actor=security_audit_log.actor,
            actor_type=security_audit_log.actor_type.value,
            target_type=security_audit_log.target_type,
            target_id=security_audit_log.target_id,
            related_task_id=security_audit_log.related_task_id,
            related_node_id=security_audit_log.related_node_id,
            related_asset_id=security_audit_log.related_asset_id,
            details=security_audit_log.details,
            message=security_audit_log.message,
            ip_address=security_audit_log.ip_address,
            user_agent=security_audit_log.user_agent,
            request_id=security_audit_log.request_id,
        )

    def get_security_audit_log(self, audit_id: str) -> Optional["SecurityAuditLog"]:
        """获取安全审计日志"""
        return self._security_audit_logs.get(audit_id)

    def query_security_audit_logs(self, **filters) -> List["SecurityAuditLog"]:
        """查询安全审计日志"""
        logs = list(self._security_audit_logs.values())

        # 应用过滤条件
        if "event_types" in filters and filters["event_types"]:
            logs = [
                log for log in logs if log.security_event_type in filters["event_types"]
            ]
        if "actor_types" in filters and filters["actor_types"]:
            logs = [log for log in logs if log.actor_type in filters["actor_types"]]
        if "result" in filters and filters["result"]:
            logs = [log for log in logs if log.result == filters["result"]]
        if "risk_level" in filters and filters["risk_level"]:
            logs = [log for log in logs if log.risk_level == filters["risk_level"]]
        if "actor_id" in filters and filters["actor_id"]:
            logs = [log for log in logs if log.actor == filters["actor_id"]]
        if "target_id" in filters and filters["target_id"]:
            logs = [log for log in logs if log.target_id == filters["target_id"]]
        if "correlation_id" in filters and filters["correlation_id"]:
            logs = [
                log for log in logs if log.correlation_id == filters["correlation_id"]
            ]

        # 时间范围过滤
        if "start_time" in filters and filters["start_time"]:
            logs = [log for log in logs if log.timestamp >= filters["start_time"]]
        if "end_time" in filters and filters["end_time"]:
            logs = [log for log in logs if log.timestamp <= filters["end_time"]]

        # 关键词搜索
        if "keyword" in filters and filters["keyword"]:
            keyword = filters["keyword"].lower()
            logs = [
                log
                for log in logs
                if keyword in log.message.lower() or keyword in str(log.details).lower()
            ]

        # 排序和分页
        logs.sort(key=lambda x: x.timestamp, reverse=True)
        limit = filters.get("limit", 100)
        return logs[:limit]

    def create_security_event(self, **kwargs) -> "SecurityEvent":
        """创建安全事件"""
        from shared.models.audit import SecurityEvent

        event_id = f"security-{uuid.uuid4().hex[:8]}"
        kwargs["event_id"] = event_id

        if "timestamp" not in kwargs:
            kwargs["timestamp"] = datetime.now(timezone.utc)

        security_event = SecurityEvent(**kwargs)
        self._security_events[event_id] = security_event

        return security_event

    def get_security_event(self, event_id: str) -> Optional["SecurityEvent"]:
        """获取安全事件"""
        return self._security_events.get(event_id)

    def list_security_events(self, **filters) -> List["SecurityEvent"]:
        """列出安全事件"""
        events = list(self._security_events.values())

        # 应用过滤条件
        if "severity" in filters and filters["severity"]:
            events = [e for e in events if e.severity == filters["severity"]]
        if "start_time" in filters and filters["start_time"]:
            events = [e for e in events if e.timestamp >= filters["start_time"]]
        if "end_time" in filters and filters["end_time"]:
            events = [e for e in events if e.timestamp <= filters["end_time"]]

        # 排序
        events.sort(key=lambda x: x.timestamp, reverse=True)

        limit = filters.get("limit", 100)
        return events[:limit]

    def get_statistics(self) -> "AuditStatisticsExtended":
        """获取审计统计信息"""
        # 检查缓存
        if (
            self._statistics_cache
            and self._cache_expiry
            and datetime.now(timezone.utc) < self._cache_expiry
        ):
            return self._statistics_cache

        from shared.models.audit import AuditStatisticsExtended

        logs = list(self._security_audit_logs.values())

        # 总体统计
        total_events = len(logs)

        # 按类型统计
        events_by_type = {}
        for log in logs:
            if log.security_event_type:
                type_str = log.security_event_type.value
                events_by_type[type_str] = events_by_type.get(type_str, 0) + 1

        # 按结果统计
        events_by_result = {}
        for log in logs:
            result_str = log.result.value
            events_by_result[result_str] = events_by_result.get(result_str, 0) + 1

        # 按风险等级统计
        events_by_risk_level = {}
        for log in logs:
            if log.risk_level:
                risk_str = log.risk_level.value
                events_by_risk_level[risk_str] = (
                    events_by_risk_level.get(risk_str, 0) + 1
                )

        # 时间统计
        events_by_hour = {}
        events_by_day = {}
        for log in logs:
            hour_key = log.timestamp.strftime("%Y-%m-%d %H:00")
            day_key = log.timestamp.strftime("%Y-%m-%d")
            events_by_hour[hour_key] = events_by_hour.get(hour_key, 0) + 1
            events_by_day[day_key] = events_by_day.get(day_key, 0) + 1

        # 操作者统计
        actor_counts = {}
        for log in logs:
            actor_counts[log.actor] = actor_counts.get(log.actor, 0) + 1

        top_actors = [
            {"actor": actor, "count": count}
            for actor, count in sorted(
                actor_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]
        ]

        # 操作者类型统计
        actors_by_type = {}
        for log in logs:
            type_str = log.actor_type.value
            actors_by_type[type_str] = actors_by_type.get(type_str, 0) + 1

        # 安全统计
        failed_auth_count = sum(
            1
            for log in logs
            if log.action
            and log.action.value in ["auth_denied"]
            and log.result.value == "failure"
        )

        permission_denied_count = sum(
            1
            for log in logs
            if log.security_event_type
            and log.security_event_type.value == "permission_denied"
        )

        security_events_count = len(self._security_events)

        # 性能统计
        durations = [log.duration_ms for log in logs if log.duration_ms is not None]
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
        else:
            avg_duration = 0.0
            max_duration = 0.0

        statistics = AuditStatisticsExtended(
            total_events=total_events,
            events_by_type=events_by_type,
            events_by_result=events_by_result,
            events_by_risk_level=events_by_risk_level,
            events_by_hour=events_by_hour,
            events_by_day=events_by_day,
            top_actors=top_actors,
            actors_by_type=actors_by_type,
            failed_auth_count=failed_auth_count,
            permission_denied_count=permission_denied_count,
            security_events_count=security_events_count,
            avg_duration_ms=avg_duration,
            max_duration_ms=max_duration,
        )

        # 缓存统计结果（5分钟有效期）
        self._statistics_cache = statistics
        self._cache_expiry = datetime.now(timezone.utc) + timedelta(minutes=5)

        return statistics


# 全局安全审计服务实例
_global_security_audit_service: Optional[SecurityAuditService] = None


def get_security_audit_service() -> SecurityAuditService:
    """获取全局安全审计服务实例"""
    global _global_security_audit_service
    if _global_security_audit_service is None:
        # 使用现有的审计服务作为基础
        base_service = get_audit_service()
        _global_security_audit_service = SecurityAuditService(base_service)
    return _global_security_audit_service
