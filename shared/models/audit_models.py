"""
HermesNexus v1.2 - 审计数据模型
支持批量操作和系统操作的审计追踪
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AuditOperationType(str, Enum):
    """审计操作类型"""

    ASSET_CREATE = "asset_create"
    ASSET_UPDATE = "asset_update"
    ASSET_DELETE = "asset_delete"
    TASK_CREATE = "task_create"
    TASK_UPDATE = "task_update"
    TASK_DELETE = "task_delete"
    BATCH_ASSET_CREATE = "batch_asset_create"
    BATCH_ASSET_UPDATE = "batch_asset_update"
    BATCH_ASSET_DELETE = "batch_asset_delete"
    BATCH_TASK_CREATE = "batch_task_create"
    BATCH_TASK_UPDATE = "batch_task_update"
    BATCH_TASK_DELETE = "batch_task_delete"


class AuditItemResult(BaseModel):
    """审计单项结果"""

    item_id: str = Field(..., description="项目ID")
    success: bool = Field(..., description="是否成功")
    operation_type: str = Field(..., description="操作类型")
    error_code: Optional[str] = Field(None, description="错误代码")
    error_message: Optional[str] = Field(None, description="错误消息")
    timestamp: datetime = Field(default_factory=datetime.now, description="操作时间")

    # 关联信息
    asset_id: Optional[str] = Field(None, description="关联资产ID")
    node_id: Optional[str] = Field(None, description="关联节点ID")
    task_id: Optional[str] = Field(None, description="关联任务ID")

    # 操作前后的数据变化（可选）
    before_data: Optional[Dict[str, Any]] = Field(None, description="操作前数据")
    after_data: Optional[Dict[str, Any]] = Field(None, description="操作后数据")

    class Config:
        json_schema_extra = {
            "example": {
                "item_id": "asset-001",
                "success": True,
                "operation_type": "asset_update",
                "error_code": None,
                "error_message": None,
                "timestamp": "2026-04-15T10:30:00Z",
                "asset_id": "asset-001",
                "node_id": None,
                "task_id": None,
            }
        }


class BatchOperationAudit(BaseModel):
    """批量操作审计记录"""

    audit_id: str = Field(..., description="审计ID")
    operation_id: str = Field(..., description="操作ID")
    operation_type: AuditOperationType = Field(..., description="操作类型")
    user_id: Optional[str] = Field(None, description="操作用户ID")
    username: Optional[str] = Field(None, description="操作用户名")
    timestamp: datetime = Field(..., description="操作时间")

    # 操作参数
    parameters: Dict[str, Any] = Field(default_factory=dict, description="操作参数")
    request_ip: Optional[str] = Field(None, description="请求IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")

    # 操作结果
    total_items: int = Field(..., description="总项目数")
    successful_items: int = Field(..., description="成功项目数")
    failed_items: int = Field(..., description="失败项目数")
    skipped_items: int = Field(0, description="跳过项目数")
    success_rate: float = Field(..., description="成功率")

    # 详细结果
    results: List[AuditItemResult] = Field(default_factory=list, description="详细结果")
    error_summary: Dict[str, int] = Field(default_factory=dict, description="错误摘要")

    # 关联信息
    related_assets: List[str] = Field(default_factory=list, description="关联资产ID")
    related_nodes: List[str] = Field(default_factory=list, description="关联节点ID")
    related_tasks: List[str] = Field(default_factory=list, description="关联任务ID")

    # 执行时间
    started_at: datetime = Field(..., description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    duration_seconds: Optional[float] = Field(None, description="执行时长（秒）")

    class Config:
        json_schema_extra = {
            "example": {
                "audit_id": "audit-12345",
                "operation_id": "batch-op-67890",
                "operation_type": "batch_asset_update",
                "user_id": "user-001",
                "username": "admin",
                "timestamp": "2026-04-15T10:30:00Z",
                "parameters": {"updates": {"status": "active"}},
                "total_items": 10,
                "successful_items": 8,
                "failed_items": 2,
                "success_rate": 80.0,
                "error_summary": {"validation_error": 1, "not_found_error": 1},
            }
        }


class AuditQueryRequest(BaseModel):
    """审计查询请求"""

    operation_id: Optional[str] = Field(None, description="操作ID")
    operation_type: Optional[AuditOperationType] = Field(None, description="操作类型")
    user_id: Optional[str] = Field(None, description="用户ID")
    asset_id: Optional[str] = Field(None, description="资产ID")
    node_id: Optional[str] = Field(None, description="节点ID")
    task_id: Optional[str] = Field(None, description="任务ID")

    # 时间范围
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")

    # 结果过滤
    success_only: bool = Field(False, description="仅显示成功")
    failed_only: bool = Field(False, description="仅显示失败")
    error_type: Optional[str] = Field(None, description="错误类型")

    # 分页
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页大小")

    # 排序
    sort_by: str = Field("timestamp", description="排序字段")
    sort_order: str = Field("desc", description="排序方向")

    class Config:
        json_schema_extra = {
            "example": {
                "operation_type": "batch_asset_update",
                "start_time": "2026-04-15T00:00:00Z",
                "end_time": "2026-04-15T23:59:59Z",
                "failed_only": True,
                "page": 1,
                "page_size": 20,
            }
        }


class AuditQueryResponse(BaseModel):
    """审计查询响应"""

    total_count: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    total_pages: int = Field(..., description="总页数")
    records: List[BatchOperationAudit] = Field(default_factory=list, description="审计记录")


class AuditStatistics(BaseModel):
    """审计统计信息"""

    total_operations: int = Field(..., description="总操作数")
    successful_operations: int = Field(..., description="成功操作数")
    failed_operations: int = Field(..., description="失败操作数")
    success_rate: float = Field(..., description="成功率")

    # 操作类型统计
    operation_type_counts: Dict[str, int] = Field(default_factory=dict, description="操作类型统计")

    # 错误类型统计
    error_type_counts: Dict[str, int] = Field(default_factory=dict, description="错误类型统计")

    # 用户活动统计
    user_activity: Dict[str, int] = Field(default_factory=dict, description="用户活动统计")

    # 时间分布
    hourly_distribution: Dict[str, int] = Field(default_factory=dict, description="每小时分布")

    # 资产活跃度
    most_active_assets: List[Dict[str, Any]] = Field(default_factory=list, description="最活跃资产")

    # 节点活跃度
    most_active_nodes: List[Dict[str, Any]] = Field(default_factory=list, description="最活跃节点")


class AuditExportRequest(BaseModel):
    """审计导出请求"""

    query: AuditQueryRequest = Field(..., description="查询条件")
    format: str = Field("json", description="导出格式")
    include_details: bool = Field(True, description="包含详细结果")
    max_records: int = Field(1000, ge=1, le=10000, description="最大记录数")
