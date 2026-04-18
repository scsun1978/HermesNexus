#!/usr/bin/env python3
"""
HermesNexus v1.2 批量操作功能验证脚本
验证批量操作的幂等性、部分失败和并行执行
"""

import sys
import os
import asyncio
from datetime import datetime, timezone

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def test_batch_operation_models():
    """测试批量操作模型"""
    print("🧪 测试批量操作模型...")

    try:
        from shared.models.batch_operations import (
            BatchOperationStatus,
            BatchItemResult,
            BatchOperationSummary,
            BatchOperationResponse,
            AssetBatchCreateRequest,
            AssetBatchUpdateRequest,
            TaskBatchCreateRequest,
        )

        # 测试BatchItemResult
        item_result = BatchItemResult(
            id="test-001", success=True, message="操作成功", data={"key": "value"}
        )
        assert item_result.success is True
        print("  ✅ BatchItemResult 模型测试通过")

        # 测试BatchOperationSummary
        summary = BatchOperationSummary(
            total_items=10,
            successful_items=8,
            failed_items=2,
            operation_id="batch-op-001",
        )
        assert summary.success_rate == 80.0
        print("  ✅ BatchOperationSummary 模型测试通过")

        # 测试AssetBatchCreateRequest
        create_request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": "asset-001",
                    "name": "Server 1",
                    "asset_type": "linux_host",
                },
                {
                    "asset_id": "asset-002",
                    "name": "Server 2",
                    "asset_type": "linux_host",
                },
            ],
            stop_on_first_error=False,
            idempotency_key="test-create-001",
        )
        assert len(create_request.assets) == 2
        assert create_request.idempotency_key == "test-create-001"
        print("  ✅ AssetBatchCreateRequest 模型测试通过")

        # 测试TaskBatchCreateRequest
        task_request = TaskBatchCreateRequest(
            tasks=[
                {
                    "task_id": "task-001",
                    "name": "Update System",
                    "command": "yum update -y",
                }
            ],
            parallel_execution=True,
            max_parallel_tasks=5,
        )
        assert task_request.parallel_execution is True
        print("  ✅ TaskBatchCreateRequest 模型测试通过")

        return True

    except Exception as e:
        print(f"  ❌ 批量操作模型测试失败: {e}")
        return False


