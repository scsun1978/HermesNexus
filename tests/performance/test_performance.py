"""
性能和压力测试

测试HermesNexus MVP的性能表现和负载能力
"""

import asyncio
import sys
import time
import statistics
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from cloud.database.db import Database


class PerformanceTester:
    """性能测试器"""

    def __init__(self, cloud_url="http://localhost:8080"):
        self.cloud_url = cloud_url
        self.results = {}

    async def test_api_response_time(self, iterations=10):
        """测试API响应时间"""
        print("🧪 API响应时间测试")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response_times = []

                for i in range(iterations):
                    start = time.time()
                    response = await client.get(f"{self.cloud_url}/health")
                    end = time.time()

                    if response.status_code == 200:
                        response_time = (end - start) * 1000  # 毫秒
                        response_times.append(response_time)
                        print(f"   请求 {i+1}: {response_time:.2f}ms")
                    else:
                        print(f"   请求 {i+1}: 失败 ({response.status_code})")

                if response_times:
                    avg_time = statistics.mean(response_times)
                    min_time = min(response_times)
                    max_time = max(response_times)
                    median_time = statistics.median(response_times)

                    print("\n   📊 响应时间统计:")
                    print(f"      平均: {avg_time:.2f}ms")
                    print(f"      中位数: {median_time:.2f}ms")
                    print(f"      最小: {min_time:.2f}ms")
                    print(f"      最大: {max_time:.2f}ms")

                    # 性能评估
                    if avg_time < 100:
                        print("   ✅ 响应时间优秀 (<100ms)")
                        self.results["api_response_time"] = "excellent"
                    elif avg_time < 500:
                        print("   ✅ 响应时间良好 (<500ms)")
                        self.results["api_response_time"] = "good"
                    else:
                        print("   ⚠️  响应时间需要优化 (≥500ms)")
                        self.results["api_response_time"] = "needs_improvement"

                    return True
                else:
                    print("   ❌ 没有成功的响应")
                    return False

        except Exception as e:
            print(f"   ❌ API响应时间测试失败: {e}")
            return False

    async def test_concurrent_requests(self, concurrent_users=5, requests_per_user=10):
        """测试并发请求处理"""
        print(f"🧪 并发请求测试 ({concurrent_users} 用户 × {requests_per_user} 请求)")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:

                async def user_requests(user_id):
                    """模拟单个用户的多个请求"""
                    user_times = []
                    user_success = 0

                    for i in range(requests_per_user):
                        try:
                            start = time.time()
                            response = await client.get(f"{self.cloud_url}/api/v1/nodes")
                            end = time.time()

                            if response.status_code == 200:
                                user_success += 1
                                user_times.append((end - start) * 1000)

                            # 随机延迟，模拟真实用户行为
                            await asyncio.sleep(0.1 + (i % 3) * 0.1)

                        except Exception as e:
                            print(f"   用户 {user_id} 请求 {i+1} 失败: {e}")

                    return user_success, user_times

                # 并发执行用户请求
                start_time = time.time()
                results = await asyncio.gather(
                    *[user_requests(user_id) for user_id in range(concurrent_users)]
                )
                end_time = time.time()

                total_time = end_time - start_time
                total_success = sum(result[0] for result in results)
                total_requests = concurrent_users * requests_per_user

                all_times = []
                for result in results:
                    all_times.extend(result[1])

                print("\n   📊 并发测试结果:")
                print(f"      总时间: {total_time:.2f}s")
                print(
                    f"      成功率: {total_success}/{total_requests} ({total_success/total_requests*100:.1f}%)"
                )
                print(f"      吞吐量: {total_success/total_time:.2f} 请求/秒")

                if all_times:
                    avg_response_time = statistics.mean(all_times)
                    print(f"      平均响应时间: {avg_response_time:.2f}ms")

                # 并发性能评估
                if total_success >= total_requests * 0.95:  # 95%成功率
                    print("   ✅ 并发处理能力优秀")
                    self.results["concurrent_requests"] = "excellent"
                elif total_success >= total_requests * 0.8:  # 80%成功率
                    print("   ✅ 并发处理能力良好")
                    self.results["concurrent_requests"] = "good"
                else:
                    print("   ⚠️  并发处理能力需要提升")
                    self.results["concurrent_requests"] = "needs_improvement"

                return True

        except Exception as e:
            print(f"   ❌ 并发请求测试失败: {e}")
            return False

    async def test_database_performance(self, operations=100):
        """测试数据库性能"""
        print(f"🧪 数据库性能测试 ({operations} 操作)")

        try:
            db = Database()

            # 测试写入性能
            write_times = []
            for i in range(operations):
                start = time.time()
                db.add_node(f"perf-test-{i}", {"node_id": f"perf-test-{i}", "status": "online"})
                end = time.time()
                write_times.append((end - start) * 1000)  # 毫秒

            # 测试读取性能
            read_times = []
            for i in range(operations):
                start = time.time()
                db.get_node(f"perf-test-{i}")
                end = time.time()
                read_times.append((end - start) * 1000)  # 毫秒

            # 测试查询性能
            start = time.time()
            nodes = db.list_nodes()
            end = time.time()
            query_time = (end - start) * 1000

            print("\n   📊 数据库性能统计:")
            print(f"      写入平均: {statistics.mean(write_times):.3f}ms")
            print(f"      读取平均: {statistics.mean(read_times):.3f}ms")
            print(f"      查询时间: {query_time:.3f}ms ({len(nodes)} 条记录)")

            # 清理测试数据
            for i in range(operations):
                db.nodes.pop(f"perf-test-{i}", None)

            # 数据库性能评估
            avg_write = statistics.mean(write_times)
            avg_read = statistics.mean(read_times)

            if avg_write < 1 and avg_read < 1:
                print("   ✅ 数据库性能优秀")
                self.results["database_performance"] = "excellent"
            elif avg_write < 5 and avg_read < 5:
                print("   ✅ 数据库性能良好")
                self.results["database_performance"] = "good"
            else:
                print("   ⚠️  数据库性能需要优化")
                self.results["database_performance"] = "needs_improvement"

            return True

        except Exception as e:
            print(f"   ❌ 数据库性能测试失败: {e}")
            return False

    async def test_memory_usage(self):
        """测试内存使用"""
        print("🧪 内存使用测试")

        try:
            import psutil

            process = psutil.Process()

            # 获取当前内存使用
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            print("   📊 内存使用:")
            print(f"      RSS: {memory_mb:.2f}MB")
            print(f"      VMS: {memory_info.vms / 1024 / 1024:.2f}MB")

            # 内存使用评估
            if memory_mb < 100:
                print("   ✅ 内存使用优秀 (<100MB)")
                self.results["memory_usage"] = "excellent"
            elif memory_mb < 500:
                print("   ✅ 内存使用良好 (<500MB)")
                self.results["memory_usage"] = "good"
            else:
                print("   ⚠️  内存使用较高 (≥500MB)")
                self.results["memory_usage"] = "needs_monitoring"

            return True

        except ImportError:
            print("   ⚠️  psutil 未安装，跳过内存测试")
            return True
        except Exception as e:
            print(f"   ❌ 内存使用测试失败: {e}")
            return False

    async def run_performance_tests(self):
        """运行所有性能测试"""
        print("🚀 开始性能和压力测试")
        print("=" * 60)

        tests = [
            ("API响应时间", self.test_api_response_time),
            ("并发请求", self.test_concurrent_requests),
            ("数据库性能", self.test_database_performance),
            ("内存使用", self.test_memory_usage),
        ]

        for test_name, test_func in tests:
            print(f"\n{'='*60}")
            print(f"性能测试: {test_name}")
            print(f"{'='*60}")

            try:
                await test_func()
            except Exception as e:
                print(f"❌ {test_name}测试失败: {e}")

            # 测试之间等待
            await asyncio.sleep(1)

        # 生成性能报告
        await self.generate_performance_report()

    async def generate_performance_report(self):
        """生成性能测试报告"""
        print("\n" + "=" * 60)
        print("📊 性能测试报告")
        print("=" * 60)

        print("\n🎯 性能指标总结:")

        performance_categories = {
            "excellent": "✅ 优秀",
            "good": "✅ 良好",
            "needs_improvement": "⚠️  需要改进",
            "needs_monitoring": "⚠️  需要监控",
        }

        for test_name, result in self.results.items():
            status = performance_categories.get(result, "❓ 未知")
            print(f"{status} {test_name}")

        # 计算总体评分
        excellent_count = sum(1 for result in self.results.values() if result == "excellent")
        good_count = sum(1 for result in self.results.values() if result == "good")
        total_count = len(self.results)

        print("\n📈 总体评分:")
        if excellent_count + good_count >= total_count * 0.8:
            print("🎉 性能表现优秀，达到MVP发布标准")
            return 0
        elif excellent_count + good_count >= total_count * 0.6:
            print("✅ 性能表现良好，基本达到MVP标准")
            return 0
        else:
            print("⚠️  性能需要优化，建议进一步调整")
            return 1


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="HermesNexus 性能测试")
    parser.add_argument("--cloud-url", default="http://localhost:8080", help="云端API URL")
    parser.add_argument("--quick", action="store_true", help="快速性能测试")

    args = parser.parse_args()

    tester = PerformanceTester(cloud_url=args.cloud_url)

    try:
        if args.quick:
            # 快速测试：只测试API响应时间
            await tester.test_api_response_time()
            return 0
        else:
            # 完整性能测试
            exit_code = await tester.run_performance_tests()
            return exit_code

    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 性能测试失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
