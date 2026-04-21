"""
HermesNexus v1.2 批量操作功能测试
使用真正的pytest断言，修复测试问题
"""

import pytest
import asyncio
from datetime import datetime, timezone
from collections import defaultdict

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from shared.models.batch_operations import (
    BatchOperationStatus,
    BatchItemResult,
    BatchOperationSummary,
    BatchOperationResponse,
    AssetBatchCreateRequest,
    AssetBatchUpdateRequest,
    AssetBatchDeleteRequest,
    TaskBatchCreateRequest,
    TaskBatchDispatchRequest,
)
from shared.services.batch_operation_service import (
    BatchOperationService,
    _classify_error,
)


class TestBatchOperationModels:
    """测试批量操作模型"""

    def test_batch_item_result(self):
        """测试单项结果模型"""
        result = BatchItemResult(id="test-001", success=True, message="操作成功", data={"key": "value"})

        assert result.success is True
        assert result.id == "test-001"
        assert result.message == "操作成功"

    def test_batch_operation_summary(self):
        """测试操作汇总模型"""
        summary = BatchOperationSummary(
            total_items=10,
            successful_items=8,
            failed_items=2,
            operation_id="batch-op-001",
        )

        assert summary.total_items == 10
        assert summary.successful_items == 8
        assert summary.failed_items == 2
        assert summary.success_rate == 80.0

    def test_asset_batch_create_request(self):
        """测试资产批量创建请求"""
        request = AssetBatchCreateRequest(
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

        assert len(request.assets) == 2
        assert request.idempotency_key == "test-create-001"
        assert request.stop_on_first_error is False

    def test_task_batch_create_request(self):
        """测试任务批量创建请求"""
        request = TaskBatchCreateRequest(
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

        assert request.parallel_execution is True
        assert request.max_parallel_tasks == 5


class TestBatchOperationService:
    """测试批量操作服务"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return BatchOperationService()

    @pytest.mark.asyncio
    async def test_idempotency_check(self, service):
        """测试幂等性检查"""
        # 第一次检查应该返回不幂等
        result1 = service._check_idempotency("test-key", "asset_create")

        assert result1.is_idempotent is False
        assert result1.message == "幂等性检查通过，可以执行新操作"

    @pytest.mark.asyncio
    async def test_create_assets_with_validation(self, service):
        """测试带验证的资产批量创建"""
        # 创建包含无效数据的请求
        request = AssetBatchCreateRequest(
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

        result = await service.create_assets_batch(request)

        # 验证部分失败处理
        assert result.summary.total_items == 4
        assert result.summary.failed_items > 0
        assert result.summary.successful_items > 0

        # 验证操作状态
        assert result.status in [
            BatchOperationStatus.PARTIAL_SUCCESS,
            BatchOperationStatus.COMPLETED,
        ]

        # 验证错误摘要
        assert len(result.error_summary) > 0
        assert "validation_error" in result.error_summary

    @pytest.mark.asyncio
    async def test_idempotency_caching(self, service):
        """测试幂等性缓存"""
        request1 = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": "asset-001",
                    "name": "Server 1",
                    "asset_type": "linux_host",
                }
            ],
            idempotency_key="test-idempotent-002",
        )

        request2 = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": "asset-001",
                    "name": "Server 1",
                    "asset_type": "linux_host",
                }
            ],
            idempotency_key="test-idempotent-002",
        )

        # 第一次执行
        result1 = await service.create_assets_batch(request1)
        operation_id = result1.operation_id

        # 第二次执行（应该命中幂等性缓存）
        result2 = await service.create_assets_batch(request2)

        # 验证幂等性
        assert result2.operation_id == operation_id
        assert result2.summary.total_items == result1.summary.total_items

    @pytest.mark.asyncio
    async def test_delete_assets_batch(self, service):
        """测试批量删除资产"""
        request = AssetBatchDeleteRequest(asset_ids=["asset-001", "asset-002"], force=False)

        # 这里会失败因为资产不存在，但可以测试错误处理
        result = await service.delete_assets_batch(request)

        assert result.operation_type == "asset_delete"
        assert result.summary.total_items == 2

    @pytest.mark.asyncio
    async def test_deactivate_assets_batch(self, service):
        """测试批量停用资产"""
        result = await service.deactivate_assets_batch(
            asset_ids=["asset-001", "asset-002"], stop_on_first_error=False
        )

        assert result.operation_type == "asset_deactivate"
        assert result.summary.total_items == 2

    @pytest.mark.asyncio
    async def test_dispatch_tasks_batch(self, service):
        """测试批量下发任务"""
        request = TaskBatchDispatchRequest(
            task_ids=["task-001", "task-002"], target_node_ids=["node-001", "node-002"]
        )

        result = await service.dispatch_tasks_batch(request)

        assert result.operation_type == "task_dispatch"
        # 应该有4个操作（2个任务 x 2个节点）
        assert result.summary.total_items == 4


class TestErrorClassification:
    """测试错误分类"""

    def test_validation_error(self):
        """测试验证错误分类"""
        assert _classify_error("Validation failed: invalid input") == "validation_error"

    def test_duplicate_error(self):
        """测试重复错误分类"""
        assert _classify_error("Duplicate entry: asset already exists") == "duplicate_error"

    def test_not_found_error(self):
        """测试未找到错误分类"""
        assert _classify_error("Asset not found") == "not_found_error"

    def test_timeout_error(self):
        """测试超时错误分类"""
        assert _classify_error("Connection timeout") == "timeout"

    def test_permission_error(self):
        """测试权限错误分类"""
        assert _classify_error("Permission denied") == "permission_error"

    def test_connection_error(self):
        """测试连接错误分类"""
        assert _classify_error("Connection refused") == "connection_error"

    def test_unknown_error(self):
        """测试未知错误分类"""
        assert _classify_error("Unknown error occurred") == "unknown_error"


class TestAssetDataValidation:
    """测试资产数据校验"""

    def test_validate_valid_asset(self):
        """测试校验有效资产"""
        from shared.services.batch_operation_service import _validate_asset_data

        asset_data = {
            "asset_id": "asset-001",
            "name": "Server 1",
            "asset_type": "linux_host",
        }

        result = _validate_asset_data(asset_data)

        assert result["valid"] is True
        assert result["error"] is None

    def test_validate_missing_required_fields(self):
        """测试缺少必需字段"""
        from shared.services.batch_operation_service import _validate_asset_data

        # 缺少name
        asset_data = {"asset_id": "asset-001", "asset_type": "linux_host"}

        result = _validate_asset_data(asset_data)

        assert result["valid"] is False
        assert "name" in result["error"]

    def test_validate_invalid_asset_type(self):
        """测试无效资产类型"""
        from shared.services.batch_operation_service import _validate_asset_data

        asset_data = {
            "asset_id": "asset-001",
            "name": "Server 1",
            "asset_type": "invalid_type",
        }

        result = _validate_asset_data(asset_data)

        assert result["valid"] is False
        assert "asset_type" in result["error"]

    def test_validate_empty_asset_id(self):
        """测试空资产ID"""
        from shared.services.batch_operation_service import _validate_asset_data

        asset_data = {"asset_id": "", "name": "Server 1", "asset_type": "linux_host"}

        result = _validate_asset_data(asset_data)

        assert result["valid"] is False
        assert "asset_id" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
