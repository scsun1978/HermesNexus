"""
HermesNexus Phase 2 - Task Service (Database Version)
任务编排业务逻辑层 - 数据库版本
"""

from typing import List, Optional, Dict
from datetime import datetime
import uuid
import math
from shared.models.task import (
    Task,
    TaskUpdateRequest,
    TaskQueryParams,
    TaskListResponse,
    TaskStats,
    TaskStatus,
    TaskPriority,
)
from shared.models.enums import validate_state_transition
from shared.dao.task_dao import TaskDAO
from shared.models.audit import (
    AuditAction,
    AuditCategory,
    EventLevel,
    AuditLogCreateRequest,
)


class TaskScheduler:
    """任务调度器"""

    def __init__(self):
        self._pending_tasks: Dict[str, Task] = {}
        self._node_loads: Dict[str, int] = {}  # 节点负载计数

    def add_to_pending(self, task: Task):
        """添加任务到待调度队列"""
        self._pending_tasks[task.task_id] = task

    def remove_from_pending(self, task_id: str):
        """从待调度队列移除"""
        if task_id in self._pending_tasks:
            del self._pending_tasks[task_id]

    def get_pending_tasks(self) -> List[Task]:
        """获取所有待调度任务"""
        return list(self._pending_tasks.values())

    def update_node_load(self, node_id: str, delta: int):
        """更新节点负载"""
        current = self._node_loads.get(node_id, 0)
        self._node_loads[node_id] = max(0, current + delta)

    def get_node_load(self, node_id: str) -> int:
        """获取节点负载"""
        return self._node_loads.get(node_id, 0)

    def select_least_loaded_node(self, available_nodes: List[str]) -> Optional[str]:
        """选择负载最低的节点"""
        if not available_nodes:
            return None

        return min(available_nodes, key=lambda node: self.get_node_load(node))


