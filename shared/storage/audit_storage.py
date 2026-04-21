"""
HermesNexus v1.2 - 审计存储服务
支持审计记录的存储、查询和统计
"""

import threading
from typing import Optional, List, Dict, Any
from datetime import datetime
from shared.models.audit_models import (
    BatchOperationAudit,
    AuditQueryRequest,
    AuditStatistics,
    AuditOperationType,
)


class AuditStorage:
    """审计存储服务"""

    def __init__(self):
        """初始化审计存储"""
        self._lock = threading.RLock()
        self._audit_records: Dict[str, BatchOperationAudit] = {}

        # 索引结构
        self._operation_id_index: Dict[str, str] = {}  # operation_id -> audit_id
        self._user_id_index: Dict[str, List[str]] = {}  # user_id -> [audit_ids]
        self._asset_id_index: Dict[str, List[str]] = {}  # asset_id -> [audit_ids]
        self._node_id_index: Dict[str, List[str]] = {}  # node_id -> [audit_ids]
        self._task_id_index: Dict[str, List[str]] = {}  # task_id -> [audit_ids]
        self._error_type_index: Dict[str, List[str]] = {}  # error_type -> [audit_ids]
        self._operation_type_index: Dict[str, List[str]] = {}  # operation_type -> [audit_ids]
        self._timestamp_index: Dict[str, List[str]] = {}  # date -> [audit_ids]

    def save_audit(self, audit: BatchOperationAudit) -> bool:
        """保存审计记录"""
        with self._lock:
            try:
                # 若同一 audit_id 已存在，先移除旧索引，避免重复引用
                existing = self._audit_records.get(audit.audit_id)
                if existing is not None:
                    self._remove_indexes(existing)

                # 保存审计记录
                self._audit_records[audit.audit_id] = audit

                # 更新索引
                self._update_indexes(audit)
                return True
            except Exception as e:
                print(f"保存审计记录失败: {e}")
                return False

    def get_audit(self, audit_id: str) -> Optional[BatchOperationAudit]:
        """获取审计记录"""
        with self._lock:
            return self._audit_records.get(audit_id)

    def get_audit_by_operation_id(self, operation_id: str) -> Optional[BatchOperationAudit]:
        """根据操作ID获取审计记录"""
        with self._lock:
            audit_id = self._operation_id_index.get(operation_id)
            if audit_id:
                return self._audit_records.get(audit_id)
            return None

    def query_audits(self, query: AuditQueryRequest) -> tuple[List[BatchOperationAudit], int]:
        """查询审计记录"""
        with self._lock:
            results = list(self._audit_records.values())

            # 按操作ID过滤
            if query.operation_id:
                audit_id = self._operation_id_index.get(query.operation_id)
                if audit_id and audit_id in self._audit_records:
                    results = [self._audit_records[audit_id]]
                else:
                    results = []

            # 按操作类型过滤
            if query.operation_type:
                operation_type = query.operation_type.value
                audit_ids = self._operation_type_index.get(operation_type, [])
                results = [r for r in results if r.audit_id in audit_ids]

            # 按用户ID过滤
            if query.user_id:
                audit_ids = self._user_id_index.get(query.user_id, [])
                results = [r for r in results if r.audit_id in audit_ids]

            # 按资产ID过滤
            if query.asset_id:
                audit_ids = self._asset_id_index.get(query.asset_id, [])
                results = [r for r in results if r.audit_id in audit_ids]

            # 按节点ID过滤
            if query.node_id:
                audit_ids = self._node_id_index.get(query.node_id, [])
                results = [r for r in results if r.audit_id in audit_ids]

            # 按任务ID过滤
            if query.task_id:
                audit_ids = self._task_id_index.get(query.task_id, [])
                results = [r for r in results if r.audit_id in audit_ids]

            # 按时间范围过滤
            if query.start_time:
                results = [r for r in results if r.timestamp >= query.start_time]
            if query.end_time:
                results = [r for r in results if r.timestamp <= query.end_time]

            # 按成功/失败过滤
            if query.success_only:
                results = [r for r in results if r.failed_items == 0]
            if query.failed_only:
                results = [r for r in results if r.failed_items > 0]

            # 按错误类型过滤
            if query.error_type:
                audit_ids = self._error_type_index.get(query.error_type, [])
                results = [r for r in results if r.audit_id in audit_ids]

            # 排序
            results = self._sort_results(results, query.sort_by, query.sort_order)

            # 计算总数
            total_count = len(results)

            # 分页
            start_idx = (query.page - 1) * query.page_size
            end_idx = start_idx + query.page_size
            paginated_results = results[start_idx:end_idx]

            return paginated_results, total_count

    def get_statistics(self, start_time: datetime, end_time: datetime) -> AuditStatistics:
        """获取审计统计信息"""
        with self._lock:
            # 获取时间范围内的所有审计记录（分批获取）
            all_results = []
            page = 1
            page_size = 100  # 最大限制

            while True:
                query = AuditQueryRequest(
                    start_time=start_time,
                    end_time=end_time,
                    page=page,
                    page_size=page_size,
                )
                results, total_count = self.query_audits(query)
                all_results.extend(results)

                if len(all_results) >= total_count:
                    break
                page += 1

            results = all_results

            statistics = AuditStatistics(
                total_operations=len(results),
                successful_operations=0,
                failed_operations=0,
                success_rate=0.0,
                operation_type_counts={},
                error_type_counts={},
                user_activity={},
                hourly_distribution={},
                most_active_assets=[],
                most_active_nodes=[],
            )

            for audit in results:
                # 操作类型统计
                op_type = audit.operation_type.value
                statistics.operation_type_counts[op_type] = (
                    statistics.operation_type_counts.get(op_type, 0) + 1
                )

                # 成功/失败统计
                if audit.failed_items == 0:
                    statistics.successful_operations += 1
                else:
                    statistics.failed_operations += 1

                # 错误类型统计
                for error_type, count in audit.error_summary.items():
                    statistics.error_type_counts[error_type] = (
                        statistics.error_type_counts.get(error_type, 0) + count
                    )

                # 用户活动统计
                if audit.user_id:
                    statistics.user_activity[audit.user_id] = (
                        statistics.user_activity.get(audit.user_id, 0) + 1
                    )

                # 时间分布
                hour_key = audit.timestamp.strftime("%Y-%m-%d %H:00")
                statistics.hourly_distribution[hour_key] = (
                    statistics.hourly_distribution.get(hour_key, 0) + 1
                )

                # 资产活跃度
                for asset_id in audit.related_assets:
                    # 统计每个资产的操作次数
                    pass  # 简化实现

                # 节点活跃度
                for node_id in audit.related_nodes:
                    # 统计每个节点的操作次数
                    pass  # 简化实现

            # 计算成功率
            if statistics.total_operations > 0:
                statistics.success_rate = round(
                    (statistics.successful_operations / statistics.total_operations) * 100,
                    1,
                )

            return statistics

    def get_asset_history(self, asset_id: str, limit: int = 100) -> List[BatchOperationAudit]:
        """获取资产审计历史"""
        with self._lock:
            audit_ids = self._asset_id_index.get(asset_id, [])
            audits = [
                self._audit_records[audit_id]
                for audit_id in audit_ids
                if audit_id in self._audit_records
            ]

            # 按时间倒序排序，取最近的记录
            audits.sort(key=lambda x: x.timestamp, reverse=True)
            return audits[:limit]

    def get_failed_operations(
        self,
        error_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[BatchOperationAudit]:
        """获取失败的操作"""
        query = AuditQueryRequest(
            failed_only=True,
            error_type=error_type,
            start_time=start_time,
            end_time=end_time,
            page=1,
            page_size=limit,
            sort_by="timestamp",
            sort_order="desc",
        )
        results, _ = self.query_audits(query)
        return results

    def _remove_indexes(self, audit: BatchOperationAudit):
        """移除旧索引"""
        audit_id = audit.audit_id

        operation_id = audit.operation_id
        if self._operation_id_index.get(operation_id) == audit_id:
            del self._operation_id_index[operation_id]

        if audit.user_id and audit.user_id in self._user_id_index:
            self._user_id_index[audit.user_id] = [
                x for x in self._user_id_index[audit.user_id] if x != audit_id
            ]
            if not self._user_id_index[audit.user_id]:
                del self._user_id_index[audit.user_id]

        op_type = audit.operation_type.value
        if op_type in self._operation_type_index:
            self._operation_type_index[op_type] = [
                x for x in self._operation_type_index[op_type] if x != audit_id
            ]
            if not self._operation_type_index[op_type]:
                del self._operation_type_index[op_type]

        for asset_id in audit.related_assets:
            if asset_id in self._asset_id_index:
                self._asset_id_index[asset_id] = [
                    x for x in self._asset_id_index[asset_id] if x != audit_id
                ]
                if not self._asset_id_index[asset_id]:
                    del self._asset_id_index[asset_id]

        for node_id in audit.related_nodes:
            if node_id in self._node_id_index:
                self._node_id_index[node_id] = [
                    x for x in self._node_id_index[node_id] if x != audit_id
                ]
                if not self._node_id_index[node_id]:
                    del self._node_id_index[node_id]

        for task_id in audit.related_tasks:
            if task_id in self._task_id_index:
                self._task_id_index[task_id] = [
                    x for x in self._task_id_index[task_id] if x != audit_id
                ]
                if not self._task_id_index[task_id]:
                    del self._task_id_index[task_id]

        for error_type in audit.error_summary.keys():
            if error_type in self._error_type_index:
                self._error_type_index[error_type] = [
                    x for x in self._error_type_index[error_type] if x != audit_id
                ]
                if not self._error_type_index[error_type]:
                    del self._error_type_index[error_type]

        date_key = audit.timestamp.strftime("%Y-%m-%d")
        if date_key in self._timestamp_index:
            self._timestamp_index[date_key] = [
                x for x in self._timestamp_index[date_key] if x != audit_id
            ]
            if not self._timestamp_index[date_key]:
                del self._timestamp_index[date_key]

    def _update_indexes(self, audit: BatchOperationAudit):
        """更新索引"""
        # 操作ID索引
        self._operation_id_index[audit.operation_id] = audit.audit_id

        # 用户ID索引
        if audit.user_id:
            if audit.user_id not in self._user_id_index:
                self._user_id_index[audit.user_id] = []
            self._user_id_index[audit.user_id].append(audit.audit_id)

        # 操作类型索引
        op_type = audit.operation_type.value
        if op_type not in self._operation_type_index:
            self._operation_type_index[op_type] = []
        self._operation_type_index[op_type].append(audit.audit_id)

        # 资产ID索引
        for asset_id in audit.related_assets:
            if asset_id not in self._asset_id_index:
                self._asset_id_index[asset_id] = []
            self._asset_id_index[asset_id].append(audit.audit_id)

        # 节点ID索引
        for node_id in audit.related_nodes:
            if node_id not in self._node_id_index:
                self._node_id_index[node_id] = []
            self._node_id_index[node_id].append(audit.audit_id)

        # 任务ID索引
        for task_id in audit.related_tasks:
            if task_id not in self._task_id_index:
                self._task_id_index[task_id] = []
            self._task_id_index[task_id].append(audit.audit_id)

        # 错误类型索引
        for error_type in audit.error_summary.keys():
            if error_type not in self._error_type_index:
                self._error_type_index[error_type] = []
            self._error_type_index[error_type].append(audit.audit_id)

        # 时间戳索引
        date_key = audit.timestamp.strftime("%Y-%m-%d")
        if date_key not in self._timestamp_index:
            self._timestamp_index[date_key] = []
        self._timestamp_index[date_key].append(audit.audit_id)

    def _sort_results(
        self, results: List[BatchOperationAudit], sort_by: str, sort_order: str
    ) -> List[BatchOperationAudit]:
        """排序结果"""
        reverse = sort_order.lower() == "desc"

        if sort_by == "timestamp":
            results.sort(key=lambda x: x.timestamp, reverse=reverse)
        elif sort_by == "operation_type":
            results.sort(key=lambda x: x.operation_type.value, reverse=reverse)
        elif sort_by == "success_rate":
            results.sort(key=lambda x: x.success_rate, reverse=reverse)
        elif sort_by == "total_items":
            results.sort(key=lambda x: x.total_items, reverse=reverse)
        elif sort_by == "duration":
            results.sort(key=lambda x: x.duration_seconds or 0, reverse=reverse)

        return results

    def clear_all(self):
        """清空所有审计记录（主要用于测试）"""
        with self._lock:
            self._audit_records.clear()
            self._operation_id_index.clear()
            self._user_id_index.clear()
            self._asset_id_index.clear()
            self._node_id_index.clear()
            self._task_id_index.clear()
            self._error_type_index.clear()
            self._operation_type_index.clear()
            self._timestamp_index.clear()

    def get_total_count(self) -> int:
        """获取审计记录总数"""
        with self._lock:
            return len(self._audit_records)
