"""
HermesNexus v1.2 - 节点列表服务
增强的节点查询和管理服务
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from shared.models.node import NodeIdentity, NodeStatus, NodeType
from shared.models.node_list import (
    NodeListRequest,
    NodeListResponse,
    NodeStatusSummary,
    NodeHeartbeatStats,
    NodeTaskSummary,
    NodeAuditSummary,
    BatchNodeRequest,
    BatchNodeResponse,
    NodeSortField,
    SortOrder
)


class NodeListService:
    """节点列表服务"""

    def __init__(self, database=None):
        """
        初始化节点列表服务

        Args:
            database: 数据库实例（可选，如果不提供则使用内存实现）
        """
        self.database = database
        # 如果没有提供数据库，创建一个简单的内存存储
        if self.database is None:
            self._nodes_storage = {}
        else:
            self._nodes_storage = None

    def get_node_list(self, request: NodeListRequest) -> NodeListResponse:
        """
        获取节点列表

        Args:
            request: 节点列表查询请求

        Returns:
            节点列表响应
        """
        # 获取所有节点
        all_nodes = self._get_all_nodes()

        # 应用筛选条件
        filtered_nodes = self._apply_filters(all_nodes, request)

        # 应用排序
        sorted_nodes = self._apply_sort(filtered_nodes, request)

        # 计算总数和分页
        total = len(sorted_nodes)
        total_pages = (total + request.page_size - 1) // request.page_size

        # 应用分页
        start_idx = (request.page - 1) * request.page_size
        end_idx = start_idx + request.page_size
        paginated_nodes = sorted_nodes[start_idx:end_idx]

        # 增强节点数据
        enhanced_nodes = []
        for node_dict in paginated_nodes:
            enhanced_node = self._enhance_node_data(
                node_dict,
                request.include_heartbeat_stats,
                request.include_task_summary,
                request.include_audit_summary
            )
            enhanced_nodes.append(enhanced_node)

        # 获取汇总统计
        status_summary = self._get_status_summary(all_nodes)
        health_summary = self._get_health_summary(enhanced_nodes)

        return NodeListResponse(
            nodes=enhanced_nodes,
            total=total,
            page=request.page,
            page_size=request.page_size,
            total_pages=total_pages,
            has_next=request.page < total_pages,
            has_prev=request.page > 1,
            status_summary=status_summary,
            health_summary=health_summary
        )

    def get_nodes_batch(self, request: BatchNodeRequest) -> BatchNodeResponse:
        """
        批量获取节点详情

        Args:
            request: 批量节点查询请求

        Returns:
            批量节点查询响应
        """
        all_nodes = self._get_all_nodes()
        nodes_dict = {}
        missing_nodes = []

        for node_id in request.node_ids:
            # 查找节点
            node_found = False
            for node_dict in all_nodes:
                if node_dict.get("node_id") == node_id:
                    enhanced_node = self._enhance_node_data(
                        node_dict,
                        request.include_heartbeat_stats,
                        request.include_task_summary,
                        request.include_audit_summary
                    )
                    nodes_dict[node_id] = enhanced_node
                    node_found = True
                    break

            if not node_found:
                missing_nodes.append(node_id)

        return BatchNodeResponse(
            nodes=nodes_dict,
            found_nodes=len(nodes_dict),
            missing_nodes=missing_nodes
        )

    def _get_all_nodes(self) -> List[Dict[str, Any]]:
        """获取所有节点"""
        if self.database:
            # 使用数据库实例
            return self.database.list_nodes()
        else:
            # 使用内存存储
            return list(self._nodes_storage.values())

    def _apply_filters(self, nodes: List[Dict[str, Any]], request: NodeListRequest) -> List[Dict[str, Any]]:
        """应用筛选条件"""
        filtered = nodes

        # 状态筛选
        if request.status:
            filtered = [node for node in filtered if node.get("status") in request.status]

        # 节点类型筛选
        if request.node_type:
            filtered = [node for node in filtered if node.get("node_type") == request.node_type]

        # 标签筛选
        if request.tags:
            filtered = [node for node in filtered if
                       any(tag in (node.get("tags") or []) for tag in request.tags)]

        # 位置筛选
        if request.location:
            filtered = [node for node in filtered if node.get("location") == request.location]

        # 搜索筛选
        if request.search:
            search_lower = request.search.lower()
            filtered = [node for node in filtered if
                       search_lower in (node.get("node_name") or "").lower() or
                       search_lower in (node.get("node_id") or "").lower()]

        # 时间范围筛选
        if request.heartbeat_after:
            heartbeat_after = datetime.fromisoformat(request.heartbeat_after)
            filtered = [node for node in filtered if
                       node.get("last_heartbeat") and
                       datetime.fromisoformat(node["last_heartbeat"]) >= heartbeat_after]

        if request.heartbeat_before:
            heartbeat_before = datetime.fromisoformat(request.heartbeat_before)
            filtered = [node for node in filtered if
                       node.get("last_heartbeat") and
                       datetime.fromisoformat(node["last_heartbeat"]) <= heartbeat_before]

        return filtered

    def _apply_sort(self, nodes: List[Dict[str, Any]], request: NodeListRequest) -> List[Dict[str, Any]]:
        """应用排序"""
        sort_field = request.sort_by.value
        reverse = request.sort_order == SortOrder.DESC

        # 根据字段排序
        if sort_field == "created_at":
            sorted_nodes = sorted(nodes, key=lambda x: x.get("created_at", ""), reverse=reverse)
        elif sort_field == "updated_at":
            sorted_nodes = sorted(nodes, key=lambda x: x.get("updated_at", ""), reverse=reverse)
        elif sort_field == "node_name":
            sorted_nodes = sorted(nodes, key=lambda x: x.get("node_name", ""), reverse=reverse)
        elif sort_field == "last_heartbeat":
            sorted_nodes = sorted(nodes, key=lambda x: x.get("last_heartbeat") or "", reverse=reverse)
        elif sort_field == "status":
            sorted_nodes = sorted(nodes, key=lambda x: x.get("status", ""), reverse=reverse)
        else:
            # 默认按创建时间排序
            sorted_nodes = sorted(nodes, key=lambda x: x.get("created_at", ""), reverse=True)

        return sorted_nodes

    def _enhance_node_data(
        self,
        node_input,
        include_heartbeat_stats: bool = False,
        include_task_summary: bool = False,
        include_audit_summary: bool = False
    ) -> Dict[str, Any]:
        """增强节点数据"""
        # 处理不同类型的输入
        if isinstance(node_input, dict):
            node_dict = node_input.copy()  # 避免修改原始数据
        else:
            # 假设是NodeIdentity对象，转换为字典
            node_dict = node_input.dict()

        # 添加状态摘要
        node_dict["status_summary"] = self._get_status_summary_for_node(node_input).dict()

        # 添加心跳统计
        if include_heartbeat_stats:
            node_dict["heartbeat_stats"] = self._get_heartbeat_stats_for_node(node_input).dict()

        # 添加任务摘要
        if include_task_summary:
            node_dict["task_summary"] = self._get_task_summary_for_node(node_input).dict()

        # 添加审计摘要
        if include_audit_summary:
            node_dict["audit_summary"] = self._get_audit_summary_for_node(node_input).dict()

        return node_dict

    def _get_status_summary_for_node(self, node_input) -> NodeStatusSummary:
        """获取节点状态摘要"""
        now = datetime.now(timezone.utc)
        heartbeat_timeout = timedelta(minutes=5)

        # 处理不同类型的输入
        if isinstance(node_input, dict):
            node_dict = node_input
            status_str = node_dict.get("status", "unknown")
            last_heartbeat_str = node_dict.get("last_heartbeat")
            assigned_tasks = node_dict.get("assigned_tasks") or []
            max_concurrent = node_dict.get("max_concurrent_tasks", 3)
        else:
            # 假设是NodeIdentity对象
            node_dict = node_input.dict()
            status_str = node_input.status.value
            last_heartbeat_str = node_input.last_heartbeat.isoformat() if node_input.last_heartbeat else None
            assigned_tasks = node_input.assigned_tasks or []
            max_concurrent = node_input.max_concurrent_tasks

        # 获取节点状态
        try:
            status = NodeStatus(status_str)
        except ValueError:
            status = NodeStatus.UNREGISTERED

        # 判断是否在线
        is_online = False
        last_heartbeat_age_seconds = None

        if last_heartbeat_str:
            try:
                last_heartbeat = datetime.fromisoformat(last_heartbeat_str)
                if last_heartbeat.tzinfo is None:
                    last_heartbeat = last_heartbeat.replace(tzinfo=timezone.utc)

                time_diff = now - last_heartbeat
                last_heartbeat_age_seconds = int(time_diff.total_seconds())
                is_online = time_diff < heartbeat_timeout
            except (ValueError, TypeError):
                pass

        # 判断是否活跃
        is_active = status == NodeStatus.ACTIVE

        # 判断是否能接受任务
        can_accept_tasks = is_online and is_active and len(assigned_tasks) < max_concurrent

        # 计算健康状态
        health_status = "unknown"
        if is_active and is_online and can_accept_tasks:
            health_status = "healthy"
        elif is_active and is_online:
            health_status = "degraded"
        elif not is_online and is_active:
            health_status = "error"
        elif status == NodeStatus.INACTIVE:
            health_status = "inactive"

        return NodeStatusSummary(
            is_online=is_online,
            is_active=is_active,
            can_accept_tasks=can_accept_tasks,
            health_status=health_status,
            last_heartbeat_age_seconds=last_heartbeat_age_seconds,
            heartbeat_timeout_seconds=int(heartbeat_timeout.total_seconds())
        )

    def _get_task_summary_for_node(self, node_input) -> NodeTaskSummary:
        """获取节点任务摘要"""
        # 处理不同类型的输入
        if isinstance(node_input, dict):
            node_dict = node_input
            assigned_tasks = node_dict.get("assigned_tasks") or []
            max_concurrent = node_dict.get("max_concurrent_tasks", 3)
        else:
            # 假设是NodeIdentity对象
            assigned_tasks = node_input.assigned_tasks or []
            max_concurrent = node_input.max_concurrent_tasks

        if isinstance(assigned_tasks, str):
            assigned_tasks = assigned_tasks.split(",") if assigned_tasks else []

        current_task_load = len(assigned_tasks)

        # 计算任务利用率
        task_utilization_percent = 0.0
        if max_concurrent > 0:
            task_utilization_percent = (current_task_load / max_concurrent) * 100

        return NodeTaskSummary(
            total_tasks=current_task_load,
            running_tasks=current_task_load,
            completed_tasks=0,
            failed_tasks=0,
            current_task_load=current_task_load,
            max_concurrent_tasks=max_concurrent,
            task_utilization_percent=round(task_utilization_percent, 1),
            recent_task_ids=assigned_tasks[-5:] if assigned_tasks else []
        )

    def _get_heartbeat_stats_for_node(self, node_input) -> NodeHeartbeatStats:
        """获取节点心跳统计"""
        # 处理不同类型的输入
        if isinstance(node_input, dict):
            last_heartbeat_str = node_input.get("last_heartbeat")
        else:
            last_heartbeat_str = node_input.last_heartbeat.isoformat() if node_input.last_heartbeat else None

        return NodeHeartbeatStats(
            total_heartbeats=0,
            successful_heartbeats=0,
            failed_heartbeats=0,
            avg_heartbeat_interval_seconds=None,
            last_successful_heartbeat=last_heartbeat_str,
            last_failed_heartbeat=None
        )

    def _get_audit_summary_for_node(self, node_input) -> NodeAuditSummary:
        """获取节点审计摘要"""
        # 处理不同类型的输入
        if isinstance(node_input, dict):
            last_heartbeat_str = node_input.get("last_heartbeat")
        else:
            last_heartbeat_str = node_input.last_heartbeat.isoformat() if node_input.last_heartbeat else None

        return NodeAuditSummary(
            total_audit_logs=0,
            recent_errors=0,
            recent_warnings=0,
            last_error=None,
            last_error_time=None,
            last_audit_log=last_heartbeat_str,
            recent_audit_activities=[]
        )

    def _get_status_summary(self, nodes: List[Dict[str, Any]]) -> Dict[str, int]:
        """获取状态摘要统计"""
        status_count = defaultdict(int)
        for node in nodes:
            status = node.get("status", "unknown")
            status_count[status] += 1

        return dict(status_count)

    def _get_health_summary(self, nodes: List[Dict[str, Any]]) -> Dict[str, int]:
        """获取健康状态摘要统计"""
        health_count = defaultdict(int)

        for node_dict in nodes:
            status_summary = node_dict.get("status_summary")
            if status_summary:
                health_status = status_summary.health_status
                health_count[health_status] += 1

        return dict(health_count)


# 全局服务实例
_node_list_service = None


def get_node_list_service(database=None) -> NodeListService:
    """获取节点列表服务实例"""
    global _node_list_service
    if _node_list_service is None:
        _node_list_service = NodeListService(database)
    return _node_list_service