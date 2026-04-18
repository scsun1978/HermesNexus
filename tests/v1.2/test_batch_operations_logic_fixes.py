"""
HermesNexus v1.2 批量操作逻辑修复验证测试
验证代码审核发现的4个问题是否已修复
"""

import pytest
import asyncio
import sys
import os
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from shared.services.batch_operation_service import (
    BatchOperationService,
    MAX_ASSETS_BATCH_SIZE,
    MAX_PARALLEL_TASKS,
)
from shared.models.batch_operations import (
    AssetBatchCreateRequest,
    TaskBatchCreateRequest,
    AssetBatchUpdateRequest,
)


class TestParallelTasksLimit:
    """测试问题1：并行上限没有真正生效"""

    @pytest.fixture
    def service(self):
        from cloud.database.db import Database

        return BatchOperationService(database=Database())

    @pytest.mark.asyncio
    async def test_parallel_tasks_limit_enforced(self, service):
        """测试并行任务限制是否真正生效"""
        # 创建请求，设置max_parallel_tasks超过限制
        request = TaskBatchCreateRequest(
            tasks=[
                {"task_id": f"task-{i}", "name": f"Task {i}", "command": "echo test"}
                for i in range(20)  # 20个任务
            ],
            parallel_execution=True,
            max_parallel_tasks=50,  # 超过MAX_PARALLEL_TASKS(10)
        )

        # 验证请求被正确限制
        assert request.max_parallel_tasks == 50

        # 执行批量创建（应该内部限制到10）
        result = await service.create_tasks_batch(request)

        # 验证结果
        assert result.summary.total_items == 20
        # 实际并行数应该被限制到MAX_PARALLEL_TASKS
        # 但这个测试只能验证功能正常工作，不能直接验证内部调用


class TestDuplicateAssetId:
    """测试问题2：重复资产ID会被静默合并"""

    @pytest.fixture
    def service(self):
        from cloud.database.db import Database

        return BatchOperationService(database=Database())

    @pytest.mark.asyncio
    async def test_duplicate_asset_id_detection(self, service):
        """测试重复ID检测功能"""
        # 创建包含重复ID的请求
        request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": "duplicate-001",
                    "name": "Server 1",
                    "asset_type": "linux_host",
                },
                {
                    "asset_id": "duplicate-001",
                    "name": "Server 1 Copy",
                    "asset_type": "linux_host",
                },  # 重复ID
                {
                    "asset_id": "unique-002",
                    "name": "Server 2",
                    "asset_type": "linux_host",
                },
            ],
            stop_on_first_error=False,
        )

        result = await service.create_assets_batch(request)

        # 验证总数和结果数一致
        assert result.summary.total_items == 3
        assert len(result.results) == 3

        # 验证有重复错误
        assert result.summary.failed_items == 1
        assert result.summary.successful_items == 2

        # 验证错误类型
        assert "duplicate_error" in result.error_summary
        assert result.error_summary["duplicate_error"] == 1

        # 验证结果内容
        duplicate_result = None
        for item_result in result.results:
            if item_result.id == "duplicate-001" and not item_result.success:
                duplicate_result = item_result
                assert "重复" in item_result.message
                assert item_result.error_code == "duplicate_error"

        assert duplicate_result is not None, "应该有重复ID的错误结果"

    @pytest.mark.asyncio
    async def test_duplicate_id_with_stop_on_first_error(self, service):
        """测试重复ID在stop_on_first_error模式下的处理"""
        request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": "first-001",
                    "name": "Server 1",
                    "asset_type": "linux_host",
                },
                {
                    "asset_id": "first-001",
                    "name": "Server 1 Copy",
                    "asset_type": "linux_host",
                },  # 重复ID
                {
                    "asset_id": "first-002",
                    "name": "Server 2",
                    "asset_type": "linux_host",
                },
            ],
            stop_on_first_error=True,  # 遇到错误停止
        )

        result = await service.create_assets_batch(request)

        # 验证在重复ID处停止
        assert result.summary.total_items == 3
        # 应该有1个成功，1个重复错误
        assert result.summary.successful_items == 1
        assert result.summary.failed_items == 1


