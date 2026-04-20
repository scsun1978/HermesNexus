"""
任务模型单元测试
"""
import pytest
from datetime import datetime
from hermesnexus.task.model import Task, TaskTemplate, TaskStatus, TaskPriority
import uuid


class TestTask:
    """Task类测试"""

    def test_task_creation(self):
        """测试任务创建"""
        task = Task.create(
            name="测试任务",
            description="这是一个测试任务",
            command="ls -la",
            target_device_id="device-001"
        )

        assert task.name == "测试任务"
        assert task.description == "这是一个测试任务"
        assert task.command == "ls -la"
        assert task.target_device_id == "device-001"
        assert task.status == TaskStatus.PENDING
        assert task.created_by == "system"
        assert isinstance(task.task_id, str)
        assert isinstance(task.created_at, datetime)
        assert task.started_at is None
        assert task.completed_at is None
        assert task.result is None

    def test_task_serialization(self):
        """测试任务序列化"""
        task = Task.create(
            name="序列化测试",
            description="测试序列化功能",
            command="echo 'hello'",
            target_device_id="device-002"
        )

        # 转换为字典
        task_dict = task.to_dict()

        assert task_dict['name'] == "序列化测试"
        assert task_dict['command'] == "echo 'hello'"
        assert isinstance(task_dict['created_at'], str)  # datetime应该转换为字符串
        assert task_dict['status'] == TaskStatus.PENDING

        # 从字典重建
        restored_task = Task.from_dict(task_dict)

        assert restored_task.name == task.name
        assert restored_task.command == task.command
        assert restored_task.target_device_id == task.target_device_id
        assert isinstance(restored_task.created_at, datetime)

    def test_task_from_dict(self):
        """测试从字典创建任务"""
        task_data = {
            'task_id': 'test-task-123',
            'name': '字典创建测试',
            'description': '测试从字典创建',
            'command': 'pwd',
            'target_device_id': 'device-003',
            'status': TaskStatus.RUNNING,
            'created_by': 'admin',
            'created_at': datetime.now().isoformat(),
            'started_at': datetime.now().isoformat()
        }

        task = Task.from_dict(task_data)

        assert task.task_id == 'test-task-123'
        assert task.name == '字典创建测试'
        assert task.status == TaskStatus.RUNNING
        assert task.created_by == 'admin'
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.started_at, datetime)

    def test_task_with_result(self):
        """测试带结果的任务"""
        result_data = {
            'success': True,
            'exit_code': 0,
            'stdout': 'file1.txt\nfile2.txt',
            'stderr': '',
            'duration_seconds': 0.5
        }

        task = Task.create(
            name="结果测试",
            description="测试任务结果存储",
            command="ls",
            target_device_id="device-004"
        )
        task.result = result_data
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()

        # 序列化测试
        task_dict = task.to_dict()
        assert task_dict['result'] == result_data
        assert task_dict['status'] == TaskStatus.COMPLETED
        assert isinstance(task_dict['completed_at'], str)

        # 反序列化测试
        restored_task = Task.from_dict(task_dict)
        assert restored_task.result == result_data
        assert restored_task.status == TaskStatus.COMPLETED
        assert isinstance(restored_task.completed_at, datetime)


class TestTaskTemplate:
    """TaskTemplate类测试"""

    def test_template_creation(self):
        """测试模板创建"""
        template = TaskTemplate.create(
            template_id="health-check",
            name="健康检查",
            description="系统健康检查模板",
            command_template="uptime && df -h"
        )

        assert template.template_id == "health-check"
        assert template.name == "健康检查"
        assert template.command_template == "uptime && df -h"
        assert template.default_params == {}

    def test_template_with_default_params(self):
        """测试带默认参数的模板"""
        template = TaskTemplate.create(
            template_id="restart-service",
            name="服务重启",
            description="重启系统服务",
            command_template="systemctl restart {service}",
            default_params={"service": "nginx"}
        )

        assert template.default_params == {"service": "nginx"}

        # 使用默认参数渲染
        command = template.render()
        assert command == "systemctl restart nginx"

    def test_template_rendering(self):
        """测试模板渲染"""
        template = TaskTemplate.create(
            template_id="backup",
            name="备份",
            description="数据库备份",
            command_template="mysqldump {database} > {backup_path}/{database}_backup.sql"
        )

        # 渲染时提供参数
        command = template.render(database="mydb", backup_path="/tmp/backups")
        expected = "mysqldump mydb > /tmp/backups/mydb_backup.sql"
        assert command == expected

    def test_template_render_override_defaults(self):
        """测试覆盖默认参数"""
        template = TaskTemplate.create(
            template_id="restart",
            name="重启服务",
            description="重启服务",
            command_template="systemctl restart {service}",
            default_params={"service": "nginx"}
        )

        # 覆盖默认参数
        command = template.render(service="apache2")
        assert command == "systemctl restart apache2"

    def test_template_render_missing_param(self):
        """测试缺少参数时的错误"""
        template = TaskTemplate.create(
            template_id="test",
            name="测试",
            description="测试模板",
            command_template="echo {message}"
        )

        # 应该抛出ValueError
        with pytest.raises(ValueError, match="Missing required parameter"):
            template.render()

    def test_template_serialization(self):
        """测试模板序列化"""
        template = TaskTemplate.create(
            template_id="test-template",
            name="序列化测试",
            description="测试模板序列化",
            command_template="cp {source} {destination}",
            default_params={"source": "/tmp/file.txt"}
        )

        # 转换为字典
        template_dict = template.to_dict()
        assert template_dict['template_id'] == "test-template"
        assert template_dict['default_params'] == {"source": "/tmp/file.txt"}

        # 从字典重建
        restored_template = TaskTemplate.from_dict(template_dict)
        assert restored_template.template_id == template.template_id
        assert restored_template.command_template == template.command_template
        assert restored_template.default_params == template.default_params


