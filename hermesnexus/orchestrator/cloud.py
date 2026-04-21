"""
云端任务编排器 - Week 5-6
支持批量任务调度和云边协同
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
import uuid

from hermesnexus.task.manager import TaskManager
from hermesnexus.task.model import Task, TaskStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BatchScheduleResult:
    """批量调度结果"""
    batch_id: str
    total_devices: int
    successful_schedules: int
    failed_schedules: int
    task_ids: List[str] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class DeviceGroup:
    """设备分组"""
    group_id: str
    group_name: str
    device_ids: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_device(self, device_id: str) -> None:
        """添加设备到分组"""
        if device_id not in self.device_ids:
            self.device_ids.append(device_id)

    def remove_device(self, device_id: str) -> None:
        """从分组移除设备"""
        if device_id in self.device_ids:
            self.device_ids.remove(device_id)


class CloudTaskOrchestrator:
    """云端任务编排器 - Week 5-6核心功能"""

    def __init__(self, edge_nodes_config: Dict[str, str], task_manager: TaskManager):
        """
        初始化云端任务编排器

        Args:
            edge_nodes_config: 边缘节点配置 {node_id: base_url}
            task_manager: 任务管理器实例
        """
        self.edge_nodes = edge_nodes_config
        self.task_manager = task_manager
        self.device_groups: Dict[str, DeviceGroup] = {}
        self.active_batches: Dict[str, BatchScheduleResult] = {}

        logger.info(f"CloudTaskOrchestrator initialized with {len(edge_nodes_config)} edge nodes")

    def schedule_task_to_devices(
        self,
        task_spec: Dict[str, Any],
        device_ids: List[str],
        batch_id: Optional[str] = None,
        parallel: bool = True
    ) -> BatchScheduleResult:
        """
        调度任务到多个设备

        Args:
            task_spec: 任务规格 {name, command, description, priority, etc.}
            device_ids: 目标设备ID列表
            batch_id: 批次ID（可选，自动生成）
            parallel: 是否并行调度

        Returns:
            BatchScheduleResult: 批量调度结果
        """
        if not batch_id:
            batch_id = str(uuid.uuid4())

        logger.info(f"Scheduling batch {batch_id} to {len(device_ids)} devices")

        result = BatchScheduleResult(
            batch_id=batch_id,
            total_devices=len(device_ids),
            successful_schedules=0,
            failed_schedules=0
        )

        if parallel:
            # 并行调度
            tasks = [
                self._schedule_single_task(task_spec, device_id, result)
                for device_id in device_ids
            ]
            # 在真实环境中这里会使用asyncio，当前简化为同步
            for task in tasks:
                task()  # 执行单个任务调度
        else:
            # 串行调度
            for device_id in device_ids:
                self._schedule_single_task(task_spec, device_id, result)()

        # 保存批次结果
        self.active_batches[batch_id] = result

        logger.info(
            f"Batch {batch_id} completed: "
            f"{result.successful_schedules}/{result.total_devices} successful"
        )

        return result

    def _schedule_single_task(
        self,
        task_spec: Dict[str, Any],
        device_id: str,
        result: BatchScheduleResult
    ) -> Callable:
        """创建单个任务调度的可调用对象"""

        def _execute():
            try:
                # 为每个设备创建独立任务
                task_name = f"{task_spec['name']}_{device_id}"
                task_description = task_spec.get('description', f"Task for device {device_id}")

                task = Task.create(
                    name=task_name,
                    description=task_description,
                    command=task_spec['command'],
                    target_device_id=device_id,
                    created_by=task_spec.get('created_by', 'orchestrator')
                )

                # 保存任务到任务管理器
                self.task_manager.create_task(task)

                # 记录成功
                result.task_ids.append(task.task_id)
                result.successful_schedules += 1

                logger.debug(f"Successfully scheduled task {task.task_id} for device {device_id}")

            except Exception as e:
                # 记录失败
                result.errors[device_id] = str(e)
                result.failed_schedules += 1
                logger.error(f"Failed to schedule task for device {device_id}: {e}")

        return _execute

    def schedule_task_to_group(
        self,
        task_spec: Dict[str, Any],
        group_id: str,
        parallel: bool = True
    ) -> BatchScheduleResult:
        """
        调度任务到设备分组

        Args:
            task_spec: 任务规格
            group_id: 设备分组ID
            parallel: 是否并行调度

        Returns:
            BatchScheduleResult: 批量调度结果
        """
        if group_id not in self.device_groups:
            raise ValueError(f"Device group '{group_id}' not found")

        group = self.device_groups[group_id]
        batch_id = f"group_{group_id}_{uuid.uuid4()}"

        logger.info(f"Scheduling task to group '{group_id}' ({len(group.device_ids)} devices)")

        return self.schedule_task_to_devices(
            task_spec,
            group.device_ids,
            batch_id=batch_id,
            parallel=parallel
        )

    def create_device_group(
        self,
        group_id: str,
        group_name: str,
        device_ids: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> DeviceGroup:
        """
        创建设备分组

        Args:
            group_id: 分组ID
            group_name: 分组名称
            device_ids: 设备ID列表
            metadata: 元数据（可选）

        Returns:
            DeviceGroup: 设备分组对象
        """
        if group_id in self.device_groups:
            logger.warning(f"Device group '{group_id}' already exists, updating...")

        group = DeviceGroup(
            group_id=group_id,
            group_name=group_name,
            device_ids=device_ids.copy(),
            metadata=metadata or {}
        )

        self.device_groups[group_id] = group
        logger.info(f"Created device group '{group_id}' with {len(device_ids)} devices")

        return group

    def get_batch_status(self, batch_id: str) -> Optional[BatchScheduleResult]:
        """
        获取批次调度状态

        Args:
            batch_id: 批次ID

        Returns:
            BatchScheduleResult: 批次调度结果，如果不存在返回None
        """
        return self.active_batches.get(batch_id)

    def get_active_batches(self) -> Dict[str, BatchScheduleResult]:
        """获取所有活跃批次"""
        return self.active_batches.copy()

    def get_device_groups(self) -> Dict[str, DeviceGroup]:
        """获取所有设备分组"""
        return self.device_groups.copy()

    def remove_device_group(self, group_id: str) -> bool:
        """
        移除设备分组

        Args:
            group_id: 分组ID

        Returns:
            bool: 是否成功移除
        """
        if group_id not in self.device_groups:
            return False

        del self.device_groups[group_id]
        logger.info(f"Removed device group '{group_id}'")
        return True

    def get_batch_progress(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        获取批次进度信息

        Args:
            batch_id: 批次ID

        Returns:
            Dict with progress info: {
                'batch_id': str,
                'total_devices': int,
                'successful': int,
                'failed': int,
                'progress_percentage': float,
                'status': str
            }
        """
        result = self.get_batch_status(batch_id)
        if not result:
            return None

        total = result.total_devices
        completed = result.successful_schedules + result.failed_schedules
        progress_percentage = (completed / total * 100) if total > 0 else 0

        # 确定批次状态
        if completed == total:
            status = "completed"
        elif completed == 0:
            status = "pending"
        else:
            status = "in_progress"

        return {
            'batch_id': result.batch_id,
            'total_devices': total,
            'successful': result.successful_schedules,
            'failed': result.failed_schedules,
            'progress_percentage': round(progress_percentage, 2),
            'status': status,
            'created_at': result.created_at.isoformat() if result.created_at else None
        }


