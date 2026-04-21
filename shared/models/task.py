"""
HermesNexus Phase 2 - Task Model
任务编排数据模型
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field, validator


class TaskType(str, Enum):
    """任务类型"""

    BASIC_EXEC = "basic_exec"  # 基础命令执行
    SCRIPT_TRANSFER = "script_transfer"  # 脚本传输执行
    FILE_TRANSFER = "file_transfer"  # 文件传输
    SYSTEM_INFO = "system_info"  # 系统信息查询
    CUSTOM = "custom"  # 自定义任务


class TaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"  # 待调度
    ASSIGNED = "assigned"  # 已分配给节点
    RUNNING = "running"  # 执行中
    SUCCEEDED = "succeeded"  # 成功完成
    COMPLETED = "succeeded"  # 兼容旧测试/旧API
    FAILED = "failed"  # 执行失败
    TIMEOUT = "timeout"  # 执行超时
    CANCELLED = "cancelled"  # 已取消

    @classmethod
    def _missing_(cls, value):
        if value == "completed":
            return cls.SUCCEEDED
        return super()._missing_(value)

    def can_transition_to(self, new_status: "TaskStatus") -> bool:
        valid_transitions = {
            TaskStatus.PENDING: [TaskStatus.ASSIGNED, TaskStatus.CANCELLED],
            TaskStatus.ASSIGNED: [TaskStatus.RUNNING, TaskStatus.CANCELLED],
            TaskStatus.RUNNING: [
                TaskStatus.SUCCEEDED,
                TaskStatus.FAILED,
                TaskStatus.TIMEOUT,
                TaskStatus.CANCELLED,
            ],
            TaskStatus.SUCCEEDED: [],
            TaskStatus.FAILED: [],
            TaskStatus.TIMEOUT: [],
            TaskStatus.CANCELLED: [],
        }
        return new_status in valid_transitions.get(self, [])

    def is_terminal(self) -> bool:
        return self in [
            TaskStatus.SUCCEEDED,
            TaskStatus.FAILED,
            TaskStatus.TIMEOUT,
            TaskStatus.CANCELLED,
        ]


class TaskPriority(str, Enum):
    """任务优先级"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskExecutionResult(BaseModel):
    """任务执行结果"""

    exit_code: Optional[int] = Field(None, description="退出码")
    stdout: Optional[str] = Field(None, description="标准输出")
    stderr: Optional[str] = Field(None, description="标准错误输出")
    output_size: Optional[int] = Field(None, description="输出大小（字节）")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")

    # 错误信息
    error_message: Optional[str] = Field(None, description="错误消息")
    error_type: Optional[str] = Field(None, description="错误类型")

    # 时间戳
    started_at: Optional[datetime] = Field(None, description="开始执行时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")

    class Config:
        json_schema_extra = {
            "example": {
                "exit_code": 0,
                "stdout": "Linux localhost 5.15.0-72-generic #79-Ubuntu SMP ...",
                "stderr": "",
                "output_size": 1024,
                "execution_time": 0.5,
                "started_at": "2026-04-12T15:30:00Z",
                "completed_at": "2026-04-12T15:30:01Z",
            }
        }


