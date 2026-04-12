"""
HermesNexus Phase 2 - Task DAO
任务数据访问对象
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import or_

from shared.dao.base_dao import BaseDAO
from shared.database.models import TaskModel
from shared.models.task import (
    Task,
    TaskExecutionResult,
)


class TaskDAO(BaseDAO):
    """任务数据访问对象"""

    @staticmethod
    def _json_safe(value):
        from datetime import datetime

        if isinstance(value, dict):
            return {k: TaskDAO._json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [TaskDAO._json_safe(v) for v in value]
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @staticmethod
    def _normalize_status_filter(status):
        if status is None:
            return None
        if isinstance(status, list):
            values = []
            for item in status:
                normalized = TaskDAO._normalize_status_filter(item)
                if isinstance(normalized, list):
                    values.extend(normalized)
                else:
                    values.append(normalized)
            return list(dict.fromkeys(values))
        if hasattr(status, "value"):
            status = status.value
        if status == "completed":
            return ["succeeded", "completed"]
        return status

    def insert(self, task: Task) -> Task:
        """
        插入任务

        Args:
            task: 任务对象

        Returns:
            插入后的任务对象
        """
        session = self._get_session()

        try:
            # 准备result数据
            result_data = None
            if task.result:
                result_data = self._json_safe(task.result.dict())

            # 创建ORM模型实例
            task_model = TaskModel(
                task_id=task.task_id,
                name=task.name,
                task_type=task.task_type,
                status=task.status,
                priority=task.priority,
                target_asset_id=task.target_asset_id,
                assigned_node_id=task.target_node_id,
                command=task.command,
                script_content=None,  # Task模型没有此字段，保持数据库兼容
                timeout=task.timeout,
                description=task.description,
                result_data=result_data,
                created_by=task.created_by,
                created_at=task.created_at,
                updated_at=task.updated_at,
                started_at=task.started_at,
                completed_at=task.completed_at,
            )

            # 插入数据库
            session.add(task_model)
            session.commit()
            session.refresh(task_model)

            # 返回任务对象
            return task

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to insert task: {e}")
        finally:
            session.close()

    def select_by_id(self, task_id: str) -> Optional[Task]:
        """
        按ID查询任务

        Args:
            task_id: 任务ID

        Returns:
            任务对象，如果不存在则返回None
        """
        session = self._get_session()

        try:
            # 查询数据库
            task_model = (
                session.query(TaskModel).filter(TaskModel.task_id == task_id).first()
            )

            if not task_model:
                return None

            # 转换为任务对象
            return self._model_to_task(task_model)

        finally:
            session.close()

    def update(self, task: Task) -> Task:
        """
        更新任务

        Args:
            task: 任务对象

        Returns:
            更新后的任务对象
        """
        session = self._get_session()

        try:
            # 查询现有任务
            task_model = (
                session.query(TaskModel)
                .filter(TaskModel.task_id == task.task_id)
                .first()
            )

            if not task_model:
                raise ValueError(f"Task not found: {task.task_id}")

            # 更新基本字段
            task_model.name = task.name
            task_model.task_type = task.task_type
            task_model.status = task.status
            task_model.priority = task.priority
            task_model.target_asset_id = task.target_asset_id
            task_model.assigned_node_id = task.target_node_id
            task_model.command = task.command
            # script_content 不更新，Task模型没有此字段
            task_model.timeout = task.timeout
            task_model.description = task.description

            # 更新result字段
            if task.result:
                task_model.result_data = self._json_safe(task.result.dict())
            else:
                task_model.result_data = None

            # 更新时间字段
            task_model.updated_at = datetime.utcnow()
            if task.started_at:
                task_model.started_at = task.started_at
            if task.completed_at:
                task_model.completed_at = task.completed_at

            # 提交更改
            session.commit()
            session.refresh(task_model)

            return task

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to update task: {e}")
        finally:
            session.close()

    def delete(self, task_id: str) -> bool:
        """
        删除任务

        Args:
            task_id: 任务ID

        Returns:
            是否删除成功
        """
        session = self._get_session()

        try:
            # 查询并删除任务
            task_model = (
                session.query(TaskModel).filter(TaskModel.task_id == task_id).first()
            )

            if not task_model:
                return False

            session.delete(task_model)
            session.commit()

            return True

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to delete task: {e}")
        finally:
            session.close()

    def list(
        self,
        filters: Dict[str, Any] = None,
        limit: int = None,
        offset: int = None,
        order_by: str = None,
    ) -> List[Task]:
        """
        查询任务列表

        Args:
            filters: 过滤条件字典
            limit: 返回数量限制
            offset: 偏移量
            order_by: 排序字段

        Returns:
            任务列表
        """
        session = self._get_session()

        try:
            # 构建查询
            query = session.query(TaskModel)

            # 应用过滤条件
            if filters:
                if "task_type" in filters:
                    query = query.filter(TaskModel.task_type == filters["task_type"])
                if "status" in filters:
                    status_filter = self._normalize_status_filter(filters["status"])
                    if isinstance(status_filter, list):
                        query = query.filter(TaskModel.status.in_(status_filter))
                    else:
                        query = query.filter(TaskModel.status == status_filter)
                if "priority" in filters:
                    query = query.filter(TaskModel.priority == filters["priority"])
                if "target_asset_id" in filters:
                    query = query.filter(
                        TaskModel.target_asset_id == filters["target_asset_id"]
                    )
                if "target_node_id" in filters:
                    query = query.filter(
                        TaskModel.assigned_node_id == filters["target_node_id"]
                    )
                if "search" in filters:
                    search_term = f"%{filters['search']}%"
                    query = query.filter(
                        or_(
                            TaskModel.name.like(search_term),
                            TaskModel.description.like(search_term),
                            TaskModel.command.like(search_term),
                        )
                    )

            # 应用排序
            if order_by:
                if order_by.startswith("-"):
                    # 降序
                    field = order_by[1:]
                    query = query.order_by(getattr(TaskModel, field).desc())
                else:
                    # 升序
                    query = query.order_by(getattr(TaskModel, order_by))

            # 应用分页
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)

            # 执行查询
            task_models = query.all()

            # 转换为任务对象列表
            return [self._model_to_task(model) for model in task_models]

        finally:
            session.close()

    def count(self, filters: Dict[str, Any] = None) -> int:
        """
        统计任务数量

        Args:
            filters: 过滤条件字典

        Returns:
            任务数量
        """
        session = self._get_session()

        try:
            # 构建查询
            query = session.query(TaskModel)

            # 应用过滤条件
            if filters:
                if "task_type" in filters:
                    query = query.filter(TaskModel.task_type == filters["task_type"])
                if "status" in filters:
                    status_filter = self._normalize_status_filter(filters["status"])
                    if isinstance(status_filter, list):
                        query = query.filter(TaskModel.status.in_(status_filter))
                    else:
                        query = query.filter(TaskModel.status == status_filter)
                if "priority" in filters:
                    query = query.filter(TaskModel.priority == filters["priority"])
                if "target_asset_id" in filters:
                    query = query.filter(
                        TaskModel.target_asset_id == filters["target_asset_id"]
                    )

            # 统计数量
            return query.count()

        finally:
            session.close()

    def _model_to_task(self, model: TaskModel) -> Task:
        """
        将ORM模型转换为任务对象

        Args:
            model: ORM模型

        Returns:
            任务对象
        """
        # 构建result对象
        result = None
        if model.result_data:
            result = TaskExecutionResult(**model.result_data)

        # 构建任务对象
        return Task(
            task_id=model.task_id,
            name=model.name,
            task_type=model.task_type,
            status=model.status,
            priority=model.priority,
            target_asset_id=model.target_asset_id,
            target_node_id=model.assigned_node_id,
            command=model.command,
            # script_content 不映射，Task模型没有此字段
            timeout=model.timeout,
            description=model.description,
            created_by=model.created_by,
            result=result,
            created_at=model.created_at,
            updated_at=model.updated_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
        )

    def select_by_ids(self, task_ids: List[str]) -> List[Task]:
        """
        批量查询任务 - 解决N+1查询问题

        Args:
            task_ids: 任务ID列表

        Returns:
            任务对象列表
        """
        if not task_ids:
            return []

        session = self._get_session()

        try:
            # 批量查询 - 一次查询获取所有数据
            task_models = (
                session.query(TaskModel).filter(TaskModel.task_id.in_(task_ids)).all()
            )

            # 转换为任务对象列表
            return [self._model_to_task(model) for model in task_models]

        finally:
            session.close()

    def insert_batch(self, tasks: List[Task]) -> List[Task]:
        """
        批量插入任务 - 提升插入性能

        Args:
            tasks: 任务对象列表

        Returns:
            插入后的任务对象列表
        """
        if not tasks:
            return []

        session = self._get_session()

        try:
            # 创建ORM模型实例列表
            task_models = []
            for task in tasks:
                # 处理result数据
                result_data = None
                if task.result:
                    result_data = {
                        "exit_code": task.result.exit_code,
                        "stdout": task.result.stdout,
                        "stderr": task.result.stderr,
                        "completed_at": (
                            task.result.completed_at.isoformat()
                            if task.result.completed_at
                            else None
                        ),
                    }

                task_model = TaskModel(
                    task_id=task.task_id,
                    name=task.name,
                    task_type=task.task_type,
                    status=task.status,
                    priority=task.priority,
                    target_asset_id=task.target_asset_id,
                    assigned_node_id=task.target_node_id,
                    command=task.command,
                    timeout=task.timeout,
                    description=task.description,
                    created_by=task.created_by,
                    result_data=result_data,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                    started_at=task.started_at,
                    completed_at=task.completed_at,
                )
                task_models.append(task_model)

            # 批量插入 - 减少数据库往返次数
            session.add_all(task_models)
            session.commit()

            return tasks

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to batch insert tasks: {e}")
        finally:
            session.close()

    def update_batch(self, tasks: List[Task]) -> List[Task]:
        """
        批量更新任务 - 提升更新性能

        Args:
            tasks: 任务对象列表

        Returns:
            更新后的任务对象列表
        """
        if not tasks:
            return []

        session = self._get_session()

        try:
            updated_tasks = []
            current_time = datetime.utcnow()

            for task in tasks:
                # 查询并更新每个任务
                task_model = (
                    session.query(TaskModel)
                    .filter(TaskModel.task_id == task.task_id)
                    .first()
                )

                if task_model:
                    # 更新字段
                    task_model.name = task.name
                    task_model.status = task.status
                    task_model.priority = task.priority
                    task_model.updated_at = current_time
                    if task.started_at:
                        task_model.started_at = task.started_at
                    if task.completed_at:
                        task_model.completed_at = task.completed_at
                    if task.result:
                        task_model.result_data = {
                            "exit_code": task.result.exit_code,
                            "stdout": task.result.stdout,
                            "stderr": task.result.stderr,
                            "completed_at": (
                                task.result.completed_at.isoformat()
                                if task.result.completed_at
                                else None
                            ),
                        }

                    updated_tasks.append(task)

            # 批量提交 - 减少事务开销
            session.commit()

            return updated_tasks

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to batch update tasks: {e}")
        finally:
            session.close()
