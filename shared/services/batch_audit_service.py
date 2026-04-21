"""
HermesNexus v1.2 - 批量操作审计服务
提供批量操作的增强审计记录功能
"""

import asyncio
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from shared.storage.audit_storage import AuditStorage
from shared.models.audit_models import (
    BatchOperationAudit,
    AuditItemResult,
    AuditQueryRequest,
    AuditQueryResponse,
    AuditStatistics,
    AuditOperationType,
)
from shared.models.batch_operations import BatchOperationResponse, BatchItemResult


class BatchAuditService:
    """批量操作审计服务"""

    def __init__(self, storage: Optional[AuditStorage] = None):
        """初始化审计服务"""
        self.storage = storage or AuditStorage()
        self._enabled = True

    def is_enabled(self) -> bool:
        """检查审计是否启用"""
        return self._enabled

    def enable(self):
        """启用审计"""
        self._enabled = True

    def disable(self):
        """禁用审计"""
        self._enabled = False

    async def log_batch_operation(
        self,
        operation: BatchOperationResponse,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[BatchOperationAudit]:
        """记录批量操作审计"""
        if not self._enabled:
            return None

        try:
            # 生成审计ID
            audit_id = f"audit-{uuid.uuid4().hex[:8]}"

            # 计算操作时长
            duration_seconds = None
            if operation.completed_at and operation.started_at:
                duration_seconds = (operation.completed_at - operation.started_at).total_seconds()

            # 提取关联信息
            related_assets = []
            related_nodes = []
            related_tasks = []

            for result in operation.results:
                if hasattr(result, "data") and result.data:
                    if "asset_id" in result.data:
                        related_assets.append(result.data["asset_id"])
                    if "node_id" in result.data:
                        related_nodes.append(result.data["node_id"])
                    if "task_id" in result.data:
                        related_tasks.append(result.data["task_id"])

            # 转换操作类型
            operation_type = self._convert_operation_type(operation.operation_type)

            # 创建详细审计结果
            audit_results = []
            for result in operation.results:
                audit_result = AuditItemResult(
                    item_id=result.id,
                    success=result.success,
                    operation_type=operation.operation_type,
                    error_code=result.error_code,
                    error_message=result.message,
                    timestamp=(
                        result.created_at
                        if hasattr(result, "created_at")
                        else datetime.now(timezone.utc)
                    ),
                )

                # 添加关联信息
                if hasattr(result, "data") and result.data:
                    audit_result.asset_id = result.data.get("asset_id")
                    audit_result.node_id = result.data.get("node_id")
                    audit_result.task_id = result.data.get("task_id")

                audit_results.append(audit_result)

            # 创建审计记录
            audit = BatchOperationAudit(
                audit_id=audit_id,
                operation_id=operation.operation_id,
                operation_type=operation_type,
                user_id=user_id,
                username=username,
                timestamp=operation.started_at,
                parameters=parameters or {},
                request_ip=request_ip,
                user_agent=user_agent,
                total_items=operation.summary.total_items,
                successful_items=operation.summary.successful_items,
                failed_items=operation.summary.failed_items,
                skipped_items=operation.summary.skipped_items,
                success_rate=operation.summary.success_rate,
                results=audit_results,
                error_summary=operation.error_summary,
                related_assets=related_assets,
                related_nodes=related_nodes,
                related_tasks=related_tasks,
                started_at=operation.started_at,
                completed_at=operation.completed_at,
                duration_seconds=duration_seconds,
            )

            # 保存审计记录
            if self.storage.save_audit(audit):
                return audit
            else:
                return None

        except Exception as e:
            print(f"记录审计失败: {e}")
            return None

    async def query_audits(self, query: AuditQueryRequest) -> AuditQueryResponse:
        """查询审计记录"""
        results, total_count = self.storage.query_audits(query)

        # 计算总页数
        total_pages = (total_count + query.page_size - 1) // query.page_size

        return AuditQueryResponse(
            total_count=total_count,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            records=results,
        )

    async def get_audit_by_operation_id(self, operation_id: str) -> Optional[BatchOperationAudit]:
        """根据操作ID获取审计记录"""
        return self.storage.get_audit_by_operation_id(operation_id)

    async def get_audit(self, audit_id: str) -> Optional[BatchOperationAudit]:
        """获取审计记录"""
        return self.storage.get_audit(audit_id)

    async def get_asset_history(self, asset_id: str, limit: int = 100) -> List[BatchOperationAudit]:
        """获取资产审计历史"""
        return self.storage.get_asset_history(asset_id, limit)

    async def get_failed_operations(
        self,
        error_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[BatchOperationAudit]:
        """获取失败的操作"""
        return self.storage.get_failed_operations(error_type, start_time, end_time, limit)

    async def get_statistics(self, start_time: datetime, end_time: datetime) -> AuditStatistics:
        """获取审计统计信息"""
        return self.storage.get_statistics(start_time, end_time)

    async def export_audits(
        self,
        query: AuditQueryRequest,
        format_type: str = "json",
        include_details: bool = True,
        max_records: int = 1000,
    ) -> str:
        """导出审计数据"""
        # 修改查询以获取所有记录
        query.page = 1
        query.page_size = max_records
        response = await self.query_audits(query)

        if format_type == "json":
            return self._export_json(response.records, include_details)
        else:
            raise ValueError(f"不支持的导出格式: {format_type}")

    def _export_json(self, records: List[BatchOperationAudit], include_details: bool) -> str:
        """导出为JSON格式"""
        import json

        export_data = {
            "export_time": datetime.now(timezone.utc).isoformat(),
            "total_records": len(records),
            "records": [],
        }

        for record in records:
            record_dict = {
                "audit_id": record.audit_id,
                "operation_id": record.operation_id,
                "operation_type": record.operation_type.value,
                "user_id": record.user_id,
                "username": record.username,
                "timestamp": record.timestamp.isoformat(),
                "total_items": record.total_items,
                "successful_items": record.successful_items,
                "failed_items": record.failed_items,
                "success_rate": record.success_rate,
                "error_summary": record.error_summary,
                "duration_seconds": record.duration_seconds,
            }

            if include_details:
                record_dict["related_assets"] = record.related_assets
                record_dict["related_nodes"] = record.related_nodes
                record_dict["related_tasks"] = record.related_tasks
                record_dict["results"] = [
                    {
                        "item_id": r.item_id,
                        "success": r.success,
                        "error_code": r.error_code,
                        "error_message": r.error_message,
                        "timestamp": r.timestamp.isoformat(),
                    }
                    for r in record.results
                ]

            export_data["records"].append(record_dict)

        return json.dumps(export_data, indent=2, ensure_ascii=False)

    def _convert_operation_type(self, operation_type: str) -> AuditOperationType:
        """转换操作类型"""
        type_mapping = {
            "asset_create": AuditOperationType.BATCH_ASSET_CREATE,
            "asset_update": AuditOperationType.BATCH_ASSET_UPDATE,
            "asset_delete": AuditOperationType.BATCH_ASSET_DELETE,
            "task_create": AuditOperationType.BATCH_TASK_CREATE,
            "task_update": AuditOperationType.BATCH_TASK_UPDATE,
            "task_delete": AuditOperationType.BATCH_TASK_DELETE,
            "batch_asset_create": AuditOperationType.BATCH_ASSET_CREATE,
            "batch_asset_update": AuditOperationType.BATCH_ASSET_UPDATE,
            "batch_asset_delete": AuditOperationType.BATCH_ASSET_DELETE,
            "batch_task_create": AuditOperationType.BATCH_TASK_CREATE,
            "batch_task_update": AuditOperationType.BATCH_TASK_UPDATE,
            "batch_task_delete": AuditOperationType.BATCH_TASK_DELETE,
        }

        return type_mapping.get(operation_type, AuditOperationType.BATCH_ASSET_CREATE)


# 全局审计服务实例
_batch_audit_service: Optional[BatchAuditService] = None


def get_batch_audit_service() -> BatchAuditService:
    """获取全局批量审计服务实例"""
    global _batch_audit_service
    if _batch_audit_service is None:
        _batch_audit_service = BatchAuditService()
    return _batch_audit_service


def set_batch_audit_service(service: BatchAuditService):
    """设置全局批量审计服务实例"""
    global _batch_audit_service
    _batch_audit_service = service
