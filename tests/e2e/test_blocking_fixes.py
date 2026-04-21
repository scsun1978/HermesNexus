"""
测试阻塞问题修复的 E2E 测试
验证之前修复的6个阻塞问题
"""

import asyncio
import sys
from pathlib import Path
import httpx
import logging

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BlockingFixesE2ETest:
    """阻塞问题修复验证测试"""

    def __init__(self, cloud_url="http://localhost:8080"):
        self.cloud_url = cloud_url
        self.test_results = []
        self.created_assets = []
        self.created_tasks = []

    async def test_1_service_accessor_functions(self):
        """测试1: 验证服务访问器函数修复"""
        logger.info("🧪 测试1: 验证服务访问器函数修复")

        try:
            # 测试导入服务访问器函数
            from shared.services.task_service import get_task_service
            from shared.services.asset_service import get_asset_service
            from shared.services.audit_service import get_audit_service

            # 测试服务实例化
            task_service = get_task_service()
            asset_service = get_asset_service()
            audit_service = get_audit_service()

            logger.info("✅ 服务访问器函数正常工作")
            logger.info(f"   - TaskService: {type(task_service).__name__}")
            logger.info(f"   - AssetService: {type(asset_service).__name__}")
            logger.info(f"   - AuditService: {type(audit_service).__name__}")

            return True

        except Exception as e:
            logger.error(f"❌ 服务访问器函数测试失败: {e}")
            return False

    async def test_2_task_api_imports(self):
        """测试2: 验证 Task API 导入修复"""
        logger.info("🧪 测试2: 验证 Task API 导入修复")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 测试任务列表 API
                response = await client.get(f"{self.cloud_url}/api/v1/tasks")

                if response.status_code == 200:
                    data = response.json()
                    logger.info("✅ Task API 导入修复成功")
                    logger.info(f"   - 响应格式正确: {list(data.keys())}")
                    logger.info(f"   - 任务数量: {data.get('total', 0)}")
                    return True
                else:
                    logger.error(f"❌ Task API 响应异常: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"❌ Task API 导入测试失败: {e}")
            return False

    async def test_3_asset_api_imports(self):
        """测试3: 验证 Asset API 导入修复"""
        logger.info("🧪 测试3: 验证 Asset API 导入修复")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 测试资产列表 API
                response = await client.get(f"{self.cloud_url}/api/v1/assets")

                if response.status_code == 200:
                    data = response.json()
                    logger.info("✅ Asset API 导入修复成功")
                    logger.info(f"   - 响应格式正确: {list(data.keys())}")
                    logger.info(f"   - 资产数量: {data.get('total', 0)}")
                    return True
                else:
                    logger.error(f"❌ Asset API 响应异常: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"❌ Asset API 导入测试失败: {e}")
            return False

    async def test_4_task_service_created_by_param(self):
        """测试4: 验证 TaskService.create_task 接受 created_by 参数"""
        logger.info("🧪 测试4: 验证 TaskService.create_task 接受 created_by 参数")

        try:
            from shared.services.task_service import get_task_service
            from shared.models.task import TaskCreateRequest, TaskType, TaskPriority

            task_service = get_task_service()

            # 创建测试任务请求
            request = TaskCreateRequest(
                name="E2E测试任务",
                task_type=TaskType.BASIC_EXEC,
                priority=TaskPriority.NORMAL,
                target_asset_id="test-asset-001",
                command="echo 'Hello World'",
            )

            # 测试带有 created_by 参数的任务创建
            task = task_service.create_task(request, created_by="e2e-test-user")

            if task and task.created_by == "e2e-test-user":
                logger.info("✅ TaskService.create_task 接受 created_by 参数")
                logger.info(f"   - 任务ID: {task.task_id}")
                logger.info(f"   - 创建者: {task.created_by}")
                self.created_tasks.append(task.task_id)
                return True
            else:
                logger.error(f"❌ created_by 参数未正确设置: {task.created_by if task else 'No task'}")
                return False

        except Exception as e:
            logger.error(f"❌ TaskService.created_by 参数测试失败: {e}")
            return False

    async def test_5_asset_service_created_by_field(self):
        """测试5: 验证 Asset 模型有 created_by 字段"""
        logger.info("🧪 测试5: 验证 Asset 模型有 created_by 字段")

        try:
            from shared.services.asset_service import get_asset_service
            from shared.models.asset import AssetCreateRequest, AssetType

            asset_service = get_asset_service()

            # 创建测试资产请求
            request = AssetCreateRequest(
                name="E2E测试资产",
                asset_type=AssetType.LINUX_HOST,
                description="用于E2E测试的资产",
            )

            # 测试带有 created_by 参数的资产创建
            asset = asset_service.create_asset(request, created_by="e2e-test-user")

            if asset and hasattr(asset, "created_by"):
                logger.info("✅ Asset 模型有 created_by 字段")
                logger.info(f"   - 资产ID: {asset.asset_id}")
                logger.info(f"   - 创建者: {asset.created_by}")
                self.created_assets.append(asset.asset_id)
                return True
            else:
                logger.error("❌ Asset 模型缺少 created_by 字段")
                return False

        except Exception as e:
            logger.error(f"❌ Asset.created_by 字段测试失败: {e}")
            return False

    async def test_6_task_service_get_pending_tasks(self):
        """测试6: 验证 TaskService.get_pending_tasks_for_node 方法"""
        logger.info("🧪 测试6: 验证 TaskService.get_pending_tasks_for_node 方法")

        try:
            from shared.services.task_service import get_task_service

            task_service = get_task_service()

            # 测试 get_pending_tasks_for_node 方法
            pending_tasks = task_service.get_pending_tasks_for_node("test-node-001", limit=10)

            if pending_tasks is not None:
                logger.info("✅ TaskService.get_pending_tasks_for_node 方法存在")
                logger.info(f"   - 返回类型: {type(pending_tasks).__name__}")
                logger.info(f"   - 返回数量: {len(pending_tasks)}")
                return True
            else:
                logger.error("❌ get_pending_tasks_for_node 方法返回 None")
                return False

        except Exception as e:
            logger.error(f"❌ get_pending_tasks_for_node 方法测试失败: {e}")
            return False

    async def test_7_task_api_pending_endpoint(self):
        """测试7: 验证 Task API 获取节点待处理任务端点"""
        logger.info("🧪 测试7: 验证 Task API 获取节点待处理任务端点")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 测试获取节点待处理任务端点
                response = await client.get(
                    f"{self.cloud_url}/api/v1/tasks/nodes/test-node-001/pending?limit=10"
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info("✅ Task API 获取节点待处理任务端点正常")
                    logger.info(f"   - 响应格式: {type(data).__name__}")
                    return True
                else:
                    logger.error(f"❌ 端点响应异常: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"❌ 获取节点待处理任务端点测试失败: {e}")
            return False

    async def test_8_asset_service_methods(self):
        """测试8: 验证 AssetService 缺失的方法"""
        logger.info("🧪 测试8: 验证 AssetService 缺失的方法")

        try:
            from shared.services.asset_service import get_asset_service

            asset_service = get_asset_service()

            # 测试 update_asset_heartbeat 方法
            methods_to_test = [
                "update_asset_heartbeat",
                "associate_node",
                "disassociate_node",
            ]
            missing_methods = []

            for method_name in methods_to_test:
                if hasattr(asset_service, method_name):
                    logger.info(f"   ✅ {method_name} 方法存在")
                else:
                    logger.error(f"   ❌ {method_name} 方法缺失")
                    missing_methods.append(method_name)

            if not missing_methods:
                logger.info("✅ AssetService 所有必需方法都存在")
                return True
            else:
                logger.error(f"❌ AssetService 缺少方法: {missing_methods}")
                return False

        except Exception as e:
            logger.error(f"❌ AssetService 方法测试失败: {e}")
            return False

    async def test_9_create_task_via_api(self):
        """测试9: 验证通过 API 创建任务（集成测试）"""
        logger.info("🧪 测试9: 验证通过 API 创建任务（集成测试）")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 创建测试任务
                task_data = {
                    "name": "E2E API测试任务",
                    "task_type": "basic_exec",
                    "priority": "normal",
                    "target_asset_id": "test-asset-api-001",
                    "command": "hostname",
                }

                response = await client.post(f"{self.cloud_url}/api/v1/tasks", json=task_data)

                if response.status_code in [200, 201]:
                    task = response.json()
                    logger.info("✅ 通过 API 创建任务成功")
                    logger.info(f"   - 任务ID: {task.get('task_id')}")
                    logger.info(f"   - 任务名称: {task.get('name')}")
                    logger.info(f"   - 创建者: {task.get('created_by', 'N/A')}")
                    return True
                else:
                    logger.error(f"❌ API 创建任务失败: {response.status_code}")
                    logger.error(f"   - 响应内容: {response.text[:200]}")
                    return False

        except Exception as e:
            logger.error(f"❌ API 创建任务测试失败: {e}")
            return False

    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始阻塞问题修复验证测试")
        logger.info("=" * 60)

        tests = [
            ("服务访问器函数修复", self.test_1_service_accessor_functions),
            ("Task API 导入修复", self.test_2_task_api_imports),
            ("Asset API 导入修复", self.test_3_asset_api_imports),
            ("TaskService.created_by 参数", self.test_4_task_service_created_by_param),
            ("Asset.created_by 字段", self.test_5_asset_service_created_by_field),
            (
                "TaskService.get_pending_tasks_for_node",
                self.test_6_task_service_get_pending_tasks,
            ),
            ("Task API 节点待处理任务端点", self.test_7_task_api_pending_endpoint),
            ("AssetService 缺失方法", self.test_8_asset_service_methods),
            ("API 创建任务集成测试", self.test_9_create_task_via_api),
        ]

        passed = 0
        failed = 0

        for i, (test_name, test_func) in enumerate(tests, 1):
            try:
                result = await test_func()
                if result:
                    passed += 1
                    self.test_results.append(("✅", test_name))
                else:
                    failed += 1
                    self.test_results.append(("❌", test_name))
            except Exception as e:
                failed += 1
                logger.error(f"测试执行异常: {e}")
                self.test_results.append(("❌", test_name))

        # 生成测试报告
        logger.info("\n" + "=" * 60)
        logger.info("📊 阻塞问题修复验证报告")
        logger.info("=" * 60)

        for status, test_name in self.test_results:
            logger.info(f"{status} {test_name}")

        logger.info("=" * 60)
        logger.info(f"总计: {len(self.test_results)} 个测试")
        logger.info(f"通过: {passed} | 失败: {failed}")

        if passed + failed > 0:
            pass_rate = (passed / (passed + failed)) * 100
            logger.info(f"通过率: {pass_rate:.1f}%")

            # 评估阻塞问题修复状态
            if pass_rate >= 90:
                logger.info("🎉 阻塞问题修复状态: ✅ 基本解决，可以进行E2E测试")
                return 0
            elif pass_rate >= 70:
                logger.info("⚠️  阻塞问题修复状态: 🟡 部分解决，需要进一步修复")
                return 1
            else:
                logger.warning("❌ 阻塞问题修复状态: ❌ 仍有主要问题")
                return 2
        else:
            logger.warning("⚠️  没有测试被执行")
            return 2


async def main():
    """主函数"""
    test = BlockingFixesE2ETest()

    try:
        exit_code = await test.run_all_tests()
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
