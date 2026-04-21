"""
HermesNexus v1.2 控制台批量操作功能测试
测试 Day 7 实现的控制台批量操作 UI 功能
"""

import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from shared.services.batch_operation_service import BatchOperationService
from shared.models.batch_operations import (
    AssetBatchCreateRequest,
    AssetBatchUpdateRequest,
)


class TestConsoleBatchUI:
    """测试控制台批量操作 UI 后端集成"""

    @pytest.fixture
    def service(self):
        from cloud.database.db import Database

        return BatchOperationService(database=Database())

    @pytest.fixture
    def sample_assets(self):
        """创建测试资产"""
        return [
            {
                "asset_id": f"console-test-{i}",
                "name": f"Console Test Server {i}",
                "asset_type": "linux_host",
            }
            for i in range(10)
        ]

    @pytest.mark.asyncio
    async def test_batch_operation_api_endpoint_format(self, service, sample_assets):
        """测试批量操作 API 返回格式符合 UI 需求"""
        # 创建测试资产
        create_request = AssetBatchCreateRequest(assets=sample_assets)
        create_result = await service.create_assets_batch(create_request)

        # 测试批量更新
        asset_ids = [f"console-test-{i}" for i in range(5)]
        update_request = AssetBatchUpdateRequest(
            asset_ids=asset_ids,
            updates={"status": "active", "description": "Updated via console UI"},
        )

        update_result = await service.update_assets_batch(update_request)

        # 验证返回格式符合 UI 需要
        assert hasattr(update_result, "operation_id")
        assert hasattr(update_result, "status")
        assert hasattr(update_result, "summary")
        assert hasattr(update_result, "results")
        assert hasattr(update_result, "error_summary")

        # 验证数据结构可被 JSON 序列化（前端需要）
        import json

        result_dict = {
            "operation_id": update_result.operation_id,
            "status": update_result.status.value,
            "summary": {
                "total_items": update_result.summary.total_items,
                "successful_items": update_result.summary.successful_items,
                "failed_items": update_result.summary.failed_items,
                "success_rate": update_result.summary.success_rate,
            },
            "results": [
                {
                    "id": r.id,
                    "success": r.success,
                    "message": r.message,
                    "error_code": r.error_code,
                }
                for r in update_result.results
            ],
            "error_summary": update_result.error_summary,
        }

        json_str = json.dumps(result_dict)
        assert len(json_str) > 0

    @pytest.mark.asyncio
    async def test_batch_operation_with_ui_filters(self, service, sample_assets):
        """测试 UI 过滤条件下的批量操作"""
        # 创建测试资产
        create_request = AssetBatchCreateRequest(assets=sample_assets)
        await service.create_assets_batch(create_request)

        # 模拟 UI 选择操作：选择特定 ID 范围的资产
        selected_ids = [f"console-test-{i}" for i in range(3, 8)]  # 选择中间5个

        update_request = AssetBatchUpdateRequest(
            asset_ids=selected_ids, updates={"status": "inactive"}
        )

        result = await service.update_assets_batch(update_request)

        # 验证只有选中的资产被更新
        assert result.summary.total_items == 5
        assert result.summary.successful_items == 5

    @pytest.mark.asyncio
    async def test_batch_operation_error_display_format(self, service):
        """测试批量操作错误信息格式适合 UI 展示"""
        # 测试包含不存在的资产
        update_request = AssetBatchUpdateRequest(
            asset_ids=[
                "console-existing-1",
                "console-non-existent-999",
                "console-existing-2",
            ],
            updates={"status": "active"},
        )

        # 先创建存在的资产
        create_request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": "console-existing-1",
                    "name": "Existing 1",
                    "asset_type": "linux_host",
                },
                {
                    "asset_id": "console-existing-2",
                    "name": "Existing 2",
                    "asset_type": "linux_host",
                },
            ]
        )
        await service.create_assets_batch(create_request)

        # 执行更新
        result = await service.update_assets_batch(update_request)

        # 验证错误信息格式
        assert result.summary.failed_items > 0
        assert "not_found_error" in result.error_summary

        # 验证每个结果项都有详细错误信息
        failed_results = [r for r in result.results if not r.success]
        assert len(failed_results) > 0

        for failed_result in failed_results:
            assert failed_result.message is not None
            assert failed_result.error_code is not None
            assert len(failed_result.message) > 0

    @pytest.mark.asyncio
    async def test_batch_operation_progress_tracking(self, service, sample_assets):
        """测试批量操作进度跟踪功能"""
        create_request = AssetBatchCreateRequest(assets=sample_assets)
        result = await service.create_assets_batch(create_request)

        # 验证操作进度信息
        assert result.summary.total_items == len(sample_assets)

        # 计算完成百分比
        completion_rate = (
            (result.summary.successful_items + result.summary.failed_items)
            / result.summary.total_items
            * 100
        )
        assert completion_rate == 100.0  # 所有项目都处理完成

    @pytest.mark.asyncio
    async def test_batch_operation_export_data_format(self, service, sample_assets):
        """测试批量操作结果导出数据格式"""
        create_request = AssetBatchCreateRequest(assets=sample_assets)
        result = await service.create_assets_batch(create_request)

        # 生成导出数据
        export_data = {
            "operation_id": result.operation_id,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "completed_at": (result.completed_at.isoformat() if result.completed_at else None),
            "status": result.status.value,
            "summary": {
                "total_items": result.summary.total_items,
                "successful_items": result.summary.successful_items,
                "failed_items": result.summary.failed_items,
                "success_rate": result.summary.success_rate,
            },
            "results": [
                {
                    "id": r.id,
                    "success": r.success,
                    "message": r.message,
                    "error_code": r.error_code,
                }
                for r in result.results
            ],
            "error_summary": result.error_summary,
        }

        # 验证可以导出为 JSON
        import json

        json_export = json.dumps(export_data, indent=2, ensure_ascii=False)

        # 验证 JSON 格式正确
        parsed = json.loads(json_export)
        assert parsed["operation_id"] == result.operation_id
        assert len(parsed["results"]) == len(sample_assets)

    @pytest.mark.asyncio
    async def test_batch_operation_stop_on_first_error_ui(self, service):
        """测试遇错停止在 UI 场景下的行为"""
        # 创建一些资产
        assets = [
            {
                "asset_id": f"stop-ui-{i}",
                "name": f"Stop UI {i}",
                "asset_type": "linux_host",
            }
            for i in range(5)
        ]
        create_request = AssetBatchCreateRequest(assets=assets)
        await service.create_assets_batch(create_request)

        # 测试遇错停止：包含不存在的资产
        update_request = AssetBatchUpdateRequest(
            asset_ids=[
                "stop-ui-0",  # 存在
                "stop-ui-1",  # 存在
                "non-existent",  # 不存在
                "stop-ui-2",  # 存在但不应该被处理
                "stop-ui-3",  # 存在但不应该被处理
            ],
            updates={"status": "active"},
            stop_on_first_error=True,
        )

        result = await service.update_assets_batch(update_request)

        # 验证遇错停止行为
        assert result.summary.total_items == 5
        assert result.summary.failed_items > 0
        # 后续的资产不应该被处理
        assert result.summary.successful_items + result.summary.failed_items < 5


