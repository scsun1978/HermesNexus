"""
任务管理器单元测试
"""
import pytest
import tempfile
import os
from datetime import datetime
from hermesnexus.task.model import Task, TaskStatus
from hermesnexus.task.manager import TaskManager


class TestTaskManager:
    """TaskManager类测试"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)

    @pytest.fixture
    def task_manager(self, temp_db):
        """创建TaskManager实例"""
        return TaskManager(temp_db)

    @pytest.fixture
    def sample_task(self):
        """创建示例任务"""
        return Task.create(
            name="测试任务",
            description="这是一个测试任务",
            command="ls -la",
            target_device_id="device-001"
        )

    def test_database_initialization(self, task_manager):
        """测试数据库初始化"""
        # 检查表是否创建成功
        import sqlite3
        conn = sqlite3.connect(task_manager.db_path)
        cursor = conn.cursor()

        # 检查v2_tasks表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='v2_tasks'")
        assert cursor.fetchone() is not None

        # 检查task_templates表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='task_templates'")
        assert cursor.fetchone() is not None

        conn.close()

    def test_create_task(self, task_manager, sample_task):
        """测试创建任务"""
        result = task_manager.create_task(sample_task)
        assert result is True

        # 验证任务已保存
        retrieved_task = task_manager.get_task(sample_task.task_id)
        assert retrieved_task is not None
        assert retrieved_task.name == sample_task.name
        assert retrieved_task.command == sample_task.command
        assert retrieved_task.target_device_id == sample_task.target_device_id

    def test_get_task(self, task_manager, sample_task):
        """测试获取任务"""
        # 创建任务
        task_manager.create_task(sample_task)

        # 获取任务
        retrieved_task = task_manager.get_task(sample_task.task_id)
        assert retrieved_task is not None
        assert retrieved_task.task_id == sample_task.task_id
        assert retrieved_task.name == sample_task.name
        assert retrieved_task.description == sample_task.description
        assert retrieved_task.status == TaskStatus.PENDING

    def test_get_nonexistent_task(self, task_manager):
        """测试获取不存在的任务"""
        task = task_manager.get_task("nonexistent-task-id")
        assert task is None

    def test_update_task_status_to_running(self, task_manager, sample_task):
        """测试更新任务状态为运行中"""
        task_manager.create_task(sample_task)

        # 更新为运行状态
        result = task_manager.update_task_status(sample_task.task_id, TaskStatus.RUNNING)
        assert result is True

        # 验证状态更新
        updated_task = task_manager.get_task(sample_task.task_id)
        assert updated_task.status == TaskStatus.RUNNING
        assert updated_task.started_at is not None
        assert isinstance(updated_task.started_at, datetime)

    def test_update_task_status_to_completed(self, task_manager, sample_task):
        """测试更新任务状态为完成"""
        task_manager.create_task(sample_task)

        # 先更新为运行状态
        task_manager.update_task_status(sample_task.task_id, TaskStatus.RUNNING)

        # 更新为完成状态
        result_data = {
            'success': True,
            'exit_code': 0,
            'stdout': 'file1.txt\nfile2.txt',
            'stderr': '',
            'duration_seconds': 0.5
        }
        result = task_manager.update_task_status(
            sample_task.task_id,
            TaskStatus.COMPLETED,
            result=result_data
        )
        assert result is True

        # 验证状态更新
        updated_task = task_manager.get_task(sample_task.task_id)
        assert updated_task.status == TaskStatus.COMPLETED
        assert updated_task.completed_at is not None
        assert isinstance(updated_task.completed_at, datetime)
        assert updated_task.result == result_data

    def test_update_task_status_with_result(self, task_manager, sample_task):
        """测试带结果更新任务状态"""
        task_manager.create_task(sample_task)

        result_data = {
            'success': False,
            'error': 'Command not found',
            'exit_code': 127
        }

        result = task_manager.update_task_status(
            sample_task.task_id,
            TaskStatus.FAILED,
            result=result_data
        )

        assert result is True
        updated_task = task_manager.get_task(sample_task.task_id)
        assert updated_task.status == TaskStatus.FAILED
        assert updated_task.result == result_data

    def test_update_invalid_status(self, task_manager, sample_task):
        """测试更新为无效状态"""
        task_manager.create_task(sample_task)

        # 应该抛出ValueError
        with pytest.raises(ValueError, match="Invalid task status"):
            task_manager.update_task_status(sample_task.task_id, "invalid_status")

    def test_list_all_tasks(self, task_manager):
        """测试列出所有任务"""
        # 创建多个任务
        tasks = []
        for i in range(5):
            task = Task.create(
                name=f"任务-{i}",
                description=f"测试任务{i}",
                command=f"echo {i}",
                target_device_id=f"device-{i}"
            )
            tasks.append(task)
            task_manager.create_task(task)

        # 列出所有任务
        listed_tasks = task_manager.list_tasks()
        assert len(listed_tasks) == 5

        # 验证任务按创建时间倒序排列
        assert listed_tasks[0].name == "任务-4"  # 最后创建的在前

    def test_list_tasks_by_device(self, task_manager):
        """测试按设备筛选任务"""
        # 创建不同设备的任务
        for device_id in ["device-001", "device-002", "device-003"]:
            for i in range(3):
                task = Task.create(
                    name=f"{device_id}-任务-{i}",
                    description=f"测试任务",
                    command="echo test",
                    target_device_id=device_id
                )
                task_manager.create_task(task)

        # 筛选device-001的任务
        device_tasks = task_manager.list_tasks(device_id="device-001")
        assert len(device_tasks) == 3
        for task in device_tasks:
            assert task.target_device_id == "device-001"

    def test_list_tasks_by_status(self, task_manager):
        """测试按状态筛选任务"""
        # 创建不同状态的任务
        task1 = Task.create("任务1", "描述1", "cmd1", "device-001")
        task2 = Task.create("任务2", "描述2", "cmd2", "device-002")
        task3 = Task.create("任务3", "描述3", "cmd3", "device-003")

        task_manager.create_task(task1)
        task_manager.create_task(task2)
        task_manager.create_task(task3)

        # 更新状态
        task_manager.update_task_status(task1.task_id, TaskStatus.RUNNING)
        task_manager.update_task_status(task2.task_id, TaskStatus.COMPLETED)

        # 筛选pending状态的任务
        pending_tasks = task_manager.list_tasks(status=TaskStatus.PENDING)
        assert len(pending_tasks) == 1
        assert pending_tasks[0].task_id == task3.task_id

        # 筛选running状态的任务
        running_tasks = task_manager.list_tasks(status=TaskStatus.RUNNING)
        assert len(running_tasks) == 1
        assert running_tasks[0].task_id == task1.task_id

    def test_list_tasks_with_limit_and_offset(self, task_manager):
        """测试分页查询"""
        # 创建10个任务
        for i in range(10):
            task = Task.create(f"任务-{i}", "描述", "cmd", f"device-{i}")
            task_manager.create_task(task)

        # 第一页，限制5条
        page1 = task_manager.list_tasks(limit=5, offset=0)
        assert len(page1) == 5
        assert page1[0].name == "任务-9"  # 最新创建的在前

        # 第二页
        page2 = task_manager.list_tasks(limit=5, offset=5)
        assert len(page2) == 5
        assert page2[0].name == "任务-4"

    def test_delete_task(self, task_manager, sample_task):
        """测试删除任务"""
        task_manager.create_task(sample_task)

        # 验证任务存在
        assert task_manager.get_task(sample_task.task_id) is not None

        # 删除任务
        result = task_manager.delete_task(sample_task.task_id)
        assert result is True

        # 验证任务已删除
        assert task_manager.get_task(sample_task.task_id) is None

    def test_delete_nonexistent_task(self, task_manager):
        """测试删除不存在的任务"""
        result = task_manager.delete_task("nonexistent-task-id")
        assert result is False

    def test_get_task_count(self, task_manager):
        """测试获取任务数量"""
        # 创建不同状态和设备的任务
        for device_id in ["device-001", "device-002"]:
            for status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.COMPLETED]:
                task = Task.create(f"任务", "描述", "cmd", device_id)
                task_manager.create_task(task)
                task_manager.update_task_status(task.task_id, status)

        # 总任务数
        total_count = task_manager.get_task_count()
        assert total_count == 6

        # 按设备筛选
        device_count = task_manager.get_task_count(device_id="device-001")
        assert device_count == 3

        # 按状态筛选
        status_count = task_manager.get_task_count(status=TaskStatus.PENDING)
        assert status_count == 2

    def test_task_manager_with_custom_created_by(self, task_manager):
        """测试自定义创建者"""
        task = Task.create(
            name="自定义创建者任务",
            description="测试自定义创建者",
            command="pwd",
            target_device_id="device-001",
            created_by="admin_user"
        )

        task_manager.create_task(task)
        retrieved_task = task_manager.get_task(task.task_id)

        assert retrieved_task.created_by == "admin_user"

    def test_task_status_update_sequence(self, task_manager, sample_task):
        """测试任务状态更新序列"""
        task_manager.create_task(sample_task)

        # 初始状态
        task = task_manager.get_task(sample_task.task_id)
        assert task.status == TaskStatus.PENDING
        assert task.started_at is None
        assert task.completed_at is None

        # 更新为运行中
        task_manager.update_task_status(sample_task.task_id, TaskStatus.RUNNING)
        task = task_manager.get_task(sample_task.task_id)
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None
        assert task.completed_at is None

        # 更新为完成
        task_manager.update_task_status(sample_task.task_id, TaskStatus.COMPLETED)
        task = task_manager.get_task(sample_task.task_id)
        assert task.status == TaskStatus.COMPLETED
        assert task.started_at is not None
        assert task.completed_at is not None

    def test_concurrent_task_creation(self, task_manager):
        """测试并发创建任务"""
        import threading

        tasks = []
        def create_task(index):
            task = Task.create(f"并发任务-{index}", "描述", "cmd", "device-001")
            task_manager.create_task(task)
            tasks.append(task)

        # 创建10个线程
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_task, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有任务都已创建
        assert len(tasks) == 10
        all_tasks = task_manager.list_tasks()
        assert len(all_tasks) == 10