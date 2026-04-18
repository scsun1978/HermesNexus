"""
HermesNexus v1.2 E2E 测试配置和辅助工具
提供端到端测试的基础设施
"""

import pytest
import asyncio
import tempfile
import shutil
from typing import AsyncGenerator, Generator
from pathlib import Path
from datetime import datetime, timezone, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from cloud.database.db import Database
from shared.services.batch_operation_service import BatchOperationService
from shared.services.batch_audit_service import BatchAuditService
from shared.storage.audit_storage import AuditStorage
from shared.models.batch_operations import (
    AssetBatchCreateRequest,
    AssetBatchUpdateRequest,
    AssetBatchDeleteRequest,
    TaskBatchCreateRequest
)


@pytest.fixture(scope="function")
async def test_database() -> AsyncGenerator[Database, None]:
    """创建测试数据库实例"""
    database = Database()
    yield database
    # 清理测试数据
    database.devices.clear()
    database.nodes.clear()
    database.jobs.clear()


@pytest.fixture(scope="function")
def test_storage() -> Generator[AuditStorage, None, None]:
    """创建测试审计存储"""
    storage = AuditStorage()
    yield storage
    # 清理测试数据
    storage.clear_all()


@pytest.fixture(scope="function")
async def test_services(test_database, test_storage) -> dict:
    """创建测试服务集合"""
    audit_service = BatchAuditService(storage=test_storage)
    batch_service = BatchOperationService(
        database=test_database,
        audit_service=audit_service
    )

    return {
        "database": test_database,
        "audit_storage": test_storage,
        "audit_service": audit_service,
        "batch_service": batch_service
    }


@pytest.fixture(scope="function")
async def sample_node(test_services) -> dict:
    """创建示例节点数据"""
    services = test_services
    database = services["database"]

    # 创建测试节点
    node_data = {
        "node_id": "test-node-001",
        "hostname": "test-server.local",
        "ip_address": "192.168.1.100",
        "status": "active",
        "last_heartbeat": datetime.now(timezone.utc).isoformat()
    }

    # 注册节点到数据库
    database.add_device("test-node-001", node_data)

    return node_data


@pytest.fixture(scope="function")
async def sample_assets(test_services) -> list:
    """创建示例资产数据"""
    services = test_services
    batch_service = services["batch_service"]

    # 批量创建测试资产
    assets = [
        {"asset_id": f"e2e-asset-{i:03d}", "name": f"E2E Test Asset {i}", "asset_type": "linux_host"}
        for i in range(10)
    ]

    request = AssetBatchCreateRequest(assets=assets)
    await batch_service.create_assets_batch(request)

    # 等待审计记录
    await asyncio.sleep(0.1)

    return assets


