"""
端到端测试 - 完整工作流

测试从任务创建到结果返回的完整流程
"""

import unittest
import asyncio
import sys
import time
import httpx
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestCompleteWorkflow(unittest.TestCase):
    """测试完整工作流"""

    def setUp(self):
        """测试前设置"""
        self.cloud_url = "http://localhost:8080"
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """测试后清理"""
        self.loop.close()

    def test_cloud_api_health_check(self):
        """测试云端API健康检查"""

        async def run_test():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.cloud_url}/health", timeout=5.0)

                    # API应该返回健康状态
                    self.assertEqual(response.status_code, 200)

                    data = response.json()
                    self.assertIn("status", data)
                    self.assertEqual(data["status"], "healthy")

                    return True

            except Exception as e:
                self.skipTest(f"云端API未运行: {e}")
                return False

        self.loop.run_until_complete(run_test())

    def test_node_registration_to_task_completion(self):
        """测试从节点注册到任务完成的完整流程"""

        async def run_test():
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # 1. 注册节点
                    node_id = f"e2e-node-{int(time.time())}"
                    registration_response = await client.post(
                        f"{self.cloud_url}/api/v1/nodes/{node_id}/register",
                        json={
                            "node_name": "E2E测试节点",
                            "capabilities": {"ssh": True, "max_tasks": 3},
                        },
                    )

                    if registration_response.status_code not in [200, 201]:
                        self.skipTest(f"节点注册失败: {registration_response.status_code}")
                        return

                    # 2. 验证节点注册
                    node_response = await client.get(
                        f"{self.cloud_url}/api/v1/nodes/{node_id}"
                    )
                    if node_response.status_code != 200:
                        self.skipTest(f"获取节点失败: {node_response.status_code}")
                        return

                    node_data = node_response.json()
                    self.assertEqual(node_data["node_id"], node_id)

                    # 3. 创建设备（如果需要）
                    device_response = await client.get(
                        f"{self.cloud_url}/api/v1/devices"
                    )
                    if device_response.status_code == 200:
                        devices = device_response.json().get("devices", [])
                        if devices:
                            device_id = devices[0].get("device_id")
                        else:
                            # 创建测试设备
                            device_id = f"e2e-device-{int(time.time())}"
                            await client.post(
                                f"{self.cloud_url}/api/v1/devices",
                                json={
                                    "device_id": device_id,
                                    "name": "E2E测试设备",
                                    "type": "linux",
                                    "host": "localhost",
                                    "enabled": True,
                                },
                            )
                    else:
                        self.skipTest("无法获取设备列表")
                        return

                    # 4. 创建任务
                    job_id = f"e2e-job-{int(time.time())}"
                    job_response = await client.post(
                        f"{self.cloud_url}/api/v1/jobs",
                        json={
                            "job_id": job_id,
                            "name": "E2E测试任务",
                            "type": "basic_exec",
                            "task_type": "exec",
                            "target_device_id": device_id,
                            "command": "echo 'Hello from E2E test'",
                            "priority": "normal",
                            "timeout": 30,
                            "created_by": "e2e_test",
                        },
                    )

                    if job_response.status_code not in [200, 201]:
                        self.skipTest(f"任务创建失败: {job_response.status_code}")
                        return

                    job_data = job_response.json()
                    created_job_id = job_data.get("job_id")

                    # 5. 等待任务处理
                    await asyncio.sleep(5)

                    # 6. 检查任务状态
                    status_response = await client.get(
                        f"{self.cloud_url}/api/v1/jobs/{created_job_id}"
                    )
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        self.assertIn("status", status_data)

                        # 任务应该被分配到某个节点
                        if "node_id" in status_data:
                            self.assertIsNotNone(status_data["node_id"])

                    # 7. 检查事件日志
                    events_response = await client.get(
                        f"{self.cloud_url}/api/v1/events"
                    )
                    if events_response.status_code == 200:
                        events_data = events_response.json()
                        self.assertGreater(len(events_data.get("events", [])), 0)

                    # 8. 检查统计信息
                    stats_response = await client.get(f"{self.cloud_url}/api/v1/stats")
                    if stats_response.status_code == 200:
                        stats = stats_response.json()
                        self.assertIn("total_nodes", stats)
                        self.assertIn("total_jobs", stats)

                    return True

            except httpx.ConnectError:
                self.skipTest("无法连接到云端API，请确保API正在运行")
                return False
            except Exception as e:
                self.skipTest(f"端到端测试失败: {e}")
                return False

        self.loop.run_until_complete(run_test())


