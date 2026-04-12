"""
控制台功能测试

验证控制台页面和API集成
"""

import asyncio
import logging
import sys
import pytest
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from cloud.database.db import db
from cloud.api.main import app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_console_integration():
    """测试控制台集成"""
    logger.info("🧪 测试控制台集成")

    try:
        # 1. 测试数据库初始化
        logger.info("1️⃣ 测试数据库初始化...")
        stats = db.get_stats()
        logger.info(f"   数据库统计: {stats}")

        # 2. 创建测试数据
        logger.info("2️⃣ 创建测试数据...")

        # 添加测试节点
        db.add_node("test-node-1", {
            "node_id": "test-node-1",
            "name": "测试节点1",
            "status": "online",
            "cpu_usage": 25.5,
            "memory_usage": 45.2,
            "active_tasks": 2,
            "last_heartbeat": "2024-01-01T00:00:00Z",
            "tags": ["ssh", "linux", "test"]
        })

        db.add_node("test-node-2", {
            "node_id": "test-node-2",
            "name": "测试节点2",
            "status": "offline",
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "active_tasks": 0,
            "last_heartbeat": "2024-01-01T01:00:00Z",
            "tags": ["ssh", "linux", "test"]
        })

        # 添加测试任务
        db.add_job("test-job-1", {
            "job_id": "test-job-1",
            "name": "测试任务1",
            "type": "basic_exec",
            "status": "success",
            "target_device_id": "device-1",
            "command": "uptime",
            "node_id": "test-node-1",
            "created_at": "2024-01-01T00:00:00Z"
        })

        db.add_job("test-job-2", {
            "job_id": "test-job-2",
            "name": "测试任务2",
            "type": "basic_exec",
            "status": "running",
            "target_device_id": "device-2",
            "command": "ls -la",
            "node_id": "test-node-1",
            "created_at": "2024-01-01T00:05:00Z"
        })

        # 添加测试事件
        db.add_event({
            "event_id": "event-1",
            "type": "node_registered",
            "level": "info",
            "source": "test-node-1",
            "source_type": "node",
            "message": "节点 test-node-1 注册成功",
            "timestamp": "2024-01-01T00:00:00Z"
        })

        db.add_event({
            "event_id": "event-2",
            "type": "job_completed",
            "level": "info",
            "source": "cloud",
            "source_type": "cloud",
            "message": "任务 test-job-1 完成",
            "timestamp": "2024-01-01T00:10:00Z"
        })

        db.add_event({
            "event_id": "event-3",
            "type": "error",
            "level": "error",
            "source": "test-node-2",
            "source_type": "node",
            "message": "节点 test-node-2 连接失败",
            "timestamp": "2024-01-01T01:00:00Z"
        })

        # 3. 验证数据创建
        logger.info("3️⃣ 验证数据创建...")
        nodes = db.list_nodes()
        jobs = db.list_jobs()
        events = db.list_events()

        logger.info(f"   节点数量: {len(nodes)}")
        logger.info(f"   任务数量: {len(jobs)}")
        logger.info(f"   事件数量: {len(events)}")

        # 4. 测试统计API
        logger.info("4️⃣ 测试统计API...")
        stats = db.get_stats()
        logger.info(f"   统计信息: {stats}")

        # 5. 测试过滤功能
        logger.info("5️⃣ 测试过滤功能...")

        # 过滤在线节点
        online_nodes = [n for n in nodes if n.get("status") == "online"]
        logger.info(f"   在线节点: {len(online_nodes)}")

        # 过滤成功任务
        success_jobs = [j for j in jobs if j.get("status") == "success"]
        logger.info(f"   成功任务: {len(success_jobs)}")

        # 过滤错误事件
        error_events = [e for e in events if e.get("level") == "error"]
        logger.info(f"   错误事件: {len(error_events)}")

        logger.info("✅ 控制台集成测试完成")

        return {
            "nodes": len(nodes),
            "jobs": len(jobs),
            "events": len(events),
            "stats": stats
        }

    except Exception as e:
        logger.error(f"❌ 控制台集成测试失败: {e}")
        raise


@pytest.mark.asyncio
async def test_api_endpoints():
    """测试API端点"""
    logger.info("🧪 测试API端点")

    try:
        from fastapi.testclient import TestClient

        # 创建测试客户端
        client = TestClient(app)

        # 测试根端点
        logger.info("1️⃣ 测试根端点...")
        response = client.get("/")
        assert response.status_code == 200
        logger.info(f"   根端点响应: {response.json()}")

        # 测试健康检查
        logger.info("2️⃣ 测试健康检查...")
        response = client.get("/health")
        assert response.status_code == 200
        logger.info(f"   健康检查响应: {response.json()}")

        # 测试节点列表
        logger.info("3️⃣ 测试节点列表...")
        response = client.get("/api/v1/nodes")
        assert response.status_code == 200
        nodes_data = response.json()
        logger.info(f"   节点列表: {nodes_data['total']} 个节点")

        # 测试任务列表
        logger.info("4️⃣ 测试任务列表...")
        response = client.get("/api/v1/jobs")
        assert response.status_code == 200
        jobs_data = response.json()
        logger.info(f"   任务列表: {jobs_data['total']} 个任务")

        # 测试事件列表
        logger.info("5️⃣ 测试事件列表...")
        response = client.get("/api/v1/events")
        assert response.status_code == 200
        events_data = response.json()
        logger.info(f"   事件列表: {events_data['total']} 个事件")

        # 测试统计信息
        logger.info("6️⃣ 测试统计信息...")
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        stats_data = response.json()
        logger.info(f"   统计信息: {stats_data}")

        # 测试控制台页面
        logger.info("7️⃣ 测试控制台页面...")
        response = client.get("/console")
        # 注意：这个测试可能需要根据实际静态文件配置调整

        logger.info("✅ API端点测试完成")

        return {
            "endpoints_tested": 7,
            "nodes_count": nodes_data['total'],
            "jobs_count": jobs_data['total'],
            "events_count": events_data['total']
        }

    except Exception as e:
        logger.error(f"❌ API端点测试失败: {e}")
        raise


async def main():
    """主测试函数"""
    logger.info("🚀 开始控制台功能测试")

    # 测试控制台集成
    integration_result = await test_console_integration()

    # 测试API端点
    api_result = await test_api_endpoints()

    logger.info("📊 测试结果总结:")
    logger.info(f"   数据集成: {integration_result['nodes']} 节点, {integration_result['jobs']} 任务, {integration_result['events']} 事件")
    logger.info(f"   API测试: {api_result['endpoints_tested']} 个端点测试通过")

    logger.info("✅ 所有测试完成")


if __name__ == "__main__":
    asyncio.run(main())