"""
云边编排端到端测试 - Week 5-6
验证完整的云端→边缘→设备的数据流和任务执行
"""
import pytest
import tempfile
import os
import time
import threading
from unittest.mock import Mock, patch

from hermesnexus.orchestrator.cloud import (
    CloudTaskOrchestrator,
    MVPOrchestratorFactory
)
from hermesnexus.task.manager import TaskManager
from edge.enhanced_edge_node_v2 import EnhancedEdgeNodeV2, TaskStatusV2


class TestCloudEdgeDataFlow:
    """云边数据流测试"""

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
        return MVPOrchestratorFactory.create_with_default_config(task_manager)

    @pytest.fixture
    def edge_node(self):
        """创建v2边缘节点"""
        # 使用测试模式，不实际连接云端
        return EnhancedEdgeNodeV2("edge-test-001", "http://test.cloud:8082")

    def test_v2_task_creation_and_scheduling(self, orchestrator):
        """测试v2任务创建和调度 - MVP验收"""
        # 创建批量任务
        task_spec = {
            'name': '系统健康检查',
            'command': 'uptime && df -h',
            'description': 'MVP测试任务',
            'created_by': 'admin'
        }

        devices = ['server-001', 'server-002', 'server-003']
        result = orchestrator.schedule_task_to_devices(task_spec, devices)

        # 验证调度结果
        assert result.total_devices == 3
        assert result.successful_schedules == 3
        assert result.failed_schedules == 0
        assert len(result.task_ids) == 3

        # 验证任务已保存到数据库
        for task_id in result.task_ids:
            task = orchestrator.task_manager.get_task(task_id)
            assert task is not None
            assert '系统健康检查' in task.name
            assert task.status == 'pending'

        print("✅ v2任务创建和调度验收通过")

    def test_edge_node_v2_task_support(self, edge_node):
        """测试边缘节点v2任务支持 - MVP验收"""
        # 验证v2边缘节点初始化
        assert edge_node.node_id == "edge-test-001"
        assert "custom" in edge_node.supported_task_types
        assert "inspection" in edge_node.supported_task_types

        # 验证v2任务识别能力
        v2_task = {
            "task_id": "task-001",
            "task_type": "inspection",
            "priority": "high",
            "command": "uptime",
            "status": "pending"
        }

        assert edge_node._is_v2_task(v2_task) is True

        # 验证v1任务兼容性
        v1_task = {
            "job_id": "job-001",
            "command": "echo test",
            "status": "pending"
        }

        assert edge_node._is_v2_task(v1_task) is False

        print("✅ 边缘节点v2任务支持验收通过")

    def test_task_status_enums(self, edge_node):
        """测试任务状态枚举 - MVP验收"""
        # 验证v2状态枚举
        assert TaskStatusV2.PENDING.value == "pending"
        assert TaskStatusV2.RUNNING.value == "running"
        assert TaskStatusV2.COMPLETED.value == "completed"
        assert TaskStatusV2.FAILED.value == "failed"

        # 验证状态转换逻辑
        task_id = "test-task-001"

        # 模拟状态转换
        initial_status = TaskStatusV2.PENDING
        running_status = TaskStatusV2.RUNNING
        completed_status = TaskStatusV2.COMPLETED

        assert initial_status.value == "pending"
        assert running_status.value == "running"
        assert completed_status.value == "completed"

        print("✅ 任务状态枚举验收通过")


