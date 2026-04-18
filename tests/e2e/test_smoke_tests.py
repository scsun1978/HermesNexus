"""
HermesNexus v1.2 冒烟测试套件
快速验证系统基本功能和可用性
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone, timedelta

from tests.e2e.conftest import E2ETestHelper, SmokeTestSuite, run_smoke_tests_async
from shared.models.batch_operations import (
    AssetBatchCreateRequest,
    AssetBatchUpdateRequest,
)


class TestSystemBasicsSmoke:
    """系统基础冒烟测试"""

    @pytest.mark.asyncio
    async def test_database_connection_and_operations(self, test_database):
        """测试数据库连接和基本操作"""
        # 测试连接
        assert test_database is not None

        # 测试基本操作
        test_device = {
            "name": "Smoke Test DB Device",
            "type": "linux_host",
            "status": "active",
        }

        # 添加设备
        test_database.add_device("smoke-db-001", test_device)

        # 获取设备
        retrieved = test_database.get_device("smoke-db-001")
        assert retrieved is not None
        assert retrieved["name"] == "Smoke Test DB Device"

        # 更新设备
        test_database.update_device("smoke-db-001", {"status": "inactive"})
        updated = test_database.get_device("smoke-db-001")
        assert updated["status"] == "inactive"

        # 模拟删除（更新为decommissioned状态）
        test_database.update_device("smoke-db-001", {"status": "decommissioned"})
        deleted_check = test_database.get_device("smoke-db-001")
        assert deleted_check["status"] == "decommissioned"

        print("✅ 数据库连接和基本操作测试通过")

    def test_import_dependencies(self):
        """测试核心依赖导入"""
        # 测试核心模块导入
        from cloud.database.db import Database
        from shared.services.batch_operation_service import BatchOperationService
        from shared.services.batch_audit_service import BatchAuditService
        from shared.storage.audit_storage import AuditStorage
        from shared.models.batch_operations import (
            AssetBatchCreateRequest,
            BatchOperationResponse,
        )
        from shared.models.audit_models import BatchOperationAudit, AuditQueryRequest

        print("✅ 核心依赖导入测试通过")


class TestBatchOperationsSmoke:
    """批量操作冒烟测试"""

    @pytest.mark.asyncio
    async def test_batch_create_small_dataset(self, test_services):
        """测试小数据集批量创建"""
        batch_service = test_services["batch_service"]

        # 创建小批量数据
        assets = [
            {
                "asset_id": f"smoke-asset-{i}",
                "name": f"Smoke Asset {i}",
                "asset_type": "linux_host",
            }
            for i in range(5)
        ]

        start_time = time.time()
        request = AssetBatchCreateRequest(assets=assets)
        response = await batch_service.create_assets_batch(request)
        elapsed_time = time.time() - start_time

        # 验证基本结果
        assert response is not None
        assert response.operation_id is not None
        assert response.summary.total_items == 5
        assert response.summary.successful_items == 5
        assert elapsed_time < 2.0  # 应该在2秒内完成

        print(f"✅ 小数据集批量创建测试通过 (耗时: {elapsed_time:.2f}s)")

    @pytest.mark.asyncio
    async def test_batch_update_basic(self, test_services):
        """测试基本批量更新"""
        batch_service = test_services["batch_service"]

        # 先创建一些资产
        assets = [
            {
                "asset_id": "smoke-update-001",
                "name": "Smoke Update 1",
                "asset_type": "linux_host",
            },
            {
                "asset_id": "smoke-update-002",
                "name": "Smoke Update 2",
                "asset_type": "linux_host",
            },
        ]
        await batch_service.create_assets_batch(AssetBatchCreateRequest(assets=assets))

        # 更新这些资产
        update_request = AssetBatchUpdateRequest(
            asset_ids=["smoke-update-001", "smoke-update-002"],
            updates={"status": "active"},
        )

        start_time = time.time()
        response = await batch_service.update_assets_batch(update_request)
        elapsed_time = time.time() - start_time

        # 验证结果
        assert response.summary.total_items == 2
        assert response.summary.successful_items == 2
        assert elapsed_time < 1.0  # 更新应该很快

        print(f"✅ 基本批量更新测试通过 (耗时: {elapsed_time:.2f}s)")

    @pytest.mark.asyncio
    async def test_batch_operation_with_errors(self, test_services):
        """测试包含错误的批量操作"""
        batch_service = test_services["batch_service"]

        # 先创建一个存在的资产
        assets = [
            {
                "asset_id": "smoke-error-001",
                "name": "Smoke Error",
                "asset_type": "linux_host",
            }
        ]
        await batch_service.create_assets_batch(AssetBatchCreateRequest(assets=assets))

        # 尝试更新包含不存在资产的列表
        update_request = AssetBatchUpdateRequest(
            asset_ids=["smoke-error-001", "non-existent-999"],
            updates={"status": "active"},
        )

        response = await batch_service.update_assets_batch(update_request)

        # 验证部分成功处理
        assert response.summary.total_items == 2
        assert response.summary.successful_items == 1  # 只有存在的成功
        assert response.summary.failed_items == 1  # 不存在的失败
        assert response.summary.success_rate == 50.0

        print("✅ 包含错误的批量操作测试通过")


class TestAuditSmoke:
    """审计功能冒烟测试"""

    @pytest.mark.asyncio
    async def test_audit_record_creation(self, test_services):
        """测试审计记录创建"""
        batch_service = test_services["batch_service"]
        audit_service = test_services["audit_service"]

        # 执行批量操作
        assets = [
            {
                "asset_id": "smoke-audit-001",
                "name": "Smoke Audit",
                "asset_type": "linux_host",
            }
        ]
        response = await batch_service.create_assets_batch(
            AssetBatchCreateRequest(assets=assets)
        )

        # 等待审计记录
        await asyncio.sleep(0.1)

        # 验证审计记录
        audit = await audit_service.get_audit_by_operation_id(response.operation_id)
        assert audit is not None
        assert audit.operation_id == response.operation_id
        assert audit.total_items == 1

        print("✅ 审计记录创建测试通过")

    @pytest.mark.asyncio
    async def test_audit_query_basic(self, test_services):
        """测试基本审计查询"""
        audit_service = test_services["audit_service"]

        # 执行基本查询
        from shared.models.audit_models import AuditQueryRequest

        query = AuditQueryRequest(page=1, page_size=10)

        start_time = time.time()
        response = await audit_service.query_audits(query)
        elapsed_time = time.time() - start_time

        # 验证查询结果
        assert response is not None
        assert isinstance(response.total_count, int)
        assert isinstance(response.records, list)
        assert elapsed_time < 1.0  # 查询应该很快

        print(f"✅ 基本审计查询测试通过 (耗时: {elapsed_time:.2f}s)")

    @pytest.mark.asyncio
    async def test_audit_statistics_basic(self, test_services):
        """测试基本审计统计"""
        audit_service = test_services["audit_service"]

        # 获取统计数据
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)

        statistics = await audit_service.get_statistics(start_time, end_time)

        # 验证统计数据
        assert statistics is not None
        assert isinstance(statistics.total_operations, int)
        assert isinstance(statistics.success_rate, float)
        assert 0 <= statistics.success_rate <= 100

        print("✅ 基本审计统计测试通过")


class TestPerformanceSmoke:
    """性能冒烟测试"""

    @pytest.mark.asyncio
    async def test_batch_operation_performance(self, test_services):
        """测试批量操作性能"""
        batch_service = test_services["batch_service"]

        # 测试中等规模批量操作性能
        asset_count = 50
        assets = [
            {
                "asset_id": f"smoke-perf-{i:03d}",
                "name": f"Smoke Perf {i}",
                "asset_type": "linux_host",
            }
            for i in range(asset_count)
        ]

        start_time = time.time()
        request = AssetBatchCreateRequest(assets=assets)
        response = await batch_service.create_assets_batch(request)
        elapsed_time = time.time() - start_time

        # 验证性能
        assert response.summary.successful_items == asset_count
        assert elapsed_time < 5.0  # 50个资产应该在5秒内完成

        throughput = asset_count / elapsed_time
        print(
            f"✅ 批量操作性能测试通过: {asset_count}个资产, {elapsed_time:.2f}s, {throughput:.1f} assets/s"
        )

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, test_services):
        """测试并发操作性能"""
        batch_service = test_services["batch_service"]

        async def create_batch(batch_id: int):
            assets = [
                {
                    "asset_id": f"smoke-concurrent-{batch_id}-{i}",
                    "name": f"Concurrent {batch_id}-{i}",
                    "asset_type": "linux_host",
                }
                for i in range(10)
            ]
            request = AssetBatchCreateRequest(assets=assets)
            return await batch_service.create_assets_batch(request)

        # 并发执行多个批量操作
        start_time = time.time()
        results = await asyncio.gather(
            create_batch(1), create_batch(2), create_batch(3)
        )
        elapsed_time = time.time() - start_time

        # 验证所有操作都成功
        total_assets = sum(r.summary.successful_items for r in results)
        assert total_assets == 30  # 3个操作，每个10个资产
        assert elapsed_time < 10.0  # 并发操作应该在10秒内完成

        print(
            f"✅ 并发操作性能测试通过: 3个并发操作, {total_assets}个资产, {elapsed_time:.2f}s"
        )


class TestIntegrationSmoke:
    """集成冒烟测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_basic_workflow(self, test_services):
        """测试基本端到端工作流"""
        batch_service = test_services["batch_service"]
        audit_service = test_services["audit_service"]

        # 1. 创建资产
        assets = [
            {
                "asset_id": "smoke-e2e-001",
                "name": "Smoke E2E",
                "asset_type": "linux_host",
            }
        ]
        create_response = await batch_service.create_assets_batch(
            AssetBatchCreateRequest(assets=assets)
        )
        assert create_response.summary.successful_items == 1

        await asyncio.sleep(0.1)

        # 2. 更新资产
        update_request = AssetBatchUpdateRequest(
            asset_ids=["smoke-e2e-001"], updates={"status": "active"}
        )
        update_response = await batch_service.update_assets_batch(update_request)
        assert update_response.summary.successful_items == 1

        await asyncio.sleep(0.1)

        # 3. 验证审计记录
        create_audit = await audit_service.get_audit_by_operation_id(
            create_response.operation_id
        )
        update_audit = await audit_service.get_audit_by_operation_id(
            update_response.operation_id
        )

        assert create_audit is not None
        assert update_audit is not None

        # 4. 查询资产历史
        asset_history = await audit_service.get_asset_history("smoke-e2e-001")
        assert len(asset_history) >= 2  # 至少有创建和更新

        print("✅ 基本端到端工作流测试通过")

    @pytest.mark.asyncio
    async def test_complete_smoke_suite(self, smoke_suite: SmokeTestSuite):
        """测试完整冒烟测试套件"""
        results = await run_complete_smoke_tests(smoke_suite)

        # 验证测试结果
        assert results["passed_tests"] >= 3
        assert results["total_tests"] == 4


async def run_complete_smoke_tests(smoke_suite: SmokeTestSuite) -> dict:
    """运行完整冒烟测试套件"""
    print("\n🔥 开始运行完整冒烟测试套件...\n")

    # 使用异步运行函数
    results = await run_smoke_tests_async(smoke_suite)

    # 输出详细结果
    print(f"\n{'='*50}")
    print(f"🔥 冒烟测试套件执行结果")
    print(f"{'='*50}")
    print(f"总测试数: {results['total_tests']}")
    print(f"通过测试: {results['passed_tests']} ✅")
    print(f"失败测试: {results['failed_tests']} ❌")
    print(f"成功率: {(results['passed_tests']/results['total_tests']*100):.1f}%")
    print(f"{'='*50}\n")

    for i, test_result in enumerate(results["test_results"], 1):
        status = "✅ 通过" if test_result["passed"] else "❌ 失败"
        print(f"{i}. {test_result['name']}: {status}")
        if test_result["error"]:
            print(f"   错误: {test_result['error']}")

    return results


def main():
    """运行冒烟测试"""
    print("🚀 HermesNexus v1.2 冒烟测试套件\n")

    pytest.main([__file__, "-v", "-s", "--tb=short"])


if __name__ == "__main__":
    main()
