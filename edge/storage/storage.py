"""
边缘节点存储管理

提供本地状态存储和任务管理
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path

from shared.protocol.messages import TaskMessage, ResultMessage
from shared.schemas.models import JobStatus, JobType

logger = logging.getLogger(__name__)


class EdgeStorage:
    """边缘节点本地存储"""

    def __init__(self, storage_dir: str = "./edge/storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 内存状态
        self.tasks: Dict[str, TaskMessage] = {}
        self.task_results: Dict[str, ResultMessage] = {}
        self.task_status: Dict[str, str] = {}

        # 文件路径
        self.tasks_file = self.storage_dir / "tasks.json"
        self.results_file = self.storage_dir / "results.json"

        # 加载已有状态
        self._load_state()

    def _load_state(self):
        """加载持久化状态"""
        try:
            if self.tasks_file.exists():
                with open(self.tasks_file, "r") as f:
                    data = json.load(f)
                    # 恢复任务状态
                    for task_id, task_data in data.get("tasks", {}).items():
                        self.task_status[task_id] = task_data.get(
                            "status", JobStatus.PENDING
                        )
                logger.info(f"✅ 加载了 {len(self.task_status)} 个任务状态")
        except Exception as e:
            logger.warning(f"⚠️  加载状态失败: {e}")

    def _save_state(self):
        """保存状态到磁盘"""
        try:
            state = {
                "tasks": {
                    task_id: {"status": status}
                    for task_id, status in self.task_status.items()
                },
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.tasks_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"❌ 保存状态失败: {e}")

    def add_task(self, task: TaskMessage) -> bool:
        """添加新任务"""
        try:
            self.tasks[task.task_id] = task
            self.task_status[task.task_id] = JobStatus.PENDING
            self._save_state()
            logger.info(f"✅ 添加任务: {task.task_id}")
            return True
        except Exception as e:
            logger.error(f"❌ 添加任务失败: {e}")
            return False

    def get_task(self, task_id: str) -> Optional[TaskMessage]:
        """获取任务"""
        return self.tasks.get(task_id)

    def get_pending_tasks(self) -> List[TaskMessage]:
        """获取待处理任务"""
        return [
            task
            for task_id, task in self.tasks.items()
            if self.task_status.get(task_id) == JobStatus.PENDING
        ]

    def update_task_status(self, task_id: str, status: str) -> bool:
        """更新任务状态"""
        try:
            if task_id in self.tasks:
                self.task_status[task_id] = status
                self._save_state()
                logger.debug(f"📊 任务状态更新: {task_id} -> {status}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ 更新任务状态失败: {e}")
            return False

    def save_result(self, result: ResultMessage) -> bool:
        """保存任务结果"""
        try:
            self.task_results[result.task_id] = result
            self.update_task_status(result.task_id, result.status)
            logger.info(f"✅ 保存任务结果: {result.task_id}")
            return True
        except Exception as e:
            logger.error(f"❌ 保存任务结果失败: {e}")
            return False

    def get_result(self, task_id: str) -> Optional[ResultMessage]:
        """获取任务结果"""
        return self.task_results.get(task_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_tasks = len(self.tasks)
        pending_tasks = len(
            [t for t, s in self.task_status.items() if s == JobStatus.PENDING]
        )
        running_tasks = len(
            [t for t, s in self.task_status.items() if s == JobStatus.RUNNING]
        )
        success_tasks = len(
            [t for t, s in self.task_status.items() if s == JobStatus.SUCCESS]
        )
        failed_tasks = len(
            [t for t, s in self.task_status.items() if s in JobStatus.FAILED]
        )

        return {
            "total_tasks": total_tasks,
            "pending_tasks": pending_tasks,
            "running_tasks": running_tasks,
            "success_tasks": success_tasks,
            "failed_tasks": failed_tasks,
            "active_tasks": pending_tasks + running_tasks,
        }

    def cleanup_old_tasks(self, keep_count: int = 100):
        """清理旧任务"""
        try:
            if len(self.tasks) > keep_count:
                # 按时间排序，删除最老的任务
                sorted_tasks = sorted(self.tasks.items(), key=lambda x: x[1].timestamp)
                tasks_to_remove = sorted_tasks[:-keep_count]

                for task_id, _ in tasks_to_remove:
                    del self.tasks[task_id]
                    if task_id in self.task_results:
                        del self.task_results[task_id]
                    if task_id in self.task_status:
                        del self.task_status[task_id]

                self._save_state()
                logger.info(f"🧹 清理了 {len(tasks_to_remove)} 个旧任务")
        except Exception as e:
            logger.error(f"❌ 清理任务失败: {e}")

    def clear(self):
        """清空所有数据"""
        self.tasks.clear()
        self.task_results.clear()
        self.task_status.clear()
        self._save_state()
        logger.info("🗑️  已清空所有任务数据")