class TestTaskStatus:
    """TaskStatus类测试"""

    def test_status_validation(self):
        """测试状态验证"""
        assert TaskStatus.is_valid(TaskStatus.PENDING)
        assert TaskStatus.is_valid(TaskStatus.RUNNING)
        assert TaskStatus.is_valid(TaskStatus.COMPLETED)
        assert TaskStatus.is_valid(TaskStatus.FAILED)
        assert TaskStatus.is_valid(TaskStatus.CANCELLED)
        assert not TaskStatus.is_valid("invalid_status")

    def test_terminal_status(self):
        """测试终止状态检查"""
        assert TaskStatus.is_terminal(TaskStatus.COMPLETED)
        assert TaskStatus.is_terminal(TaskStatus.FAILED)
        assert TaskStatus.is_terminal(TaskStatus.CANCELLED)
        assert not TaskStatus.is_terminal(TaskStatus.PENDING)
        assert not TaskStatus.is_terminal(TaskStatus.RUNNING)


class TestTaskPriority:
    """TaskPriority类测试"""

    def test_priority_weights(self):
        """测试优先级权重"""
        assert TaskPriority.get_weight(TaskPriority.LOW) == 1
        assert TaskPriority.get_weight(TaskPriority.MEDIUM) == 2
        assert TaskPriority.get_weight(TaskPriority.HIGH) == 3
        assert TaskPriority.get_weight(TaskPriority.CRITICAL) == 4
        assert TaskPriority.get_weight("unknown") == 2  # 默认为MEDIUM

    def test_priority_ordering(self):
        """测试优先级排序"""
        priorities = [
            TaskPriority.HIGH,
            TaskPriority.LOW,
            TaskPriority.CRITICAL,
            TaskPriority.MEDIUM
        ]

        # 按权重排序
        sorted_priorities = sorted(priorities, key=TaskPriority.get_weight)

        assert sorted_priorities == [
            TaskPriority.LOW,
            TaskPriority.MEDIUM,
            TaskPriority.HIGH,
            TaskPriority.CRITICAL
        ]


class TestTaskIntegration:
    """任务模型集成测试"""

    def test_task_lifecycle(self):
        """测试任务生命周期"""
        # 创建任务
        task = Task.create(
            name="生命周期测试",
            description="测试完整的任务生命周期",
            command="sleep 1",
            target_device_id="device-005"
        )

        assert task.status == TaskStatus.PENDING
        assert task.started_at is None
        assert task.completed_at is None

        # 开始执行
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        assert task.status == TaskStatus.RUNNING
        assert isinstance(task.started_at, datetime)

        # 完成执行
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        task.result = {
            'success': True,
            'exit_code': 0,
            'stdout': '',
            'stderr': ''
        }

        assert task.status == TaskStatus.COMPLETED
        assert isinstance(task.completed_at, datetime)
        assert task.result['success'] is True

    def test_task_template_integration(self):
        """测试任务和模板集成"""
        template = TaskTemplate.create(
            template_id="disk-check",
            name="磁盘检查",
            description="检查磁盘使用情况",
            command_template="df -h {mount_point}",
            default_params={"mount_point": "/"}
        )

        # 从模板创建命令
        command = template.render()
        assert command == "df -h /"

        # 创建使用此命令的任务
        task = Task.create(
            name="根磁盘检查",
            description="检查根分区使用情况",
            command=command,
            target_device_id="device-006"
        )

        assert task.command == "df -h /"
        assert task.status == TaskStatus.PENDING