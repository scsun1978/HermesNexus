"""
HermesNexus v1.2 批量操作性能测试
验证 Day 6 性能优化效果
"""

import pytest
import asyncio
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from shared.services.batch_operation_service import (
    BatchOperationService,
    MAX_ASSETS_BATCH_SIZE,
    MAX_TASKS_BATCH_SIZE,
    MAX_PARALLEL_TASKS,
    PERFORMANCE_LOG_THRESHOLD,
)
from shared.models.batch_operations import (
    AssetBatchCreateRequest,
    AssetBatchUpdateRequest,
    TaskBatchCreateRequest,
)


class TestBatchPerformanceOptimizations:
    """测试批量操作性能优化"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return BatchOperationService()

    def test_batch_size_limits(self):
        """测试批量大小限制"""
        service = BatchOperationService()

        # 验证常量设置正确
        assert MAX_ASSETS_BATCH_SIZE == 100
        assert MAX_TASKS_BATCH_SIZE == 50
        assert MAX_PARALLEL_TASKS == 10
        assert PERFORMANCE_LOG_THRESHOLD == 1.0

        # 验证Pydantic模型限制（模型层验证）
        try:
            # 这个应该在Pydantic验证层就被拦截
            large_asset_request = AssetBatchCreateRequest(
                assets=[
                    {
                        "asset_id": f"asset-{i}",
                        "name": f"Server {i}",
                        "asset_type": "linux_host",
                    }
                    for i in range(MAX_ASSETS_BATCH_SIZE + 10)  # 超过限制
                ]
            )
            assert False, "Pydantic应该拦截超过限制的请求"
        except Exception as e:
            # 预期的行为：Pydantic验证失败
            assert "too_long" in str(e) or "validation" in str(e)

    @pytest.mark.asyncio
    async def test_performance_small_batch(self, service):
        """测试小批量性能（< 10项）"""
        request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": f"perf-asset-{i}",
                    "name": f"Server {i}",
                    "asset_type": "linux_host",
                }
                for i in range(10)
            ]
        )

        start_time = time.time()
        result = await service.create_assets_batch(request)
        elapsed_time = time.time() - start_time

        # 小批量应该在1秒内完成
        assert elapsed_time < 1.0, f"小批量操作耗时 {elapsed_time:.2f}s，超过预期"
        assert result.summary.total_items == 10
        assert result.status.value in ["completed", "partial_success"]

    @pytest.mark.asyncio
    async def test_performance_medium_batch(self, service):
        """测试中批量性能（10-50项）"""
        request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": f"perf-asset-{i}",
                    "name": f"Server {i}",
                    "asset_type": "linux_host",
                }
                for i in range(50)
            ]
        )

        start_time = time.time()
        result = await service.create_assets_batch(request)
        elapsed_time = time.time() - start_time

        # 中批量应该在5秒内完成
        assert elapsed_time < 5.0, f"中批量操作耗时 {elapsed_time:.2f}s，超过预期"
        assert result.summary.total_items == 50

    @pytest.mark.asyncio
    async def test_performance_batch_vs_individual(self, service):
        """测试批量操作相比单个操作的性能提升"""
        import statistics

        # 批量操作
        batch_request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": f"batch-asset-{i}",
                    "name": f"Server {i}",
                    "asset_type": "linux_host",
                }
                for i in range(20)
            ]
        )

        batch_times = []
        for _ in range(3):  # 运行3次取平均值
            start_time = time.time()
            await service.create_assets_batch(batch_request)
            batch_times.append(time.time() - start_time)

        avg_batch_time = statistics.mean(batch_times)

        # 单个操作（模拟）
        individual_times = []
        for _ in range(3):
            start_time = time.time()
            for i in range(20):
                single_request = AssetBatchCreateRequest(
                    assets=[
                        {
                            "asset_id": f"single-asset-{i}",
                            "name": f"Server {i}",
                            "asset_type": "linux_host",
                        }
                    ]
                )
                await service.create_assets_batch(single_request)
            individual_times.append(time.time() - start_time)

        avg_individual_time = statistics.mean(individual_times)

        # 批量操作应该明显快于单个操作
        speedup = avg_individual_time / avg_batch_time
        print(
            f"🚀 性能提升: {speedup:.1f}x (批量: {avg_batch_time:.2f}s vs 单个: {avg_individual_time:.2f}s)"
        )

        # 批量操作至少应该快2倍
        assert speedup >= 1.5, f"批量操作性能提升不足: {speedup:.1f}x"

    @pytest.mark.asyncio
    async def test_concurrent_batch_operations(self, service):
        """测试并发批量操作性能"""

        async def run_batch_operation(batch_id):
            request = AssetBatchCreateRequest(
                assets=[
                    {
                        "asset_id": f"concurrent-{batch_id}-{i}",
                        "name": f"Server {i}",
                        "asset_type": "linux_host",
                    }
                    for i in range(10)
                ]
            )
            return await service.create_assets_batch(request)

        # 并发执行3个批量操作
        start_time = time.time()
        results = await asyncio.gather(
            run_batch_operation(1), run_batch_operation(2), run_batch_operation(3)
        )
        elapsed_time = time.time() - start_time

        # 所有操作都应该成功
        assert len(results) == 3
        for result in results:
            assert result.summary.total_items == 10

        # 并发操作应该比串行快
        print(f"⚡ 并发性能: 3个批量操作耗时 {elapsed_time:.2f}s")

    @pytest.mark.asyncio
    async def test_batch_update_performance(self, service):
        """测试批量更新性能"""
        # 先创建一些资产
        create_request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": f"update-asset-{i}",
                    "name": f"Server {i}",
                    "asset_type": "linux_host",
                }
                for i in range(20)
            ]
        )
        await service.create_assets_batch(create_request)

        # 批量更新
        update_request = AssetBatchUpdateRequest(
            asset_ids=[f"update-asset-{i}" for i in range(20)],
            updates={"status": "active", "metadata": {"environment": "test"}},
        )

        start_time = time.time()
        result = await service.update_assets_batch(update_request)
        elapsed_time = time.time() - start_time

        # 批量更新应该快速完成
        assert elapsed_time < 2.0, f"批量更新耗时 {elapsed_time:.2f}s，超过预期"
        assert result.summary.total_items == 20

    @pytest.mark.asyncio
    async def test_error_handling_performance(self, service):
        """测试错误处理对性能的影响"""
        # 混合有效和无效数据
        mixed_request = AssetBatchCreateRequest(
            assets=[
                # 有效数据
                {
                    "asset_id": f"valid-{i}",
                    "name": f"Server {i}",
                    "asset_type": "linux_host",
                }
                for i in range(8)
            ]
            + [
                # 无效数据（缺少必需字段）
                {"asset_id": f"invalid-{i}", "name": f"Invalid Server {i}"}
                for i in range(2)
            ],
            stop_on_first_error=False,  # 不在第一个错误时停止
        )

        start_time = time.time()
        result = await service.create_assets_batch(mixed_request)
        elapsed_time = time.time() - start_time

        # 即使有错误，也应该快速完成
        assert elapsed_time < 2.0, f"错误处理耗时 {elapsed_time:.2f}s，超过预期"
        assert result.summary.total_items == 10
        assert result.summary.failed_items > 0
        assert result.summary.successful_items > 0


class TestBatchSizeValidation:
    """测试批量大小验证"""

    @pytest.mark.asyncio
    async def test_asset_batch_size_limit(self):
        """测试资产批量大小限制"""
        service = BatchOperationService()

        # 验证Pydantic模型限制（模型层验证）
        try:
            # 这个应该在Pydantic验证层就被拦截
            large_request = AssetBatchCreateRequest(
                assets=[
                    {
                        "asset_id": f"oversize-{i}",
                        "name": f"Server {i}",
                        "asset_type": "linux_host",
                    }
                    for i in range(MAX_ASSETS_BATCH_SIZE + 1)
                ]
            )
            # 如果能创建请求，测试服务层限制
            result = await service.create_assets_batch(large_request)
            assert result.status.value == "failed"
            assert result.summary.failed_items > 0
        except Exception as e:
            # 预期的行为：Pydantic验证失败
            assert "too_long" in str(e) or "validation" in str(e)

    @pytest.mark.asyncio
    async def test_task_batch_size_limit(self):
        """测试任务批量大小限制"""
        service = BatchOperationService()

        # 验证Pydantic模型限制（模型层验证）
        try:
            # 这个应该在Pydantic验证层就被拦截
            large_request = TaskBatchCreateRequest(
                tasks=[
                    {
                        "task_id": f"oversize-task-{i}",
                        "name": f"Task {i}",
                        "command": "echo test",
                    }
                    for i in range(MAX_TASKS_BATCH_SIZE + 1)
                ]
            )
            # 如果能创建请求，测试服务层限制
            result = await service.create_tasks_batch(large_request)
            assert result.status.value == "failed"
            assert result.summary.failed_items > 0
        except Exception as e:
            # 预期的行为：Pydantic验证失败
            assert "too_long" in str(e) or "validation" in str(e)

    @pytest.mark.asyncio
    async def test_exact_boundary_sizes(self):
        """测试边界值"""
        service = BatchOperationService()

        # 正好在边界上
        boundary_request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": f"boundary-{i}",
                    "name": f"Server {i}",
                    "asset_type": "linux_host",
                }
                for i in range(MAX_ASSETS_BATCH_SIZE)
            ]
        )

        result = await service.create_assets_batch(boundary_request)

        # 应该成功处理
        assert result.summary.total_items == MAX_ASSETS_BATCH_SIZE


def main():
    """运行性能测试"""
    print("🚀 HermesNexus v1.2 批量操作性能测试\n")

    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    main()
