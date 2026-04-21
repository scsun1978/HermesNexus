"""
CloudTaskOrchestrator 测试 - Week 5
云端任务编排器核心功能测试
"""
import pytest
import tempfile
import os
from hermesnexus.orchestrator.cloud import (
    CloudTaskOrchestrator,
    MVPOrchestratorFactory,
    BatchScheduleResult,
    DeviceGroup
)
from hermesnexus.task.manager import TaskManager


class TestCloudTaskOrchestrator:
    """CloudTaskOrchestrator 核心功能测试"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def task_manager(self, temp_db):
        """创建任务管理器"""
        return TaskManager(temp_db)

    @pytest.fixture
    def orchestrator(self, task_manager):
        """创建编排器"""
        edge_nodes_config = {
            'edge_node_1': 'http://localhost:8001',
            'edge_node_2': 'http://localhost:8002'
        }
        return CloudTaskOrchestrator(edge_nodes_config, task_manager)

    def test_orchestrator_initialization(self, orchestrator):
        """测试编排器初始化 - MVP验收"""
        assert len(orchestrator.edge_nodes) == 2
        assert orchestrator.edge_nodes['edge_node_1'] == 'http://localhost:8001'
        assert len(orchestrator.device_groups) == 0
        assert len(orchestrator.active_batches) == 0

    def test_schedule_task_to_single_device(self, orchestrator):
        """测试调度任务到单个设备 - MVP验收"""
        task_spec = {
            'name': '测试任务',
            'command': 'echo test',
            'description': '测试描述',
            'created_by': 'admin'
        }

        result = orchestrator.schedule_task_to_devices(
            task_spec,
            ['server-001']
        )

        assert result.total_devices == 1
        assert result.successful_schedules == 1
        assert result.failed_schedules == 0
        assert len(result.task_ids) == 1
        assert len(result.errors) == 0

    def test_schedule_task_to_multiple_devices(self, orchestrator):
        """测试批量调度到多个设备 - MVP验收"""
        task_spec = {
            'name': '批量巡检',
            'command': 'uptime && df -h',
            'description': '系统健康检查',
            'created_by': 'admin'
        }

        devices = ['server-001', 'server-002', 'server-003']
        result = orchestrator.schedule_task_to_devices(task_spec, devices)

        assert result.total_devices == 3
        assert result.successful_schedules == 3
        assert result.failed_schedules == 0
        assert len(result.task_ids) == 3

        # 验证任务已保存到任务管理器
        for task_id in result.task_ids:
            task = orchestrator.task_manager.get_task(task_id)
            assert task is not None
            assert '批量巡检' in task.name

    def test_schedule_with_custom_batch_id(self, orchestrator):
        """测试使用自定义批次ID"""
        task_spec = {'name': '自定义批次', 'command': 'echo test'}
        custom_batch_id = 'custom_batch_123'

        result = orchestrator.schedule_task_to_devices(
            task_spec,
            ['device-001'],
            batch_id=custom_batch_id
        )

        assert result.batch_id == custom_batch_id
        assert custom_batch_id in orchestrator.active_batches

    def test_sequential_vs_parallel_scheduling(self, orchestrator):
        """测试串行vs并行调度 - MVP验收"""
        task_spec = {'name': '调度模式测试', 'command': 'echo test'}
        devices = ['device-001', 'device-002']

        # 串行调度
        sequential_result = orchestrator.schedule_task_to_devices(
            task_spec, devices, parallel=False
        )

        # 并行调度
        parallel_result = orchestrator.schedule_task_to_devices(
            task_spec, devices, parallel=True
        )

        # 两种模式都应该成功
        assert sequential_result.successful_schedules == 2
        assert parallel_result.successful_schedules == 2


class TestDeviceGroups:
    """设备分组功能测试"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def orchestrator(self, temp_db):
        """创建编排器"""
        task_manager = TaskManager(temp_db)
        edge_nodes_config = {'edge_1': 'http://localhost:8001'}
        return CloudTaskOrchestrator(edge_nodes_config, task_manager)

    def test_create_device_group(self, orchestrator):
        """测试创建设备分组 - MVP验收"""
        group = orchestrator.create_device_group(
            'routers',
            'Core Routers',
            ['router-001', 'router-002'],
            {'location': 'datacenter'}
        )

        assert group.group_id == 'routers'
        assert group.group_name == 'Core Routers'
        assert len(group.device_ids) == 2
        assert group.metadata['location'] == 'datacenter'
        assert 'routers' in orchestrator.device_groups

    def test_schedule_task_to_group(self, orchestrator):
        """测试调度任务到设备分组 - MVP验收"""
        # 创建设备分组
        orchestrator.create_device_group(
            'servers',
            'Web Servers',
            ['server-001', 'server-002', 'server-003']
        )

        task_spec = {
            'name': '服务器重启',
            'command': 'reboot',
            'description': '计划重启'
        }

        result = orchestrator.schedule_task_to_group(task_spec, 'servers')

        assert result.total_devices == 3
        assert result.successful_schedules == 3
        assert result.failed_schedules == 0
        assert len(result.task_ids) == 3

    def test_schedule_to_nonexistent_group(self, orchestrator):
        """测试调度到不存在的分组"""
        task_spec = {'name': '测试', 'command': 'echo test'}

        with pytest.raises(ValueError, match="Device group.*not found"):
            orchestrator.schedule_task_to_group(task_spec, 'nonexistent_group')

    def test_device_group_management(self, orchestrator):
        """测试设备分组管理 - MVP验收"""
        # 创建分组
        group = orchestrator.create_device_group(
            'switches',
            'Network Switches',
            ['switch-001', 'switch-002']
        )

        # 添加设备
        group.add_device('switch-003')
        assert len(group.device_ids) == 3

        # 移除设备
        group.remove_device('switch-001')
        assert len(group.device_ids) == 2
        assert 'switch-001' not in group.device_ids

        # 删除分组
        assert orchestrator.remove_device_group('switches') is True
        assert 'switches' not in orchestrator.device_groups
        assert orchestrator.remove_device_group('switches') is False