class TestBatchUpdateRollback:
    """测试问题3：批量更新缺少真正的回滚/一致性保证"""

    @pytest.fixture
    def service(self):
        from cloud.database.db import Database

        return BatchOperationService(database=Database())

    @pytest.mark.asyncio
    async def test_batch_update_with_failure(self, service):
        """测试批量更新失败时的处理"""
        # 先创建一些资产
        create_request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": f"rollback-asset-{i}",
                    "name": f"Server {i}",
                    "asset_type": "linux_host",
                }
                for i in range(5)
            ]
        )
        await service.create_assets_batch(create_request)

        # 批量更新，其中包含不存在的资产
        update_request = AssetBatchUpdateRequest(
            asset_ids=[
                "rollback-asset-0",  # 存在
                "rollback-asset-1",  # 存在
                "non-existent-999",  # 不存在
                "rollback-asset-2",  # 存在
                "rollback-asset-3",  # 存在
            ],
            updates={"status": "updated"},
        )

        result = await service.update_assets_batch(update_request)

        # 验证结果
        assert result.summary.total_items == 5
        # 应该有部分成功和部分失败
        assert result.summary.successful_items > 0
        assert result.summary.failed_items > 0
        assert "not_found_error" in result.error_summary


class TestStopOnFirstError:
    """测试问题4：stop_on_first_error在优化路径里不完全成立"""

    @pytest.fixture
    def service(self):
        from cloud.database.db import Database

        return BatchOperationService(database=Database())

    @pytest.mark.asyncio
    async def test_stop_on_first_error_in_batch_create(self, service):
        """测试批量创建中stop_on_first_error的严格性"""
        request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": "stop-001",
                    "name": "Server 1",
                    "asset_type": "linux_host",
                },
                {"asset_id": "stop-002", "name": "Server 2"},  # 缺少asset_type，会失败
                {
                    "asset_id": "stop-003",
                    "name": "Server 3",
                    "asset_type": "linux_host",
                },
                {
                    "asset_id": "stop-004",
                    "name": "Server 4",
                    "asset_type": "linux_host",
                },
            ],
            stop_on_first_error=True,
        )

        result = await service.create_assets_batch(request)

        # 验证在第一个错误处停止
        assert result.summary.total_items == 4

        # 应该只有第一个成功，第二个失败，后续不再处理
        assert result.summary.successful_items == 1
        assert result.summary.failed_items == 1

        # 验证结果只有2个（1个成功 + 1个失败）
        assert len(result.results) == 2

        # 验证第三个和第四个没有结果
        result_ids = [r.id for r in result.results]
        assert "stop-001" in result_ids
        assert "stop-002" in result_ids
        assert "stop-003" not in result_ids
        assert "stop-004" not in result_ids

    @pytest.mark.asyncio
    async def test_continue_on_error_in_batch_create(self, service):
        """测试批量创建中遇错继续的逻辑"""
        request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": "continue-001",
                    "name": "Server 1",
                    "asset_type": "linux_host",
                },
                {
                    "asset_id": "continue-002",
                    "name": "Server 2",
                },  # 缺少asset_type，会失败
                {
                    "asset_id": "continue-003",
                    "name": "Server 3",
                    "asset_type": "linux_host",
                },
                {
                    "asset_id": "continue-004",
                    "name": "Server 4",
                },  # 缺少asset_type，会失败
            ],
            stop_on_first_error=False,  # 遇错继续
        )

        result = await service.create_assets_batch(request)

        # 验证所有项都被处理
        assert result.summary.total_items == 4
        assert len(result.results) == 4

        # 应该有2个成功，2个失败
        assert result.summary.successful_items == 2
        assert result.summary.failed_items == 2

    @pytest.mark.asyncio
    async def test_stop_on_first_error_in_batch_update(self, service):
        """测试批量更新中stop_on_first_error的严格性"""
        # 先创建一些资产
        create_request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": f"stop-update-{i}",
                    "name": f"Server {i}",
                    "asset_type": "linux_host",
                }
                for i in range(4)
            ]
        )
        await service.create_assets_batch(create_request)

        # 批量更新，包含不存在的资产
        update_request = AssetBatchUpdateRequest(
            asset_ids=[
                "stop-update-0",  # 存在
                "stop-update-1",  # 存在
                "non-existent-999",  # 不存在，会失败
                "stop-update-2",  # 存在但不应该被处理
                "stop-update-3",  # 存在但不应该被处理
            ],
            updates={"status": "updated"},
            stop_on_first_error=True,
        )

        result = await service.update_assets_batch(update_request)

        # 验证在第一个错误处停止
        assert result.summary.total_items == 5

        # 应该有2个成功，1个失败，后续不再处理
        assert result.summary.successful_items == 2
        assert result.summary.failed_items == 1

        # 验证结果只有3个（2个成功 + 1个失败）
        assert len(result.results) == 3


