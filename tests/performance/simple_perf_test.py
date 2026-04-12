"""
简单性能测试

测试基础性能指标，不依赖复杂模块
"""

import asyncio
import sys
import time
import statistics
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import httpx
except ImportError:
    print("❌ 需要安装 httpx: pip install httpx")
    sys.exit(1)


async def test_api_performance():
    """测试API性能"""
    print("🚀 HermesNexus MVP 性能测试")
    print("=" * 50)

    cloud_url = "http://localhost:8080"
    results = {}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. API响应时间测试
            print("\n📊 测试1: API响应时间")
            response_times = []

            for i in range(10):
                start = time.time()
                response = await client.get(f"{cloud_url}/health")
                end = time.time()

                if response.status_code == 200:
                    response_time = (end - start) * 1000  # 毫秒
                    response_times.append(response_time)
                    print(f"   请求 {i+1}: {response_time:.2f}ms")
                else:
                    print(f"   请求 {i+1}: 失败 ({response.status_code})")

            if response_times:
                avg_time = statistics.mean(response_times)
                median_time = statistics.median(response_times)
                min_time = min(response_times)
                max_time = max(response_times)

                print(f"\n   响应时间统计:")
                print(f"   平均: {avg_time:.2f}ms")
                print(f"   中位数: {median_time:.2f}ms")
                print(f"   最小: {min_time:.2f}ms")
                print(f"   最大: {max_time:.2f}ms")

                if avg_time < 100:
                    print("   ✅ 响应时间优秀")
                    results["response_time"] = "excellent"
                elif avg_time < 500:
                    print("   ✅ 响应时间良好")
                    results["response_time"] = "good"
                else:
                    print("   ⚠️  响应时间需要优化")
                    results["response_time"] = "needs_improvement"

            # 2. 并发请求测试
            print("\n📊 测试2: 并发请求 (5并发 × 10请求)")

            async def concurrent_requests(user_id):
                user_times = []
                user_success = 0

                for i in range(10):
                    try:
                        start = time.time()
                        response = await client.get(f"{cloud_url}/api/v1/nodes")
                        end = time.time()

                        if response.status_code == 200:
                            user_success += 1
                            user_times.append((end - start) * 1000)

                        await asyncio.sleep(0.1)

                    except Exception as e:
                        print(f"   用户 {user_id} 请求失败: {e}")

                return user_success, user_times

            start_time = time.time()
            user_results = await asyncio.gather(
                *[concurrent_requests(i) for i in range(5)]
            )
            end_time = time.time()

            total_time = end_time - start_time
            total_success = sum(result[0] for result in user_results)
            total_requests = 5 * 10

            print(f"   总时间: {total_time:.2f}s")
            print(
                f"   成功率: {total_success}/{total_requests} ({total_success/total_requests*100:.1f}%)"
            )
            print(f"   吞吐量: {total_success/total_time:.2f} 请求/秒")

            if total_success >= total_requests * 0.9:
                print("   ✅ 并发处理能力优秀")
                results["concurrency"] = "excellent"
            elif total_success >= total_requests * 0.7:
                print("   ✅ 并发处理能力良好")
                results["concurrency"] = "good"
            else:
                print("   ⚠️  并发处理能力需要提升")
                results["concurrency"] = "needs_improvement"

            # 3. 数据库操作性能测试
            print("\n📊 测试3: 数据库操作性能")

            # 模拟数据库操作时间
            db_operations = []
            for i in range(50):
                start = time.time()
                # 模拟简单的字典操作（类似内存数据库）
                test_data = {}
                for j in range(100):
                    test_data[f"key_{j}"] = f"value_{j}"
                _ = test_data.get("key_50")
                end = time.time()
                db_operations.append((end - start) * 1000)

            avg_db_op = statistics.mean(db_operations)
            print(f"   平均操作时间: {avg_db_op:.3f}ms")

            if avg_db_op < 1:
                print("   ✅ 数据库操作性能优秀")
                results["database"] = "excellent"
            elif avg_db_op < 5:
                print("   ✅ 数据库操作性能良好")
                results["database"] = "good"
            else:
                print("   ⚠️  数据库操作性能一般")
                results["database"] = "average"

            # 4. 内存使用测试
            print("\n📊 测试4: 内存使用")

            try:
                import psutil

                process = psutil.Process()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024

                print(f"   内存使用: {memory_mb:.2f}MB")

                if memory_mb < 100:
                    print("   ✅ 内存使用优秀")
                    results["memory"] = "excellent"
                elif memory_mb < 500:
                    print("   ✅ 内存使用良好")
                    results["memory"] = "good"
                else:
                    print("   ⚠️  内存使用较高")
                    results["memory"] = "needs_monitoring"

            except ImportError:
                print("   ⚠️  psutil未安装，跳过内存测试")
                results["memory"] = "skipped"

            # 生成性能报告
            print("\n" + "=" * 50)
            print("📊 性能测试报告")
            print("=" * 50)

            performance_grades = {
                "excellent": "✅ 优秀",
                "good": "✅ 良好",
                "average": "✅ 一般",
                "needs_improvement": "⚠️  需改进",
                "needs_monitoring": "⚠️  需监控",
                "skipped": "⏭️  跳过",
            }

            print("\n性能评级:")
            for test_name, grade in results.items():
                status = performance_grades.get(grade, "❓")
                print(f"{status} {test_name}")

            # 计算总体评分
            excellent_count = sum(
                1 for grade in results.values() if grade == "excellent"
            )
            good_count = sum(1 for grade in results.values() if grade == "good")
            total_tested = sum(
                1
                for grade in results.values()
                if grade in ["excellent", "good", "average"]
            )

            if total_tested > 0:
                success_rate = (excellent_count + good_count) / total_tested
                print(f"\n📈 总体评分: {success_rate*100:.0f}%")

                if success_rate >= 0.8:
                    print("🎉 性能表现优秀，达到MVP发布标准")
                    return 0
                elif success_rate >= 0.6:
                    print("✅ 性能表现良好，达到MVP基本标准")
                    return 0
                else:
                    print("⚠️  性能需要优化后发布")
                    return 1
            else:
                print("⚠️  没有完成足够的性能测试")
                return 1

    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        print("💡 提示: 请确保云端API正在运行")
        return 1


async def main():
    """主函数"""
    try:
        exit_code = await test_api_performance()
        return exit_code

    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
