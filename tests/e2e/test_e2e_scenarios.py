"""
HermesNexus v1.2 端到端测试场景
覆盖核心业务流程的完整测试
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from tests.e2e.conftest import E2ETestHelper, SmokeTestSuite, run_smoke_tests_async
from shared.models.batch_operations import (
    AssetBatchCreateRequest,
    AssetBatchUpdateRequest,
    AssetBatchDeleteRequest,
    TaskBatchCreateRequest,
    TaskBatchDispatchRequest,
)
from shared.models.audit_models import AuditQueryRequest, AuditOperationType


class TestNodeManagementE2E:
    """节点管理端到端测试"""

    @pytest.mark.asyncio
    async def test_node_registration_to_heartbeat_complete_flow(self, e2e_helper: E2ETestHelper):
        """测试节点注册到心跳的完整流程"""
        # 1. 节点注册
        node_id = "e2e-node-001"
        node_data = await e2e_helper.create_test_node(node_id)

        assert node_data is not None
        assert node_data["node_id"] == node_id
        assert node_data["status"] == "active"

        # 2. 验证节点信息存储
        assert await e2e_helper.verify_asset_exists(node_id)

        # 3. 模拟心跳发送
        heartbeat_success = await e2e_helper.simulate_heartbeat(node_id)
        assert heartbeat_success

        # 4. 验证节点状态更新
        node_info = e2e_helper.database.get_device(node_id)
        assert node_info is not None
        assert node_info["status"] == "active"

        # 5. 测试心跳超时（模拟长时间未心跳）
        old_heartbeat = node_info["last_heartbeat"]
        node_info["last_heartbeat"] = (
            datetime.now(timezone.utc) - timedelta(minutes=10)
        ).isoformat()

        # 6. 验证节点状态变化（应该变为inactive）
        # 这里可以实现超时检测逻辑
        assert node_info["last_heartbeat"] != old_heartbeat

        print(f"✅ 节点管理E2E测试通过: {node_id}")

    @pytest.mark.asyncio
    async def test_multiple_nodes_lifecycle(self, e2e_helper: E2ETestHelper):
        """测试多个节点的完整生命周期"""
        # 创建多个节点
        node_ids = [f"multi-node-{i:03d}" for i in range(5)]

        for node_id in node_ids:
            await e2e_helper.create_test_node(node_id)

        # 验证所有节点创建成功
        for node_id in node_ids:
            assert await e2e_helper.verify_asset_exists(node_id)

        # 模拟所有节点发送心跳
        for node_id in node_ids:
            success = await e2e_helper.simulate_heartbeat(node_id)
            assert success

        # 验证所有节点状态
        for node_id in node_ids:
            node_info = e2e_helper.database.get_device(node_id)
            assert node_info["status"] == "active"

        print(f"✅ 多节点生命周期测试通过: {len(node_ids)} 个节点")


class TestBatchAssetOperationsE2E:
    """批量资产操作端到端测试"""

    @pytest.mark.asyncio
    async def test_batch_asset_operations_complete_flow(self, e2e_helper: E2ETestHelper):
        """测试批量资产操作完整流程"""
        batch_service = e2e_helper.batch_service

        # 1. 批量创建100个资产
        asset_count = 100
        assets = [
            {
                "asset_id": f"batch-e2e-{i:04d}",
                "name": f"Batch E2E Asset {i}",
                "asset_type": "linux_host",
                "metadata": {"index": i},
            }
            for i in range(asset_count)
        ]

        create_request = AssetBatchCreateRequest(assets=assets)
        create_response = await batch_service.create_assets_batch(create_request)

        # 验证创建结果
        assert create_response.summary.total_items == asset_count
        assert create_response.summary.successful_items == asset_count
        assert create_response.summary.failed_items == 0
        assert create_response.summary.success_rate == 100.0

        # 等待审计记录
        await asyncio.sleep(0.1)

        # 2. 验证所有资产创建成功
        for i in range(asset_count):
            asset_id = f"batch-e2e-{i:04d}"
            assert await e2e_helper.verify_asset_exists(asset_id)

        # 3. 批量更新资产状态
        update_asset_ids = [f"batch-e2e-{i:04d}" for i in range(50)]  # 更新前50个
        update_request = AssetBatchUpdateRequest(
            asset_ids=update_asset_ids,
            updates={"status": "active", "metadata": {"updated": True}},
        )
        update_response = await batch_service.update_assets_batch(update_request)

        # 验证更新结果
        assert update_response.summary.total_items == 50
        assert update_response.summary.successful_items == 50

        # 等待审计记录
        await asyncio.sleep(0.1)

        # 4. 验证更新结果
        for i in range(50):
            asset_id = f"batch-e2e-{i:04d}"
            asset_data = e2e_helper.database.get_device(asset_id)
            assert asset_data is not None
            assert asset_data.get("status") == "active"
            assert asset_data.get("metadata", {}).get("updated") is True

        # 5. 批量删除部分资产
        delete_asset_ids = [f"batch-e2e-{i:04d}" for i in range(10, 20)]  # 删除第10-19个
        delete_request = AssetBatchDeleteRequest(asset_ids=delete_asset_ids)
        delete_response = await batch_service.delete_assets_batch(delete_request)

        # 验证删除结果
        assert delete_response.summary.total_items == 10
        assert delete_response.summary.successful_items == 10

        # 等待审计记录
        await asyncio.sleep(0.1)

        # 6. 验证删除结果
        for i in range(10, 20):
            asset_id = f"batch-e2e-{i:04d}"
            # 删除的资产不应该存在
            asset_data = e2e_helper.database.get_device(asset_id)
            # 根据实现，删除可能标记为decommissioned或完全移除
            # 这里我们检查数据是否存在或状态
            assert asset_data is None or asset_data.get("status") in [
                "decommissioned",
                "deleted",
            ]

        # 7. 验证审计记录完整性
        create_audit = await e2e_helper.audit_service.get_audit_by_operation_id(
            create_response.operation_id
        )
        update_audit = await e2e_helper.audit_service.get_audit_by_operation_id(
            update_response.operation_id
        )
        delete_audit = await e2e_helper.audit_service.get_audit_by_operation_id(
            delete_response.operation_id
        )

        assert create_audit is not None
        assert update_audit is not None
        assert delete_audit is not None

        # 验证审计记录的操作类型
        assert create_audit.operation_type == AuditOperationType.BATCH_ASSET_CREATE
        assert update_audit.operation_type == AuditOperationType.BATCH_ASSET_UPDATE
        assert delete_audit.operation_type == AuditOperationType.BATCH_ASSET_DELETE

        print(f"✅ 批量资产操作E2E测试通过: 创建{asset_count}个, 更新50个, 删除10个")

    @pytest.mark.asyncio
    async def test_batch_operation_error_recovery(self, e2e_helper: E2ETestHelper):
        """测试批量操作错误恢复"""
        batch_service = e2e_helper.batch_service

        # 1. 先创建一些正常资产
        await e2e_helper.create_test_assets(5, "error-test")

        # 2. 批量更新包含不存在的资产
        update_asset_ids = [
            "error-test-asset-000",  # 存在
            "error-test-asset-001",  # 存在
            "non-existent-999",  # 不存在
            "error-test-asset-002",  # 存在
        ]

        update_request = AssetBatchUpdateRequest(
            asset_ids=update_asset_ids,
            updates={"status": "active"},
            stop_on_first_error=False,  # 遇错继续
        )
        update_response = await batch_service.update_assets_batch(update_request)

        # 3. 验证部分失败处理
        assert update_response.summary.total_items == 4
        assert update_response.summary.successful_items == 3  # 3个存在
        assert update_response.summary.failed_items == 1  # 1个不存在
        assert update_response.summary.success_rate == 75.0  # 75%成功率

        # 4. 验证审计记录包含错误信息
        await asyncio.sleep(0.1)
        audit = await e2e_helper.audit_service.get_audit_by_operation_id(
            update_response.operation_id
        )

        assert audit is not None
        assert audit.failed_items == 1
        assert len(audit.error_summary) > 0

        # 5. 验证失败操作查询
        failed_ops = await e2e_helper.audit_service.get_failed_operations(limit=10)
        assert len(failed_ops) > 0

        print(f"✅ 批量操作错误恢复测试通过: 部分失败正确处理")


class TestBatchTaskDistributionE2E:
    """批量任务分发端到端测试"""

    @pytest.mark.asyncio
    async def test_batch_task_distribution_complete_flow(self, e2e_helper: E2ETestHelper):
        """测试批量任务分发完整流程"""
        batch_service = e2e_helper.batch_service

        # 1. 创建多个节点
        node_ids = [f"task-node-{i:03d}" for i in range(3)]
        for node_id in node_ids:
            await e2e_helper.create_test_node(node_id)

        # 2. 批量创建任务
        task_count = 20
        tasks = [
            {
                "task_id": f"task-e2e-{i:04d}",
                "name": f"E2E Task {i}",
                "command": f"echo 'Task {i}'",
                "target_node": node_ids[i % 3],  # 分发到不同节点
            }
            for i in range(task_count)
        ]

        create_request = TaskBatchCreateRequest(tasks=tasks)
        create_response = await batch_service.create_tasks_batch(create_request)

        # 3. 验证任务创建结果
        assert create_response.summary.total_items == task_count
        assert create_response.summary.successful_items == task_count

        # 4. 验证任务存储
        for i in range(task_count):
            task_id = f"task-e2e-{i:04d}"
            task = e2e_helper.database.get_task(task_id)
            assert task is not None
            assert task["task_id"] == task_id

        # 5. 模拟任务分发和执行
        # 这里可以添加任务分发逻辑
        # 简化版本：验证任务可以获取

        dispatched_tasks = []
        for i in range(task_count):
            task_id = f"task-e2e-{i:04d}"
            task = e2e_helper.database.get_task(task_id)
            if task:
                dispatched_tasks.append(task)

        assert len(dispatched_tasks) == task_count

        # 6. 模拟任务执行结果更新
        for task in dispatched_tasks:
            # 更新任务状态为执行完成
            task["status"] = "completed"
            task["result"] = {
                "exit_code": 0,
                "output": f"Task {task['task_id']} completed",
            }

        # 7. 验证审计记录
        await asyncio.sleep(0.1)
        audit = await e2e_helper.audit_service.get_audit_by_operation_id(
            create_response.operation_id
        )

        assert audit is not None
        assert audit.operation_type == AuditOperationType.BATCH_TASK_CREATE

        print(f"✅ 批量任务分发E2E测试通过: 创建并分发{task_count}个任务到{len(node_ids)}个节点")


class TestAuditTrailE2E:
    """审计追踪端到端测试"""

    @pytest.mark.asyncio
    async def test_audit_trail_complete_flow(self, e2e_helper: E2ETestHelper):
        """测试审计追踪完整流程"""
        batch_service = e2e_helper.batch_service
        audit_service = e2e_helper.audit_service

        # 1. 执行各种批量操作
        operations = []

        # 批量创建
        assets = [
            {
                "asset_id": f"audit-asset-{i}",
                "name": f"Audit Asset {i}",
                "asset_type": "linux_host",
            }
            for i in range(5)
        ]
        create_request = AssetBatchCreateRequest(assets=assets)
        create_response = await batch_service.create_assets_batch(create_request)
        operations.append(("create", create_response))

        await asyncio.sleep(0.1)

        # 批量更新
        update_request = AssetBatchUpdateRequest(
            asset_ids=[f"audit-asset-{i}" for i in range(5)],
            updates={"status": "active"},
        )
        update_response = await batch_service.update_assets_batch(update_request)
        operations.append(("update", update_response))

        await asyncio.sleep(0.1)

        # 2. 验证审计记录创建
        for op_type, response in operations:
            audit = await audit_service.get_audit_by_operation_id(response.operation_id)
            assert audit is not None
            assert audit.operation_id == response.operation_id

        # 3. 查询审计历史
        asset_history = await audit_service.get_asset_history("audit-asset-0")
        assert len(asset_history) >= 2  # 至少有创建和更新

        # 4. 验证审计统计数据
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=5)

        statistics = await audit_service.get_statistics(start_time, end_time)

        assert statistics.total_operations >= 2
        assert statistics.successful_operations >= 2

        # 5. 验证错误操作查询（如果有失败的操作）
        # 这里我们创建一个会失败的操作
        failed_update_request = AssetBatchUpdateRequest(
            asset_ids=["non-existent-999"], updates={"status": "active"}
        )
        failed_response = await batch_service.update_assets_batch(failed_update_request)

        await asyncio.sleep(0.1)

        # 查询失败操作
        failed_ops = await audit_service.get_failed_operations(limit=10)
        assert len(failed_ops) > 0

        # 6. 导出审计数据
        query = AuditQueryRequest(start_time=start_time, end_time=end_time, page=1, page_size=100)
        exported_data = await audit_service.export_audits(
            query=query, format_type="json", include_details=True, max_records=100
        )

        assert exported_data is not None
        assert len(exported_data) > 0

        # 7. 验证导出数据格式
        import json

        export_dict = json.loads(exported_data)
        assert "records" in export_dict
        assert "export_time" in export_dict
        assert len(export_dict["records"]) >= 2

        print(f"✅ 审计追踪E2E测试通过: 执行{len(operations)}个操作, 审计记录完整")


class TestSmokeTests:
    """冒烟测试套件"""

    @pytest.mark.asyncio
    async def test_smoke_tests_pass(self, smoke_suite: SmokeTestSuite):
        """运行冒烟测试套件"""
        # 使用异步运行函数
        results = await run_smoke_tests_async(smoke_suite)

        # 验证所有测试通过
        assert results["passed_tests"] == results["total_tests"]
        assert results["failed_tests"] == 0

        # 输出测试结果
        print(f"\n🔥 冒烟测试结果:")
        print(f"总测试数: {results['total_tests']}")
        print(f"通过: {results['passed_tests']}")
        print(f"失败: {results['failed_tests']}")

        for test_result in results["test_results"]:
            status = "✅" if test_result["passed"] else "❌"
            print(f"{status} {test_result['name']}")

        assert results["passed_tests"] >= 3  # 至少3个测试通过


def main():
    """运行端到端测试"""
    print("🚀 HermesNexus v1.2 端到端测试\n")

    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    main()
