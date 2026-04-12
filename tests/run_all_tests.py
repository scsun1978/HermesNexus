"""
测试运行器 - 运行所有测试套件

执行单元测试、集成测试和端到端测试
"""

import subprocess
import sys
import time


def run_command(command, description, timeout=300):
    """运行命令并返回结果"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"命令: {command}")
    print(f"{'-'*60}")

    start_time = time.time()

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )

        elapsed_time = time.time() - start_time

        # 输出结果
        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print("STDERR:", result.stderr)

        print(f"{'-'*60}")
        print(f"✅ 完成 (耗时: {elapsed_time:.2f}秒)")
        print(f"返回码: {result.returncode}")

        return result.returncode == 0, result.returncode

    except subprocess.TimeoutExpired:
        print(f"❌ 超时 (>{timeout}秒)")
        return False, -1
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False, -1


def main():
    """主测试函数"""
    print("🚀 HermesNexus MVP 测试运行器")
    print("=" * 60)

    results = []

    # 1. 单元测试
    print("\n📋 第一阶段: 单元测试")
    success, returncode = run_command(
        "python -m pytest tests/unit/ -v --tb=short", "运行单元测试", timeout=120
    )
    results.append(("单元测试", success, returncode))

    # 2. 集成测试
    print("\n📋 第二阶段: 集成测试")
    success, returncode = run_command(
        "python -m pytest tests/integration/ -v --tb=short", "运行集成测试", timeout=180
    )
    results.append(("集成测试", success, returncode))

    # 3. 模拟器测试
    print("\n📋 第三阶段: 模拟器测试")
    success, returncode = run_command(
        "python tests/test_simulators.py", "运行模拟器测试", timeout=60
    )
    results.append(("模拟器测试", success, returncode))

    # 4. 控制台测试
    print("\n📋 第四阶段: 控制台测试")
    success, returncode = run_command(
        "python tests/test_console.py", "运行控制台测试", timeout=60
    )
    results.append(("控制台测试", success, returncode))

    # 5. SSH执行器测试
    print("\n📋 第五阶段: SSH执行器测试")
    success, returncode = run_command(
        "python tests/test_ssh_executor.py", "运行SSH执行器测试", timeout=60
    )
    results.append(("SSH执行器测试", success, returncode))

    # 6. 云端边缘集成测试
    print("\n📋 第六阶段: 云端边缘集成测试")
    success, returncode = run_command(
        "python tests/test_cloud_edge_integration.py",
        "运行云端边缘集成测试",
        timeout=120,
    )
    results.append(("云端边缘集成测试", success, returncode))

    # 7. 端到端测试 (需要服务运行)
    print("\n📋 第七阶段: 端到端测试")
    print("⚠️  注意: 端到端测试需要云端API运行")
    user_input = input("是否运行端到端测试? (y/n): ").strip().lower()

    if user_input == "y":
        success, returncode = run_command(
            "python -m pytest tests/e2e/ -v --tb=short", "运行端到端测试", timeout=180
        )
        results.append(("端到端测试", success, returncode))
    else:
        print("⏭️  跳过端到端测试")
        results.append(("端到端测试", None, "skipped"))

    # 输出测试结果总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)

    passed = 0
    failed = 0
    skipped = 0

    for test_name, success, returncode in results:
        if success is None:
            status = "⏭️  跳过"
            skipped += 1
        elif success:
            status = "✅ 通过"
            passed += 1
        else:
            status = "❌ 失败"
            failed += 1

        print(f"{status}: {test_name}")

    print("=" * 60)
    print(f"总计: {passed + failed + skipped} 个测试套件")
    print(f"通过: {passed} | 失败: {failed} | 跳过: {skipped}")

    # 计算通过率
    if passed + failed > 0:
        pass_rate = (passed / (passed + failed)) * 100
        print(f"通过率: {pass_rate:.1f}%")

        # 验收标准
        if pass_rate >= 90:
            print("🎉 测试通过率达到验收标准 (≥90%)")
            return 0
        else:
            print("⚠️  测试通过率未达到验收标准 (需要≥90%)")
            return 1
    else:
        print("⚠️  没有测试被执行")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试运行器错误: {e}")
        sys.exit(1)
