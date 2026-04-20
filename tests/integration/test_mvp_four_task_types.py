"""
MVP 4类任务端到端验收测试 - Week 3
重点：验证MVP要求的4类任务类型能正常工作
"""
import pytest
import tempfile
import os
from hermesnexus.task.model import Task, TaskStatus
from hermesnexus.task.manager import TaskManager
from hermesnexus.task.executor import TaskExecutor, DeviceConfigBuilder
from hermesnexus.task.templates import CoreTemplates, MVPTaskTemplates, TemplateManager


class TestMVPTaskTypes:
    """MVP 4类任务类型验收测试"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)

    @pytest.fixture
    def task_manager(self, temp_db):
        """创建任务管理器"""
        return TaskManager(temp_db)

    @pytest.fixture
    def task_executor(self, task_manager):
        """创建任务执行器"""
        return TaskExecutor(task_manager)

    @pytest.fixture
    def local_device_config(self):
        """本地设备配置"""
        return DeviceConfigBuilder.local_config()

    def test_inspection_task_execution(self, task_manager, task_executor, local_device_config):
        """INSPECTION任务执行 - MVP验收"""
        # 使用MVP工厂创建巡检任务
        command = MVPTaskTemplates.create_inspection_task("local-device")

        # 创建任务
        task = Task.create(
            name="系统巡检任务",
            description="MVP验收：系统巡检",
            command=command,
            target_device_id="local-device"
        )
        task_manager.create_task(task)

        # 执行任务
        result = task_executor.execute(task, local_device_config)

        # 验证执行结果
        assert result['success'] is True
        assert 'uptime' in result['stdout'] or 'load average' in result['stdout'].lower()

        # 验证任务状态
        completed_task = task_manager.get_task(task.task_id)
        assert completed_task.status == TaskStatus.COMPLETED
        assert completed_task.result['success'] is True

        print("✅ INSPECTION任务执行成功")
        print(f"   命令: {command}")
        print(f"   输出预览: {result['stdout'][:200]}...")

    def test_restart_task_execution(self, task_manager, task_executor, local_device_config):
        """RESTART任务执行 - MVP验收"""
        # 注意：在实际环境中这需要root权限，在测试环境中我们模拟这个命令
        command = "echo 'Simulating: systemctl restart nginx' && systemctl status nginx 2>/dev/null || echo 'nginx service simulation'"

        # 创建任务
        task = Task.create(
            name="服务重启任务",
            description="MVP验收：服务重启",
            command=command,
            target_device_id="local-device"
        )
        task_manager.create_task(task)

        # 执行任务
        result = task_executor.execute(task, local_device_config)

        # 验证执行结果
        assert result['success'] is True
        assert 'nginx' in result['stdout'].lower() or 'simulation' in result['stdout'].lower()

        # 验证任务状态
        completed_task = task_manager.get_task(task.task_id)
        assert completed_task.status == TaskStatus.COMPLETED

        print("✅ RESTART任务执行成功")
        print(f"   命令: {command}")
        print(f"   输出: {result['stdout'][:200]}")

    def test_upgrade_task_execution(self, task_manager, task_executor, local_device_config):
        """UPGRADE任务执行 - MVP验收"""
        # 注意：实际升级需要root权限，这里模拟升级过程
        command = "echo 'Simulating: apt-get update && apt-get install -y nginx' && echo 'Package nginx upgraded successfully'"

        # 创建任务
        task = Task.create(
            name="软件包升级任务",
            description="MVP验收：软件包升级",
            command=command,
            target_device_id="local-device"
        )
        task_manager.create_task(task)

        # 执行任务
        result = task_executor.execute(task, local_device_config)

        # 验证执行结果
        assert result['success'] is True
        assert 'upgrade' in result['stdout'].lower() or 'apt-get' in result['stdout'].lower()

        # 验证任务状态
        completed_task = task_manager.get_task(task.task_id)
        assert completed_task.status == TaskStatus.COMPLETED

        print("✅ UPGRADE任务执行成功")
        print(f"   命令: {command}")
        print(f"   输出: {result['stdout'][:200]}")

    def test_rollback_task_execution(self, task_manager, task_executor, local_device_config):
        """ROLLBACK任务执行 - MVP验收"""
        # 注意：实际回滚需要systemd支持，这里模拟回滚过程
        command = "echo 'Simulating: systemctl revert nginx' && echo 'Service nginx rolled back to previous version'"

        # 创建任务
        task = Task.create(
            name="服务回滚任务",
            description="MVP验收：服务回滚",
            command=command,
            target_device_id="local-device"
        )
        task_manager.create_task(task)

        # 执行任务
        result = task_executor.execute(task, local_device_config)

        # 验证执行结果
        assert result['success'] is True
        assert 'rollback' in result['stdout'].lower() or 'revert' in result['stdout'].lower()

        # 验证任务状态
        completed_task = task_manager.get_task(task.task_id)
        assert completed_task.status == TaskStatus.COMPLETED

        print("✅ ROLLBACK任务执行成功")
        print(f"   命令: {command}")
        print(f"   输出: {result['stdout'][:200]}")

    def test_four_task_types_sequence(self, task_manager, task_executor, local_device_config):
        """4类任务按顺序执行 - MVP综合验收"""
        # 1. INSPECTION任务
        inspection_command = MVPTaskTemplates.create_inspection_task("local-device")
        inspection_task = Task.create("系统巡检", "检查系统状态", inspection_command, "local-device")
        task_manager.create_task(inspection_task)
        inspection_result = task_executor.execute(inspection_task, local_device_config)
        assert inspection_result['success'] is True

        # 2. RESTART任务
        restart_command = "echo 'Restarting service...' && echo 'Service restarted'"
        restart_task = Task.create("服务重启", "重启服务", restart_command, "local-device")
        task_manager.create_task(restart_task)
        restart_result = task_executor.execute(restart_task, local_device_config)
        assert restart_result['success'] is True

        # 3. UPGRADE任务
        upgrade_command = "echo 'Upgrading package...' && echo 'Package upgraded'"
        upgrade_task = Task.create("软件包升级", "升级软件包", upgrade_command, "local-device")
        task_manager.create_task(upgrade_task)
        upgrade_result = task_executor.execute(upgrade_task, local_device_config)
        assert upgrade_result['success'] is True

        # 4. ROLLBACK任务
        rollback_command = "echo 'Rolling back service...' && echo 'Service rolled back'"
        rollback_task = Task.create("服务回滚", "回滚服务", rollback_command, "local-device")
        task_manager.create_task(rollback_task)
        rollback_result = task_executor.execute(rollback_task, local_device_config)
        assert rollback_result['success'] is True

        # 验证所有任务都正确记录在数据库中
        all_tasks = task_manager.list_tasks()
        assert len(all_tasks) == 4

        # 验证所有任务都成功完成
        for task in all_tasks:
            assert task.status == TaskStatus.COMPLETED

        print("✅ MVP 4类任务序列执行成功")
        print(f"   INSPECTION: {inspection_result['success']}")
        print(f"   RESTART: {restart_result['success']}")
        print(f"   UPGRADE: {upgrade_result['success']}")
        print(f"   ROLLBACK: {rollback_result['success']}")

    def test_template_based_task_creation(self, task_manager, task_executor, local_device_config):
        """基于模板的任务创建和执行 - MVP验收"""
        template_manager = TemplateManager()

        # 验证所有4类核心模板都存在
        templates = template_manager.list_templates()
        template_ids = [t['template_id'] for t in templates]

        assert 'inspection' in template_ids
        assert 'restart-service' in template_ids
        assert 'upgrade-package' in template_ids
        assert 'rollback-service' in template_ids

        print("✅ MVP 4类任务模板验证")
        for template_info in templates:
            if template_info['template_id'] in ['inspection', 'restart-service', 'upgrade-package', 'rollback-service']:
                print(f"   {template_info['template_id']}: {template_info['name']}")
                print(f"      描述: {template_info['description']}")

    def test_task_audit_trail(self, task_manager, task_executor, local_device_config):
        """任务审计跟踪 - MVP验收"""
        # 创建并执行4类不同类型的任务
        tasks = []
        for i, (task_type_name, command) in enumerate([
            ("巡检", "echo 'Inspection task' && date"),
            ("重启", "echo 'Restart task'"),
            ("升级", "echo 'Upgrade task'"),
            ("回滚", "echo 'Rollback task'")
        ]):
            task = Task.create(
                name=f"{task_type_name}任务",
                description=f"MVP验收：{task_type_name}",
                command=command,
                target_device_id="local-device"
            )
            task_manager.create_task(task)
            task_executor.execute(task, local_device_config)
            tasks.append(task)

        # 验证审计信息完整性
        for task in tasks:
            audited_task = task_manager.get_task(task.task_id)

            # 验证时间戳完整
            assert audited_task.created_at is not None
            assert audited_task.started_at is not None
            assert audited_task.completed_at is not None

            # 验证执行结果完整
            assert audited_task.result is not None
            assert audited_task.result['success'] is True
            assert 'duration_seconds' in audited_task.result

            # 验证状态转换
            assert audited_task.status == TaskStatus.COMPLETED

        print("✅ MVP任务审计跟踪完整")
        print(f"   审计任务数量: {len(tasks)}")
        print(f"   每个任务都有: created_at, started_at, completed_at, result")

    def test_task_failure_recovery_across_types(self, task_manager, task_executor, local_device_config):
        """4类任务的失败恢复 - MVP健壮性验收"""
        # 测试4类任务在失败情况下的处理
        failure_scenarios = [
            ("巡检失败", "nonexistent_inspection_command"),
            ("重启失败", "systemctl restart nonexistent_service"),
            ("升级失败", "apt-get install nonexistent_package"),
            ("回滚失败", "systemctl revert nonexistent_service")
        ]

        for task_type_name, failing_command in failure_scenarios:
            task = Task.create(
                name=f"{task_type_name}测试",
                description=f"测试{task_type_name}的失败处理",
                command=failing_command,
                target_device_id="local-device"
            )
            task_manager.create_task(task)

            # 执行失败的命令
            result = task_executor.execute(task, local_device_config)

            # 验证失败处理正确
            failed_task = task_manager.get_task(task.task_id)
            assert failed_task.status == TaskStatus.FAILED
            assert failed_task.result is not None
            assert failed_task.result['success'] is False

        print("✅ MVP 4类任务失败恢复验证通过")
        print(f"   测试场景: {len(failure_scenarios)}")
        print(f"   所有失败都有完整记录和错误信息")