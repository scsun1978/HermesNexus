"""
模拟器和集成脚本测试

验证所有模拟器和脚本的基本功能
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def test_simulator_modules():
    """测试模拟器模块导入"""
    logger.info("🧪 测试模拟器模块导入")

    try:
        # 测试SSH模拟器
        logger.info("1️⃣ 测试SSH模拟器模块...")
        from tests.simulators.ssh_host_simulator import SSHHostSimulator

        logger.info("   ✅ SSH模拟器模块导入成功")

        # 测试简单SSH服务器
        logger.info("2️⃣ 测试简单SSH服务器模块...")
        from tests.simulators.simple_ssh_server import SSHTestServer

        logger.info("   ✅ 简单SSH服务器模块导入成功")

        # 测试集成脚本
        logger.info("3️⃣ 测试边缘节点集成脚本...")
        from tests.scripts.deploy_edge_node import EdgeNodeIntegrator

        logger.info("   ✅ 边缘节点集成脚本导入成功")

        # 测试任务分发器
        logger.info("4️⃣ 测试任务分发器...")
        from tests.scripts.task_dispatcher import TaskDispatcher

        logger.info("   ✅ 任务分发器导入成功")

        # 测试失败场景
        logger.info("5️⃣ 测试失败场景脚本...")
        from tests.scripts.failure_scenarios import FailureScenarios

        logger.info("   ✅ 失败场景脚本导入成功")

        logger.info("✅ 所有模拟器模块导入成功")
        return True

    except ImportError as e:
        logger.error(f"❌ 模块导入失败: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False


async def test_simulator_creation():
    """测试模拟器实例创建"""
    logger.info("🧪 测试模拟器实例创建")

    try:
        from tests.simulators.ssh_host_simulator import SSHHostSimulator
        from tests.simulators.simple_ssh_server import SSHTestServer

        # 测试SSH主机模拟器创建
        logger.info("1️⃣ 创建SSH主机模拟器...")
        ssh_simulator = SSHHostSimulator(host="127.0.0.1", port=2223)
        logger.info(f"   ✅ SSH主机模拟器创建成功: {ssh_simulator.hostname}")

        # 测试简单SSH服务器创建
        logger.info("2️⃣ 创建简单SSH服务器...")
        ssh_server = SSHTestServer(host="127.0.0.1", port=2224)
        logger.info(f"   ✅ 简单SSH服务器创建成功: {ssh_server.hostname}")

        logger.info("✅ 所有模拟器实例创建成功")
        return True

    except Exception as e:
        logger.error(f"❌ 模拟器创建失败: {e}")
        return False


async def test_script_instances():
    """测试脚本实例创建"""
    logger.info("🧪 测试脚本实例创建")

    try:
        from tests.scripts.deploy_edge_node import EdgeNodeIntegrator
        from tests.scripts.task_dispatcher import TaskDispatcher
        from tests.scripts.failure_scenarios import FailureScenarios

        # 测试边缘节点集成器
        logger.info("1️⃣ 创建边缘节点集成器...")
        integrator = EdgeNodeIntegrator(cloud_url="http://localhost:8080")
        logger.info(f"   ✅ 边缘节点集成器创建成功: {integrator.node_id}")

        # 测试任务分发器
        logger.info("2️⃣ 创建任务分发器...")
        dispatcher = TaskDispatcher(cloud_url="http://localhost:8080")
        logger.info("   ✅ 任务分发器创建成功")

        # 测试失败场景测试器
        logger.info("3️⃣ 创建失败场景测试器...")
        failure_tester = FailureScenarios(cloud_url="http://localhost:8080")
        logger.info("   ✅ 失败场景测试器创建成功")

        logger.info("✅ 所有脚本实例创建成功")
        return True

    except Exception as e:
        logger.error(f"❌ 脚本实例创建失败: {e}")
        return False


async def test_simulator_basic_functionality():
    """测试模拟器基本功能"""
    logger.info("🧪 测试模拟器基本功能")

    try:
        from tests.simulators.ssh_host_simulator import SSHHostSimulator

        # 创建模拟器
        simulator = SSHHostSimulator(host="127.0.0.1", port=2225)

        # 测试命令执行
        logger.info("1️⃣ 测试命令执行功能...")

        # 测试uptime命令
        uptime_result = simulator._cmd_uptime()
        logger.info(f"   uptime命令: {uptime_result}")

        # 测试hostname命令
        hostname_result = simulator._cmd_hostname()
        logger.info(f"   hostname命令: {hostname_result}")

        # 测试uname命令
        uname_result = simulator._cmd_uname(["-a"])
        logger.info(f"   uname -a命令: {uname_result[:50]}...")

        # 测试ls命令
        ls_result = simulator._cmd_ls([])
        logger.info(f"   ls命令: {ls_result}")

        # 测试echo命令
        echo_result = simulator._execute_command("echo 'Hello HermesNexus'")
        logger.info(f"   echo命令: {echo_result}")

        logger.info("✅ 模拟器基本功能测试成功")
        return True

    except Exception as e:
        logger.error(f"❌ 基本功能测试失败: {e}")
        return False


async def test_file_structure():
    """测试文件结构"""
    logger.info("🧪 测试文件结构")

    try:
        base_path = Path(__file__).parent.parent

        # 检查模拟器文件
        simulator_files = [
            "tests/simulators/ssh_host_simulator.py",
            "tests/simulators/simple_ssh_server.py",
        ]

        # 检查脚本文件
        script_files = [
            "tests/scripts/deploy_edge_node.py",
            "tests/scripts/task_dispatcher.py",
            "tests/scripts/failure_scenarios.py",
        ]

        all_files_exist = True

        logger.info("1️⃣ 检查模拟器文件...")
        for file_path in simulator_files:
            full_path = base_path / file_path
            if full_path.exists():
                logger.info(f"   ✅ {file_path}")
            else:
                logger.error(f"   ❌ {file_path} 不存在")
                all_files_exist = False

        logger.info("2️⃣ 检查脚本文件...")
        for file_path in script_files:
            full_path = base_path / file_path
            if full_path.exists():
                logger.info(f"   ✅ {file_path}")
            else:
                logger.error(f"   ❌ {file_path} 不存在")
                all_files_exist = False

        if all_files_exist:
            logger.info("✅ 所有必需文件都存在")
            return True
        else:
            logger.error("❌ 部分文件缺失")
            return False

    except Exception as e:
        logger.error(f"❌ 文件结构测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    logger.info("🚀 开始模拟器和脚本测试")

    results = []

    # 1. 测试文件结构
    logger.info("=" * 60)
    result = await test_file_structure()
    results.append(("文件结构", result))

    # 2. 测试模块导入
    logger.info("=" * 60)
    result = await test_simulator_modules()
    results.append(("模块导入", result))

    # 3. 测试实例创建
    logger.info("=" * 60)
    result = await test_simulator_creation()
    results.append(("模拟器创建", result))

    # 4. 测试脚本实例
    logger.info("=" * 60)
    result = await test_script_instances()
    results.append(("脚本实例", result))

    # 5. 测试基本功能
    logger.info("=" * 60)
    result = await test_simulator_basic_functionality()
    results.append(("基本功能", result))

    # 输出测试结果总结
    logger.info("=" * 60)
    logger.info("📊 测试结果总结:")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info("=" * 60)
    logger.info(f"总计: {passed}/{total} 测试通过")

    if passed == total:
        logger.info("🎉 所有测试通过!")
        return 0
    else:
        logger.warning(f"⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
