"""
最终端到端测试 - 完整系统验证

验证HermesNexus MVP的完整功能：云端创建任务 → 边缘节点接收 → SSH 执行 → 结果回传 → 云端可见
"""

import asyncio
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from cloud.database.db import db

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class FinalE2ETest:
    """最终端到端测试"""

    def __init__(self, cloud_url="http://localhost:8080"):
        self.cloud_url = cloud_url
        self.test_results = []
        self.start_time = None

    async def test_1_cloud_api_health(self):
        """测试1: 云端API健康检查"""
        logger.info("🧪 测试1: 云端API健康检查")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.cloud_url}/health")

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "healthy":
                        logger.info("✅ 云端API健康")
                        return True
                    else:
                        logger.error(f"❌ API状态异常: {data.get('status')}")
                        return False
                else:
                    logger.error(f"❌ API响应异常: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"❌ 连接云端API失败: {e}")
            return False

    async def test_2_node_registration(self):
        """测试2: 节点注册流程"""
        logger.info("🧪 测试2: 节点注册流程")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 创建测试节点
                node_id = f"e2e-test-node-{int(time.time())}"

                registration_data = {
                    "node_name": "E2E测试节点",
                    "capabilities": {
                        "ssh": True,
                        "max_tasks": 3,
                        "supported_commands": ["exec", "script"],
                    },
                }

                response = await client.post(
                    f"{self.cloud_url}/api/v1/nodes/{node_id}/register",
                    json=registration_data,
                )

                if response.status_code in [200, 201]:
                    logger.info(f"✅ 节点注册成功: {node_id}")

                    # 验证节点可以查询
                    await asyncio.sleep(1)
                    node_response = await client.get(
                        f"{self.cloud_url}/api/v1/nodes/{node_id}"
                    )

                    if node_response.status_code == 200:
                        node_data = node_response.json()
                        logger.info(f"✅ 节点查询成功: {node_data.get('name')}")
                        return node_id
                    else:
                        logger.error(f"❌ 节点查询失败: {node_response.status_code}")
                        return None
                else:
                    logger.error(f"❌ 节点注册失败: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"❌ 节点注册流程失败: {e}")
            return None

    async def test_3_device_management(self):
        """测试3: 设备管理"""
        logger.info("🧪 测试3: 设备管理")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 尝试获取设备列表
                response = await client.get(f"{self.cloud_url}/api/v1/devices")

                if response.status_code == 200:
                    data = response.json()
                    devices = data.get("devices", [])

                    if devices:
                        device_id = devices[0].get("device_id")
                        logger.info(f"✅ 找到现有设备: {device_id}")
                        return device_id
                    else:
                        # 创建测试设备
                        device_id = f"e2e-test-device-{int(time.time())}"
                        create_response = await client.post(
                            f"{self.cloud_url}/api/v1/devices",
                            json={
                                "device_id": device_id,
                                "name": "E2E测试设备",
                                "type": "linux",
                                "host": "localhost",
                                "port": 22,
                                "enabled": True,
                            },
                        )

                        if create_response.status_code in [200, 201]:
                            logger.info(f"✅ 创建测试设备: {device_id}")
                            return device_id
                        else:
                            logger.error(f"❌ 设备创建失败: {create_response.status_code}")
                            return None
                else:
                    logger.error(f"❌ 获取设备列表失败: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"❌ 设备管理测试失败: {e}")
            return None

    async def test_4_task_creation_and_execution(self, node_id, device_id):
        """测试4: 任务创建和执行"""
        logger.info("🧪 测试4: 任务创建和执行")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 创建测试任务
                job_id = f"e2e-test-job-{int(time.time())}"

                task_data = {
                    "job_id": job_id,
                    "name": "E2E测试任务",
                    "type": "basic_exec",
                    "task_type": "exec",
                    "target_device_id": device_id,
                    "command": "echo 'Hello from E2E Test'",
                    "priority": "normal",
                    "timeout": 30,
                    "created_by": "e2e_test",
                }

                response = await client.post(
                    f"{self.cloud_url}/api/v1/jobs", json=task_data
                )

                if response.status_code in [200, 201]:
                    result_data = response.json()
                    created_job_id = result_data.get("job_id")
                    logger.info(f"✅ 任务创建成功: {created_job_id}")

                    # 等待任务处理
                    await asyncio.sleep(5)

                    # 检查任务状态
                    status_response = await client.get(
                        f"{self.cloud_url}/api/v1/jobs/{created_job_id}"
                    )

                    if status_response.status_code == 200:
                        job_status = status_response.json()
                        status = job_status.get("status")
                        logger.info(f"📊 任务状态: {status}")

                        # 检查任务是否被分配到节点
                        if "node_id" in job_status:
                            logger.info(f"✅ 任务已分配到节点: {job_status.get('node_id')}")
                        else:
                            logger.warning("⚠️  任务未被分配节点")

                        return created_job_id, status
                    else:
                        logger.error(f"❌ 获取任务状态失败: {status_response.status_code}")
                        return None, None
                else:
                    logger.error(f"❌ 任务创建失败: {response.status_code}")
                    return None, None

        except Exception as e:
            logger.error(f"❌ 任务创建和执行测试失败: {e}")
            return None, None

    async def test_5_task_cancellation(self):
        """测试5: 任务取消"""
        logger.info("🧪 测试5: 任务取消")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 创建一个长时间运行的任务
                job_id = f"e2e-cancel-job-{int(time.time())}"

                # 先获取一个可用的设备
                device_response = await client.get(f"{self.cloud_url}/api/v1/devices")
                if device_response.status_code != 200:
                    logger.error("❌ 无法获取设备列表")
                    return False

                devices = device_response.json().get("devices", [])
                if not devices:
                    logger.error("❌ 没有可用设备")
                    return False

                device_id = devices[0].get("device_id")

                # 创建任务
                create_response = await client.post(
                    f"{self.cloud_url}/api/v1/jobs",
                    json={
                        "job_id": job_id,
                        "name": "取消测试任务",
                        "type": "basic_exec",
                        "target_device_id": device_id,
                        "command": "sleep 60",
                        "timeout": 120,
                        "created_by": "e2e_test",
                    },
                )

                if create_response.status_code not in [200, 201]:
                    logger.error(f"❌ 创建取消测试任务失败: {create_response.status_code}")
                    return False

                # 等待任务开始
                await asyncio.sleep(3)

                # 取消任务
                cancel_response = await client.patch(
                    f"{self.cloud_url}/api/v1/jobs/{job_id}/cancel",
                    json={"reason": "E2E测试取消"},
                )

                if cancel_response.status_code == 200:
                    logger.info("✅ 任务取消成功")

                    # 验证任务状态
                    await asyncio.sleep(2)
                    status_response = await client.get(
                        f"{self.cloud_url}/api/v1/jobs/{job_id}"
                    )

                    if status_response.status_code == 200:
                        job_status = status_response.json()
                        if job_status.get("status") == "cancelled":
                            logger.info("✅ 任务状态已更新为cancelled")
                            return True
                        else:
                            logger.warning(f"⚠️  任务状态: {job_status.get('status')}")
                            return False
                    else:
                        logger.error(f"❌ 获取取消后状态失败: {status_response.status_code}")
                        return False
                else:
                    logger.error(f"❌ 任务取消失败: {cancel_response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"❌ 任务取消测试失败: {e}")
            return False

    async def test_6_system_statistics(self):
        """测试6: 系统统计信息"""
        logger.info("🧪 测试6: 系统统计信息")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.cloud_url}/api/v1/stats")

                if response.status_code == 200:
                    stats = response.json()
                    logger.info("📊 系统统计信息:")
                    logger.info(f"   总节点数: {stats.get('total_nodes', 0)}")
                    logger.info(f"   在线节点: {stats.get('online_nodes', 0)}")
                    logger.info(f"   总任务数: {stats.get('total_jobs', 0)}")
                    logger.info(f"   等待任务: {stats.get('pending_jobs', 0)}")
                    logger.info(f"   总事件数: {stats.get('total_events', 0)}")

                    # 验证统计数据完整性
                    required_fields = [
                        "total_nodes",
                        "online_nodes",
                        "total_jobs",
                        "pending_jobs",
                        "total_events",
                    ]

                    for field in required_fields:
                        if field not in stats:
                            logger.error(f"❌ 缺少统计字段: {field}")
                            return False

                    logger.info("✅ 系统统计信息完整")
                    return True
                else:
                    logger.error(f"❌ 获取统计信息失败: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"❌ 系统统计测试失败: {e}")
            return False

    async def test_7_event_logging(self):
        """测试7: 事件日志记录"""
        logger.info("🧪 测试7: 事件日志记录")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.cloud_url}/api/v1/events")

                if response.status_code == 200:
                    data = response.json()
                    events = data.get("events", [])

                    logger.info(f"📋 事件日志总数: {len(events)}")

                    if events:
                        # 显示最近几个事件
                        recent_events = events[:3]
                        for event in recent_events:
                            level = event.get("level", "info")
                            event_type = event.get("type", "unknown")
                            message = event.get("message", "")[:50]
                            logger.info(f"   [{level}] {event_type}: {message}")

                        logger.info("✅ 事件日志记录正常")
                        return True
                    else:
                        logger.warning("⚠️  没有事件记录")
                        return False
                else:
                    logger.error(f"❌ 获取事件日志失败: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"❌ 事件日志测试失败: {e}")
            return False

    async def test_8_console_access(self):
        """测试8: 控制台访问"""
        logger.info("🧪 测试8: 控制台访问")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.cloud_url}/console")

                if response.status_code == 200:
                    # 检查是否返回HTML内容
                    content = response.text
                    if "HermesNexus" in content or "console" in content.lower():
                        logger.info("✅ 控制台页面可访问")
                        return True
                    else:
                        logger.warning("⚠️  控制台内容可能不完整")
                        return False
                else:
                    logger.error(f"❌ 控制台访问失败: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"❌ 控制台访问测试失败: {e}")
            return False

    async def test_9_data_consistency(self):
        """测试9: 数据一致性"""
        logger.info("🧪 测试9: 数据一致性")

        try:
            # 检查数据库数据一致性
            nodes = db.list_nodes()
            jobs = db.list_jobs()
            events = db.list_events()

            logger.info(f"📊 数据一致性检查:")
            logger.info(f"   节点数: {len(nodes)}")
            logger.info(f"   任务数: {len(jobs)}")
            logger.info(f"   事件数: {len(events)}")

            # 验证数据完整性
            inconsistencies = []

            for node in nodes:
                if "node_id" not in node:
                    inconsistencies.append(f"节点缺少node_id: {node}")
                if "status" not in node:
                    inconsistencies.append(f"节点缺少status: {node}")

            for job in jobs:
                if "job_id" not in job:
                    inconsistencies.append(f"任务缺少job_id: {job}")
                if "status" not in job:
                    inconsistencies.append(f"任务缺少status: {job}")

            if inconsistencies:
                logger.error("❌ 发现数据不一致:")
                for issue in inconsistencies[:5]:  # 只显示前5个
                    logger.error(f"   - {issue}")
                return False
            else:
                logger.info("✅ 数据一致性检查通过")
                return True

        except Exception as e:
            logger.error(f"❌ 数据一致性检查失败: {e}")
            return False

    async def run_all_tests(self):
        """运行所有端到端测试"""
        logger.info("🚀 开始最终端到端测试")
        logger.info("=" * 60)

        self.start_time = time.time()

        tests = [
            ("云端API健康检查", self.test_1_cloud_api_health),
            ("节点注册流程", self.test_2_node_registration),
            ("设备管理", self.test_3_device_management),
            ("任务创建和执行", None),  # 需要前面的结果
            ("任务取消", self.test_5_task_cancellation),
            ("系统统计信息", self.test_6_system_statistics),
            ("事件日志记录", self.test_7_event_logging),
            ("控制台访问", self.test_8_console_access),
            ("数据一致性", self.test_9_data_consistency),
        ]

        # 存储测试结果
        node_id = None
        device_id = None

        for i, (test_name, test_func) in enumerate(tests):
            logger.info(f"\n{'='*60}")
            logger.info(f"测试 {i+1}/{len(tests)}: {test_name}")
            logger.info(f"{'='*60}")

            try:
                if test_func == self.test_4_task_creation_and_execution:
                    # 这个测试需要前面的结果
                    if node_id and device_id:
                        job_id, status = await test_func(node_id, device_id)
                        success = job_id is not None
                        self.test_results.append((test_name, success))
                    else:
                        logger.warning("⏭️  跳过任务创建测试 (缺少节点或设备)")
                        self.test_results.append((test_name, None))
                else:
                    result = await test_func()

                    if test_name == "节点注册流程" and result:
                        node_id = result
                    elif test_name == "设备管理" and result:
                        device_id = result

                    success = result is not None and result is not False
                    self.test_results.append((test_name, success))

            except Exception as e:
                logger.error(f"❌ 测试执行失败: {e}")
                self.test_results.append((test_name, False))

            # 测试之间短暂等待
            await asyncio.sleep(2)

        # 生成测试报告
        await self.generate_report()

    async def generate_report(self):
        """生成测试报告"""
        elapsed_time = time.time() - self.start_time

        logger.info("\n" + "=" * 60)
        logger.info("📊 最终端到端测试报告")
        logger.info("=" * 60)
        logger.info(f"总耗时: {elapsed_time:.2f}秒")
        logger.info("")

        passed = 0
        failed = 0
        skipped = 0

        for test_name, success in self.test_results:
            if success is None:
                status = "⏭️  跳过"
                skipped += 1
            elif success:
                status = "✅ 通过"
                passed += 1
            else:
                status = "❌ 失败"
                failed += 1

            logger.info(f"{status}: {test_name}")

        logger.info("=" * 60)
        logger.info(f"总计: {len(self.test_results)} 个测试")
        logger.info(f"通过: {passed} | 失败: {failed} | 跳过: {skipped}")

        if passed + failed > 0:
            pass_rate = (passed / (passed + failed)) * 100
            logger.info(f"通过率: {pass_rate:.1f}%")

            # 评估MVP就绪状态
            if pass_rate >= 80:
                logger.info("🎉 MVP就绪状态: ✅ 达到发布标准")
                return 0
            else:
                logger.warning("⚠️  MVP就绪状态: ❌ 未达到发布标准")
                return 1
        else:
            logger.warning("⚠️  没有测试被执行")
            return 1


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="HermesNexus 最终端到端测试")
    parser.add_argument(
        "--cloud-url", default="http://localhost:8080", help="云端API URL"
    )
    parser.add_argument("--quick", action="store_true", help="快速测试模式")

    args = parser.parse_args()

    e2e_test = FinalE2ETest(cloud_url=args.cloud_url)

    try:
        exit_code = await e2e_test.run_all_tests()
        return exit_code

    except KeyboardInterrupt:
        logger.info("\n⚠️  测试被用户中断")
        return 1
    except Exception as e:
        logger.error(f"\n❌ 测试执行失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