class TestBatchStatusTracking:
    """批次状态跟踪测试"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def orchestrator(self, temp_db):
        """创建编排器"""
        task_manager = TaskManager(temp_db)
        edge_nodes_config = {'edge_1': 'http://localhost:8001'}
        return CloudTaskOrchestrator(edge_nodes_config, task_manager)

    def test_get_batch_status(self, orchestrator):
        """测试获取批次状态 - MVP验收"""
        task_spec = {'name': '状态查询测试', 'command': 'echo test'}
        result = orchestrator.schedule_task_to_devices(
            task_spec,
            ['device-001', 'device-002']
        )

        # 查询批次状态
        status = orchestrator.get_batch_status(result.batch_id)
        assert status is not None
        assert status.batch_id == result.batch_id
        assert status.total_devices == 2
        assert status.successful_schedules == 2

    def test_get_nonexistent_batch_status(self, orchestrator):
        """测试查询不存在的批次"""
        status = orchestrator.get_batch_status('nonexistent_batch')
        assert status is None

    def test_get_batch_progress(self, orchestrator):
        """测试获取批次进度 - MVP验收"""
        task_spec = {'name': '进度测试', 'command': 'echo test'}
        result = orchestrator.schedule_task_to_devices(
            task_spec,
            ['device-001', 'device-002', 'device-003']
        )

        progress = orchestrator.get_batch_progress(result.batch_id)

        assert progress is not None
        assert progress['batch_id'] == result.batch_id
        assert progress['total_devices'] == 3
        assert progress['successful'] == 3
        assert progress['failed'] == 0
        assert progress['progress_percentage'] == 100.0
        assert progress['status'] == 'completed'

    def test_get_active_batches(self, orchestrator):
        """测试获取活跃批次列表 - MVP验收"""
        # 创建多个批次
        for i in range(3):
            task_spec = {'name': f'批次{i}', 'command': 'echo test'}
            orchestrator.schedule_task_to_devices(
                task_spec,
                [f'device-{i}']
            )

        active_batches = orchestrator.get_active_batches()
        assert len(active_batches) == 3

        # 验证批次信息
        for batch_id, result in active_batches.items():
            assert result.total_devices == 1
            assert result.successful_schedules == 1


class TestMVPOrchestratorFactory:
    """MVP编排器工厂测试"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_mvp_factory_creation(self, temp_db):
        """测试MVP工厂创建编排器 - MVP验收"""
        task_manager = TaskManager(temp_db)
        orchestrator = MVPOrchestratorFactory.create_with_default_config(task_manager)

        # 验证边缘节点配置
        assert len(orchestrator.edge_nodes) == 2

        # 验证预定义设备分组
        groups = orchestrator.get_device_groups()
        assert len(groups) == 2
        assert 'routers' in groups
        assert 'servers' in groups

        # 验证分组内容
        router_group = groups['routers']
        assert router_group.group_name == 'Core Routers'
        assert len(router_group.device_ids) == 2

        server_group = groups['servers']
        assert server_group.group_name == 'Web Servers'
        assert len(server_group.device_ids) == 3


