"""
共享模块测试
"""

import pytest
from shared.schemas.models import Node, Device, Job, EventType, JobType, DeviceType, DeviceProtocol
from shared.protocol.messages import MessageType, HeartbeatMessage, TaskMessage


def test_node_creation():
    """测试节点创建"""
    node = Node(
        node_id="test-node-1",
        name="Test Node",
        location="Test Location"
    )
    assert node.node_id == "test-node-1"
    assert node.name == "Test Node"
    assert node.status == "offline"


def test_device_creation():
    """测试设备创建"""
    device = Device(
        device_id="test-device-1",
        name="Test Device",
        type=DeviceType.LINUX_HOST,
        protocol=DeviceProtocol.SSH,
        host="192.168.1.100"
    )
    assert device.device_id == "test-device-1"
    assert device.host == "192.168.1.100"
    assert device.type == DeviceType.LINUX_HOST
    assert device.protocol == DeviceProtocol.SSH


def test_job_creation():
    """测试任务创建"""
    job = Job(
        job_id="test-job-1",
        name="Test Job",
        type=JobType.BASIC_EXEC,
        target_device_id="test-device-1"
    )
    assert job.job_id == "test-job-1"
    assert job.status == "pending"


def test_heartbeat_message():
    """测试心跳消息"""
    heartbeat = HeartbeatMessage(
        node_id="test-node-1",
        status="online"
    )
    assert heartbeat.type == MessageType.HEARTBEAT
    assert heartbeat.node_id == "test-node-1"


def test_task_message():
    """测试任务消息"""
    task = TaskMessage(
        node_id="test-node-1",
        task_id="test-task-1",
        task_type="inspection",
        target_device="test-device-1"
    )
    assert task.type == MessageType.TASK_ASSIGN
    assert task.task_id == "test-task-1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