class Task(BaseModel):
    """任务模型"""

    task_id: str = Field(..., description="任务唯一标识")
    name: str = Field(..., description="任务名称", min_length=1, max_length=255)
    task_type: TaskType = Field(..., description="任务类型")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="任务优先级")

    # 目标信息
    target_asset_id: str = Field(..., description="目标资产ID")
    target_node_id: Optional[str] = Field(None, description="目标节点ID（调度后分配）")

    # 任务内容
    command: str = Field(..., description="要执行的命令或脚本")
    arguments: List[str] = Field(default_factory=list, description="命令参数")
    working_dir: Optional[str] = Field(None, description="工作目录")
    environment: Dict[str, str] = Field(default_factory=dict, description="环境变量")

    # 执行配置
    timeout: int = Field(300, description="超时时间（秒）", ge=1, le=3600)
    retry_count: int = Field(0, description="重试次数", ge=0, le=5)
    retry_delay: int = Field(5, description="重试延迟（秒）", ge=1, le=300)

    # 调度信息
    scheduled_at: Optional[datetime] = Field(None, description="计划执行时间")
    assigned_at: Optional[datetime] = Field(None, description="分配时间")

    # 执行信息
    started_at: Optional[datetime] = Field(None, description="开始执行时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    result: Optional[TaskExecutionResult] = Field(None, description="执行结果")

    # 创建信息
    created_by: str = Field(..., description="创建者")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="更新时间"
    )

    # 描述和标签
    description: Optional[str] = Field(None, description="任务描述", max_length=1000)
    tags: List[str] = Field(default_factory=list, description="任务标签")

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="任务元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task-001",
                "name": "系统信息查询",
                "task_type": "basic_exec",
                "status": "succeeded",
                "priority": "normal",
                "target_asset_id": "asset-001",
                "target_node_id": "node-001",
                "command": "uname -a",
                "arguments": [],
                "timeout": 30,
                "retry_count": 0,
                "created_by": "admin",
                "created_at": "2026-04-12T10:00:00Z",
                "description": "查询系统详细信息",
            }
        }

    @validator("task_id")
    def validate_task_id(cls, v):
        """验证任务ID格式"""
        if not v or len(v.strip()) == 0:
            raise ValueError("task_id cannot be empty")
        return v.strip()

    @validator("name")
    def validate_name(cls, v):
        """验证任务名称"""
        if not v or len(v.strip()) == 0:
            raise ValueError("name cannot be empty")
        return v.strip()


class TaskCreateRequest(BaseModel):
    """任务创建请求"""

    task_id: Optional[str] = Field(None, description="任务ID（不指定则自动生成）")
    name: str = Field(..., description="任务名称", min_length=1, max_length=255)
    task_type: TaskType = Field(default=TaskType.BASIC_EXEC, description="任务类型")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="任务优先级")

    # 目标信息
    target_asset_id: str = Field(..., description="目标资产ID")

    # 任务内容
    command: str = Field(..., description="要执行的命令或脚本")
    arguments: List[str] = Field(default_factory=list, description="命令参数")
    working_dir: Optional[str] = Field(None, description="工作目录")
    environment: Dict[str, str] = Field(default_factory=dict, description="环境变量")

    # 执行配置
    timeout: int = Field(300, description="超时时间（秒）", ge=1, le=3600)
    retry_count: int = Field(0, description="重试次数", ge=0, le=5)
    retry_delay: int = Field(5, description="重试延迟（秒）", ge=1, le=300)

    # 调度配置
    scheduled_at: Optional[datetime] = Field(None, description="计划执行时间")

    # 描述和标签
    description: Optional[str] = Field(None, description="任务描述", max_length=1000)
    tags: List[str] = Field(default_factory=list, description="任务标签")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="任务元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "系统信息查询",
                "task_type": "basic_exec",
                "priority": "normal",
                "target_asset_id": "asset-001",
                "command": "uname -a",
                "timeout": 30,
                "description": "查询系统详细信息",
            }
        }


class TaskUpdateRequest(BaseModel):
    """任务更新请求"""

    name: Optional[str] = Field(None, description="任务名称", min_length=1, max_length=255)
    priority: Optional[TaskPriority] = Field(None, description="任务优先级")
    status: Optional[TaskStatus] = Field(None, description="任务状态")
    description: Optional[str] = Field(None, description="任务描述", max_length=1000)
    tags: Optional[List[str]] = Field(None, description="任务标签")
    metadata: Optional[Dict[str, Any]] = Field(None, description="任务元数据")

    class Config:
        json_schema_extra = {"example": {"priority": "high", "status": "cancelled"}}


