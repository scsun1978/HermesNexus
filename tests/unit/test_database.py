"""
数据库模块单元测试

测试数据库的CRUD操作和线程安全性
"""

import unittest
import threading
import time
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cloud.database.db import Database


class TestDatabaseCRUD(unittest.TestCase):
    """测试数据库CRUD操作"""

    def setUp(self):
        """测试前设置"""
        self.db = Database()

    def test_add_and_get_node(self):
        """测试添加和获取节点"""
        node_id = "test-node-1"
        node_data = {
            "node_id": node_id,
            "name": "测试节点",
            "status": "online",
            "cpu_usage": 25.5,
        }

        # 添加节点
        result = self.db.add_node(node_id, node_data)
        self.assertTrue(result)

        # 获取节点
        retrieved_node = self.db.get_node(node_id)
        self.assertIsNotNone(retrieved_node)
        self.assertEqual(retrieved_node["node_id"], node_id)
        self.assertEqual(retrieved_node["name"], "测试节点")

    def test_add_and_get_job(self):
        """测试添加和获取任务"""
        job_id = "test-job-1"
        job_data = {
            "job_id": job_id,
            "name": "测试任务",
            "command": "uptime",
            "status": "pending",
        }

        # 添加任务
        result = self.db.add_job(job_id, job_data)
        self.assertTrue(result)

        # 获取任务
        retrieved_job = self.db.get_job(job_id)
        self.assertIsNotNone(retrieved_job)
        self.assertEqual(retrieved_job["job_id"], job_id)
        self.assertEqual(retrieved_job["command"], "uptime")

    def test_add_and_get_device(self):
        """测试添加和获取设备"""
        device_id = "test-device-1"
        device_data = {
            "device_id": device_id,
            "name": "测试设备",
            "type": "linux",
            "host": "192.168.1.100",
        }

        # 添加设备
        result = self.db.add_device(device_id, device_data)
        self.assertTrue(result)

        # 获取设备
        retrieved_device = self.db.get_device(device_id)
        self.assertIsNotNone(retrieved_device)
        self.assertEqual(retrieved_device["device_id"], device_id)

    def test_update_node(self):
        """测试更新节点"""
        node_id = "test-node-2"
        original_data = {"node_id": node_id, "status": "online", "cpu_usage": 20.0}

        # 添加原始节点
        self.db.add_node(node_id, original_data)

        # 更新节点
        updates = {"cpu_usage": 75.5, "memory_usage": 60.0}
        result = self.db.update_node(node_id, updates)
        self.assertTrue(result)

        # 验证更新
        updated_node = self.db.get_node(node_id)
        self.assertEqual(updated_node["cpu_usage"], 75.5)
        self.assertEqual(updated_node["memory_usage"], 60.0)
        # 原有字段应该保持不变
        self.assertEqual(updated_node["status"], "online")

    def test_update_job(self):
        """测试更新任务"""
        job_id = "test-job-2"
        original_data = {"job_id": job_id, "status": "pending", "command": "uptime"}

        # 添加原始任务
        self.db.add_job(job_id, original_data)

        # 更新任务状态
        updates = {"status": "success", "result": {"exit_code": 0}}
        result = self.db.update_job(job_id, updates)
        self.assertTrue(result)

        # 验证更新
        updated_job = self.db.get_job(job_id)
        self.assertEqual(updated_job["status"], "success")
        self.assertIn("result", updated_job)

    def test_list_nodes(self):
        """测试列出节点"""
        # 添加多个节点
        nodes = [
            ("node-1", {"node_id": "node-1", "status": "online"}),
            ("node-2", {"node_id": "node-2", "status": "offline"}),
            ("node-3", {"node_id": "node-3", "status": "online"}),
        ]

        for node_id, node_data in nodes:
            self.db.add_node(node_id, node_data)

        # 列出所有节点
        all_nodes = self.db.list_nodes()
        self.assertEqual(len(all_nodes), 3)

        # 过滤在线节点
        online_nodes = [n for n in all_nodes if n.get("status") == "online"]
        self.assertEqual(len(online_nodes), 2)

    def test_list_jobs(self):
        """测试列出任务"""
        # 添加多个任务
        jobs = [
            ("job-1", {"job_id": "job-1", "node_id": "node-1"}),
            ("job-2", {"job_id": "job-2", "node_id": "node-1"}),
            ("job-3", {"job_id": "job-3", "node_id": "node-2"}),
        ]

        for job_id, job_data in jobs:
            self.db.add_job(job_id, job_data)
            # 更新状态
            if job_id == "job-2":
                self.db.update_job(job_id, {"status": "running"})

        # 列出所有任务
        all_jobs = self.db.list_jobs()
        self.assertEqual(len(all_jobs), 3)

        # 按状态过滤 (job-1和job-3是pending状态)
        pending_jobs = self.db.list_jobs(status="pending")
        self.assertEqual(len(pending_jobs), 2)

        # 按节点过滤
        node1_jobs = self.db.list_jobs(node_id="node-1")
        self.assertEqual(len(node1_jobs), 2)

    def test_add_and_list_events(self):
        """测试添加和列出事件"""
        events = [
            {"event_id": "event-1", "type": "node_registered", "level": "info"},
            {"event_id": "event-2", "type": "job_completed", "level": "info"},
            {"event_id": "event-3", "type": "error", "level": "error"},
        ]

        for event in events:
            self.db.add_event(event)

        # 列出事件
        all_events = self.db.list_events()
        self.assertEqual(len(all_events), 3)

        # 按级别过滤
        error_events = self.db.list_events(event_type="error")
        self.assertEqual(len(error_events), 1)

    def test_add_and_list_audit_logs(self):
        """测试添加和列出审计日志"""
        logs = [
            {"action": "create", "actor": "user1", "resource_type": "job"},
            {"action": "update", "actor": "user2", "resource_type": "node"},
            {"action": "delete", "actor": "user1", "resource_type": "device"},
        ]

        for log in logs:
            self.db.add_audit_log(log)

        # 列出审计日志
        all_logs = self.db.list_audit_logs()
        self.assertEqual(len(all_logs), 3)

        # 按操作者过滤
        user1_logs = self.db.list_audit_logs(actor="user1")
        self.assertEqual(len(user1_logs), 2)

    def test_get_stats(self):
        """测试获取统计信息"""
        # 添加测试数据
        self.db.add_node("node-1", {"node_id": "node-1", "status": "online"})
        self.db.add_node("node-2", {"node_id": "node-2", "status": "offline"})

        # 添加任务（会自动设置为pending）
        self.db.add_job("job-1", {"job_id": "job-1"})
        self.db.add_job("job-2", {"job_id": "job-2"})

        # 更新第二个任务状态
        self.db.update_job("job-2", {"status": "success"})

        # 获取统计信息
        stats = self.db.get_stats()

        self.assertEqual(stats["total_nodes"], 2)
        self.assertEqual(stats["online_nodes"], 1)
        self.assertEqual(stats["total_jobs"], 2)
        # 现在只有job-1是pending状态
        self.assertEqual(stats["pending_jobs"], 1)
        self.assertIn("total_events", stats)


