"""
边缘节点云边通信

实现与云端API的通信功能
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
import aiohttp
from datetime import datetime, timezone

from shared.protocol.messages import (
    MessageType,
    RegisterMessage,
    HeartbeatMessage,
    TaskMessage,
    ResultMessage,
    ErrorMessage,
)
from shared.protocol.error_codes import ErrorCode, ErrorDetail
from shared.schemas.models import NodeStatus, JobStatus

logger = logging.getLogger(__name__)


class CloudClient:
    """云端API客户端"""

    def __init__(
        self, cloud_server_url: str, api_key: str, node_id: str, timeout: int = 30
    ):
        self.cloud_server_url = cloud_server_url.rstrip("/")
        self.api_key = api_key
        self.node_id = node_id
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        """启动客户端"""
        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        self.session = aiohttp.ClientSession(
            base_url=self.cloud_server_url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=self.timeout),
        )
        logger.info(f"✅ 云端客户端已启动: {self.cloud_server_url}")

    async def stop(self):
        """停止客户端"""
        if self.session:
            await self.session.close()
            logger.info("🔌 云端客户端已停止")

    async def register_node(self, node_name: str, capabilities: Dict[str, Any]) -> bool:
        """注册节点到云端"""
        try:
            register_msg = RegisterMessage(
                node_id=self.node_id, node_name=node_name, capabilities=capabilities
            )

            # 发送注册请求
            response = await self.session.post(
                f"/api/v1/nodes/{self.node_id}/register", json=register_msg.to_dict()
            )

            if response.status == 200:
                logger.info(f"✅ 节点注册成功: {self.node_id}")
                return True
            else:
                error_text = await response.text()
                logger.error(f"❌ 节点注册失败: {response.status} - {error_text}")
                return False

        except Exception as e:
            logger.error(f"❌ 节点注册异常: {e}")
            return False

    async def send_heartbeat(self, heartbeat_data: Dict[str, Any]) -> bool:
        """发送心跳到云端"""
        try:
            heartbeat = HeartbeatMessage(
                node_id=self.node_id,
                message_id=f"heartbeat-{datetime.now(timezone.utc).timestamp()}",
                **heartbeat_data,
            )

            response = await self.session.post(
                f"/api/v1/nodes/{self.node_id}/heartbeat", json=heartbeat.to_dict()
            )

            if response.status == 200:
                logger.debug(f"💓 心跳发送成功: {self.node_id}")
                return True
            else:
                logger.warning(f"⚠️  心跳发送失败: {response.status}")
                return False

        except Exception as e:
            logger.error(f"❌ 心跳发送异常: {e}")
            return False

    async def fetch_tasks(self) -> List[TaskMessage]:
        """从云端获取待处理任务"""
        try:
            response = await self.session.get(f"/api/v1/nodes/{self.node_id}/tasks")

            if response.status == 200:
                data = await response.json()
                tasks_data = data.get("tasks", [])

                tasks = []
                for task_data in tasks_data:
                    task = TaskMessage(
                        node_id=self.node_id,
                        task_id=task_data.get("task_id", ""),
                        job_id=task_data.get("job_id", ""),
                        task_type=task_data.get("task_type", "exec"),
                        target_device=task_data.get("target_device_id", ""),
                        target_host=task_data.get("target_host", ""),
                        command=task_data.get("command", ""),
                        script=task_data.get("script", ""),
                        parameters=task_data.get("parameters", {}),
                        timeout=task_data.get("timeout", 300),
                        priority=task_data.get("priority", "normal"),
                        created_by=task_data.get("created_by", "system"),
                    )
                    tasks.append(task)

                if tasks:
                    logger.info(f"📥 获取到 {len(tasks)} 个待处理任务")
                return tasks

            else:
                logger.warning(f"⚠️  获取任务失败: {response.status}")
                return []

        except Exception as e:
            logger.error(f"❌ 获取任务异常: {e}")
            return []

    async def report_result(self, result: ResultMessage) -> bool:
        """向云端报告任务执行结果"""
        try:
            response = await self.session.post(
                f"/api/v1/nodes/{self.node_id}/tasks/{result.task_id}/result",
                json=result.to_dict(),
            )

            if response.status == 200:
                logger.info(f"✅ 任务结果上报成功: {result.task_id}")
                return True
            else:
                error_text = await response.text()
                logger.error(f"❌ 任务结果上报失败: {response.status} - {error_text}")
                return False

        except Exception as e:
            logger.error(f"❌ 任务结果上报异常: {e}")
            return False

    async def report_error(self, error: ErrorMessage) -> bool:
        """向云端报告错误"""
        try:
            response = await self.session.post(
                f"/api/v1/nodes/{self.node_id}/errors", json=error.to_dict()
            )

            if response.status == 200:
                logger.info(f"✅ 错误上报成功: {error.error_code}")
                return True
            else:
                logger.warning(f"⚠️  错误上报失败: {response.status}")
                return False

        except Exception as e:
            logger.error(f"❌ 错误上报异常: {e}")
            return False