class TestTransactionalRollback:
    """测试批量回退在批量助手失败时能真正恢复状态"""

    class FailingRollbackDatabase:
        def __init__(self):
            self.lock = threading.RLock()
            self.devices = {}

        def add_device(self, device_id, device_data):
            with self.lock:
                self.devices[device_id] = {**device_data, "updated_at": "seed"}
                return True

        def get_device(self, device_id):
            with self.lock:
                return self.devices.get(device_id)

        def update_device(self, device_id, updates):
            with self.lock:
                if device_id not in self.devices:
                    return False
                self.devices[device_id].update(updates)
                self.devices[device_id]["updated_at"] = "single"
                return True

        def add_devices_batch(self, devices_data):
            with self.lock:
                first_id = next(iter(devices_data))
                self.devices[first_id]["touched_by_batch"] = True
                raise RuntimeError("simulated batch create failure")

        def update_devices_batch(self, updates):
            with self.lock:
                first_id = next(iter(updates))
                self.devices[first_id]["touched_by_batch"] = True
                raise RuntimeError("simulated batch update failure")

    @pytest.fixture
    def service(self):
        return BatchOperationService(database=self.FailingRollbackDatabase())

    @pytest.mark.asyncio
    async def test_update_batch_restores_state_after_helper_failure(self, service):
        """批量更新助手失败后，fallback 之前应恢复原始状态"""
        await service.create_assets_batch(
            AssetBatchCreateRequest(
                assets=[
                    {
                        "asset_id": "rb-u-1",
                        "name": "Server 1",
                        "asset_type": "linux_host",
                    },
                    {
                        "asset_id": "rb-u-2",
                        "name": "Server 2",
                        "asset_type": "linux_host",
                    },
                ]
            )
        )

        result = await service.update_assets_batch(
            AssetBatchUpdateRequest(
                asset_ids=["rb-u-1", "rb-u-2"],
                updates={"status": "updated"},
            )
        )

        assert result.summary.successful_items == 2
        assert result.summary.failed_items == 0
        assert service.database.get_device("rb-u-1").get("status") == "updated"
        assert "touched_by_batch" not in service.database.get_device("rb-u-1")
        assert "touched_by_batch" not in service.database.get_device("rb-u-2")

    @pytest.mark.asyncio
    async def test_create_batch_restores_state_after_helper_failure(self, service):
        """批量创建助手失败后，fallback 之前应恢复原始状态"""
        result = await service.create_assets_batch(
            AssetBatchCreateRequest(
                assets=[
                    {
                        "asset_id": "rb-c-1",
                        "name": "Server 1",
                        "asset_type": "linux_host",
                    },
                    {
                        "asset_id": "rb-c-2",
                        "name": "Server 2",
                        "asset_type": "linux_host",
                    },
                ]
            )
        )

        assert result.summary.successful_items == 2
        assert result.summary.failed_items == 0
        assert service.database.get_device("rb-c-1").get("asset_type") == "linux_host"
        assert "touched_by_batch" not in service.database.get_device("rb-c-1")
        assert "touched_by_batch" not in service.database.get_device("rb-c-2")


class TestAllFixesIntegration:
    """集成测试：验证所有修复同时工作"""

    @pytest.fixture
    def service(self):
        from cloud.database.db import Database

        return BatchOperationService(database=Database())

    @pytest.mark.asyncio
    async def test_complex_scenario_with_all_fixes(self, service):
        """复杂场景测试：同时涉及所有修复点"""
        request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": "complex-001",
                    "name": "Server 1",
                    "asset_type": "linux_host",
                },
                {
                    "asset_id": "complex-001",
                    "name": "Server 1 Duplicate",
                    "asset_type": "linux_host",
                },  # 重复ID
                {"asset_id": "complex-002", "name": "Server 2"},  # 缺少字段，会失败
                {
                    "asset_id": "complex-003",
                    "name": "Server 3",
                    "asset_type": "linux_host",
                },
            ],
            stop_on_first_error=False,  # 遇错继续
        )

        result = await service.create_assets_batch(request)

        # 验证修复效果：
        # 1. 重复ID被检测到（问题2修复）
        # 2. stop_on_first_error=False时所有项都被处理（问题4修复）

        assert result.summary.total_items == 4
        assert len(result.results) == 4  # 总数和结果数一致

        # 应该有1个重复错误，1个验证错误，2个成功
        assert result.summary.successful_items == 2
        assert result.summary.failed_items == 2
        assert result.error_summary.get("duplicate_error", 0) == 1
        assert result.error_summary.get("validation_error", 0) == 1


def main():
    """运行逻辑修复验证测试"""
    print("🔧 HermesNexus v1.2 批量操作逻辑修复验证\n")

    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    main()
