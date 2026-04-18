"""
任务分发模拟脚本

模拟完整的任务分发流程：创建任务 -> 分配节点 -> 执行 -> 返回结果
"""

import asyncio
import sys
import time
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


class TaskDispatcher:
    """任务分发器"""

    def __init__(self, cloud_url="http://localhost:8080"):
        self.cloud_url = cloud_url
        self.client = None
        self.created_jobs = []

    async def __aenter__(self):
        """进入上下文"""
        self.client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if self.client:
            await self.client.aclose()

    async def check_cloud_health(self):
        """检查云端健康状态"""
        try:
            response = await self.client.get(f"{self.cloud_url}/health")
            if response.status_code == 200:
                logger.info("✅ 云端API健康")
                return True
            else:
                logger.error(f"❌ 云端API不健康: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ 无法连接到云端: {e}")
            return False

    async def get_nodes(self):
        """获取节点列表"""
        try:
            response = await self.client.get(f"{self.cloud_url}/api/v1/nodes")
            if response.status_code == 200:
                data = response.json()
                nodes = data.get("nodes", [])
                logger.info(f"📡 获取到 {len(nodes)} 个节点")
                return nodes
            else:
                logger.error(f"❌ 获取节点失败: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"❌ 获取节点异常: {e}")
            return []

    async def get_devices(self):
        """获取设备列表"""
        try:
            response = await self.client.get(f"{self.cloud_url}/api/v1/devices")
            if response.status_code == 200:
                data = response.json()
                devices = data.get("devices", [])
                logger.info(f"🔧 获取到 {len(devices)} 个设备")
                return devices
            else:
                logger.error(f"❌ 获取设备失败: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"❌ 获取设备异常: {e}")
            return []

    async def create_test_device(self, device_id=None):
        """创建测试设备"""
        try:
            device_data = {
                "device_id": device_id
                or f"test-device-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "name": f"测试设备 {device_id or ''}",
                "type": "linux",
                "host": "localhost",
                "port": 2222,
                "username": "testuser",
                "enabled": True,
            }

            response = await self.client.post(
                f"{self.cloud_url}/api/v1/devices", json=device_data
            )

            if response.status_code in [200, 201]:
                logger.info(f"✅ 创建测试设备: {device_data['device_id']}")
                return device_data
            else:
                logger.warning(f"⚠️  创建设备失败: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ 创建设备异常: {e}")
            return None

    async def create_job(self, task_config):
        """创建任务"""
        try:
            response = await self.client.post(
                f"{self.cloud_url}/api/v1/jobs", json=task_config
            )

            if response.status_code in [200, 201]:
                job_data = response.json()
                job_id = job_data.get("job_id")
                logger.info(f"✅ 创建任务: {job_id}")
                self.created_jobs.append(job_id)
                return job_data
            else:
                error_detail = response.text
                logger.error(
                    f"❌ 创建任务失败: {response.status_code} - {error_detail}"
                )
                return None

        except Exception as e:
            logger.error(f"❌ 创建任务异常: {e}")
            return None

    async def get_job_status(self, job_id):
        """获取任务状态"""
        try:
            response = await self.client.get(f"{self.cloud_url}/api/v1/jobs/{job_id}")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ 获取任务状态失败: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ 获取任务状态异常: {e}")
            return None

    async def cancel_job(self, job_id, reason="测试取消"):
        """取消任务"""
        try:
            response = await self.client.patch(
                f"{self.cloud_url}/api/v1/jobs/{job_id}/cancel", json={"reason": reason}
            )

            if response.status_code == 200:
                logger.info(f"✅ 取消任务: {job_id}")
                return True
            else:
                logger.error(f"❌ 取消任务失败: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ 取消任务异常: {e}")
            return False

    async def wait_for_job_completion(self, job_id, timeout=120, check_interval=5):
        """等待任务完成"""
        try:
            start_time = time.time()
            logger.info(f"⏳ 等待任务完成: {job_id}")

            while time.time() - start_time < timeout:
                job_status = await self.get_job_status(job_id)

                if not job_status:
                    return False, "无法获取任务状态"

                status = job_status.get("status")
                logger.info(f"📊 任务状态: {status}")

                if status in ["success", "failed", "cancelled"]:
                    logger.info(f"✅ 任务完成: {status}")
                    return True, status

                await asyncio.sleep(check_interval)

            logger.warning(f"⏰ 等待超时: {job_id}")
            return False, "timeout"

        except Exception as e:
            logger.error(f"❌ 等待任务完成异常: {e}")
            return False, str(e)

    async def dispatch_single_task(self, task_config, wait_for_completion=True):
        """分发单个任务"""
        try:
            # 创建任务
            job_data = await self.create_job(task_config)

            if not job_data:
                return False, "创建任务失败"

            job_id = job_data.get("job_id")

            # 等待任务完成
            if wait_for_completion:
                success, result = await self.wait_for_job_completion(job_id)
                return success, result
            else:
                return True, job_id

        except Exception as e:
            logger.error(f"❌ 分发任务失败: {e}")
            return False, str(e)

    async def dispatch_batch_tasks(self, task_configs, delay=2):
        """批量分发任务"""
        try:
            logger.info(f"📤 批量分发 {len(task_configs)} 个任务")

            results = []
            for i, config in enumerate(task_configs):
                logger.info(f"分发任务 {i+1}/{len(task_configs)}")
                success, result = await self.dispatch_single_task(
                    config, wait_for_completion=False
                )
                results.append({"config": config, "success": success, "result": result})

                # 延迟以避免过载
                if i < len(task_configs) - 1:
                    await asyncio.sleep(delay)

            success_count = sum(1 for r in results if r["success"])
            logger.info(f"✅ 批量分发完成: {success_count}/{len(task_configs)} 成功")

            return results

        except Exception as e:
            logger.error(f"❌ 批量分发失败: {e}")
            return []

    async def run_test_scenarios(self, device_id=None):
        """运行测试场景"""
        try:
            logger.info("🧪 开始运行测试场景")

            # 1. 检查云端健康
            if not await self.check_cloud_health():
                return False

            # 2. 获取或创建测试设备
            devices = await self.get_devices()
            target_device = None

            if device_id:
                target_device = next(
                    (d for d in devices if d.get("device_id") == device_id), None
                )
            elif devices:
                target_device = devices[0]

            if not target_device:
                logger.info("创建测试设备...")
                target_device = await self.create_test_device()
                if not target_device:
                    return False

            device_id = target_device.get("device_id")
            logger.info(f"使用设备: {device_id}")

            # 3. 定义测试任务
            test_tasks = [
                {
                    "name": "系统信息查询",
                    "type": "basic_exec",
                    "task_type": "exec",
                    "target_device_id": device_id,
                    "command": "uname -a",
                    "priority": "normal",
                    "timeout": 10,
                    "created_by": "test_scenario",
                },
                {
                    "name": "运行时间查询",
                    "type": "basic_exec",
                    "task_type": "exec",
                    "target_device_id": device_id,
                    "command": "uptime",
                    "priority": "normal",
                    "timeout": 10,
                    "created_by": "test_scenario",
                },
                {
                    "name": "磁盘空间查询",
                    "type": "basic_exec",
                    "task_type": "exec",
                    "target_device_id": device_id,
                    "command": "df -h",
                    "priority": "normal",
                    "timeout": 15,
                    "created_by": "test_scenario",
                },
                {
                    "name": "内存使用查询",
                    "type": "basic_exec",
                    "task_type": "exec",
                    "target_device_id": device_id,
                    "command": "free -h",
                    "priority": "normal",
                    "timeout": 10,
                    "created_by": "test_scenario",
                },
                {
                    "name": "进程列表",
                    "type": "basic_exec",
                    "task_type": "exec",
                    "target_device_id": device_id,
                    "command": "ps aux",
                    "priority": "low",
                    "timeout": 15,
                    "created_by": "test_scenario",
                },
            ]

            # 4. 执行测试任务
            logger.info("开始执行测试任务...")
            results = await self.dispatch_batch_tasks(test_tasks)

            # 5. 等待所有任务完成
            logger.info("等待任务完成...")
            await asyncio.sleep(30)

            # 6. 检查结果
            success_count = sum(1 for r in results if r["success"])
            logger.info(f"✅ 测试场景完成: {success_count}/{len(test_tasks)} 任务成功")

            return success_count > 0

        except Exception as e:
            logger.error(f"❌ 测试场景失败: {e}")
            return False

    async def cleanup(self):
        """清理创建的任务"""
        try:
            if not self.created_jobs:
                return

            logger.info(f"🧹 清理 {len(self.created_jobs)} 个任务...")

            for job_id in self.created_jobs:
                await self.cancel_job(job_id, reason="测试清理")

            self.created_jobs.clear()
            logger.info("✅ 清理完成")

        except Exception as e:
            logger.error(f"❌ 清理失败: {e}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="任务分发模拟脚本")
    parser.add_argument(
        "--cloud-url", default="http://localhost:8080", help="云端API URL"
    )
    parser.add_argument("--device-id", help="目标设备ID")
    parser.add_argument("--command", help="要执行的命令")
    parser.add_argument("--batch", type=int, help="批量任务数量")
    parser.add_argument("--scenario", action="store_true", help="运行测试场景")
    parser.add_argument("--no-cleanup", action="store_true", help="不清理创建的任务")

    args = parser.parse_args()

    async with TaskDispatcher(cloud_url=args.cloud_url) as dispatcher:
        try:
            if args.scenario:
                # 运行测试场景
                success = await dispatcher.run_test_scenarios(args.device_id)
                return 0 if success else 1

            elif args.batch:
                # 批量创建简单任务
                if not args.device_id:
                    logger.error("批量模式需要指定设备ID")
                    return 1

                batch_tasks = []
                for i in range(args.batch):
                    task_config = {
                        "name": f"批量任务 {i+1}",
                        "type": "basic_exec",
                        "task_type": "exec",
                        "target_device_id": args.device_id,
                        "command": f"echo 'Batch task {i+1}'",
                        "priority": "normal",
                        "timeout": 10,
                        "created_by": "batch_test",
                    }
                    batch_tasks.append(task_config)

                results = await dispatcher.dispatch_batch_tasks(batch_tasks)
                success_count = sum(1 for r in results if r["success"])

                logger.info(f"批量任务结果: {success_count}/{args.batch} 成功")
                return 0 if success_count > 0 else 1

            elif args.command:
                # 执行单个命令
                if not args.device_id:
                    logger.error("命令模式需要指定设备ID")
                    return 1

                task_config = {
                    "name": "命令执行",
                    "type": "basic_exec",
                    "task_type": "exec",
                    "target_device_id": args.device_id,
                    "command": args.command,
                    "priority": "normal",
                    "timeout": 30,
                    "created_by": "command_line",
                }

                success, result = await dispatcher.dispatch_single_task(task_config)
                return 0 if success else 1

            else:
                # 默认运行测试场景
                success = await dispatcher.run_test_scenarios(args.device_id)
                return 0 if success else 1

        except Exception as e:
            logger.error(f"❌ 脚本执行失败: {e}")
            return 1
        finally:
            if not args.no_cleanup:
                await dispatcher.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