def test_batch_operation_service():
    """测试批量操作服务"""
    print("🧪 测试批量操作服务...")

    try:
        from shared.services.batch_operation_service import BatchOperationService
        from shared.models.batch_operations import AssetBatchCreateRequest

        service = BatchOperationService()

        # 测试幂等性检查
        idempotency_result = service._check_idempotency("test-key", "asset_create")
        assert idempotency_result.is_idempotent is False
        print("  ✅ 幂等性检查测试通过")

        # 测试创建批量请求
        create_request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": "asset-001",
                    "name": "Server 1",
                    "asset_type": "linux_host",
                },
                {
                    "asset_id": "asset-002",
                    "name": "Server 2",
                    "asset_type": "linux_host",
                },
            ],
            stop_on_first_error=False,
            idempotency_key="test-cache-001",
        )

        # 运行异步测试
        async def test_async_operations():
            # 测试批量创建资产
            result = await service.create_assets_batch(create_request)
            assert result.operation_type == "asset_create"
            assert result.summary.total_items == 2
            print("  ✅ 批量创建资产测试通过")

            # 测试幂等性缓存
            cache_key = f"asset_create:{create_request.idempotency_key}"
            assert cache_key in service._idempotency_cache
            print("  ✅ 幂等性缓存测试通过")

            # 测试操作历史记录
            assert result.operation_id in service._operation_history
            print("  ✅ 操作历史记录测试通过")

            return True

        # 运行异步测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(test_async_operations())
            return result
        finally:
            loop.close()

    except Exception as e:
        print(f"  ❌ 批量操作服务测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_error_classification():
    """测试错误分类"""
    print("🧪 测试错误分类...")

    try:
        from shared.services.batch_operation_service import _classify_error

        # 测试各种错误分类
        assert _classify_error("Validation failed: invalid input") == "validation_error"
        assert (
            _classify_error("Duplicate entry: asset already exists")
            == "duplicate_error"
        )
        assert _classify_error("Asset not found") == "not_found_error"
        assert _classify_error("Connection timeout") == "timeout"
        assert _classify_error("Permission denied") == "permission_error"
        assert _classify_error("Connection refused") == "connection_error"
        assert _classify_error("Unknown error occurred") == "unknown_error"

        print("  ✅ 错误分类测试通过")
        return True

    except Exception as e:
        print(f"  ❌ 错误分类测试失败: {e}")
        return False


def test_idempotency():
    """测试幂等性功能"""
    print("🧪 测试幂等性功能...")

    try:
        from shared.services.batch_operation_service import BatchOperationService
        from shared.models.batch_operations import AssetBatchCreateRequest

        service = BatchOperationService()

        # 第一次请求
        request1 = AssetBatchCreateRequest(
            assets=[{"asset_id": "asset-001", "name": "Server 1"}],
            idempotency_key="test-idempotent-001",
        )

        # 第二次相同请求
        request2 = AssetBatchCreateRequest(
            assets=[{"asset_id": "asset-001", "name": "Server 1"}],
            idempotency_key="test-idempotent-001",
        )

        async def test_idempotent_requests():
            # 第一次执行
            result1 = await service.create_assets_batch(request1)
            operation_id = result1.operation_id

            # 第二次执行（应该命中幂等性缓存）
            result2 = await service.create_assets_batch(request2)

            # 验证幂等性
            assert result2.operation_id == operation_id
            print("  ✅ 幂等性操作ID一致测试通过")

            # 验证缓存结果
            assert result1.operation_id == result2.operation_id
            print("  ✅ 幂等性缓存结果测试通过")

            return True

        # 运行异步测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(test_idempotent_requests())
            return result
        finally:
            loop.close()

    except Exception as e:
        print(f"  ❌ 幂等性测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_partial_failure_handling():
    """测试部分失败处理"""
    print("🧪 测试部分失败处理...")

    try:
        from shared.services.batch_operation_service import BatchOperationService
        from shared.models.batch_operations import AssetBatchCreateRequest

        service = BatchOperationService()

        # 创建包含有效和无效数据的请求
        mixed_request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": "asset-001",
                    "name": "Valid Server",
                    "asset_type": "linux_host",
                },
                {"asset_id": "asset-002"},  # 缺少必需字段
                {
                    "asset_id": "asset-003",
                    "name": "Another Valid Server",
                    "asset_type": "linux_host",
                },
                {"asset_id": "asset-004"},  # 缺少必需字段
            ],
            stop_on_first_error=False,  # 不在第一个错误时停止
        )

        async def test_partial_failure():
            result = await service.create_assets_batch(mixed_request)

            # 验证部分成功处理
            assert result.summary.total_items == 4
            assert result.summary.failed_items > 0
            assert result.summary.successful_items > 0
            print("  ✅ 部分失败统计测试通过")

            # 验证操作状态
            from shared.models.batch_operations import BatchOperationStatus

            assert result.status in [
                BatchOperationStatus.PARTIAL_SUCCESS,
                BatchOperationStatus.COMPLETED,
            ]
            print("  ✅ 部分失败状态测试通过")

            # 验证错误摘要
            assert len(result.error_summary) > 0
            print("  ✅ 错误摘要统计测试通过")

            return True

        # 运行异步测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(test_partial_failure())
            return result
        finally:
            loop.close()

    except Exception as e:
        print(f"  ❌ 部分失败处理测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_parallel_execution():
    """测试并行执行"""
    print("🧪 测试并行执行...")

    try:
        from shared.services.batch_operation_service import BatchOperationService
        from shared.models.batch_operations import TaskBatchCreateRequest

        service = BatchOperationService()

        # 创建并行任务请求
        parallel_request = TaskBatchCreateRequest(
            tasks=[
                {
                    "task_id": f"task-{i:03d}",
                    "name": f"Task {i}",
                    "command": "echo test",
                }
                for i in range(10)
            ],
            parallel_execution=True,
            max_parallel_tasks=3,
        )

        async def test_parallel_tasks():
            import time

            start_time = time.time()

            result = await service.create_tasks_batch(parallel_request)

            elapsed_time = time.time() - start_time

            # 验证结果
            assert result.summary.total_items == 10
            print(f"  ✅ 并行任务执行测试通过 (耗时: {elapsed_time:.2f}秒)")

            return True

        # 运行异步测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(test_parallel_tasks())
            return result
        finally:
            loop.close()

    except Exception as e:
        print(f"  ❌ 并行执行测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🚀 HermesNexus v1.2 批量操作功能验证\n")

    test_results = []

    # 运行所有测试
    test_results.append(("批量操作模型", test_batch_operation_models()))
    test_results.append(("批量操作服务", test_batch_operation_service()))
    test_results.append(("错误分类", test_error_classification()))
    test_results.append(("幂等性功能", test_idempotency()))
    test_results.append(("部分失败处理", test_partial_failure_handling()))
    test_results.append(("并行执行", test_parallel_execution()))

    # 汇总结果
    print(f"\n📊 测试结果汇总:")
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    for name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("🎉 所有测试通过！批量操作功能实现成功。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查实现。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
