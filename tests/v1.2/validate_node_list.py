#!/usr/bin/env python3
"""
HermesNexus v1.2 节点列表功能验证脚本
不依赖pytest框架，直接验证新功能
"""

import sys
import os
from datetime import datetime, timedelta, timezone

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def test_node_list_models():
    """测试节点列表模型"""
    print("🧪 测试节点列表模型...")

    try:
        from shared.models.node_list import (
            NodeListRequest,
            NodeStatusSummary,
            NodeTaskSummary,
            BatchNodeRequest,
        )

        # 测试NodeListRequest
        request = NodeListRequest(
            page=1, page_size=20, status=["active"], include_heartbeat_stats=True
        )
        assert request.page == 1
        print("  ✅ NodeListRequest 模型测试通过")

        # 测试NodeStatusSummary
        summary = NodeStatusSummary(
            is_online=True,
            is_active=True,
            can_accept_tasks=True,
            health_status="healthy",
        )
        assert summary.health_status == "healthy"
        print("  ✅ NodeStatusSummary 模型测试通过")

        # 测试NodeTaskSummary
        task_summary = NodeTaskSummary(
            total_tasks=100,
            running_tasks=2,
            current_task_load=2,
            max_concurrent_tasks=3,
        )
        assert task_summary.total_tasks == 100
        print("  ✅ NodeTaskSummary 模型测试通过")

        return True

    except Exception as e:
        print(f"  ❌ 模型测试失败: {e}")
        return False


def test_node_identity_models():
    """测试节点身份模型"""
    print("🧪 测试节点身份模型...")

    try:
        from shared.models.node import NodeIdentity, NodeStatus, NodeType

        now = datetime.now(timezone.utc)
        node = NodeIdentity(
            node_id="test-node-001",
            node_name="Test Node",
            node_type=NodeType.PHYSICAL,
            tenant_id="tenant-1",
            region_id="region-1",
            status=NodeStatus.ACTIVE,
            last_heartbeat=now - timedelta(seconds=30),
            max_concurrent_tasks=3,
            registered_at=now - timedelta(days=1),
        )

        assert node.node_id == "test-node-001"
        assert node.is_active() is True
        assert node.can_accept_tasks() is True
        print("  ✅ NodeIdentity 模型测试通过")

        return True

    except Exception as e:
        print(f"  ❌ 节点身份模型测试失败: {e}")
        return False


def test_node_list_service():
    """测试节点列表服务"""
    print("🧪 测试节点列表服务...")

    try:
        from shared.services.node_list_service import NodeListService
        from shared.models.node import NodeIdentity, NodeStatus, NodeType

        service = NodeListService()
        now = datetime.now(timezone.utc)

        # 创建测试节点
        test_node = NodeIdentity(
            node_id="test-node-002",
            node_name="Test Node 2",
            node_type=NodeType.PHYSICAL,
            tenant_id="tenant-1",
            region_id="region-1",
            status=NodeStatus.ACTIVE,
            last_heartbeat=now - timedelta(seconds=45),
            max_concurrent_tasks=3,
            assigned_tasks=["task-001", "task-002"],
            registered_at=now - timedelta(days=2),
        )

        # 测试状态摘要生成
        status_summary = service._get_status_summary_for_node(test_node)
        assert status_summary.is_online is True
        assert status_summary.health_status == "healthy"
        print("  ✅ 状态摘要生成测试通过")

        # 测试任务摘要生成
        task_summary = service._get_task_summary_for_node(test_node)
        assert task_summary.current_task_load == 2
        assert task_summary.max_concurrent_tasks == 3
        print("  ✅ 任务摘要生成测试通过")

        # 测试数据增强
        enhanced_node = service._enhance_node_data(test_node, True, True, True)
        assert "status_summary" in enhanced_node
        assert "task_summary" in enhanced_node
        assert "heartbeat_stats" in enhanced_node
        print("  ✅ 节点数据增强测试通过")

        return True

    except Exception as e:
        print(f"  ❌ 节点列表服务测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_api_integration():
    """测试API集成"""
    print("🧪 测试API集成...")

    try:
        # 测试模型导入
        from shared.models.node_list import NodeListRequest
        from shared.services.node_list_service import get_node_list_service

        # 测试服务实例获取
        service = get_node_list_service()
        assert service is not None
        print("  ✅ 服务实例获取测试通过")

        # 测试API请求模型
        api_request_data = {
            "page": 1,
            "page_size": 20,
            "status": ["active"],
            "include_heartbeat_stats": True,
            "include_task_summary": True,
        }

        request = NodeListRequest(**api_request_data)
        assert request.page == 1
        print("  ✅ API请求模型测试通过")

        return True

    except Exception as e:
        print(f"  ❌ API集成测试失败: {e}")
        return False


def test_ui_compatibility():
    """测试UI兼容性"""
    print("🧪 测试UI兼容性...")

    try:
        from shared.models.node_list import NodeListResponse

        # 模拟API响应数据结构
        response_data = {
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
                    "task_summary": {"running_tasks": 1, "max_concurrent_tasks": 3},
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
            "total_pages": 1,
            "has_next": False,
            "has_prev": False,
            "status_summary": {"active": 1},
            "health_summary": {"healthy": 1},
        }

        response = NodeListResponse(**response_data)
        assert len(response.nodes) == 1
        assert response.total == 1
        print("  ✅ UI响应数据结构测试通过")

        return True

    except Exception as e:
        print(f"  ❌ UI兼容性测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 HermesNexus v1.2 节点列表功能验证\n")

    test_results = []

    # 运行所有测试
    test_results.append(("节点列表模型", test_node_list_models()))
    test_results.append(("节点身份模型", test_node_identity_models()))
    test_results.append(("节点列表服务", test_node_list_service()))
    test_results.append(("API集成", test_api_integration()))
    test_results.append(("UI兼容性", test_ui_compatibility()))

    # 汇总结果
    print(f"\n📊 测试结果汇总:")
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    for name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("🎉 所有测试通过！节点列表功能实现成功。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查实现。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
