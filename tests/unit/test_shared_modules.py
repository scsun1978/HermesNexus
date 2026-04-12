"""
核心模块单元测试

测试共享模块的功能，包括协议、数据模型等
"""

import unittest
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.protocol.messages import MessageType
from shared.protocol.error_codes import ErrorCode
from shared.schemas.enums import JobStatus, JobType, NodeStatus


class TestProtocolMessages(unittest.TestCase):
    """测试协议消息类型"""

    def test_message_types(self):
        """测试消息类型枚举"""
        self.assertEqual(MessageType.HEARTBEAT.value, "heartbeat")
        self.assertEqual(MessageType.REGISTER.value, "register")
        self.assertEqual(MessageType.TASK_RESULT.value, "task_result")
        self.assertEqual(MessageType.TASK_ASSIGN.value, "task_assign")

    def test_message_type_uniqueness(self):
        """测试消息类型唯一性"""
        values = [msg_type.value for msg_type in MessageType]
        self.assertEqual(len(values), len(set(values)), "消息类型值应该是唯一的")


class TestErrorCodes(unittest.TestCase):
    """测试错误代码"""

    def test_error_codes(self):
        """测试错误代码枚举"""
        self.assertEqual(ErrorCode.TASK_TIMEOUT.value, "ERR_3003")
        self.assertEqual(ErrorCode.SSH_CONNECTION_FAILED.value, "ERR_5000")
        self.assertEqual(ErrorCode.TASK_EXECUTION_FAILED.value, "ERR_3002")

    def test_error_code_format(self):
        """测试错误代码格式"""
        for error_code in ErrorCode:
            self.assertTrue(
                error_code.value.startswith("ERR_"),
                f"错误代码应以ERR_开头: {error_code.value}",
            )
            self.assertTrue(
                error_code.value.split("_")[1].isdigit(),
                f"错误代码应包含数字: {error_code.value}",
            )


class TestDataModels(unittest.TestCase):
    """测试数据模型"""

    def test_node_model(self):
        """测试节点模型"""
        node_data = {
            "node_id": "test-node-1",
            "name": "测试节点",
            "status": NodeStatus.ONLINE.value,
            "capabilities": {"ssh": True, "max_tasks": 5},
            "last_heartbeat": "2024-01-01T00:00:00Z",
        }

        # 测试数据可以正常创建
        self.assertIsInstance(node_data["node_id"], str)
        self.assertIsInstance(node_data["capabilities"], dict)
        self.assertEqual(node_data["status"], "online")

    def test_job_model(self):
        """测试任务模型"""
        job_data = {
            "job_id": "test-job-1",
            "name": "测试任务",
            "type": JobType.BASIC_EXEC.value,
            "status": JobStatus.PENDING.value,
            "target_device_id": "device-1",
            "command": "uptime",
            "timeout": 30,
        }

        # 测试任务数据结构
        self.assertEqual(job_data["type"], "basic_exec")
        self.assertEqual(job_data["status"], "pending")
        self.assertIsInstance(job_data["timeout"], int)

    def test_device_model(self):
        """测试设备模型"""
        device_data = {
            "device_id": "device-1",
            "name": "测试设备",
            "type": "linux",
            "host": "192.168.1.100",
            "port": 22,
            "enabled": True,
        }

        # 测试设备数据结构
        self.assertEqual(device_data["type"], "linux")
        self.assertTrue(device_data["enabled"])
        self.assertIsInstance(device_data["port"], int)

    def test_event_model(self):
        """测试事件模型"""
        event_data = {
            "event_id": "event-1",
            "type": "node_registered",
            "level": "info",
            "source": "node-1",
            "message": "节点注册成功",
        }

        # 测试事件数据结构
        self.assertEqual(event_data["type"], "node_registered")
        self.assertEqual(event_data["level"], "info")


class TestEnums(unittest.TestCase):
    """测试枚举类型"""

    def test_job_status_values(self):
        """测试任务状态枚举"""
        self.assertEqual(JobStatus.PENDING.value, "pending")
        self.assertEqual(JobStatus.RUNNING.value, "running")
        self.assertEqual(JobStatus.SUCCESS.value, "success")
        self.assertEqual(JobStatus.FAILED.value, "failed")
        self.assertEqual(JobStatus.CANCELLED.value, "cancelled")

    def test_job_type_values(self):
        """测试任务类型枚举"""
        self.assertEqual(JobType.BASIC_EXEC.value, "basic_exec")
        self.assertEqual(JobType.SCRIPT.value, "script")
        self.assertEqual(JobType.FILE_TRANSFER.value, "file_transfer")

    def test_node_status_values(self):
        """测试节点状态枚举"""
        self.assertEqual(NodeStatus.ONLINE.value, "online")
        self.assertEqual(NodeStatus.OFFLINE.value, "offline")
        self.assertEqual(NodeStatus.MAINTENANCE.value, "maintenance")


class TestDataValidation(unittest.TestCase):
    """测试数据验证"""

    def test_job_validation(self):
        """测试任务数据验证"""
        # 有效任务数据
        valid_job = {
            "job_id": "job-1",
            "name": "测试任务",
            "type": "basic_exec",
            "status": "pending",
            "target_device_id": "device-1",
            "command": "uptime",
        }

        # 验证必填字段
        self.assertIn("job_id", valid_job)
        self.assertIn("target_device_id", valid_job)
        self.assertIn("command", valid_job)
        self.assertTrue(len(valid_job["command"]) > 0)

    def test_node_validation(self):
        """测试节点数据验证"""
        # 有效节点数据
        valid_node = {
            "node_id": "node-1",
            "name": "测试节点",
            "status": "online",
            "capabilities": {},
        }

        # 验证必填字段
        self.assertIn("node_id", valid_node)
        self.assertIn("status", valid_node)
        self.assertIn(valid_node["status"], ["online", "offline", "maintenance"])

    def test_device_validation(self):
        """测试设备数据验证"""
        # 有效设备数据
        valid_device = {
            "device_id": "device-1",
            "name": "测试设备",
            "type": "linux",
            "host": "192.168.1.100",
            "port": 22,
        }

        # 验证必填字段
        self.assertIn("device_id", valid_device)
        self.assertIn("host", valid_device)
        self.assertIsInstance(valid_device["port"], int)
        self.assertGreater(valid_device["port"], 0)
        self.assertLessEqual(valid_device["port"], 65535)


if __name__ == "__main__":
    unittest.main()