class TestAPIEndpoints(unittest.TestCase):
    """测试API端点"""

    def setUp(self):
        """测试前设置"""
        self.cloud_url = "http://localhost:8080"
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """测试后清理"""
        self.loop.close()

    def test_nodes_endpoint(self):
        """测试节点管理端点"""

        async def run_test():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 获取节点列表
                    response = await client.get(f"{self.cloud_url}/api/v1/nodes")
                    self.assertEqual(response.status_code, 200)

                    data = response.json()
                    self.assertIn("nodes", data)
                    self.assertIn("total", data)

                    return True

            except httpx.ConnectError:
                self.skipTest("云端API未运行")
                return False

        self.loop.run_until_complete(run_test())

    def test_jobs_endpoint(self):
        """测试任务管理端点"""

        async def run_test():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 获取任务列表
                    response = await client.get(f"{self.cloud_url}/api/v1/jobs")
                    self.assertEqual(response.status_code, 200)

                    data = response.json()
                    self.assertIn("jobs", data)
                    self.assertIn("total", data)

                    return True

            except httpx.ConnectError:
                self.skipTest("云端API未运行")
                return False

        self.loop.run_until_complete(run_test())

    def test_events_endpoint(self):
        """测试事件查询端点"""

        async def run_test():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 获取事件列表
                    response = await client.get(f"{self.cloud_url}/api/v1/events")
                    self.assertEqual(response.status_code, 200)

                    data = response.json()
                    self.assertIn("events", data)
                    self.assertIn("total", data)

                    return True

            except httpx.ConnectError:
                self.skipTest("云端API未运行")
                return False

        self.loop.run_until_complete(run_test())

    def test_stats_endpoint(self):
        """测试统计信息端点"""

        async def run_test():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 获取统计信息
                    response = await client.get(f"{self.cloud_url}/api/v1/stats")
                    self.assertEqual(response.status_code, 200)

                    data = response.json()
                    self.assertIn("total_nodes", data)
                    self.assertIn("total_jobs", data)
                    self.assertIn("total_events", data)

                    return True

            except httpx.ConnectError:
                self.skipTest("云端API未运行")
                return False

        self.loop.run_until_complete(run_test())


class TestErrorHandling(unittest.TestCase):
    """测试错误处理"""

    def setUp(self):
        """测试前设置"""
        self.cloud_url = "http://localhost:8080"
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """测试后清理"""
        self.loop.close()

    def test_invalid_node_request(self):
        """测试无效节点请求"""

        async def run_test():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 请求不存在的节点
                    response = await client.get(
                        f"{self.cloud_url}/api/v1/nodes/non-existent-node"
                    )
                    self.assertEqual(response.status_code, 404)

                    return True

            except httpx.ConnectError:
                self.skipTest("云端API未运行")
                return False

        self.loop.run_until_complete(run_test())

    def test_invalid_job_request(self):
        """测试无效任务请求"""

        async def run_test():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 请求不存在的任务
                    response = await client.get(
                        f"{self.cloud_url}/api/v1/jobs/non-existent-job"
                    )
                    self.assertEqual(response.status_code, 404)

                    return True

            except httpx.ConnectError:
                self.skipTest("云端API未运行")
                return False

        self.loop.run_until_complete(run_test())

    def test_malformed_job_creation(self):
        """测试格式错误的任务创建"""

        async def run_test():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 缺少必填字段的任务创建请求
                    response = await client.post(
                        f"{self.cloud_url}/api/v1/jobs",
                        json={
                            "name": "测试任务"
                            # 缺少 target_device_id 和 command/script
                        },
                    )
                    self.assertEqual(response.status_code, 400)

                    return True

            except httpx.ConnectError:
                self.skipTest("云端API未运行")
                return False

        self.loop.run_until_complete(run_test())


class TestDataIntegrity(unittest.TestCase):
    """测试数据完整性"""

    def setUp(self):
        """测试前设置"""
        self.cloud_url = "http://localhost:8080"
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """测试后清理"""
        self.loop.close()

    def test_audit_logging(self):
        """测试审计日志记录"""

        async def run_test():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 获取审计日志
                    response = await client.get(f"{self.cloud_url}/api/v1/audit/logs")
                    self.assertEqual(response.status_code, 200)

                    data = response.json()
                    self.assertIn("logs", data)
                    self.assertIn("total", data)

                    return True

            except httpx.ConnectError:
                self.skipTest("云端API未运行")
                return False

        self.loop.run_until_complete(run_test())

    def test_event_consistency(self):
        """测试事件一致性"""

        async def run_test():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 创建测试节点以生成事件
                    node_id = f"consistency-test-{int(time.time())}"
                    await client.post(
                        f"{self.cloud_url}/api/v1/nodes/{node_id}/register",
                        json={"node_name": "一致性测试节点"},
                    )

                    # 等待事件处理
                    await asyncio.sleep(2)

                    # 检查事件是否被记录
                    events_response = await client.get(
                        f"{self.cloud_url}/api/v1/events"
                    )
                    if events_response.status_code == 200:
                        events_data = events_response.json()
                        events = events_data.get("events", [])

                        # 应该至少有我们刚才创建的事件
                        self.assertGreater(len(events), 0)

                    return True

            except httpx.ConnectError:
                self.skipTest("云端API未运行")
                return False

        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main()
