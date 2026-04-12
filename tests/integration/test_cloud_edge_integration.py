"""
集成测试 - 云端与边缘节点集成

测试云端API和边缘节点之间的完整集成
"""

import unittest
import asyncio
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cloud.database.db import Database
from edge.storage.storage import EdgeStorage


class TestCloudEdgeIntegration(unittest.TestCase):
    """测试云端与边缘节点的集成"""

    def setUp(self):
        """测试前设置"""
        self.db = Database()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """测试后清理"""
        self.loop.close()

    def test_node_registration_flow(self):
        """测试节点注册流程"""

        async def run_test():
            # 创建边缘存储
            EdgeStorage()

            # 模拟节点注册
            node_id = "test-node-1"
            registration_data = {
                "node_id": node_id,
                "name": "测试节点1",
                "capabilities": {"ssh": True, "max_tasks": 5},
            }

            # 通过数据库注册节点
            self.db.add_node(
                node_id,
                {
                    "node_id": node_id,
                    "name": registration_data["name"],
                    "status": "online",
                    "capabilities": registration_data["capabilities"],
                    "last_heartbeat": time.time(),
                },
            )

            # 验证节点已注册
            registered_node = self.db.get_node(node_id)
            self.assertIsNotNone(registered_node)
            self.assertEqual(registered_node["status"], "online")
            self.assertIn("ssh", registered_node["capabilities"])

        self.loop.run_until_complete(run_test())

    def test_heartbeat_flow(self):
        """测试心跳流程"""

        async def run_test():
            node_id = "heartbeat-node"

            # 注册节点
            self.db.add_node(
                node_id,
                {"node_id": node_id, "status": "online", "last_heartbeat": time.time()},
            )

            # 模拟心跳更新
            heartbeat_data = {
                "status": "online",
                "cpu_usage": 35.5,
                "memory_usage": 60.2,
                "active_tasks": 2,
            }

            self.db.update_node(
                node_id, {"last_heartbeat": time.time(), **heartbeat_data}
            )

            # 验证心跳更新
            updated_node = self.db.get_node(node_id)
            self.assertEqual(updated_node["cpu_usage"], 35.5)
            self.assertEqual(updated_node["active_tasks"], 2)

        self.loop.run_until_complete(run_test())

    def test_task_creation_and_assignment(self):
        """测试任务创建和分配"""

        async def run_test():
            # 注册节点
            self.db.add_node("task-node", {"node_id": "task-node", "status": "online"})

            # 注册设备
            self.db.add_device(
                "task-device",
                {
                    "device_id": "task-device",
                    "name": "测试设备",
                    "host": "192.168.1.100",
                },
            )

            # 创建任务
            job_id = "test-job-1"
            job_data = {
                "job_id": job_id,
                "name": "测试任务",
                "type": "basic_exec",
                "status": "pending",
                "target_device_id": "task-device",
                "command": "uptime",
                "node_id": "task-node",
                "created_at": time.time(),
            }

            self.db.add_job(job_id, job_data)

            # 验证任务创建
            created_job = self.db.get_job(job_id)
            self.assertIsNotNone(created_job)
            self.assertEqual(created_job["command"], "uptime")
            self.assertEqual(created_job["node_id"], "task-node")

        self.loop.run_until_complete(run_test())

    def test_task_execution_flow(self):
        """测试任务执行流程"""

        async def run_test():
            # 创建任务
            job_id = "exec-job-1"
            self.db.add_job(
                job_id, {"job_id": job_id, "status": "pending", "command": "uptime"}
            )

            # 模拟任务开始执行
            self.db.update_job(job_id, {"status": "running"})

            running_job = self.db.get_job(job_id)
            self.assertEqual(running_job["status"], "running")

            # 模拟任务完成
            result = {
                "success": True,
                "stdout": "up 1 day, 2:30",
                "exit_code": 0,
                "execution_time": 1.5,
            }

            self.db.update_job(
                job_id,
                {"status": "success", "result": result, "completed_at": time.time()},
            )

            # 验证任务完成
            completed_job = self.db.get_job(job_id)
            self.assertEqual(completed_job["status"], "success")
            self.assertIn("result", completed_job)
            self.assertTrue(completed_job["result"]["success"])

        self.loop.run_until_complete(run_test())

    def test_event_logging_flow(self):
        """测试事件记录流程"""

        async def run_test():
            # 记录节点注册事件
            self.db.add_event(
                {
                    "event_id": "event-1",
                    "type": "node_registered",
                    "level": "info",
                    "source": "node-1",
                    "message": "节点注册成功",
                }
            )

            # 记录任务完成事件
            self.db.add_event(
                {
                    "event_id": "event-2",
                    "type": "job_completed",
                    "level": "info",
                    "source": "cloud",
                    "message": "任务完成",
                }
            )

            # 记录错误事件
            self.db.add_event(
                {
                    "event_id": "event-3",
                    "type": "error",
                    "level": "error",
                    "source": "node-2",
                    "message": "连接失败",
                }
            )

            # 验证事件记录
            events = self.db.list_events()
            self.assertEqual(len(events), 3)

            # 验证事件类型过滤
            error_events = self.db.list_events(event_type="error")
            self.assertEqual(len(error_events), 1)

        self.loop.run_until_complete(run_test())