class TaskListResponse(BaseModel):
    """任务列表响应"""

    total: int = Field(..., description="总数量")
    tasks: List[Task] = Field(..., description="任务列表")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    total_pages: int = Field(..., description="总页数")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 200,
                "tasks": [],
                "page": 1,
                "page_size": 20,
                "total_pages": 10,
            }
        }


class TaskQueryParams(BaseModel):
    """任务查询参数"""

    task_type: Optional[TaskType] = Field(None, description="按任务类型过滤")
    status: Optional[TaskStatus] = Field(None, description="按状态过滤")
    priority: Optional[TaskPriority] = Field(None, description="按优先级过滤")
    target_asset_id: Optional[str] = Field(None, description="按目标资产过滤")
    target_node_id: Optional[str] = Field(None, description="按目标节点过滤")
    created_by: Optional[str] = Field(None, description="按创建者过滤")
    search: Optional[str] = Field(None, description="搜索关键词（名称、描述、命令）")
    tags: Optional[List[str]] = Field(None, description="按标签过滤")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页大小")
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="排序方向")

    class Config:
        json_schema_extra = {
            "example": {
                "task_type": "basic_exec",
                "status": "running",
                "target_asset_id": "asset-001",
                "page": 1,
                "page_size": 20,
                "sort_by": "created_at",
                "sort_order": "desc",
            }
        }


class TaskStats(BaseModel):
    """任务统计信息"""

    total_tasks: int = Field(..., description="总任务数")
    by_type: Dict[str, int] = Field(default_factory=dict, description="按类型统计")
    by_status: Dict[str, int] = Field(default_factory=dict, description="按状态统计")
    by_priority: Dict[str, int] = Field(default_factory=dict, description="按优先级统计")

    # 执行统计
    running_tasks: int = Field(..., description="运行中任务数")
    pending_tasks: int = Field(..., description="待处理任务数")
    completed_tasks: int = Field(..., description="已完成任务数")
    failed_tasks: int = Field(..., description="失败任务数")

    # 成功率
    success_rate: float = Field(..., description="成功率（百分比）")

    class Config:
        json_schema_extra = {
            "example": {
                "total_tasks": 1500,
                "by_type": {
                    "basic_exec": 1200,
                    "script_transfer": 200,
                    "file_transfer": 80,
                    "system_info": 20,
                },
                "by_status": {
                    "pending": 50,
                    "assigned": 30,
                    "running": 20,
                    "succeeded": 1300,
                    "failed": 80,
                    "timeout": 15,
                    "cancelled": 5,
                },
                "by_priority": {"low": 200, "normal": 1000, "high": 250, "urgent": 50},
                "running_tasks": 20,
                "pending_tasks": 50,
                "completed_tasks": 1380,
                "failed_tasks": 95,
                "success_rate": 93.5,
            }
        }


class TaskDispatchRequest(BaseModel):
    """任务分发请求"""

    task_ids: List[str] = Field(..., description="要分发的任务ID列表")
    target_node_id: str = Field(..., description="目标节点ID")
    dispatch_strategy: str = Field("batch", description="分发策略: batch, round_robin, least_loaded")

    class Config:
        json_schema_extra = {
            "example": {
                "task_ids": ["task-001", "task-002", "task-003"],
                "target_node_id": "node-001",
                "dispatch_strategy": "batch",
            }
        }


class TaskResultSubmit(BaseModel):
    """任务结果提交"""

    task_id: str = Field(..., description="任务ID")
    node_id: str = Field(..., description="执行节点ID")
    status: TaskStatus = Field(..., description="最终状态")
    result: TaskExecutionResult = Field(..., description="执行结果")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task-001",
                "node_id": "node-001",
                "status": "succeeded",
                "result": {
                    "exit_code": 0,
                    "stdout": "Linux localhost 5.15.0-72-generic",
                    "stderr": "",
                    "execution_time": 0.5,
                },
            }
        }
