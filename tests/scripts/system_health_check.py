"""
系统健康检查脚本

快速验证HermesNexus MVP各组件状态
"""

import subprocess
import sys
import time
import asyncio
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def check_python_environment():
    """检查Python环境"""
    print("🐍 检查Python环境...")

    try:
        # 检查Python版本
        version = sys.version_info
        print(f"   Python版本: {version.major}.{version.minor}.{version.micro}")

        # 检查虚拟环境
        in_venv = hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        )
        print(f"   虚拟环境: {'✅' if in_venv else '❌'}")

        return True

    except Exception as e:
        print(f"❌ Python环境检查失败: {e}")
        return False


def check_dependencies():
    """检查依赖包"""
    print("📦 检查依赖包...")

    required_packages = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("sqlalchemy", "SQLAlchemy"),
        ("pydantic", "Pydantic"),
        ("aiohttp", "aiohttp"),
        ("paramiko", "paramiko"),
        ("psutil", "psutil"),
    ]

    missing_packages = []

    for package, display_name in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {display_name}")
        except ImportError:
            print(f"   ❌ {display_name}")
            missing_packages.append(display_name)

    if missing_packages:
        print(f"\n❌ 缺少依赖包: {', '.join(missing_packages)}")
        return False
    else:
        print("✅ 所有依赖包已安装")
        return True


def check_project_structure():
    """检查项目结构"""
    print("📁 检查项目结构...")

    required_dirs = ["cloud", "edge", "shared", "console", "tests", "docs"]

    missing_dirs = []

    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists() and dir_path.is_dir():
            print(f"   ✅ {dir_name}/")
        else:
            print(f"   ❌ {dir_name}/")
            missing_dirs.append(dir_name)

    if missing_dirs:
        print(f"\n❌ 缺少目录: {', '.join(missing_dirs)}")
        return False
    else:
        print("✅ 项目结构完整")
        return True


async def check_cloud_api():
    """检查云端API"""
    print("☁️  检查云端API...")

    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8080/health")

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    print("   ✅ 云端API运行正常")
                    return True
                else:
                    print(f"   ❌ API状态: {data.get('status')}")
                    return False
            else:
                print(f"   ❌ API响应码: {response.status_code}")
                return False

    except Exception as e:
        print(f"   ❌ 云端API连接失败: {e}")
        print("   💡 提示: 请运行 'make run-cloud' 启动云端API")
        return False


def check_database():
    """检查数据库模块"""
    print("🗄️  检查数据库模块...")

    try:
        from cloud.database.db import Database

        db = Database()

        # 测试基本操作
        db.add_node("health-check", {"node_id": "health-check", "status": "online"})

        node = db.get_node("health-check")

        if node and node.get("node_id") == "health-check":
            print("   ✅ 数据库模块正常")
            return True
        else:
            print("   ❌ 数据库操作异常")
            return False

    except Exception as e:
        print(f"   ❌ 数据库模块检查失败: {e}")
        return False


def check_shared_modules():
    """检查共享模块"""
    print("📦 检查共享模块...")

    try:
        from shared.protocol.messages import MessageType
        from shared.protocol.error_codes import ErrorCode
        from shared.schemas.models import Node, Device, Job
        from shared.schemas.enums import JobStatus, NodeStatus

        print("   ✅ 协议消息")
        print("   ✅ 错误代码")
        print("   ✅ 数据模型")
        print("   ✅ 枚举类型")

        return True

    except Exception as e:
        print(f"   ❌ 共享模块检查失败: {e}")
        return False


def check_console():
    """检查控制台"""
    print("🖥️  检查控制台...")

    console_dir = project_root / "console"
    index_file = console_dir / "index.html"

    if index_file.exists():
        print("   ✅ 控制台页面存在")

        # 检查静态文件
        static_dir = console_dir / "static"
        if static_dir.exists():
            css_file = static_dir / "css" / "style.css"
            js_file = static_dir / "js" / "app.js"

            if css_file.exists() and js_file.exists():
                print("   ✅ 静态资源完整")
                return True
            else:
                print("   ❌ 静态资源不完整")
                return False
        else:
            print("   ❌ 静态文件目录缺失")
            return False
    else:
        print("   ❌ 控制台页面缺失")
        return False


def generate_mvp_summary():
    """生成MVP总结报告"""
    print("\n" + "=" * 60)
    print("📊 HermesNexus MVP 系统状态")
    print("=" * 60)

    checks = [
        ("Python环境", check_python_environment),
        ("依赖包", check_dependencies),
        ("项目结构", check_project_structure),
        ("共享模块", check_shared_modules),
        ("数据库模块", check_database),
        ("控制台", check_console),
    ]

    results = []

    for check_name, check_func in checks:
        try:
            if asyncio.iscoroutinefunction(check_func):
                result = asyncio.run(check_func())
            else:
                result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name}检查异常: {e}")
            results.append((check_name, False))

    # 异步检查云端API
    try:
        api_result = asyncio.run(check_cloud_api())
        results.append(("云端API", api_result))
    except Exception as e:
        print(f"❌ 云端API检查异常: {e}")
        results.append(("云端API", False))

    # 输出结果
    print("\n" + "=" * 60)
    print("📋 检查结果汇总")
    print("=" * 60)

    passed = 0
    failed = 0

    for check_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"通过: {passed}/{len(results)}")

    if failed == 0:
        print("🎉 系统状态良好，可以进行MVP测试")
        return 0
    else:
        print(f"⚠️  发现 {failed} 个问题，请先修复")
        return 1


def main():
    """主函数"""
    print("🚀 HermesNexus MVP 系统健康检查")
    print("=" * 60)

    try:
        exit_code = generate_mvp_summary()
        return exit_code

    except KeyboardInterrupt:
        print("\n⚠️  检查被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 系统检查失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