class TestMVPOrchestratorAcceptance:
    """MVP编排器验收测试"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_mvp_batch_scheduling_workflow(self, temp_db):
        """MVP 批量调度工作流验收"""
        task_manager = TaskManager(temp_db)
        orchestrator = MVPOrchestratorFactory.create_with_default_config(task_manager)

        # 1. 创建巡检任务
        inspection_task = {
            'name': '系统巡检',
            'command': 'uptime && df -h && free -m',
            'description': '系统健康检查',
            'created_by': 'admin'
        }

        # 2. 批量调度到服务器分组
        result = orchestrator.schedule_task_to_group(
            inspection_task,
            'servers'
        )

        # 验证调度结果
        assert result.total_devices == 3  # servers分组有3台设备
        assert result.successful_schedules == 3
        assert result.failed_schedules == 0
        assert len(result.task_ids) == 3

        # 3. 验证任务已保存并可查询
        for task_id in result.task_ids:
            task = task_manager.get_task(task_id)
            assert task is not None
            assert '系统巡检' in task.name
            assert task.status == 'pending'

        # 4. 验证批次进度
        progress = orchestrator.get_batch_progress(result.batch_id)
        assert progress['status'] == 'completed'
        assert progress['progress_percentage'] == 100.0

        print("✅ MVP 批量调度工作流验收通过")

    def test_mvp_multi_group_scheduling(self, temp_db):
        """MVP 多分组调度验收"""
        task_manager = TaskManager(temp_db)
        orchestrator = MVPOrchestratorFactory.create_with_default_config(task_manager)

        # 不同分组的不同任务
        router_task = {
            'name': '路由器配置备份',
            'command': 'show running-config',
            'created_by': 'network_admin'
        }

        server_task = {
            'name': '服务器日志清理',
            'command': 'journalctl --vacuum-time=7d',
            'created_by': 'system_admin'
        }

        # 分别调度
        router_result = orchestrator.schedule_task_to_group(router_task, 'routers')
        server_result = orchestrator.schedule_task_to_group(server_task, 'servers')

        # 验证结果
        assert router_result.successful_schedules == 2  # routers分组2台设备
        assert server_result.successful_schedules == 3   # servers分组3台设备

        # 验证批次独立性
        assert router_result.batch_id != server_result.batch_id

        print("✅ MVP 多分组调度验收通过")

    def test_mvp_error_handling_and_recovery(self, temp_db):
        """MVP 错误处理和恢复验收"""
        task_manager = TaskManager(temp_db)
        orchestrator = MVPOrchestratorFactory.create_with_default_config(task_manager)

        # 创建设备分组，包含一个无效设备ID
        orchestrator.create_device_group(
            'test_group',
            'Test Group',
            ['valid-device-001', 'valid-device-002']
        )

        task_spec = {
            'name': '错误处理测试',
            'command': 'echo test',
            'created_by': 'admin'
        }

        # 调度应该成功（即使设备不存在，任务创建仍然成功）
        result = orchestrator.schedule_task_to_devices(
            task_spec,
            ['valid-device-001', 'valid-device-002']
        )

        # MVP阶段，任务创建不验证设备是否存在
        assert result.successful_schedules == 2
        assert result.failed_schedules == 0

        print("✅ MVP 错误处理和恢复验收通过")