class TaskService:
    """任务编排服务 - 数据库版本"""

    def __init__(self, database=None):
        """
        初始化任务服务

        Args:
            database: 数据库实例
        """
        self.database = database

        # 如果有数据库，使用DAO；否则使用内存存储
        if database:
            self.task_dao = TaskDAO(database)
            self._tasks: Optional[Dict[str, Task]] = None
        else:
            self.task_dao = None
            self._tasks: Dict[str, Task] = {}

        # 任务调度器（保持内存存储）
        self.scheduler = TaskScheduler()

    def create_task(self, request, created_by: str = None) -> Task:
        """
        创建任务

        Args:
            request: 任务创建请求或完整 Task 对象
            created_by: 创建者用户ID（可选）

        Returns:
            创建的任务
        """
        if isinstance(request, Task):
            task = request
            task_id = task.task_id
        else:
            task_id = request.task_id or f"task-{uuid.uuid4().hex[:8]}"
            timeout = getattr(request, "timeout", None)
            if timeout is None:
                timeout = getattr(request, "timeout_seconds", 30)
            task = Task(
                task_id=task_id,
                name=request.name,
                task_type=request.task_type,
                status=TaskStatus.PENDING,
                priority=request.priority or TaskPriority.NORMAL,
                target_asset_id=request.target_asset_id,
                command=request.command,
                arguments=getattr(request, "arguments", []),
                working_dir=getattr(request, "working_dir", None),
                environment=getattr(request, "environment", {}),
                timeout=timeout,
                retry_count=getattr(request, "retry_count", 0),
                retry_delay=getattr(request, "retry_delay", 5),
                description=getattr(request, "description", None),
                tags=getattr(request, "tags", []),
                metadata=getattr(request, "metadata", {}),
                created_by=created_by or "admin",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

        if self.task_dao:
            saved = self.task_dao.insert(task)
        else:
            self._tasks[task_id] = task
            saved = task

        self._audit_task_event(saved, AuditAction.TASK_CREATED, "Task created")
        return saved

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        获取任务详情

        Args:
            task_id: 任务ID

        Returns:
            任务对象，如果不存在则返回None
        """
        if self.task_dao:
            return self.task_dao.select_by_id(task_id)
        else:
            return self._tasks.get(task_id)

    def update_task(self, task_id: str, request: TaskUpdateRequest) -> Optional[Task]:
        """
        更新任务

        Args:
            task_id: 任务ID
            request: 更新请求

        Returns:
            更新后的任务，如果不存在则返回None
        """
        if self.task_dao:
            task = self.task_dao.select_by_id(task_id)
            if not task:
                return None

            # 更新字段
            if request.name is not None:
                task.name = request.name
            if request.status is not None:
                if not validate_state_transition("task", task.status, request.status):
                    raise ValueError(f"Invalid state transition: {task.status} -> {request.status}")
                task.status = request.status
            if request.priority is not None:
                task.priority = request.priority
            if request.target_node_id is not None:
                task.target_node_id = request.target_node_id
            if request.description is not None:
                task.description = request.description

            task.updated_at = datetime.utcnow()

            return self.task_dao.update(task)
        else:
            task = self._tasks.get(task_id)
            if not task:
                return None

            # 更新字段
            if request.name is not None:
                task.name = request.name
            if request.status is not None:
                task.status = request.status
            if request.priority is not None:
                task.priority = request.priority
            if request.target_node_id is not None:
                task.target_node_id = request.target_node_id

            task.updated_at = datetime.utcnow()
            return task

    def cancel_task(self, task_id: str) -> Optional[Task]:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            取消后的任务，如果不存在则返回None
        """
        return self.update_task(task_id, TaskUpdateRequest(status=TaskStatus.CANCELLED))

    def list_tasks(self, params: TaskQueryParams = None):
        """
        查询任务列表

        Args:
            params: 查询参数；如果不提供则直接返回任务列表

        Returns:
            任务列表或任务列表响应
        """
        if params is None:
            if self.task_dao:
                return self.task_dao.list()
            return list(self._tasks.values())

        filters = {}
        if params.task_type:
            filters["task_type"] = params.task_type
        if params.status:
            filters["status"] = params.status
        if params.priority:
            filters["priority"] = params.priority
        if params.target_asset_id:
            filters["target_asset_id"] = params.target_asset_id
        if params.target_node_id:
            filters["target_node_id"] = params.target_node_id
        if params.search:
            filters["search"] = params.search

        if self.task_dao:
            tasks = self.task_dao.list(
                filters=filters,
                limit=params.page_size,
                offset=(params.page - 1) * params.page_size,
                order_by=(f"-{params.sort_by}" if params.sort_order == "desc" else params.sort_by),
            )
            total = self.task_dao.count(filters)
        else:
            tasks = list(self._tasks.values())
            total = len(tasks)

        total_pages = math.ceil(total / params.page_size) if params.page_size else 0
        return TaskListResponse(
            tasks=tasks,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    def get_task_stats(self) -> TaskStats:
        """
        获取任务统计信息

        Returns:
            任务统计信息
        """
        if self.task_dao:
            total = self.task_dao.count({})
            status_stats = {
                status.value: self.task_dao.count({"status": status}) for status in TaskStatus
            }
        else:
            tasks = list(self._tasks.values())
            total = len(tasks)
            status_stats = {}
            for task in tasks:
                status_stats[task.status.value] = status_stats.get(task.status.value, 0) + 1

        return TaskStats(
            total_tasks=total,
            by_type={},
            by_status=status_stats,
            by_priority={},
            running_tasks=status_stats.get(TaskStatus.RUNNING.value, 0),
            pending_tasks=status_stats.get(TaskStatus.PENDING.value, 0),
            completed_tasks=(
                status_stats.get(TaskStatus.SUCCEEDED.value, 0)
                + status_stats.get(TaskStatus.CANCELLED.value, 0)
            ),
            failed_tasks=status_stats.get(TaskStatus.FAILED.value, 0),
            success_rate=(
                (100.0 * status_stats.get(TaskStatus.SUCCEEDED.value, 0) / total) if total else 0.0
            ),
        )

    def dispatch_tasks(self, request):
        """
        分发任务到节点

        Args:
            request: 任务分发请求

        Returns:
            分发结果
        """
        # 这里简化实现，实际需要调用TaskScheduler
        dispatched = []
        for task_id in request.task_ids:
            task = self.get_task(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.ASSIGNED
                task.target_node_id = request.target_node_id
                task.updated_at = datetime.utcnow()

                if self.task_dao:
                    self.task_dao.update(task)

                self.scheduler.add_to_pending(task)
                dispatched.append(task)

        return {"dispatched": len(dispatched)}

    def assign_node_to_task(self, task_id: str, node_id: str) -> Optional[Task]:
        task = self.get_task(task_id)
        if not task:
            return None
        task.status = TaskStatus.ASSIGNED
        task.target_node_id = node_id
        task.updated_at = datetime.utcnow()
        if self.task_dao:
            updated = self.task_dao.update(task)
        else:
            updated = task
        self._audit_task_event(updated, AuditAction.TASK_ASSIGNED, "Task assigned")
        return updated

    def start_task(self, task_id: str, node_id: str) -> Optional[Task]:
        """
        开始执行任务

        Args:
            task_id: 任务ID
            node_id: 执行节点ID

        Returns:
            更新后的任务
        """
        task = self.get_task(task_id)
        if not task:
            return None

        task.status = TaskStatus.RUNNING
        task.target_node_id = node_id
        task.started_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()

        if self.task_dao:
            updated = self.task_dao.update(task)
        else:
            updated = task
        self._audit_task_event(updated, AuditAction.TASK_STARTED, "Task started")
        return updated

    def submit_task_result(self, task_id: str, result) -> Optional[Task]:
        """
        提交任务结果

        Args:
            task_id: 任务ID
            result: 任务执行结果

        Returns:
            更新后的任务
        """
        task = self.get_task(task_id)
        if not task:
            return None

        task.result = result
        task.status = TaskStatus.SUCCEEDED if result.exit_code == 0 else TaskStatus.FAILED
        task.completed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()

        if self.task_dao:
            updated = self.task_dao.update(task)
        else:
            updated = task
        self._audit_task_event(
            updated,
            (AuditAction.TASK_SUCCEEDED if result.exit_code == 0 else AuditAction.TASK_FAILED),
            "Task completed",
        )
        return updated

    def complete_task(self, task_id: str, result) -> Optional[Task]:
        """兼容旧测试的完成任务接口"""
        return self.submit_task_result(task_id, result)

    def get_pending_tasks_for_node(self, node_id: str, limit: int = 10) -> List[Task]:
        """
        获取节点的待执行任务列表

        Args:
            node_id: 节点ID
            limit: 最大返回数量

        Returns:
            待执行任务列表
        """
        if self.task_dao:
            # 查询分配给该节点且状态为PENDING或ASSIGNED的任务
            filters = {
                "target_node_id": node_id,
                "status": [TaskStatus.PENDING, TaskStatus.ASSIGNED],
            }
            tasks = self.task_dao.list(filters=filters, limit=limit, order_by="-created_at")
            return tasks
        else:
            # 内存实现
            pending_tasks = [
                task
                for task in self._tasks.values()
                if task.target_node_id == node_id
                and task.status in [TaskStatus.PENDING, TaskStatus.ASSIGNED]
            ]
            # 按创建时间排序
            pending_tasks.sort(key=lambda t: t.created_at, reverse=True)
            return pending_tasks[:limit]

    def _audit_task_event(self, task: Task, action: AuditAction, message: str) -> None:
        if not self.database:
            return
        from shared.services.audit_service import AuditService

        audit_service = AuditService(database=self.database)
        audit_service.log_action(
            AuditLogCreateRequest(
                action=action,
                category=AuditCategory.TASK,
                level=(EventLevel.ERROR if action == AuditAction.TASK_FAILED else EventLevel.INFO),
                actor="system",
                target_type="task",
                target_id=task.task_id,
                related_task_id=task.task_id,
                related_asset_id=task.target_asset_id,
                related_node_id=task.target_node_id,
                message=message,
                details={
                    "task_name": task.name,
                    "status": task.status.value,
                    "target_asset_id": task.target_asset_id,
                    "target_node_id": task.target_node_id,
                },
            )
        )


# 全局服务实例（用于简单的单例模式）
_task_service_instance = None


def get_task_service(database=None):
    """
    获取任务服务实例（单例模式）

    Args:
        database: 数据库实例（首次调用时提供）

    Returns:
        TaskService 实例
    """
    global _task_service_instance
    if _task_service_instance is None:
        _task_service_instance = TaskService(database=database)
    elif database is not None and _task_service_instance.database is None:
        # 如果首次创建时没有数据库，但后续提供了数据库，则重新创建
        _task_service_instance = TaskService(database=database)
    return _task_service_instance