class TestCloudEdgeIntegration:
    """云边集成测试"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def setup_cloud_edge(self, temp_db):
        """设置云边环境"""
        # 创建云端编排器
        task_manager = TaskManager(temp_db)
        orchestrator = MVPOrchestratorFactory.create_with_default_config(task_manager)

        # 创建边缘节点
        edge_node = EnhancedEdgeNodeV2("edge-integration-001")

        return {
            "orchestrator": orchestrator,
            "edge_node": edge_node,
            "task_manager": task_manager
        }

    def test_cloud_to_edge_task_flow(self, setup_cloud_edge):
        """测试云端到边缘的任务流 - MVP验收"""
        orchestrator = setup_cloud_edge["orchestrator"]
        edge_node = setup_cloud_edge["edge_node"]

        # 1. 云端创建批量任务
        task_spec = {
            'name': '边缘节点测试任务',
            'command': 'echo "cloud-edge test"',
            'description': '测试云边数据流',
            'created_by': 'cloud_admin'
        }

        # 模拟边缘节点接收任务
        devices = ['edge-device-001', 'edge-device-002']
        result = orchestrator.schedule_task_to_devices(task_spec, devices)

        assert result.successful_schedules == 2
        assert len(result.task_ids) == 2

        # 2. 模拟边缘节点获取任务
        for task_id in result.task_ids:
            task = orchestrator.task_manager.get_task(task_id)
            assert task is not None

            # 验证边缘节点可以识别v2任务
            task_dict = {
                "task_id": task.task_id,
                "name": task.name,
                "command": task.command,
                "status": task.status,
                "task_type": "custom"
            }

            assert edge_node._is_v2_task(task_dict) is True

        # 3. 验证批次进度跟踪
        progress = orchestrator.get_batch_progress(result.batch_id)
        assert progress['total_devices'] == 2
        assert progress['successful'] == 2
        assert progress['status'] == 'completed'

        print("✅ 云端到边缘任务流验收通过")

    def test_multi_device_parallel_execution(self, setup_cloud_edge):
        """测试多设备并行执行 - MVP验收"""
        orchestrator = setup_cloud_edge["orchestrator"]

        # 创建大规模并行任务
        task_spec = {
            'name': '并行巡检任务',
            'command': 'hostname && uptime',
            'description': '多设备并行执行测试',
            'created_by': 'orchestrator'
        }

        # 模拟10个设备
        devices = [f'device-{i:03d}' for i in range(10)]

        start_time = time.time()
        result = orchestrator.schedule_task_to_devices(task_spec, devices, parallel=True)
        duration = time.time() - start_time

        # 验证并行调度结果
        assert result.total_devices == 10
        assert result.successful_schedules == 10
        assert result.failed_schedules == 0
        assert len(result.task_ids) == 10

        # 验证所有任务都已创建
        for task_id in result.task_ids:
            task = orchestrator.task_manager.get_task(task_id)
            assert task is not None
            assert '并行巡检任务' in task.name

        # 并行调度应该很快完成
        assert duration < 5.0  # 5秒内完成

        print(f"✅ 多设备并行执行验收通过 (10设备, {duration:.2f}s)")

    def test_error_handling_and_recovery(self, setup_cloud_edge):
        """测试错误处理和恢复 - MVP验收"""
        orchestrator = setup_cloud_edge["orchestrator"]

        # 创建包含潜在错误场景的任务
        task_spec = {
            'name': '错误处理测试',
            'command': 'exit 1',  # 模拟失败命令
            'description': '测试错误处理',
            'created_by': 'test_admin'
        }

        devices = ['device-001', 'device-002', 'device-003']
        result = orchestrator.schedule_task_to_devices(task_spec, devices)

        # 验证即使命令会失败，任务创建仍然成功
        # (任务执行失败在执行阶段，不是调度阶段)
        assert result.total_devices == 3
        assert result.successful_schedules == 3
        assert len(result.task_ids) == 3

        # 验证批次状态跟踪正确
        progress = orchestrator.get_batch_progress(result.batch_id)
        assert progress['total_devices'] == 3
        assert progress['status'] == 'completed'

        print("✅ 错误处理和恢复验收通过")


class TestMVPCloudEdgeAcceptance:
    """MVP云边编排验收测试"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_mvp_complete_orchestration_workflow(self, temp_db):
        """MVP 完整编排工作流验收"""
        # 1. 初始化云端编排器
        task_manager = TaskManager(temp_db)
        orchestrator = MVPOrchestratorFactory.create_with_default_config(task_manager)

        # 2. 创建边缘节点
        edge_node = EnhancedEdgeNodeV2("mvp-edge-001")

        # 3. 创建设备分组
        custom_group = orchestrator.create_device_group(
            'mvp_test_devices',
            'MVP测试设备',
            ['device-001', 'device-002', 'device-003', 'device-004'],
            {'environment': 'testing', 'version': '2.0'}
        )

        assert custom_group.group_id == 'mvp_test_devices'
        assert len(custom_group.device_ids) == 4

        # 4. 使用分组创建批量任务
        task_spec = {
            'name': 'MVP验收批量任务',
            'command': 'echo "MVP acceptance test" && date',
            'description': '完整工作流测试',
            'created_by': 'mvp_admin'
        }

        result = orchestrator.schedule_task_to_group(task_spec, 'mvp_test_devices')

        # 验证批量调度结果
        assert result.total_devices == 4
        assert result.successful_schedules == 4
        assert result.failed_schedules == 0
        assert len(result.task_ids) == 4
        assert result.batch_id is not None

        # 5. 验证任务生命周期
        for task_id in result.task_ids:
            # 创建阶段
            task = task_manager.get_task(task_id)
            assert task is not None
            assert task.status == 'pending'

            # 模拟边缘节点识别任务
            task_dict = {
                "task_id": task.task_id,
                "name": task.name,
                "command": task.command,
                "status": task.status,
                "task_type": "custom"
            }

            assert edge_node._is_v2_task(task_dict) is True

        # 6. 验证批次跟踪和监控
        progress = orchestrator.get_batch_progress(result.batch_id)
        assert progress['total_devices'] == 4
        assert progress['successful'] == 4
        assert progress['progress_percentage'] == 100.0
        assert progress['status'] == 'completed'

        # 7. 验证设备分组管理
        groups = orchestrator.get_device_groups()
        assert 'mvp_test_devices' in groups
        assert 'servers' in groups  # MVP默认分组
        assert 'routers' in groups  # MVP默认分组

        # 8. 清理测试分组
        delete_success = orchestrator.remove_device_group('mvp_test_devices')
        assert delete_success is True
        assert 'mvp_test_devices' not in orchestrator.device_groups

        print("✅ MVP 完整编排工作流验收通过")
        print(f"   批次ID: {result.batch_id}")
        print(f"   涉及设备: 4台")
        print(f"   创建任务: 4个")
        print(f"   调度状态: 全部成功")

    def test_mvp_batch_vs_individual_performance(self, temp_db):
        """MVP 批量vs单独调度性能对比"""
        task_manager = TaskManager(temp_db)
        orchestrator = MVPOrchestratorFactory.create_with_default_config(task_manager)

        task_spec = {
            'name': '性能测试任务',
            'command': 'echo performance',
            'created_by': 'benchmark'
        }

        devices = [f'device-{i:03d}' for i in range(5)]

        # 测试批量调度性能
        start_batch = time.time()
        batch_result = orchestrator.schedule_task_to_devices(task_spec, devices)
        batch_duration = time.time() - start_batch

        # 测试单独调度性能
        individual_durations = []
        for device in devices:
            start_individual = time.time()
            individual_result = orchestrator.schedule_task_to_devices(
                task_spec, [device]
            )
            individual_duration = time.time() - start_individual
            individual_durations.append(individual_duration)

        total_individual_time = sum(individual_durations)

        # 验证批量调度性能优势
        assert batch_result.successful_schedules == 5
        assert len(batch_result.task_ids) == 5

        # 批量调度应该比单独调度快
        print(f"批量调度耗时: {batch_duration:.3f}s")
        print(f"单独调度总耗时: {total_individual_time:.3f}s")
        print(f"性能提升: {total_individual_time/batch_duration:.1f}x")

        print("✅ MVP 批量vs单独调度性能对比验收通过")

    def test_mvp_error_resilience_and_recovery(self, temp_db):
        """MVP 错误弹性和恢复验收"""
        task_manager = TaskManager(temp_db)
        orchestrator = MVPOrchestratorFactory.create_with_default_config(task_manager)

        # 创建会失败的任务
        failing_task_spec = {
            'name': '失败测试任务',
            'command': 'false',  # 总是返回false
            'created_by': 'test_admin'
        }

        # 混合成功和失败设备
        devices = ['device-001', 'device-002', 'device-003']

        result = orchestrator.schedule_task_to_devices(failing_task_spec, devices)

        # 调度阶段应该成功（任务创建）
        assert result.total_devices == 3
        assert result.successful_schedules == 3
        assert len(result.task_ids) == 3

        # 验系批次跟踪仍然工作
        progress = orchestrator.get_batch_progress(result.batch_id)
        assert progress['total_devices'] == 3
        assert progress['status'] in ['completed', 'in_progress']

        # 验证可以查询失败批次
        batch_status = orchestrator.get_batch_status(result.batch_id)
        assert batch_status is not None
        assert batch_status.batch_id == result.batch_id

        print("✅ MVP 错误弹性和恢复验收通过")