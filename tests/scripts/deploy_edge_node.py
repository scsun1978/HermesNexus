"""
边缘节点集成脚本

自动化边缘节点的部署、注册和测试
"""

import asyncio
import sys
import os
import argparse
import logging
import signal
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from edge.runtime.core import EdgeRuntime
from edge.cloud.client import CloudClient
from edge.storage.storage import EdgeStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class EdgeNodeIntegrator:
    """边缘节点集成器"""

    def __init__(self, cloud_url="http://localhost:8080", node_id=None):
        self.cloud_url = cloud_url
        self.node_id = node_id or f"edge-node-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.runtime = None
        self.cloud_client = None
        self.running = False

        # 配置参数
        self.config = {
            "heartbeat_interval": 10,  # 心跳间隔（秒）
            "task_poll_interval": 5,   # 任务轮询间隔（秒）
            "max_concurrent_tasks": 3, # 最大并发任务数
            "ssh_timeout": 30,         # SSH超时（秒）
            "log_level": "INFO"
        }

    async def deploy(self):
        """部署边缘节点"""
        try:
            logger.info(f"🚀 开始部署边缘节点: {self.node_id}")

            # 1. 初始化存储
            logger.info("1️⃣ 初始化本地存储...")
            storage = EdgeStorage()

            # 2. 创建云端客户端
            logger.info("2️⃣ 创建云端连接...")
            self.cloud_client = CloudClient(
                cloud_url=self.cloud_url,
                node_id=self.node_id
            )

            # 3. 创建边缘运行时
            logger.info("3️⃣ 创建边缘运行时...")
            self.runtime = EdgeRuntime(
                node_id=self.node_id,
                cloud_client=self.cloud_client,
                storage=storage,
                config=self.config
            )

            # 4. 启动边缘节点
            logger.info("4️⃣ 启动边缘节点...")
            await self.runtime.start()

            self.running = True
            logger.info(f"✅ 边缘节点 {self.node_id} 部署成功")

            return True

        except Exception as e:
            logger.error(f"❌ 部署失败: {e}")
            return False

    async def register(self, capabilities=None):
        """注册节点到云端"""
        try:
            logger.info("📝 向云端注册节点...")

            if not self.cloud_client:
                raise Exception("云客户端未初始化")

            # 准备注册信息
            registration_data = {
                "node_name": self.node_id,
                "capabilities": capabilities or {
                    "ssh": True,
                    "max_tasks": self.config["max_concurrent_tasks"],
                    "supported_commands": ["exec", "script", "file_transfer"]
                }
            }

            # 注册节点
            success = await self.cloud_client.register_node(registration_data)

            if success:
                logger.info(f"✅ 节点 {self.node_id} 注册成功")
                return True
            else:
                logger.error(f"❌ 节点 {self.node_id} 注册失败")
                return False

        except Exception as e:
            logger.error(f"❌ 注册失败: {e}")
            return False

    async def verify(self):
        """验证节点状态"""
        try:
            logger.info("🔍 验证节点状态...")

            if not self.runtime:
                raise Exception("运行时未初始化")

            # 检查运行时状态
            is_running = self.runtime.is_running
            logger.info(f"运行时状态: {'运行中' if is_running else '未运行'}")

            # 检查连接状态
            is_connected = self.cloud_client.is_connected if self.cloud_client else False
            logger.info(f"云端连接: {'已连接' if is_connected else '未连接'}")

            # 检查统计信息
            stats = self.runtime.get_stats()
            logger.info(f"统计信息: {stats}")

            return is_running and is_connected

        except Exception as e:
            logger.error(f"❌ 验证失败: {e}")
            return False

    async def run_test_task(self, test_device=None, test_command="uptime"):
        """运行测试任务"""
        try:
            logger.info("🧪 运行测试任务...")

            if not self.runtime:
                raise Exception("运行时未初始化")

            # 创建测试任务
            test_task = {
                "task_id": f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "task_type": "exec",
                "target_device_id": test_device or "test-device",
                "target_host": "localhost",
                "command": test_command,
                "timeout": 10,
                "priority": "normal",
                "created_by": "integration_test"
            }

            # 执行任务
            logger.info(f"执行测试命令: {test_command}")
            result = await self.runtime.execute_task(test_task)

            if result.get("success"):
                logger.info(f"✅ 测试任务成功")
                logger.info(f"输出: {result.get('stdout', '')[:200]}")
                return True
            else:
                logger.error(f"❌ 测试任务失败: {result.get('error')}")
                return False

        except Exception as e:
            logger.error(f"❌ 测试任务执行失败: {e}")
            return False

    async def monitor(self, duration=60):
        """监控节点运行"""
        try:
            logger.info(f"📊 监控节点运行 ({duration}秒)...")

            start_time = asyncio.get_event_loop().time()
            end_time = start_time + duration

            while asyncio.get_event_loop().time() < end_time:
                if not self.running:
                    break

                # 获取状态
                if self.runtime:
                    stats = self.runtime.get_stats()
                    logger.info(f"状态: {stats}")

                # 等待一段时间
                await asyncio.sleep(10)

            logger.info("✅ 监控完成")

        except Exception as e:
            logger.error(f"❌ 监控失败: {e}")

    async def cleanup(self):
        """清理资源"""
        try:
            logger.info("🧹 清理资源...")

            self.running = False

            if self.runtime:
                await self.runtime.stop()

            logger.info("✅ 清理完成")

        except Exception as e:
            logger.error(f"❌ 清理失败: {e}")

    async def run_integration_test(self, test_device=None):
        """运行完整的集成测试"""
        try:
            logger.info("🚀 开始边缘节点集成测试")

            # 1. 部署节点
            if not await self.deploy():
                return False

            # 2. 注册节点
            if not await self.register():
                await self.cleanup()
                return False

            # 3. 验证状态
            if not await self.verify():
                await self.cleanup()
                return False

            # 4. 运行测试任务
            if test_device:
                if not await self.run_test_task(test_device):
                    await self.cleanup()
                    return False

            # 5. 监控一段时间
            await self.monitor(duration=30)

            logger.info("✅ 集成测试完成")
            return True

        except Exception as e:
            logger.error(f"❌ 集成测试失败: {e}")
            return False
        finally:
            await self.cleanup()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='边缘节点集成脚本')
    parser.add_argument('--cloud-url', default='http://localhost:8080', help='云端API URL')
    parser.add_argument('--node-id', help='节点ID')
    parser.add_argument('--test-device', help='测试设备ID')
    parser.add_argument('--test-command', default='uptime', help='测试命令')
    parser.add_argument('--deploy-only', action='store_true', help='仅部署节点')
    parser.add_argument('--register-only', action='store_true', help='仅注册节点')
    parser.add_argument('--test-only', action='store_true', help='仅运行测试')
    parser.add_argument('--monitor', type=int, default=60, help='监控时长（秒）')

    args = parser.parse_args()

    # 创建集成器
    integrator = EdgeNodeIntegrator(
        cloud_url=args.cloud_url,
        node_id=args.node_id
    )

    try:
        if args.deploy_only:
            # 仅部署
            success = await integrator.deploy()
            if success:
                logger.info("✅ 部署完成，按Ctrl+C停止")
                # 保持运行直到收到中断信号
                await integrator.monitor(duration=3600)  # 1小时

        elif args.register_only:
            # 部署并注册
            success = await integrator.deploy()
            if success:
                await integrator.register()
                await integrator.monitor(duration=args.monitor)

        elif args.test_only:
            # 运行完整测试
            success = await integrator.run_integration_test(args.test_device)

        else:
            # 运行完整集成测试
            success = await integrator.run_integration_test(args.test_device)

        return 0 if success else 1

    except KeyboardInterrupt:
        logger.info("收到中断信号，正在停止...")
        await integrator.cleanup()
        return 0
    except Exception as e:
        logger.error(f"❌ 集成脚本失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)