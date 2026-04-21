"""
HermesNexus v1.2 - 批量操作模型
支持资产和任务的批量操作
"""

from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime


class BatchOperationStatus(str, Enum):
    """批量操作状态"""

    PENDING = "pending"  # 待处理
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 已完成
    PARTIAL_SUCCESS = "partial_success"  # 部分成功
    FAILED = "failed"  # 失败


class BatchItemResult(BaseModel):
    """批量操作单项结果"""

    id: str = Field(..., description="项目ID")
    success: bool = Field(..., description="是否成功")
    message: Optional[str] = Field(None, description="结果消息")
    error_code: Optional[str] = Field(None, description="错误码")
    data: Optional[Dict[str, Any]] = Field(None, description="返回数据")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "asset-001",
                "success": True,
                "message": "资产创建成功",
                "data": {"asset_id": "asset-001", "name": "Server 1"},
            }
        }


class BatchOperationSummary(BaseModel):
    """批量操作汇总"""

    total_items: int = Field(..., description="总项目数")
    successful_items: int = Field(0, description="成功项目数")
    failed_items: int = Field(0, description="失败项目数")
    skipped_items: int = Field(0, description="跳过项目数")
    success_rate: float = Field(0.0, description="成功率(%)")
    operation_id: str = Field(..., description="操作ID")

    @model_validator(mode="after")
    def calculate_success_rate(self):
        """自动计算成功率"""
        if self.total_items > 0:
            self.success_rate = round((self.successful_items / self.total_items) * 100, 1)
        else:
            self.success_rate = 0.0
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "total_items": 10,
                "successful_items": 8,
                "failed_items": 2,
                "skipped_items": 0,
                "success_rate": 80.0,
                "operation_id": "batch-op-001",
            }
        }


class BatchOperationResponse(BaseModel):
    """批量操作响应"""

    operation_id: str = Field(..., description="操作ID")
    operation_type: str = Field(..., description="操作类型")
    status: BatchOperationStatus = Field(..., description="操作状态")
    summary: BatchOperationSummary = Field(..., description="操作汇总")
    results: List[BatchItemResult] = Field(default_factory=list, description="单项结果列表")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    error_summary: Dict[str, int] = Field(default_factory=dict, description="错误统计")

    class Config:
        json_schema_extra = {
            "example": {
                "operation_id": "batch-op-001",
                "operation_type": "asset_create",
                "status": "completed",
                "summary": {
                    "total_items": 10,
                    "successful_items": 8,
                    "failed_items": 2,
                    "skipped_items": 0,
                    "success_rate": 80.0,
                    "operation_id": "batch-op-001",
                },
                "results": [],
                "error_summary": {"validation_error": 1, "duplicate_error": 1},
            }
        }


# ==================== 资产批量操作模型 ====================


class AssetBatchCreateRequest(BaseModel):
    """资产批量创建请求"""

    assets: List[Dict[str, Any]] = Field(..., description="资产列表", min_items=1, max_items=100)
    stop_on_first_error: bool = Field(False, description="遇错是否停止")
    validate_only: bool = Field(False, description="仅验证不执行")
    idempotency_key: Optional[str] = Field(None, description="幂等性键")
    user_id: Optional[str] = Field(None, description="操作用户ID")
    username: Optional[str] = Field(None, description="操作用户名")
    request_ip: Optional[str] = Field(None, description="请求IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")

    class Config:
        json_schema_extra = {
            "example": {
                "assets": [
                    {
                        "asset_id": "asset-001",
                        "name": "Server 1",
                        "asset_type": "linux_host",
                        "metadata": {"ip_address": "192.168.1.1"},
                    },
                    {
                        "asset_id": "asset-002",
                        "name": "Server 2",
                        "asset_type": "linux_host",
                        "metadata": {"ip_address": "192.168.1.2"},
                    },
                ],
                "stop_on_first_error": False,
                "validate_only": False,
                "idempotency_key": "create-assets-2026-04-15",
            }
        }


class AssetBatchUpdateRequest(BaseModel):
    """资产批量更新请求"""

    asset_ids: List[str] = Field(..., description="资产ID列表", min_items=1, max_items=100)
    updates: Dict[str, Any] = Field(..., description="要更新的字段")
    stop_on_first_error: bool = Field(False, description="遇错是否停止")
    validate_only: bool = Field(False, description="仅验证不执行")
    idempotency_key: Optional[str] = Field(None, description="幂等性键")
    user_id: Optional[str] = Field(None, description="操作用户ID")
    username: Optional[str] = Field(None, description="操作用户名")
    request_ip: Optional[str] = Field(None, description="请求IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")

    class Config:
        json_schema_extra = {
            "example": {
                "asset_ids": ["asset-001", "asset-002"],
                "updates": {
                    "status": "active",
                    "metadata": {"environment": "production"},
                },
                "stop_on_first_error": False,
                "validate_only": False,
            }
        }


class AssetBatchDeleteRequest(BaseModel):
    """资产批量删除请求"""

    asset_ids: List[str] = Field(..., description="资产ID列表", min_items=1, max_items=100)
    force: bool = Field(False, description="强制删除")
    stop_on_first_error: bool = Field(False, description="遇错是否停止")
    idempotency_key: Optional[str] = Field(None, description="幂等性键")
    user_id: Optional[str] = Field(None, description="操作用户ID")
    username: Optional[str] = Field(None, description="操作用户名")
    request_ip: Optional[str] = Field(None, description="请求IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")

    class Config:
        json_schema_extra = {
            "example": {
                "asset_ids": ["asset-001", "asset-002"],
                "force": False,
                "stop_on_first_error": False,
            }
        }