class TestDatabaseThreadSafety(unittest.TestCase):
    """测试数据库线程安全性"""

    def setUp(self):
        """测试前设置"""
        self.db = Database()
        self.errors = []

    def test_concurrent_node_updates(self):
        """测试并发节点更新"""
        node_id = "concurrent-node"
        self.db.add_node(node_id, {"node_id": node_id, "cpu_usage": 0.0})

        def update_node(thread_id):
            try:
                for i in range(100):
                    self.db.update_node(node_id, {"cpu_usage": float(i)})
                    time.sleep(0.001)  # 模拟一些处理时间
            except Exception as e:
                self.errors.append(f"Thread {thread_id}: {e}")

        # 创建多个线程同时更新节点
        threads = []
        for i in range(5):
            thread = threading.Thread(target=update_node, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 检查是否有错误
        self.assertEqual(len(self.errors), 0, f"并发更新出错: {self.errors}")

        # 验证节点数据仍然有效
        node = self.db.get_node(node_id)
        self.assertIsNotNone(node)
        self.assertIn("cpu_usage", node)

    def test_concurrent_job_creation(self):
        """测试并发任务创建"""

        def create_jobs(thread_id):
            try:
                for i in range(50):
                    job_id = f"job-{thread_id}-{i}"
                    self.db.add_job(
                        job_id,
                        {"job_id": job_id, "status": "pending", "command": "echo test"},
                    )
            except Exception as e:
                self.errors.append(f"Thread {thread_id}: {e}")

        # 创建多个线程同时创建任务
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_jobs, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 检查是否有错误
        self.assertEqual(len(self.errors), 0, f"并发创建出错: {self.errors}")

        # 验证任务数量
        all_jobs = self.db.list_jobs()
        self.assertEqual(len(all_jobs), 250)  # 5 threads * 50 jobs

    def test_concurrent_reads_and_writes(self):
        """测试并发读写操作"""
        node_id = "rw-node"
        self.db.add_node(node_id, {"node_id": node_id, "counter": 0})

        def read_write(thread_id):
            try:
                for i in range(50):
                    # 读取
                    node = self.db.get_node(node_id)
                    if node:
                        # 写入
                        current = node.get("counter", 0)
                        self.db.update_node(node_id, {"counter": current + 1})
                    time.sleep(0.001)
            except Exception as e:
                self.errors.append(f"Thread {thread_id}: {e}")

        # 创建读写线程
        threads = []
        for i in range(3):
            thread = threading.Thread(target=read_write, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 检查是否有错误
        self.assertEqual(len(self.errors), 0, f"并发读写出错: {self.errors}")

        # 验证最终计数器值
        node = self.db.get_node(node_id)
        self.assertIsNotNone(node)
        # 计数器应该是 3 * 50 = 150
        self.assertEqual(node.get("counter"), 150)


class TestDatabaseEdgeCases(unittest.TestCase):
    """测试数据库边界情况"""

    def setUp(self):
        """测试前设置"""
        self.db = Database()

    def test_get_nonexistent_node(self):
        """测试获取不存在的节点"""
        node = self.db.get_node("nonexistent")
        self.assertIsNone(node)

    def test_update_nonexistent_node(self):
        """测试更新不存在的节点"""
        result = self.db.update_node("nonexistent", {"cpu_usage": 50.0})
        self.assertFalse(result)

    def test_empty_database_stats(self):
        """测试空数据库统计"""
        stats = self.db.get_stats()
        self.assertEqual(stats["total_nodes"], 0)
        self.assertEqual(stats["total_jobs"], 0)
        self.assertEqual(stats["online_nodes"], 0)

    def test_event_list_limit(self):
        """测试事件列表限制"""
        # 添加超过限制的事件
        for i in range(1500):  # 超过1000的限制
            self.db.add_event({"event_id": f"event-{i}", "type": "test", "level": "info"})

        # 事件数量应该被限制在1000
        all_events = self.db.list_events(limit=2000)
        self.assertLessEqual(len(all_events), 1000)

    def test_audit_log_limit(self):
        """测试审计日志限制"""
        # 添加超过限制的审计日志
        for i in range(1500):  # 超过1000的限制
            self.db.add_audit_log({"action": "test", "actor": f"user-{i}", "resource_type": "test"})

        # 审计日志数量应该被限制在1000
        all_logs = self.db.list_audit_logs(limit=2000)
        self.assertLessEqual(len(all_logs), 1000)


if __name__ == "__main__":
    unittest.main()