class TestTaskLifecycle(unittest.TestCase):
    """测试任务生命周期"""

    def setUp(self):
        """测试前设置"""
        self.db = Database()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """测试后清理"""
        self.loop.close()

    def test_complete_task_lifecycle(self):
        """测试完整任务生命周期"""

        async def run_test():
            # 准备环境
            self.db.add_node(
                "lifecycle-node", {"node_id": "lifecycle-node", "status": "online"}
            )
            self.db.add_device(
                "lifecycle-device",
                {"device_id": "lifecycle-device", "host": "localhost"},
            )

            # 1. 创建任务
            job_id = "lifecycle-job"
            self.db.add_job(
                job_id,
                {
                    "job_id": job_id,
                    "status": "pending",
                    "command": "uptime",
                    "node_id": "lifecycle-node",
                },
            )

            job = self.db.get_job(job_id)
            self.assertEqual(job["status"], "pending")

            # 2. 分配任务
            self.db.update_job(job_id, {"status": "running"})
            job = self.db.get_job(job_id)
            self.assertEqual(job["status"], "running")

            # 3. 完成任务
            self.db.update_job(
                job_id,
                {
                    "status": "success",
                    "result": {"success": True, "stdout": "test output"},
                },
            )
            job = self.db.get_job(job_id)
            self.assertEqual(job["status"], "success")

            # 4. 验证统计信息
            stats = self.db.get_stats()
            self.assertEqual(stats["total_jobs"], 1)

        self.loop.run_until_complete(run_test())

    def test_task_cancellation(self):
        """测试任务取消"""

        async def run_test():
            job_id = "cancel-job"

            # 创建运行中的任务
            self.db.add_job(
                job_id,
                {"job_id": job_id, "status": "running", "command": "long-running-task"},
            )

            # 取消任务
            self.db.update_job(
                job_id,
                {
                    "status": "cancelled",
                    "result": {"cancelled": True, "reason": "用户取消"},
                },
            )

            # 验证任务被取消
            job = self.db.get_job(job_id)
            self.assertEqual(job["status"], "cancelled")
            self.assertTrue(job["result"]["cancelled"])

        self.loop.run_until_complete(run_test())

    def test_task_failure_handling(self):
        """测试任务失败处理"""

        async def run_test():
            job_id = "failed-job"

            # 创建任务
            self.db.add_job(
                job_id,
                {"job_id": job_id, "status": "running", "command": "invalid-command"},
            )

            # 模拟任务失败
            self.db.update_job(
                job_id,
                {
                    "status": "failed",
                    "result": {
                        "success": False,
                        "error": "Command not found",
                        "exit_code": 127,
                    },
                },
            )

            # 验证任务失败
            job = self.db.get_job(job_id)
            self.assertEqual(job["status"], "failed")
            self.assertFalse(job["result"]["success"])

            # 验证统计信息
            stats = self.db.get_stats()
            # 注意：根据实现，失败的任务可能计入不同的统计类别
            self.assertGreater(stats["total_jobs"], 0)

        self.loop.run_until_complete(run_test())