class E2ETestHelper:
    """E2E测试辅助类"""

    def __init__(self, services: dict):
        self.services = services
        self.database = services["database"]
        self.audit_service = services["audit_service"]
        self.batch_service = services["batch_service"]

    async def create_test_node(self, node_id: str) -> dict:
        """创建测试节点"""
        node_data = {
            "node_id": node_id,
            "hostname": f"{node_id}.local",
            "ip_address": f"192.168.1.{hash(node_id) % 250 + 1}",
            "status": "active",
            "last_heartbeat": datetime.now(timezone.utc).isoformat()
        }

        self.database.add_device(node_id, node_data)
        return node_data

    async def create_test_assets(self, count: int, prefix: str = "test") -> list:
        """创建测试资产"""
        assets = [
            {
                "asset_id": f"{prefix}-asset-{i:03d}",
                "name": f"{prefix.title()} Asset {i}",
                "asset_type": "linux_host"
            }
            for i in range(count)
        ]

        request = AssetBatchCreateRequest(assets=assets)
        await self.batch_service.create_assets_batch(request)
        await asyncio.sleep(0.1)

        return assets

    async def verify_asset_exists(self, asset_id: str) -> bool:
        """验证资产存在"""
        device = self.database.get_device(asset_id)
        return device is not None

    async def verify_audit_exists(self, operation_id: str) -> bool:
        """验证审计记录存在"""
        audit = await self.audit_service.get_audit_by_operation_id(operation_id)
        return audit is not None

    async def get_asset_audit_history(self, asset_id: str) -> list:
        """获取资产审计历史"""
        return await self.audit_service.get_asset_history(asset_id)

    async def simulate_heartbeat(self, node_id: str) -> bool:
        """模拟心跳发送"""
        node_data = self.database.get_device(node_id)
        if node_data:
            node_data["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
            node_data["status"] = "active"
            return True
        return False

    def cleanup_test_data(self):
        """清理测试数据"""
        self.database.devices.clear()
        self.database.nodes.clear()
        self.database.jobs.clear()


@pytest.fixture(scope="function")
async def e2e_helper(test_services) -> E2ETestHelper:
    """创建E2E测试辅助实例"""
    helper = E2ETestHelper(test_services)
    yield helper
    # 清理测试数据
    helper.cleanup_test_data()


class SmokeTestSuite:
    """冒烟测试套件"""

    def __init__(self, services: dict):
        self.services = services
        self.database = services["database"]
        self.audit_service = services["audit_service"]
        self.batch_service = services["batch_service"]

    async def test_database_basic_operations(self) -> bool:
        """测试数据库基本操作"""
        try:
            # 测试添加设备
            test_device = {
                "name": "Smoke Test Device",
                "type": "linux_host",
                "status": "active"
            }
            self.database.add_device("smoke-test-001", test_device)

            # 测试获取设备
            retrieved = self.database.get_device("smoke-test-001")
            assert retrieved is not None
            assert retrieved["name"] == "Smoke Test Device"

            # 测试更新设备
            self.database.update_device("smoke-test-001", {"status": "inactive"})
            updated = self.database.get_device("smoke-test-001")
            assert updated["status"] == "inactive"

            # 测试列表功能
            devices_list = self.database.list_devices()
            assert len(devices_list) >= 1

            # 清理：标记为已退役
            self.database.update_device("smoke-test-001", {"status": "decommissioned"})

            return True
        except Exception as e:
            print(f"数据库基本操作测试失败: {e}")
            return False

    async def test_batch_service_availability(self) -> bool:
        """测试批量操作服务可用性"""
        try:
            # 测试简单的批量创建
            request = AssetBatchCreateRequest(assets=[
                {"asset_id": "smoke-asset-001", "name": "Smoke Asset", "asset_type": "linux_host"}
            ])
            response = await self.batch_service.create_assets_batch(request)

            assert response is not None
            assert response.operation_id is not None
            assert response.summary.total_items == 1

            return True
        except Exception as e:
            print(f"批量操作服务测试失败: {e}")
            return False

    async def test_audit_service_availability(self) -> bool:
        """测试审计服务可用性"""
        try:
            # 测试审计记录创建
            query_count = self.services["audit_storage"].get_total_count()
            assert isinstance(query_count, int)

            # 测试查询功能
            from shared.models.audit_models import AuditQueryRequest
            query = AuditQueryRequest(page=1, page_size=10)
            response = await self.audit_service.query_audits(query)

            assert response is not None
            assert response.total_count >= 0

            return True
        except Exception as e:
            print(f"审计服务测试失败: {e}")
            return False

    async def test_end_to_end_basic_flow(self) -> bool:
        """测试基本端到端流程"""
        try:
            # 1. 创建资产
            create_request = AssetBatchCreateRequest(assets=[
                {"asset_id": "smoke-e2e-001", "name": "E2E Asset", "asset_type": "linux_host"}
            ])
            create_response = await self.batch_service.create_assets_batch(create_request)

            # 2. 验证创建成功
            assert create_response.summary.successful_items == 1

            # 3. 更新资产
            await asyncio.sleep(0.1)  # 等待审计
            update_request = AssetBatchUpdateRequest(
                asset_ids=["smoke-e2e-001"],
                updates={"status": "active"}
            )
            update_response = await self.batch_service.update_assets_batch(update_request)

            # 4. 验证更新成功
            assert update_response.summary.successful_items == 1

            # 5. 验证审计记录
            await asyncio.sleep(0.1)  # 等待审计
            create_audit = await self.audit_service.get_audit_by_operation_id(create_response.operation_id)
            update_audit = await self.audit_service.get_audit_by_operation_id(update_response.operation_id)

            assert create_audit is not None
            assert update_audit is not None

            return True
        except Exception as e:
            print(f"端到端基本流程测试失败: {e}")
            return False


@pytest.fixture(scope="function")
async def smoke_suite(test_services) -> SmokeTestSuite:
    """创建冒烟测试套件实例"""
    suite = SmokeTestSuite(test_services)
    yield suite


def run_smoke_tests(smoke_suite: SmokeTestSuite) -> dict:
    """运行冒烟测试套件"""
    results = {
        "total_tests": 4,
        "passed_tests": 0,
        "failed_tests": 0,
        "test_results": []
    }

    async def run_tests():
        tests = [
            ("数据库基本操作", smoke_suite.test_database_basic_operations),
            ("批量操作服务可用性", smoke_suite.test_batch_service_availability),
            ("审计服务可用性", smoke_suite.test_audit_service_availability),
            ("端到端基本流程", smoke_suite.test_end_to_end_basic_flow)
        ]

        for test_name, test_func in tests:
            try:
                result = await test_func()
                test_result = {
                    "name": test_name,
                    "passed": result,
                    "error": None
                }

                if result:
                    results["passed_tests"] += 1
                else:
                    results["failed_tests"] += 1

                results["test_results"].append(test_result)

            except Exception as e:
                test_result = {
                    "name": test_name,
                    "passed": False,
                    "error": str(e)
                }
                results["failed_tests"] += 1
                results["test_results"].append(test_result)

    return results


# 简化的同步包装函数
def run_smoke_tests(smoke_suite: SmokeTestSuite):
    """运行冒烟测试套件的同步包装"""
    return run_smoke_tests_async


async def run_smoke_tests_async(smoke_suite: SmokeTestSuite) -> dict:
    """异步运行冒烟测试套件"""
    results = {
        "total_tests": 4,
        "passed_tests": 0,
        "failed_tests": 0,
        "test_results": []
    }

    tests = [
        ("数据库基本操作", smoke_suite.test_database_basic_operations),
        ("批量操作服务可用性", smoke_suite.test_batch_service_availability),
        ("审计服务可用性", smoke_suite.test_audit_service_availability),
        ("端到端基本流程", smoke_suite.test_end_to_end_basic_flow)
    ]

    for test_name, test_func in tests:
        try:
            result = await test_func()
            test_result = {
                "name": test_name,
                "passed": result,
                "error": None
            }

            if result:
                results["passed_tests"] += 1
            else:
                results["failed_tests"] += 1

            results["test_results"].append(test_result)

        except Exception as e:
            test_result = {
                "name": test_name,
                "passed": False,
                "error": str(e)
            }
            results["failed_tests"] += 1
            results["test_results"].append(test_result)

    return results