class AssetBatchOperationRequest(BaseModel):
    """资产批量操作统一请求"""

    operation: Literal["create", "update", "delete", "deactivate"] = Field(..., description="操作类型")
    items: List[Dict[str, Any]] = Field(..., description="操作项目列表")
    options: Dict[str, Any] = Field(default_factory=dict, description="操作选项")
    idempotency_key: Optional[str] = Field(None, description="幂等性键")

    class Config:
        json_schema_extra = {
            "example": {
                "operation": "create",
                "items": [
                    {
                        "asset_id": "asset-001",
                        "name": "Server 1",
                        "asset_type": "linux_host",
                    }
                ],
                "options": {"stop_on_first_error": False, "validate_only": False},
            }
        }


# ==================== 任务批量操作模型 ====================


class TaskBatchCreateRequest(BaseModel):
    """任务批量创建请求"""

    tasks: List[Dict[str, Any]] = Field(..., description="任务列表", min_items=1, max_items=50)
    stop_on_first_error: bool = Field(False, description="遇错是否停止")
    validate_only: bool = Field(False, description="仅验证不执行")
    idempotency_key: Optional[str] = Field(None, description="幂等性键")
    parallel_execution: bool = Field(True, description="是否并行执行")
    max_parallel_tasks: int = Field(10, ge=1, le=50, description="最大并行任务数")
    user_id: Optional[str] = Field(None, description="操作用户ID")
    username: Optional[str] = Field(None, description="操作用户名")
    request_ip: Optional[str] = Field(None, description="请求IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")

    class Config:
        json_schema_extra = {
            "example": {
                "tasks": [
                    {
                        "task_id": "task-001",
                        "name": "Update System",
                        "target_device_id": "asset-001",
                        "command": "yum update -y",
                    },
                    {
                        "task_id": "task-002",
                        "name": "Check Disk",
                        "target_device_id": "asset-002",
                        "command": "df -h",
                    },
                ],
                "stop_on_first_error": False,
                "parallel_execution": True,
                "max_parallel_tasks": 5,
            }
        }


class TaskBatchDispatchRequest(BaseModel):
    """任务批量下发请求"""

    task_ids: List[str] = Field(..., description="任务ID列表", min_items=1, max_items=50)
    target_node_ids: List[str] = Field(..., description="目标节点ID列表")
    dispatch_options: Dict[str, Any] = Field(default_factory=dict, description="下发选项")
    idempotency_key: Optional[str] = Field(None, description="幂等性键")
    user_id: Optional[str] = Field(None, description="操作用户ID")
    username: Optional[str] = Field(None, description="操作用户名")
    request_ip: Optional[str] = Field(None, description="请求IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")

    class Config:
        json_schema_extra = {
            "example": {
                "task_ids": ["task-001", "task-002"],
                "target_node_ids": ["node-001", "node-002"],
                "dispatch_options": {"parallel": True, "timeout": 300},
            }
        }


class TaskBatchOperationRequest(BaseModel):
    """任务批量操作统一请求"""

    operation: Literal["create", "dispatch", "cancel", "retry"] = Field(..., description="操作类型")
    tasks: List[Dict[str, Any]] = Field(..., description="任务列表")
    options: Dict[str, Any] = Field(default_factory=dict, description="操作选项")
    idempotency_key: Optional[str] = Field(None, description="幂等性键")

    class Config:
        json_schema_extra = {
            "example": {
                "operation": "create",
                "tasks": [
                    {
                        "task_id": "task-001",
                        "name": "Update System",
                        "target_device_id": "asset-001",
                        "command": "yum update -y",
                    }
                ],
                "options": {"parallel_execution": True, "max_parallel_tasks": 5},
            }
        }


# ==================== 幂等性和重试模型 ====================


class IdempotencyResult(BaseModel):
    """幂等性检查结果"""

    is_idempotent: bool = Field(..., description="是否幂等")
    existing_operation_id: Optional[str] = Field(None, description="已存在的操作ID")
    cached_result: Optional[BatchOperationResponse] = Field(None, description="缓存的结果")
    message: str = Field(..., description="结果消息")

    class Config:
        json_schema_extra = {
            "example": {
                "is_idempotent": True,
                "existing_operation_id": "batch-op-001",
                "cached_result": None,
                "message": "操作已存在，返回缓存结果",
            }
        }


class BatchRetryPolicy(BaseModel):
    """批量重试策略"""

    max_retries: int = Field(3, ge=0, le=10, description="最大重试次数")
    retry_delay_seconds: int = Field(5, ge=0, le=300, description="重试延迟(秒)")
    retry_on_errors: List[str] = Field(
        default_factory=lambda: ["timeout", "connection_error", "temporary_error"],
        description="可重试的错误类型",
    )
    backoff_multiplier: float = Field(2.0, ge=1.0, le=10.0, description="退避乘数")

    class Config:
        json_schema_extra = {
            "example": {
                "max_retries": 3,
                "retry_delay_seconds": 5,
                "retry_on_errors": ["timeout", "connection_error"],
                "backoff_multiplier": 2.0,
            }
        }


class BatchPartialFailureHandling(BaseModel):
    """批量部分失败处理策略"""

    continue_on_error: bool = Field(True, description="出错时是否继续")
    failure_threshold_percent: float = Field(50.0, ge=0.0, le=100.0, description="失败阈值(%)")
    rollback_on_threshold_exceeded: bool = Field(False, description="超过阈值是否回滚")
    save_partial_results: bool = Field(True, description="是否保存部分结果")

    class Config:
        json_schema_extra = {
            "example": {
                "continue_on_error": True,
                "failure_threshold_percent": 50.0,
                "rollback_on_threshold_exceeded": False,
                "save_partial_results": True,
            }
        }