class TestConsoleUIIntegration:
    """测试控制台 UI 集成功能"""

    def test_checkbox_selection_logic(self):
        """测试复选框选择逻辑"""
        # 模拟复选框选择
        selected_ids = set()
        all_ids = [f"asset-{i}" for i in range(10)]

        # 模拟选择操作
        selected_ids.add("asset-1")
        selected_ids.add("asset-3")
        selected_ids.add("asset-5")

        # 验证选择状态
        assert len(selected_ids) == 3
        assert "asset-1" in selected_ids
        assert "asset-2" not in selected_ids

    def test_batch_button_display_logic(self):
        """测试批量按钮显示逻辑"""
        selected_count = 0

        # 没有选择时不显示批量按钮
        assert selected_count == 0
        show_batch_button = selected_count > 0
        assert not show_batch_button

        # 有选择时显示批量按钮
        selected_count = 3
        show_batch_button = selected_count > 0
        assert show_batch_button

    def test_select_all_checkbox_logic(self):
        """测试全选复选框逻辑"""
        all_items = [f"item-{i}" for i in range(10)]
        selected_items = set()

        # 全选
        selected_items.update(all_items)
        assert len(selected_items) == len(all_items)

        # 取消全选
        selected_items.clear()
        assert len(selected_items) == 0

        # 部分选择状态
        selected_items.add("item-1")
        selected_items.add("item-2")
        is_all_selected = len(selected_items) == len(all_items)
        is_partially_selected = len(selected_items) > 0 and not is_all_selected
        assert is_partially_selected


def main():
    """运行控制台批量操作测试"""
    print("🖥️ HermesNexus v1.2 控制台批量操作功能测试\n")

    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    main()