class MVPOrchestratorFactory:
    """MVP编排器工厂 - 简化编排器创建"""

    @staticmethod
    def create_with_default_config(task_manager: TaskManager) -> CloudTaskOrchestrator:
        """创建带默认配置的编排器"""
        # MVP阶段使用简单的边缘节点配置
        edge_nodes_config = {
            'edge_node_1': 'http://localhost:8001',
            'edge_node_2': 'http://localhost:8002'
        }

        orchestrator = CloudTaskOrchestrator(edge_nodes_config, task_manager)

        # 创建MVP设备分组
        orchestrator.create_device_group(
            'routers', 'Core Routers',
            ['router-001', 'router-002'],
            {'location': 'datacenter', 'priority': 'high'}
        )

        orchestrator.create_device_group(
            'servers', 'Web Servers',
            ['server-001', 'server-002', 'server-003'],
            {'location': 'dmz', 'priority': 'medium'}
        )

        return orchestrator


# MVP示例用法
if __name__ == "__main__":
    import tempfile
    import os
    from hermesnexus.task.manager import TaskManager

    # 创建临时数据库用于测试
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    try:
        # 初始化
        task_manager = TaskManager(db_path)
        orchestrator = MVPOrchestratorFactory.create_with_default_config(task_manager)

        # 示例1: 批量调度到设备列表
        task_spec = {
            'name': '系统巡检',
            'command': 'uptime && df -h',
            'description': '检查系统健康状态',
            'created_by': 'admin'
        }

        devices = ['server-001', 'server-002', 'server-003']
        result = orchestrator.schedule_task_to_devices(task_spec, devices)

        print(f"批量调度完成:")
        print(f"  总设备数: {result.total_devices}")
        print(f"  成功: {result.successful_schedules}")
        print(f"  失败: {result.failed_schedules}")
        print(f"  任务IDs: {result.task_ids}")

        # 示例2: 调度到设备分组
        group_result = orchestrator.schedule_task_to_group(
            task_spec,
            'routers'
        )

        print(f"\n分组调度完成:")
        print(f"  分组: routers")
        print(f"  成功: {group_result.successful_schedules}")

        # 示例3: 查询批次进度
        progress = orchestrator.get_batch_progress(result.batch_id)
        print(f"\n批次进度:")
        print(f"  进度: {progress['progress_percentage']}%")
        print(f"  状态: {progress['status']}")

    finally:
        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)