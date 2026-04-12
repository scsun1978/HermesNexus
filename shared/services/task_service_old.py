"""
HermesNexus Phase 2 - Task Service
任务编排业务逻辑层
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from shared.models.task import (
    Task, TaskCreateRequest, TaskUpdateRequest,
    TaskQueryParams, TaskListResponse, TaskStats,
    TaskDispatchRequest, TaskResultSubmit,
    TaskType, TaskStatus, TaskPriority
)
from shared.models.enums import validate_state_transition


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
    """任务管理服务"""

    def __init__(self, database=None):
        """
        初始化任务服务

        Args:
            database: 数据库实例（可以是 SQLAlchemy, SQLite 等）
        """
        self.database = database
        self._tasks: Dict[str, Task] = {}  # 内存存储（Phase 2 MVP）
        self.scheduler = TaskScheduler()

    def create_task(self, request: TaskCreateRequest, created_by: str) -> Task:
        """
        创建任务

        Args:
            request: 任务创建请求
            created_by: 创建者

        Returns:
            创建的任务

        Raises:
            ValueError: 如果任务ID已存在
        """
        # 生成或使用提供的任务ID
        task_id = request.task_id or f"task-{uuid.uuid4().hex[:8]}"

        # 检查ID是否已存在
        if task_id in self._tasks:
            raise ValueError(f"Task with ID '{task_id}' already exists")

        # 创建任务对象
        task = Task(
            task_id=task_id,
            name=request.name,
            task_type=request.task_type,
            status=TaskStatus.PENDING,
            priority=request.priority,
            target_asset_id=request.target_asset_id,
            command=request.command,
            arguments=request.arguments,
            working_dir=request.working_dir,
            environment=request.environment,
            timeout=request.timeout,
            retry_count=request.retry_count,
            retry_delay=request.retry_delay,
            scheduled_at=request.scheduled_at,
            created_by=created_by,
            description=request.description,
            tags=request.tags,
            metadata=request.metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # 保存任务
        self._tasks[task_id] = task

        # 添加到待调度队列
        if task.status == TaskStatus.PENDING:
            self.scheduler.add_to_pending(task)

        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        获取任务详情

        Args:
            task_id: 任务ID

        Returns:
            任务对象，如果不存在则返回 None
        """
        return self._tasks.get(task_id)

    def update_task(self, task_id: str, request: TaskUpdateRequest) -> Optional[Task]:
        """
        更新任务

        Args:
            task_id: 任务ID
            request: 更新请求

        Returns:
            更新后的任务，如果不存在则返回 None

        Raises:
            ValueError: 如果状态转换不合法
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        # 更新字段
        if request.name is not None:
            task.name = request.name
        if request.priority is not None:
            task.priority = request.priority
        if request.description is not None:
            task.description = request.description
        if request.tags is not None:
            task.tags = request.tags
        if request.metadata is not None:
            task.metadata = request.metadata

        # 状态转换验证
        if request.status is not None:
            validate_state_transition(task.status, request.status, "task")
            task.status = request.status

            # 状态转换处理
            if request.status == TaskStatus.PENDING:
                self.scheduler.add_to_pending(task)
            elif task_id in self.scheduler._pending_tasks:
                self.scheduler.remove_from_pending(task_id)

        task.updated_at = datetime.utcnow()

        return task

    def list_tasks(self, params: TaskQueryParams) -> TaskListResponse:
        """
        列出任务

        Args:
            params: 查询参数

        Returns:
            任务列表响应
        """
        # 获取所有任务
        tasks = list(self._tasks.values())

        # 应用过滤
        if params.task_type:
            tasks = [t for t in tasks if t.task_type == params.task_type]

        if params.status:
            tasks = [t for t in tasks if t.status == params.status]

        if params.priority:
            tasks = [t for t in tasks if t.priority == params.priority]

        if params.target_asset_id:
            tasks = [t for t in tasks if t.target_asset_id == params.target_asset_id]

        if params.target_node_id:
            tasks = [t for t in tasks if t.target_node_id == params.target_node_id]

        if params.created_by:
            tasks = [t for t in tasks if t.created_by == params.created_by]

        if params.search:
            search_lower = params.search.lower()
            tasks = [
                t for t in tasks
                if search_lower in t.name.lower() or
                (t.description and search_lower in t.description.lower()) or
                search_lower in t.command.lower()
            ]

        if params.tags:
            tasks = [
                t for t in tasks
                if any(tag in t.tags for tag in params.tags)
            ]

        # 排序
        reverse = params.sort_order == "desc"
        if hasattr(Task, params.sort_by):
            tasks.sort(key=lambda t: getattr(t, params.sort_by), reverse=reverse)
        else:
            # 按优先级排序（urgent > high > normal > low）
            priority_order = {
                TaskPriority.URGENT: 4,
                TaskPriority.HIGH: 3,
                TaskPriority.NORMAL: 2,
                TaskPriority.LOW: 1
            }
            tasks.sort(key=lambda t: priority_order.get(t.priority, 0), reverse=reverse)

        # 分页
        total = len(tasks)
        start = (params.page - 1) * params.page_size
        end = start + params.page_size
        paged_tasks = tasks[start:end]

        total_pages = (total + params.page_size - 1) // params.page_size

        return TaskListResponse(
            total=total,
            tasks=paged_tasks,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages
        )

    def get_task_stats(self) -> TaskStats:
        """
        获取任务统计信息

        Returns:
            任务统计信息
        """
        tasks = list(self._tasks.values())

        # 按类型统计
        by_type: Dict[str, int] = {}
        for task_type in TaskType:
            count = sum(1 for t in tasks if t.task_type == task_type)
            by_type[task_type.value] = count

        # 按状态统计
        by_status: Dict[str, int] = {}
        for status in TaskStatus:
            count = sum(1 for t in tasks if t.status == status)
            by_status[status.value] = count

        # 按优先级统计
        by_priority: Dict[str, int] = {}
        for priority in TaskPriority:
            count = sum(1 for t in tasks if t.priority == priority)
            by_priority[priority.value] = count

        # 执行统计
        running_tasks = sum(1 for t in tasks if t.status == TaskStatus.RUNNING)
        pending_tasks = sum(1 for t in tasks if t.status == TaskStatus.PENDING)
        completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.SUCCEEDED)
        failed_tasks = sum(1 for t in tasks if t.status in [TaskStatus.FAILED, TaskStatus.TIMEOUT])

        # 成功率计算
        total_finished = completed_tasks + failed_tasks
        success_rate = (completed_tasks / total_finished * 100) if total_finished > 0 else 0.0

        return TaskStats(
            total_tasks=len(tasks),
            by_type=by_type,
            by_status=by_status,
            by_priority=by_priority,
            running_tasks=running_tasks,
            pending_tasks=pending_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            success_rate=round(success_rate, 1)
        )

    def dispatch_tasks(self, request: TaskDispatchRequest) -> List[Task]:
        """
        分发任务到节点

        Args:
            request: 分发请求

        Returns:
            分发的任务列表

        Raises:
            ValueError: 如果任务不存在或状态不正确
        """
        dispatched_tasks = []

        for task_id in request.task_ids:
            task = self._tasks.get(task_id)
            if not task:
                raise ValueError(f"Task '{task_id}' not found")

            # 验证任务状态
            if task.status != TaskStatus.PENDING:
                raise ValueError(
                    f"Task '{task_id}' is not in PENDING status (current: {task.status})"
                )

            # 更新任务状态
            task.status = TaskStatus.ASSIGNED
            task.target_node_id = request.target_node_id
            task.assigned_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()

            # 从待调度队列移除
            self.scheduler.remove_from_pending(task_id)

            # 更新节点负载
            self.scheduler.update_node_load(request.target_node_id, 1)

            dispatched_tasks.append(task)

        return dispatched_tasks

    def start_task(self, task_id: str) -> Optional[Task]:
        """
        开始执行任务

        Args:
            task_id: 任务ID

        Returns:
            更新后的任务，如果不存在则返回 None
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        # 状态转换
        if task.status != TaskStatus.ASSIGNED:
            raise ValueError(
                f"Task '{task_id}' is not in ASSIGNED status (current: {task.status})"
            )

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()

        return task

    def submit_task_result(self, submission: TaskResultSubmit) -> Optional[Task]:
        """
        提交任务执行结果

        Args:
            submission: 结果提交

        Returns:
            更新后的任务，如果不存在则返回 None
        """
        task = self._tasks.get(submission.task_id)
        if not task:
            return None

        # 验证节点ID
        if task.target_node_id != submission.node_id:
            raise ValueError(
                f"Node ID mismatch: expected {task.target_node_id}, got {submission.node_id}"
            )

        # 更新状态和结果
        task.status = submission.status
        task.result = submission.result
        task.completed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()

        # 从节点负载中移除
        if task.target_node_id:
            self.scheduler.update_node_load(task.target_node_id, -1)

        return task

    def cancel_task(self, task_id: str) -> Optional[Task]:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            更新后的任务，如果不存在则返回 None

        Raises:
            ValueError: 如果任务无法取消
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        # 检查是否可以取消
        if task.status.is_terminal():
            raise ValueError(
                f"Cannot cancel task in terminal status: {task.status}"
            )

        # 更新状态
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()

        # 从待调度队列移除
        if task_id in self.scheduler._pending_tasks:
            self.scheduler.remove_from_pending(task_id)

        # 从节点负载中移除
        if task.target_node_id:
            self.scheduler.update_node_load(task.target_node_id, -1)

        return task

    def get_pending_tasks_for_node(self, node_id: str, limit: int = 10) -> List[Task]:
        """
        获取节点的待执行任务

        Args:
            node_id: 节点ID
            limit: 最大返回数量

        Returns:
            待执行任务列表
        """
        # 获取分配给该节点的任务
        node_tasks = [
            task for task in self._tasks.values()
            if task.target_node_id == node_id and task.status == TaskStatus.ASSIGNED
        ]

        # 按优先级和创建时间排序
        priority_order = {
            TaskPriority.URGENT: 4,
            TaskPriority.HIGH: 3,
            TaskPriority.NORMAL: 2,
            TaskPriority.LOW: 1
        }

        node_tasks.sort(
            key=lambda t: (priority_order.get(t.priority, 0), t.created_at),
            reverse=True
        )

        return node_tasks[:limit]


# 全局服务实例（Phase 2 MVP 使用内存存储）
_task_service: Optional[TaskService] = None


def get_task_service() -> TaskService:
    """获取全局任务服务实例"""
    global _task_service
    if _task_service is None:
        _task_service = TaskService()
    return _task_service
