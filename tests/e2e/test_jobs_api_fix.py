"""
测试jobs API修复 - 验证422错误是否解决

专门测试 /api/v1/jobs 端点的契约正确性
"""

import unittest
import asyncio
import httpx
import time
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestJobsAPIFix(unittest.TestCase):
    """专门测试jobs API修复"""

    def setUp(self):
        """测试前设置"""
        self.cloud_url = "http://localhost:8080"
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """测试后清理"""
        self.loop.close()

    def test_get_jobs_endpoint(self):
        """测试GET /api/v1/jobs端点 - 最基础的连通性测试"""

        async def run_test():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 直接获取任务列表，不传任何参数
                    response = await client.get(f"{self.cloud_url}/api/v1/jobs")

                    print(f"GET /api/v1/jobs - Status: {response.status_code}")
                    print(f"Response: {response.text}")

                    # 应该返回200，不是422
                    self.assertEqual(
                        response.status_code,
                        200,
                        f"Expected 200, got {response.status_code}. Response: {response.text}",
                    )

                    data = response.json()
                    # 验证响应格式
                    self.assertIn("jobs", data)
                    self.assertIn("total", data)
                    self.assertIsInstance(data["jobs"], list)
                    self.assertIsInstance(data["total"], int)

                    print(f"✅ GET /api/v1/jobs 返回正确格式: jobs={data['total']}")
                    return True

            except httpx.ConnectError:
                self.skipTest("无法连接到云端API，请确保API正在运行")
                return False
            except Exception as e:
                self.fail(f"测试失败: {e}")
                return False

        self.loop.run_until_complete(run_test())

    def test_get_jobs_with_parameters(self):
        """测试GET /api/v1/jobs带查询参数"""

        async def run_test():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 测试带参数的请求
                    response = await client.get(
                        f"{self.cloud_url}/api/v1/jobs", params={"status": "pending", "limit": 10}
                    )

                    print(
                        f"GET /api/v1/jobs?status=pending&limit=10 - Status: {response.status_code}"
                    )

                    # 应该返回200，不是422
                    self.assertEqual(
                        response.status_code,
                        200,
                        f"Expected 200, got {response.status_code}. Response: {response.text}",
                    )

                    data = response.json()
                    self.assertIn("jobs", data)
                    self.assertIn("total", data)

                    print(f"✅ GET /api/v1/jobs 带参数返回正确格式: jobs={data['total']}")
                    return True

            except httpx.ConnectError:
                self.skipTest("无法连接到云端API")
                return False
            except Exception as e:
                self.fail(f"测试失败: {e}")
                return False

        self.loop.run_until_complete(run_test())

    def test_create_job_endpoint(self):
        """测试POST /api/v1/jobs端点 - 创建任务"""

        async def run_test():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 首先创建一个测试设备
                    device_id = f"test-device-{int(time.time())}"
                    device_response = await client.post(
                        f"{self.cloud_url}/api/v1/devices",
                        json={
                            "device_id": device_id,
                            "name": "测试设备",
                            "type": "linux",
                            "host": "localhost",
                            "enabled": True,
                        },
                    )

                    if device_response.status_code not in [200, 201]:
                        self.skipTest(f"无法创建测试设备: {device_response.status_code}")
                        return False

                    # 创建任务
                    job_id = f"test-job-{int(time.time())}"
                    job_response = await client.post(
                        f"{self.cloud_url}/api/v1/jobs",
                        json={
                            "job_id": job_id,
                            "name": "测试任务",
                            "type": "basic_exec",
                            "task_type": "exec",
                            "target_device_id": device_id,
                            "command": "echo 'Hello from API fix test'",
                            "priority": "normal",
                            "timeout": 30,
                            "created_by": "api_test",
                        },
                    )

                    print(f"POST /api/v1/jobs - Status: {job_response.status_code}")
                    print(f"Response: {job_response.text}")

                    # 不应该返回422，应该是200或201
                    self.assertIn(
                        job_response.status_code,
                        [200, 201],
                        f"Expected 200/201, got {job_response.status_code}. Response: {job_response.text}",
                    )

                    data = job_response.json()
                    # 验证响应格式
                    self.assertIn("job_id", data)
                    self.assertIn("status", data)
                    self.assertEqual(data["job_id"], job_id)

                    print(f"✅ POST /api/v1/jobs 创建任务成功: {job_id}")
                    return True

            except httpx.ConnectError:
                self.skipTest("无法连接到云端API")
                return False
            except Exception as e:
                self.fail(f"测试失败: {e}")
                return False

        self.loop.run_until_complete(run_test())

    def test_get_specific_job(self):
        """测试GET /api/v1/jobs/{job_id}端点"""

        async def run_test():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 先创建一个任务
                    device_id = f"test-device-{int(time.time())}"
                    await client.post(
                        f"{self.cloud_url}/api/v1/devices",
                        json={
                            "device_id": device_id,
                            "name": "测试设备",
                            "type": "linux",
                            "host": "localhost",
                            "enabled": True,
                        },
                    )

                    job_id = f"test-job-{int(time.time())}"
                    create_response = await client.post(
                        f"{self.cloud_url}/api/v1/jobs",
                        json={
                            "job_id": job_id,
                            "name": "测试任务",
                            "target_device_id": device_id,
                            "command": "echo 'test'",
                        },
                    )

                    if create_response.status_code not in [200, 201]:
                        self.skipTest("无法创建测试任务")
                        return False

                    # 获取任务详情
                    job_response = await client.get(f"{self.cloud_url}/api/v1/jobs/{job_id}")

                    print(f"GET /api/v1/jobs/{job_id} - Status: {job_response.status_code}")

                    # 应该返回200，不是422
                    self.assertEqual(
                        job_response.status_code,
                        200,
                        f"Expected 200, got {job_response.status_code}. Response: {job_response.text}",
                    )

                    data = job_response.json()
                    self.assertIn("job_id", data)
                    self.assertEqual(data["job_id"], job_id)

                    print(f"✅ GET /api/v1/jobs/{{job_id}} 返回正确格式")
                    return True

            except httpx.ConnectError:
                self.skipTest("无法连接到云端API")
                return False
            except Exception as e:
                self.fail(f"测试失败: {e}")
                return False

        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    # 运行测试并提供详细输出
    unittest.main(verbosity=2)
