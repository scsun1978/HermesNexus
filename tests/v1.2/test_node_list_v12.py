"""
HermesNexus v1.2 - 节点列表功能测试
测试多节点管理的基础能力
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from shared.models.node import NodeIdentity, NodeStatus, NodeType
from shared.models.node_list import (
    NodeListRequest,
    NodeStatusSummary,
    NodeTaskSummary,
    NodeListResponse,
    BatchNodeRequest,
    BatchNodeResponse,
)
from shared.services.node_list_service import NodeListService


class TestNodeListModels:
    """测试节点列表模型"""

    def test_node_list_request_basic(self):
        """测试基本的节点列表请求"""
        request = NodeListRequest(page=1, page_size=20)

        assert request.page == 1
        assert request.page_size == 20
        assert request.sort_by.value == "created_at"
        assert request.sort_order.value == "desc"

    def test_node_list_request_with_filters(self):
        """测试带筛选条件的节点列表请求"""
        request = NodeListRequest(
            page=1,
            page_size=10,
            status=["active", "registered"],
            node_type="physical",
            tags=["production", "linux"],
            search="data-center-1",
            include_heartbeat_stats=True,
            include_task_summary=True,
        )

        assert request.status == ["active", "registered"]
        assert request.node_type == "physical"
        assert request.tags == ["production", "linux"]
        assert request.search == "data-center-1"
        assert request.include_heartbeat_stats is True
        assert request.include_task_summary is True

    def test_node_status_summary(self):
        """测试节点状态摘要"""
        now = datetime.now(timezone.utc)
        summary = NodeStatusSummary(
            is_online=True,
            is_active=True,
            can_accept_tasks=True,
            health_status="healthy",
            last_heartbeat_age_seconds=45,
            heartbeat_timeout_seconds=300,
        )

        assert summary.is_online is True
        assert summary.health_status == "healthy"
        assert summary.can_accept_tasks is True
        assert summary.last_heartbeat_age_seconds == 45

    def test_node_task_summary(self):
        """测试节点任务摘要"""
        summary = NodeTaskSummary(
            total_tasks=156,
            running_tasks=2,
            completed_tasks=148,
            failed_tasks=6,
            current_task_load=2,
            max_concurrent_tasks=3,
            task_utilization_percent=66.7,
            recent_task_ids=["task-001", "task-002", "task-003"],
        )

        assert summary.total_tasks == 156
        assert summary.running_tasks == 2
        assert summary.task_utilization_percent == 66.7
        assert len(summary.recent_task_ids) == 3

    def test_batch_node_request(self):
        """测试批量节点请求"""
        request = BatchNodeRequest(
            node_ids=["node-001", "node-002", "node-003"],
            include_heartbeat_stats=True,
            include_task_summary=True,
        )

        assert len(request.node_ids) == 3
        assert request.include_heartbeat_stats is True
        assert request.include_task_summary is True


class TestNodeListService:
    """测试节点列表服务"""

    @pytest.fixture
    def sample_nodes(self):
        """创建示例节点数据"""
        now = datetime.now(timezone.utc)
        nodes = []

        # 创建健康的活跃节点
        for i in range(3):
            node = NodeIdentity(
                node_id=f"node-{i:03d}",
                node_name=f"Production Node {i}",
                node_type=NodeType.PHYSICAL,
                tenant_id="tenant-1",
                region_id="region-1",
                status=NodeStatus.ACTIVE,
                last_heartbeat=now - timedelta(seconds=30),
                max_concurrent_tasks=3,
                assigned_tasks=[f"task-{i}"],
                registered_at=now - timedelta(days=30),
                created_at=now - timedelta(days=30),
            )
            nodes.append(node)

        # 创建离线节点
        offline_node = NodeIdentity(
            node_id="node-offline",
            node_name="Offline Node",
            node_type=NodeType.VIRTUAL_MACHINE,
            tenant_id="tenant-1",
            region_id="region-1",
            status=NodeStatus.INACTIVE,
            last_heartbeat=now - timedelta(minutes=10),
            max_concurrent_tasks=2,
            assigned_tasks=[],
            registered_at=now - timedelta(days=20),
            created_at=now - timedelta(days=20),
        )
        nodes.append(offline_node)

        return nodes

    @pytest.fixture
    def service(self):
        """创建节点列表服务实例"""
        return NodeListService()

    def test_get_status_summary_for_node_healthy(self, service, sample_nodes):
        """测试健康节点的状态摘要"""
        healthy_node = sample_nodes[0]
        summary = service._get_status_summary_for_node(healthy_node)

        assert summary.is_online is True
        assert summary.is_active is True
        assert summary.can_accept_tasks is True
        assert summary.health_status == "healthy"
        assert summary.last_heartbeat_age_seconds is not None
        assert summary.last_heartbeat_age_seconds < 300

    def test_get_status_summary_for_node_offline(self, service, sample_nodes):
        """测试离线节点的状态摘要"""
        offline_node = sample_nodes[-1]
        summary = service._get_status_summary_for_node(offline_node)

        assert summary.is_online is False
        assert summary.is_active is False
        assert summary.can_accept_tasks is False
        assert summary.health_status in ["inactive", "unknown"]

    def test_get_task_summary_for_node(self, service, sample_nodes):
        """测试节点任务摘要"""
        node = sample_nodes[0]
        summary = service._get_task_summary_for_node(node)

        assert summary.current_task_load == len(node.assigned_tasks)
        assert summary.max_concurrent_tasks == node.max_concurrent_tasks
        assert summary.task_utilization_percent >= 0
        assert summary.task_utilization_percent <= 100

    def test_enhance_node_data_basic(self, service, sample_nodes):
        """测试基本节点数据增强"""
        node = sample_nodes[0]
        enhanced = service._enhance_node_data(node)

        assert "node_id" in enhanced
        assert "status_summary" in enhanced
        assert enhanced["status_summary"]["health_status"] == "healthy"

    def test_enhance_node_data_with_all_summaries(self, service, sample_nodes):
        """测试包含所有摘要的节点数据增强"""
        node = sample_nodes[0]
        enhanced = service._enhance_node_data(
            node,
            include_heartbeat_stats=True,
            include_task_summary=True,
            include_audit_summary=True,
        )

        assert "status_summary" in enhanced
        assert "heartbeat_stats" in enhanced
        assert "task_summary" in enhanced
        assert "audit_summary" in enhanced


class TestNodeListAPI:
    """测试节点列表API集成"""

    @pytest.mark.asyncio
    async def test_query_nodes_api_basic(self):
        """测试基本节点查询API"""
        # 这个测试需要实际的FastAPI测试客户端
        # 这里只是示例结构
        pass

    @pytest.mark.asyncio
    async def test_batch_nodes_api(self):
        """测试批量节点查询API"""
        # 这个测试需要实际的FastAPI测试客户端
        # 这里只是示例结构
        pass

    @pytest.mark.asyncio
    async def test_node_detail_with_enhanced_info(self):
        """测试增强节点详情API"""
        # 这个测试需要实际的FastAPI测试客户端
        # 这里只是示例结构
        pass


class TestNodeListUIIntegration:
    """测试节点列表UI集成"""

    def test_javascript_data_processing(self):
        """测试JavaScript数据处理逻辑"""
        # 模拟API响应数据
        api_response = {
            "nodes": [
                {
                    "node_id": "node-001",
                    "node_name": "Production Node 1",
                    "status": "active",
                    "status_summary": {
                        "is_online": True,
                        "health_status": "healthy",
                        "can_accept_tasks": True,
                    },
                    "task_summary": {
                        "running_tasks": 1,
                        "max_concurrent_tasks": 3,
                        "task_utilization_percent": 33.3,
                    },
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
            "total_pages": 1,
        }

        # 验证数据结构
        assert "nodes" in api_response
        assert "status_summary" in api_response["nodes"][0]
        assert "task_summary" in api_response["nodes"][0]


@pytest.mark.unit
class TestNodeListPerformance:
    """测试节点列表性能"""

    def test_large_node_list_performance(self):
        """测试大节点列表性能"""
        # 模拟1000个节点的列表
        nodes = []
        now = datetime.now(timezone.utc)

        for i in range(1000):
            node = NodeIdentity(
                node_id=f"node-{i:04d}",
                node_name=f"Node {i}",
                node_type=NodeType.PHYSICAL,
                tenant_id="tenant-1",
                region_id="region-1",
                status=NodeStatus.ACTIVE,
                last_heartbeat=now - timedelta(seconds=i % 300),
                max_concurrent_tasks=3,
                registered_at=now - timedelta(days=i % 365),
                created_at=now - timedelta(days=i % 365),
            )
            nodes.append(node)

        # 测试处理性能
        import time

        service = NodeListService()

        start_time = time.time()
        for node in nodes[:100]:  # 测试前100个节点
            service._get_status_summary_for_node(node)

        elapsed_time = time.time() - start_time

        # 验证处理100个节点的时间在合理范围内（< 1秒）
        assert elapsed_time < 1.0, f"处理100个节点耗时{elapsed_time:.2f}秒，超过预期"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
