"""
HermesNexus v1.2 审计增强功能测试
测试 Day 8 实现的审计功能
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from shared.services.batch_operation_service import BatchOperationService
from shared.services.batch_audit_service import BatchAuditService
from shared.storage.audit_storage import AuditStorage
from shared.models.batch_operations import (
    AssetBatchCreateRequest,
    AssetBatchUpdateRequest,
    AssetBatchDeleteRequest,
)
from shared.models.audit_models import (
    AuditQueryRequest,
    AuditOperationType,
    BatchOperationAudit,
)


class TestBatchAuditService:
    """测试批量操作审计服务"""

    @pytest.fixture
    def storage(self):
        """创建审计存储"""
        return AuditStorage()

    @pytest.fixture
    def audit_service(self, storage):
        """创建审计服务"""
        return BatchAuditService(storage=storage)

    @pytest.fixture
    def batch_service(self):
        """创建批量操作服务"""
        from cloud.database.db import Database

        return BatchOperationService(database=Database())

    @pytest.mark.asyncio
    async def test_audit_service_creates_records(self, batch_service, audit_service):
        """测试审计服务创建记录"""
        # 创建测试资产
        assets = [
            {
                "asset_id": f"audit-test-{i}",
                "name": f"Audit Test {i}",
                "asset_type": "linux_host",
            }
            for i in range(5)
        ]

        request = AssetBatchCreateRequest(assets=assets)
        response = await batch_service.create_assets_batch(request)

        # 记录审计
        audit = await audit_service.log_batch_operation(
            operation=response, user_id="test-user", username="testuser"
        )

        # 验证审计记录
        assert audit is not None
        assert audit.operation_id == response.operation_id
        assert audit.user_id == "test-user"
        assert audit.username == "testuser"
        assert audit.total_items == 5
        assert audit.successful_items == 5
        assert audit.failed_items == 0

    @pytest.mark.asyncio
    async def test_audit_query_by_operation_id(self, batch_service, audit_service):
        """测试按操作ID查询审计"""
        # 创建操作
        assets = [
            {
                "asset_id": "query-test-1",
                "name": "Query Test 1",
                "asset_type": "linux_host",
            },
            {
                "asset_id": "query-test-2",
                "name": "Query Test 2",
                "asset_type": "linux_host",
            },
        ]

        request = AssetBatchCreateRequest(assets=assets)
        response = await batch_service.create_assets_batch(request)

        # 记录审计
        await audit_service.log_batch_operation(response)

        # 查询审计
        found_audit = await audit_service.get_audit_by_operation_id(
            response.operation_id
        )

        # 验证查询结果
        assert found_audit is not None
        assert found_audit.operation_id == response.operation_id
        assert found_audit.total_items == 2

    @pytest.mark.asyncio
    async def test_audit_query_by_asset_id(self, batch_service, audit_service):
        """测试按资产ID查询审计"""
        # 创建操作
        assets = [
            {
                "asset_id": "asset-history-test",
                "name": "Asset History Test",
                "asset_type": "linux_host",
            }
        ]

        request = AssetBatchCreateRequest(assets=assets)
        response = await batch_service.create_assets_batch(request)

        # 记录审计
        audit = await audit_service.log_batch_operation(response)
        # 手动添加资产关联（因为内存数据库可能不包含详细数据）
        audit.related_assets = ["asset-history-test"]
        audit_service.storage.save_audit(audit)

        # 查询资产历史
        asset_history = await audit_service.get_asset_history("asset-history-test")

        # 验证查询结果
        assert len(asset_history) > 0
        assert any(a.operation_id == response.operation_id for a in asset_history)

    @pytest.mark.asyncio
    async def test_audit_failed_operations(self, batch_service, audit_service):
        """测试失败操作的审计记录"""
        # 创建包含失败的操作
        request = AssetBatchUpdateRequest(
            asset_ids=[
                "failed-op-existing-1",
                "failed-op-non-existent-999",
                "failed-op-existing-2",
            ],
            updates={"status": "active"},
        )

        # 先创建存在的资产
        create_request = AssetBatchCreateRequest(
            assets=[
                {
                    "asset_id": "failed-op-existing-1",
                    "name": "Existing 1",
                    "asset_type": "linux_host",
                },
                {
                    "asset_id": "failed-op-existing-2",
                    "name": "Existing 2",
                    "asset_type": "linux_host",
                },
            ]
        )
        await batch_service.create_assets_batch(create_request)

        # 执行更新操作
        response = await batch_service.update_assets_batch(request)

        # 记录审计
        audit = await audit_service.log_batch_operation(response)

        # 验证失败操作记录
        assert audit.failed_items > 0
        assert audit.success_rate < 100.0
        assert len(audit.error_summary) > 0

        # 验证详细结果包含失败项
        failed_results = [r for r in audit.results if not r.success]
        assert len(failed_results) > 0

    @pytest.mark.asyncio
    async def test_audit_statistics(self, audit_service):
        """测试审计统计功能"""
        # 创建多个审计记录
        now = datetime.now(timezone.utc)

        # 手动创建一些审计数据用于测试统计
        for i in range(10):
            from shared.models.audit_models import BatchOperationAudit, AuditItemResult

            audit = BatchOperationAudit(
                audit_id=f"stat-audit-{i}",
                operation_id=f"stat-op-{i}",
                operation_type=AuditOperationType.BATCH_ASSET_CREATE,
                timestamp=now - timedelta(hours=i),
                total_items=10,
                successful_items=8 if i % 2 == 0 else 10,
                failed_items=2 if i % 2 == 0 else 0,
                success_rate=80.0 if i % 2 == 0 else 100.0,
                error_summary={"validation_error": 2} if i % 2 == 0 else {},
                started_at=now - timedelta(hours=i),
                completed_at=now - timedelta(hours=i) + timedelta(minutes=5),
                duration_seconds=300.0,
            )
            audit_service.storage.save_audit(audit)

        # 获取统计数据
        start_time = now - timedelta(hours=12)
        end_time = now
        statistics = await audit_service.get_statistics(start_time, end_time)

        # 验证统计数据
        assert statistics.total_operations == 10
        assert statistics.successful_operations > 0
        assert statistics.failed_operations > 0
        assert 0 < statistics.success_rate < 100


class TestAuditQueryFunctionality:
    """测试审计查询功能"""

    @pytest.fixture
    def audit_service(self):
        """创建审计服务"""
        storage = AuditStorage()
        return BatchAuditService(storage=storage)

    @pytest.mark.asyncio
    async def test_complex_audit_query(self, audit_service):
        """测试复杂审计查询"""
        # 创建测试数据
        now = datetime.now(timezone.utc)

        # 创建不同类型的审计记录
        test_audits = [
            {
                "audit_id": "complex-1",
                "operation_id": "complex-op-1",
                "operation_type": AuditOperationType.BATCH_ASSET_CREATE,
                "user_id": "user-alice",
                "timestamp": now - timedelta(hours=1),
                "total_items": 10,
                "successful_items": 10,
                "failed_items": 0,
                "success_rate": 100.0,
                "error_summary": {},
                "started_at": now - timedelta(hours=1),
                "completed_at": now - timedelta(hours=1) + timedelta(minutes=2),
            },
            {
                "audit_id": "complex-2",
                "operation_id": "complex-op-2",
                "operation_type": AuditOperationType.BATCH_ASSET_UPDATE,
                "user_id": "user-bob",
                "timestamp": now - timedelta(hours=2),
                "total_items": 10,
                "successful_items": 8,
                "failed_items": 2,
                "success_rate": 80.0,
                "error_summary": {"validation_error": 2},
                "started_at": now - timedelta(hours=2),
                "completed_at": now - timedelta(hours=2) + timedelta(minutes=3),
            },
            {
                "audit_id": "complex-3",
                "operation_id": "complex-op-3",
                "operation_type": AuditOperationType.BATCH_ASSET_CREATE,
                "user_id": "user-alice",
                "timestamp": now - timedelta(hours=3),
                "total_items": 10,
                "successful_items": 5,
                "failed_items": 5,
                "success_rate": 50.0,
                "error_summary": {"not_found_error": 5},
                "started_at": now - timedelta(hours=3),
                "completed_at": now - timedelta(hours=3) + timedelta(minutes=1),
            },
        ]

        # 保存审计记录
        for audit_data in test_audits:
            from shared.models.audit_models import BatchOperationAudit

            audit = BatchOperationAudit(**audit_data)
            audit_service.storage.save_audit(audit)

        # 测试1：按用户查询
        user_query = AuditQueryRequest(user_id="user-alice", page=1, page_size=10)
        user_results = await audit_service.query_audits(user_query)
        assert user_results.total_count == 2

        # 测试2：按操作类型查询
        type_query = AuditQueryRequest(
            operation_type=AuditOperationType.BATCH_ASSET_CREATE, page=1, page_size=10
        )
        type_results = await audit_service.query_audits(type_query)
        assert type_results.total_count == 2

        # 测试3：查询失败操作
        failed_query = AuditQueryRequest(failed_only=True, page=1, page_size=10)
        failed_results = await audit_service.query_audits(failed_query)
        assert failed_results.total_count == 2

        # 测试4：按错误类型查询
        error_query = AuditQueryRequest(
            error_type="validation_error", page=1, page_size=10
        )
        error_results = await audit_service.query_audits(error_query)
        assert error_results.total_count == 1

        # 测试5：按时间范围查询
        time_query = AuditQueryRequest(
            start_time=now - timedelta(hours=2, minutes=30),
            end_time=now,
            page=1,
            page_size=10,
        )
        time_results = await audit_service.query_audits(time_query)
        assert time_results.total_count == 2

    @pytest.mark.asyncio
    async def test_audit_pagination(self, audit_service):
        """测试审计分页功能"""
        # 创建多个审计记录
        now = datetime.now(timezone.utc)

        for i in range(25):
            from shared.models.audit_models import BatchOperationAudit

            audit = BatchOperationAudit(
                audit_id=f"page-audit-{i}",
                operation_id=f"page-op-{i}",
                operation_type=AuditOperationType.BATCH_ASSET_CREATE,
                timestamp=now - timedelta(minutes=i),
                total_items=10,
                successful_items=10,
                failed_items=0,
                success_rate=100.0,
                error_summary={},
                started_at=now - timedelta(minutes=i),
                completed_at=now - timedelta(minutes=i) + timedelta(minutes=1),
            )
            audit_service.storage.save_audit(audit)

        # 测试分页
        page1_query = AuditQueryRequest(page=1, page_size=10)
        page1_results = await audit_service.query_audits(page1_query)

        assert page1_results.total_count == 25
        assert page1_results.total_pages == 3
        assert len(page1_results.records) == 10
        assert page1_results.page == 1

        # 测试第二页
        page2_query = AuditQueryRequest(page=2, page_size=10)
        page2_results = await audit_service.query_audits(page2_query)

        assert len(page2_results.records) == 10
        assert page2_results.page == 2


class TestAuditIntegration:
    """测试审计功能集成"""

    @pytest.fixture
    def integrated_batch_service(self):
        """创建集成了审计服务的批量操作服务"""
        from cloud.database.db import Database

        storage = AuditStorage()
        audit_service = BatchAuditService(storage=storage)
        batch_service = BatchOperationService(
            database=Database(), audit_service=audit_service
        )

        return batch_service, audit_service

    @pytest.mark.asyncio
    async def test_automatic_audit_logging(self, integrated_batch_service):
        """测试自动审计记录"""
        batch_service, audit_service = integrated_batch_service

        # 执行批量操作
        assets = [
            {
                "asset_id": f"auto-audit-{i}",
                "name": f"Auto Audit {i}",
                "asset_type": "linux_host",
            }
            for i in range(5)
        ]

        request = AssetBatchCreateRequest(
            assets=assets,
            user_id="audit-user-1",
            username="audit-admin",
            request_ip="10.0.0.8",
            user_agent="pytest",
        )
        response = await batch_service.create_assets_batch(request)

        # 等待审计记录完成（异步操作）
        await asyncio.sleep(0.1)

        # 验证审计记录
        audit = await audit_service.get_audit_by_operation_id(response.operation_id)
        assert audit is not None
        assert audit.total_items == 5
        assert audit.user_id == "audit-user-1"
        assert audit.username == "audit-admin"
        assert audit.request_ip == "10.0.0.8"
        assert audit.user_agent == "pytest"
        assert audit.parameters.get("user_id") == "audit-user-1"
        assert audit.parameters.get("username") == "audit-admin"
        assert len(audit.parameters.get("assets", [])) == 5

    @pytest.mark.asyncio
    async def test_delete_operation_is_audited(self, integrated_batch_service):
        """测试批量删除也会落审计"""
        batch_service, audit_service = integrated_batch_service

        assets = [
            {
                "asset_id": "delete-audit-1",
                "name": "Delete 1",
                "asset_type": "linux_host",
            }
        ]
        await batch_service.create_assets_batch(AssetBatchCreateRequest(assets=assets))
        response = await batch_service.delete_assets_batch(
            AssetBatchDeleteRequest(asset_ids=["delete-audit-1"])
        )
        await asyncio.sleep(0.1)

        audit = await audit_service.get_audit_by_operation_id(response.operation_id)
        assert audit is not None
        assert audit.operation_type == AuditOperationType.BATCH_ASSET_DELETE
        assert audit.total_items == 1


class TestAuditStorageUpsertSafety:
    """测试审计存储幂等写入安全性"""

    def test_save_audit_is_upsert_safe(self):
        storage = AuditStorage()
        now = datetime.now(timezone.utc)
        audit = BatchOperationAudit(
            audit_id="upsert-audit",
            operation_id="upsert-op",
            operation_type=AuditOperationType.BATCH_ASSET_CREATE,
            timestamp=now,
            total_items=1,
            successful_items=1,
            failed_items=0,
            success_rate=100.0,
            results=[],
            error_summary={},
            related_assets=["upsert-asset"],
            started_at=now,
            completed_at=now + timedelta(seconds=1),
            duration_seconds=1.0,
        )

        assert storage.save_audit(audit) is True
        assert storage.save_audit(audit) is True
        assert storage.get_total_count() == 1
        assert len(storage.get_asset_history("upsert-asset")) == 1


def main():
    """运行审计增强测试"""
    print("🔍 HermesNexus v1.2 审计增强功能测试\n")

    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    main()
