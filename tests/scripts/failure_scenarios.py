"""
失败场景模拟脚本

测试各种失败场景下系统的错误处理和恢复能力
"""

import asyncio
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import httpx

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class FailureScenarios:
    """失败场景测试器"""

    def __init__(self, cloud_url="http://localhost:8080"):
        self.cloud_url = cloud_url
        self.client = None
        self.test_results = []

    async def __aenter__(self):
        """进入上下文"""
        self.client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if self.client:
            await self.client.aclose()

    def log_result(self, scenario, success, details=""):
        """记录测试结果"""
        result = {
            "scenario": scenario,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)

        status = "✅" if success else "❌"
        logger.info(f"{status} {scenario}: {details}")

    async def test_invalid_device(self):
        """测试无效设备"""
        try:
            logger.info("🧪 场景1: 无效设备ID")

            task_config = {
                "name": "无效设备测试",
                "type": "basic_exec",
                "task_type": "exec",
                "target_device_id": "non-existent-device-12345",
                "command": "echo test",
                "priority": "normal",
                "timeout": 10,
                "created_by": "failure_test",
            }

            response = await self.client.post(
                f"{self.cloud_url}/api/v1/jobs", json=task_config
            )

            if response.status_code == 404:
                self.log_result("无效设备ID", True, "正确返回404错误")
                return True
            elif response.status_code in [200, 201]:
                self.log_result("无效设备ID", False, "应该拒绝无效设备")
                return False
            else:
                self.log_result(
                    "无效设备ID", False, f"意外状态码: {response.status_code}"
                )
                return False

        except Exception as e:
            self.log_result("无效设备ID", False, f"异常: {str(e)}")
            return False

    async def test_invalid_command(self):
        """测试无效命令"""
        try:
            logger.info("🧪 场景2: 无效命令")

            # 首先获取有效设备
            response = await self.client.get(f"{self.cloud_url}/api/v1/devices")
            if response.status_code != 200:
                self.log_result("无效命令", False, "无法获取设备列表")
                return False

            devices = response.json().get("devices", [])
            if not devices:
                self.log_result("无效命令", False, "没有可用设备")
                return False

            device_id = devices[0].get("device_id")

            task_config = {
                "name": "无效命令测试",
                "type": "basic_exec",
                "task_type": "exec",
                "target_device_id": device_id,
                "command": "/invalid/nonexistent/command",
                "priority": "normal",
                "timeout": 10,
                "created_by": "failure_test",
            }

            response = await self.client.post(
                f"{self.cloud_url}/api/v1/jobs", json=task_config
            )

            if response.status_code in [200, 201]:
                job_data = response.json()
                job_id = job_data.get("job_id")

                # 等待任务执行并检查结果
                await asyncio.sleep(15)

                job_response = await self.client.get(
                    f"{self.cloud_url}/api/v1/jobs/{job_id}"
                )
                if job_response.status_code == 200:
                    job_status = job_response.json()
                    if job_status.get("status") == "failed":
                        self.log_result("无效命令", True, "任务正确失败")
                        return True
                    else:
                        self.log_result(
                            "无效命令",
                            False,
                            f"任务状态异常: {job_status.get('status')}",
                        )
                        return False
                else:
                    self.log_result("无效命令", False, "无法获取任务状态")
                    return False
            else:
                self.log_result(
                    "无效命令", False, f"创建任务失败: {response.status_code}"
                )
                return False

        except Exception as e:
            self.log_result("无效命令", False, f"异常: {str(e)}")
            return False

    async def test_timeout_command(self):
        """测试超时命令"""
        try:
            logger.info("🧪 场景3: 命令超时")

            # 获取有效设备
            response = await self.client.get(f"{self.cloud_url}/api/v1/devices")
            if response.status_code != 200:
                self.log_result("命令超时", False, "无法获取设备列表")
                return False

            devices = response.json().get("devices", [])
            if not devices:
                self.log_result("命令超时", False, "没有可用设备")
                return False

            device_id = devices[0].get("device_id")

            task_config = {
                "name": "超时命令测试",
                "type": "basic_exec",
                "task_type": "exec",
                "target_device_id": device_id,
                "command": "sleep 100",  # 一个会超时的命令
                "priority": "normal",
                "timeout": 5,  # 5秒超时
                "created_by": "failure_test",
            }

            response = await self.client.post(
                f"{self.cloud_url}/api/v1/jobs", json=task_config
            )

            if response.status_code in [200, 201]:
                job_data = response.json()
                job_id = job_data.get("job_id")

                # 等待超时发生
                await asyncio.sleep(10)

                job_response = await self.client.get(
                    f"{self.cloud_url}/api/v1/jobs/{job_id}"
                )
                if job_response.status_code == 200:
                    job_status = job_response.json()
                    status = job_status.get("status")

                    if status in ["failed", "cancelled"]:
                        self.log_result("命令超时", True, f"任务因超时被终止: {status}")
                        return True
                    else:
                        self.log_result(
                            "命令超时", False, f"任务应该因超时失败: {status}"
                        )
                        return False
                else:
                    self.log_result("命令超时", False, "无法获取任务状态")
                    return False
            else:
                self.log_result(
                    "命令超时", False, f"创建任务失败: {response.status_code}"
                )
                return False

        except Exception as e:
            self.log_result("命令超时", False, f"异常: {str(e)}")
            return False

    async def test_malformed_request(self):
        """测试格式错误的请求"""
        try:
            logger.info("🧪 场景4: 格式错误的请求")

            # 缺少必填字段的请求
            invalid_requests = [
                {
                    "name": "缺少device_id",
                    "type": "basic_exec",
                    "task_type": "exec",
                    # 缺少 target_device_id
                },
                {
                    "name": "缺少命令",
                    "type": "basic_exec",
                    "task_type": "exec",
                    "target_device_id": "test-device",
                    # 缺少 command 或 script
                },
                {
                    "name": "无效类型",
                    "type": "invalid_type",
                    "task_type": "exec",
                    "target_device_id": "test-device",
                    "command": "echo test",
                },
            ]

            all_correctly_rejected = True
            for i, invalid_request in enumerate(invalid_requests):
                response = await self.client.post(
                    f"{self.cloud_url}/api/v1/jobs", json=invalid_request
                )

                if response.status_code == 400:
                    logger.info(f"  ✅ 正确拒绝无效请求 {i+1}")
                else:
                    logger.warning(
                        f"  ⚠️  应该拒绝无效请求 {i+1}: {response.status_code}"
                    )
                    all_correctly_rejected = False

            if all_correctly_rejected:
                self.log_result("格式错误请求", True, "所有无效请求都被正确拒绝")
                return True
            else:
                self.log_result("格式错误请求", False, "部分无效请求未被正确处理")
                return False

        except Exception as e:
            self.log_result("格式错误请求", False, f"异常: {str(e)}")
            return False

    async def test_cancel_running_task(self):
        """测试取消运行中的任务"""
        try:
            logger.info("🧪 场景5: 取消运行中的任务")

            # 获取有效设备
            response = await self.client.get(f"{self.cloud_url}/api/v1/devices")
            if response.status_code != 200:
                self.log_result("取消运行任务", False, "无法获取设备列表")
                return False

            devices = response.json().get("devices", [])
            if not devices:
                self.log_result("取消运行任务", False, "没有可用设备")
                return False

            device_id = devices[0].get("device_id")

            # 创建一个会运行一段时间的任务
            task_config = {
                "name": "长时间运行任务",
                "type": "basic_exec",
                "task_type": "exec",
                "target_device_id": device_id,
                "command": "sleep 30",
                "priority": "normal",
                "timeout": 60,
                "created_by": "failure_test",
            }

            response = await self.client.post(
                f"{self.cloud_url}/api/v1/jobs", json=task_config
            )

            if response.status_code in [200, 201]:
                job_data = response.json()
                job_id = job_data.get("job_id")

                # 等待任务开始运行
                await asyncio.sleep(5)

                # 取消任务
                cancel_response = await self.client.patch(
                    f"{self.cloud_url}/api/v1/jobs/{job_id}/cancel",
                    json={"reason": "测试取消"},
                )

                if cancel_response.status_code == 200:
                    # 检查任务状态
                    await asyncio.sleep(2)

                    job_response = await self.client.get(
                        f"{self.cloud_url}/api/v1/jobs/{job_id}"
                    )
                    if job_response.status_code == 200:
                        job_status = job_response.json()
                        if job_status.get("status") == "cancelled":
                            self.log_result("取消运行任务", True, "任务成功被取消")
                            return True
                        else:
                            self.log_result(
                                "取消运行任务",
                                False,
                                f"任务状态异常: {job_status.get('status')}",
                            )
                            return False
                    else:
                        self.log_result("取消运行任务", False, "无法获取任务状态")
                        return False
                else:
                    self.log_result(
                        "取消运行任务",
                        False,
                        f"取消请求失败: {cancel_response.status_code}",
                    )
                    return False
            else:
                self.log_result(
                    "取消运行任务", False, f"创建任务失败: {response.status_code}"
                )
                return False

        except Exception as e:
            self.log_result("取消运行任务", False, f"异常: {str(e)}")
            return False

    async def test_resource_exhaustion(self):
        """测试资源耗尽"""
        try:
            logger.info("🧪 场景6: 资源耗尽")

            # 获取可用节点
            response = await self.client.get(f"{self.cloud_url}/api/v1/nodes")
            if response.status_code != 200:
                self.log_result("资源耗尽", False, "无法获取节点列表")
                return False

            nodes = response.json().get("nodes", [])
            if not nodes:
                self.log_result("资源耗尽", False, "没有可用节点")
                return False

            # 获取设备
            response = await self.client.get(f"{self.cloud_url}/api/v1/devices")
            if response.status_code != 200:
                self.log_result("资源耗尽", False, "无法获取设备列表")
                return False

            devices = response.json().get("devices", [])
            if not devices:
                self.log_result("资源耗尽", False, "没有可用设备")
                return False

            device_id = devices[0].get("device_id")

            # 创建多个任务直到资源耗尽
            logger.info("创建大量任务以测试资源限制...")
            task_count = 10  # 创建10个任务
            created_jobs = []

            for i in range(task_count):
                task_config = {
                    "name": f"资源测试任务 {i+1}",
                    "type": "basic_exec",
                    "task_type": "exec",
                    "target_device_id": device_id,
                    "command": f"echo 'Task {i+1}' && sleep 10",
                    "priority": "normal",
                    "timeout": 15,
                    "created_by": "resource_test",
                }

                response = await self.client.post(
                    f"{self.cloud_url}/api/v1/jobs", json=task_config
                )

                if response.status_code in [200, 201]:
                    job_data = response.json()
                    created_jobs.append(job_data.get("job_id"))
                else:
                    logger.info(f"创建任务 {i+1} 失败: {response.status_code}")
                    break

            logger.info(f"成功创建了 {len(created_jobs)} 个任务")

            # 等待并检查系统是否仍能响应
            await asyncio.sleep(5)

            # 检查API是否仍可访问
            health_response = await self.client.get(f"{self.cloud_url}/health")
            system_healthy = health_response.status_code == 200

            # 清理创建的任务
            for job_id in created_jobs:
                await self.client.patch(
                    f"{self.cloud_url}/api/v1/jobs/{job_id}/cancel",
                    json={"reason": "资源测试清理"},
                )

            if system_healthy:
                self.log_result(
                    "资源耗尽",
                    True,
                    f"系统在高负载下保持健康，创建了{len(created_jobs)}个任务",
                )
                return True
            else:
                self.log_result("资源耗尽", False, "系统在高负载下变得不健康")
                return False

        except Exception as e:
            self.log_result("资源耗尽", False, f"异常: {str(e)}")
            return False

    async def run_all_scenarios(self):
        """运行所有失败场景测试"""
        try:
            logger.info("🚀 开始运行所有失败场景测试")

            scenarios = [
                ("无效设备ID", self.test_invalid_device),
                ("无效命令", self.test_invalid_command),
                ("命令超时", self.test_timeout_command),
                ("格式错误请求", self.test_malformed_request),
                ("取消运行任务", self.test_cancel_running_task),
                ("资源耗尽", self.test_resource_exhaustion),
            ]

            results = []
            for scenario_name, scenario_func in scenarios:
                try:
                    result = await scenario_func()
                    results.append((scenario_name, result))

                    # 在测试之间添加延迟
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.error(f"❌ 场景 {scenario_name} 执行失败: {e}")
                    results.append((scenario_name, False))

            # 输出测试结果总结
            logger.info("=" * 50)
            logger.info("📊 失败场景测试结果总结:")
            logger.info("=" * 50)

            passed = sum(1 for _, result in results if result)
            total = len(results)

            for scenario_name, result in results:
                status = "✅ PASS" if result else "❌ FAIL"
                logger.info(f"{status}: {scenario_name}")

            logger.info("=" * 50)
            logger.info(f"总计: {passed}/{total} 场景通过")

            if passed == total:
                logger.info("🎉 所有失败场景测试通过!")
                return True
            else:
                logger.warning(f"⚠️  {total - passed} 个场景失败")
                return False

        except Exception as e:
            logger.error(f"❌ 运行失败场景测试失败: {e}")
            return False

    async def generate_report(self):
        """生成测试报告"""
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(self.test_results),
                "passed_tests": sum(1 for r in self.test_results if r["success"]),
                "failed_tests": sum(1 for r in self.test_results if not r["success"]),
                "results": self.test_results,
            }

            logger.info("📋 测试报告:")
            logger.info(f"  总测试数: {report['total_tests']}")
            logger.info(f"  通过: {report['passed_tests']}")
            logger.info(f"  失败: {report['failed_tests']}")
            logger.info(
                f"  成功率: {report['passed_tests']/report['total_tests']*100:.1f}%"
            )

            return report

        except Exception as e:
            logger.error(f"❌ 生成报告失败: {e}")
            return None


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="失败场景模拟脚本")
    parser.add_argument(
        "--cloud-url", default="http://localhost:8080", help="云端API URL"
    )
    parser.add_argument(
        "--scenario",
        choices=[
            "invalid_device",
            "invalid_command",
            "timeout",
            "malformed_request",
            "cancel_task",
            "resource_exhaustion",
        ],
        help="运行特定场景",
    )

    args = parser.parse_args()

    async with FailureScenarios(cloud_url=args.cloud_url) as tester:
        try:
            if args.scenario:
                # 运行特定场景
                scenario_methods = {
                    "invalid_device": tester.test_invalid_device,
                    "invalid_command": tester.test_invalid_command,
                    "timeout": tester.test_timeout_command,
                    "malformed_request": tester.test_malformed_request,
                    "cancel_task": tester.test_cancel_running_task,
                    "resource_exhaustion": tester.test_resource_exhaustion,
                }

                method = scenario_methods.get(args.scenario)
                if method:
                    success = await method()
                    return 0 if success else 1
                else:
                    logger.error(f"未知场景: {args.scenario}")
                    return 1
            else:
                # 运行所有场景
                success = await tester.run_all_scenarios()

                # 生成报告
                await tester.generate_report()

                return 0 if success else 1

        except Exception as e:
            logger.error(f"❌ 脚本执行失败: {e}")
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