class TestMultiNodeScenarios(unittest.TestCase):
    """测试多节点场景"""

    def setUp(self):
        """测试前设置"""
        self.db = Database()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """测试后清理"""
        self.loop.close()

    def test_multiple_nodes_registration(self):
        """测试多节点注册"""

        async def run_test():
            # 注册多个节点
            nodes = [
                ("node-1", {"name": "节点1", "status": "online"}),
                ("node-2", {"name": "节点2", "status": "online"}),
                ("node-3", {"name": "节点3", "status": "offline"}),
            ]

            for node_id, node_data in nodes:
                self.db.add_node(node_id, {"node_id": node_id, **node_data})

            # 验证所有节点都注册成功
            all_nodes = self.db.list_nodes()
            self.assertEqual(len(all_nodes), 3)

            # 验证在线节点统计
            online_nodes = [n for n in all_nodes if n.get("status") == "online"]
            self.assertEqual(len(online_nodes), 2)

        self.loop.run_until_complete(run_test())

    def test_task_distribution_across_nodes(self):
        """测试任务在节点间分布"""

        async def run_test():
            # 注册多个节点
            for i in range(3):
                self.db.add_node(
                    f"node-{i}", {"node_id": f"node-{i}", "status": "online"}
                )

            # 创建任务并分配到不同节点
            for i in range(5):
                node_id = f"node-{i % 3}"  # 循环分配
                self.db.add_job(
                    f"job-{i}",
                    {
                        "job_id": f"job-{i}",
                        "status": "pending",
                        "node_id": node_id,
                        "command": "echo test",
                    },
                )

            # 验证任务分布
            node0_jobs = self.db.list_jobs(node_id="node-0")
            node1_jobs = self.db.list_jobs(node_id="node-1")
            node2_jobs = self.db.list_jobs(node_id="node-2")

            self.assertEqual(len(node0_jobs) + len(node1_jobs) + len(node2_jobs), 5)

        self.loop.run_until_complete(run_test())

    def test_node_failure_and_recovery(self):
        """测试节点故障和恢复"""

        async def run_test():
            node_id = "recovery-node"

            # 1. 节点在线
            self.db.add_node(
                node_id,
                {"node_id": node_id, "status": "online", "last_heartbeat": time.time()},
            )

            node = self.db.get_node(node_id)
            self.assertEqual(node["status"], "online")

            # 2. 节点故障
            self.db.update_node(
                node_id,
                {"status": "offline", "last_heartbeat": time.time() - 300},  # 5分钟前
            )

            node = self.db.get_node(node_id)
            self.assertEqual(node["status"], "offline")

            # 3. 节点恢复
            self.db.update_node(
                node_id, {"status": "online", "last_heartbeat": time.time()}
            )

            node = self.db.get_node(node_id)
            self.assertEqual(node["status"], "online")

        self.loop.run_until_complete(run_test())


class TestDataConsistency(unittest.TestCase):
    """测试数据一致性"""

    def setUp(self):
        """测试前设置"""
        self.db = Database()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """测试后清理"""
        self.loop.close()

    def test_audit_trail_consistency(self):
        """测试审计轨迹一致性"""

        async def run_test():
            # 执行一系列操作
            operations = [
                ("create", "user1", "job", "job-1"),
                ("update", "user1", "job", "job-1"),
                ("complete", "system", "job", "job-1"),
                ("create", "user2", "job", "job-2"),
            ]

            for action, actor, resource_type, resource_id in operations:
                self.db.add_audit_log(
                    {
                        "action": action,
                        "actor": actor,
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "success": True,
                    }
                )

            # 验证审计日志完整性
            all_logs = self.db.list_audit_logs()
            self.assertEqual(len(all_logs), 4)

            # 验证操作序列
            user1_logs = self.db.list_audit_logs(actor="user1")
            self.assertEqual(len(user1_logs), 2)

        self.loop.run_until_complete(run_test())

    def test_event_sequence_consistency(self):
        """测试事件序列一致性"""

        async def run_test():
            # 记录一系列事件
            events = [
                ("node_registered", "node-1", "info"),
                ("job_created", "cloud", "info"),
                ("job_assigned", "cloud", "info"),
                ("job_started", "node-1", "info"),
                ("job_completed", "node-1", "info"),
            ]

            for i, (event_type, source, level) in enumerate(events):
                self.db.add_event(
                    {
                        "event_id": f"event-{i}",
                        "type": event_type,
                        "source": source,
                        "level": level,
                        "message": f"{event_type} occurred",
                    }
                )

            # 验证事件序列
            all_events = self.db.list_events()
            self.assertEqual(len(all_events), 5)

            # 验证事件类型按预期顺序
            event_types = [e["type"] for e in all_events]
            expected_types = [e[0] for e in events]
            self.assertEqual(event_types, expected_types)

        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main()
