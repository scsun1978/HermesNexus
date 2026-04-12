"""
边缘节点运行时核心

实现边缘节点的主要功能：注册、心跳、任务执行
"""

import asyncio
import logging
import psutil
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from shared.protocol.messages import (
    TaskMessage,
    ResultMessage,
)
from shared.protocol.error_codes import ErrorCode
from shared.schemas.models import NodeStatus, JobStatus, TaskType

from ..cloud.client import CloudClient
from ..storage.storage import EdgeStorage
from ..executors.ssh_executor import SSHExecutorPool
from ..audit.audit import AuditLogger

logger = logging.getLogger(__name__)


class EdgeRuntime:
    """边缘节点运行时"""

    def __init__(
        self,
        node_id: str,
        node_name: str,
        cloud_server_url: str,
        api_key: str,
        heartbeat_interval: int = 30,
    ):
        self.node_id = node_id
        self.node_name = node_name
        self.cloud_server_url = cloud_server_url
        self.api_key = api_key
        self.heartbeat_interval = heartbeat_interval
        self.status = NodeStatus.OFFLINE
        self.running = False

        # 组件
        self.cloud_client: Optional[CloudClient] = None
        self.storage: Optional[EdgeStorage] = None
        self.audit_logger: Optional[AuditLogger] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.task_processor_task: Optional[asyncio.Task] = None

        # SSH 执行器连接池
        self.ssh_pool: Optional[SSHExecutorPool] = None

        # 统计信息
        self.stats = {
            "tasks_processed": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
            "started_at": None,
        }

    async def start(self):
        """启动边缘节点"""
        logger.info(f"🚀 启动边缘节点: {self.node_id}")

        try:
            # 初始化组件
            self.cloud_client = CloudClient(
                self.cloud_server_url, self.api_key, self.node_id
            )
            await self.cloud_client.start()

            self.storage = EdgeStorage()
            logger.info("📦 本地存储已初始化")

            self.audit_logger = AuditLogger()
            logger.info("📝 审计日志已初始化")

            # 初始化SSH连接池
            self.ssh_pool = SSHExecutorPool(max_connections=5)
            logger.info("🔌 SSH连接池已初始化")

            # 注册到云端
            capabilities = {
                "protocols": ["ssh"],
                "device_types": ["linux_host"],
                "max_concurrent_tasks": 5,
                "version": "0.1.0",
            }

            if await self.register(capabilities):
                self.status = NodeStatus.ONLINE
                self.stats["started_at"] = datetime.now(timezone.utc).isoformat()

                # 启动后台任务
                self.running = True
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                self.task_processor_task = asyncio.create_task(
                    self._task_processor_loop()
                )

                logger.info(f"✅ 边缘节点启动完成: {self.node_id}")
            else:
                logger.error(f"❌ 节点注册失败: {self.node_id}")
                raise Exception("节点注册失败")

        except Exception as e:
            logger.error(f"❌ 启动边缘节点失败: {e}")
            raise

    async def stop(self):
        """停止边缘节点"""
        logger.info(f"🛑 停止边缘节点: {self.node_id}")

        self.running = False

        # 取消后台任务
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        if self.task_processor_task:
            self.task_processor_task.cancel()
            try:
                await self.task_processor_task
            except asyncio.CancelledError:
                pass

        # 关闭SSH连接池
        if self.ssh_pool:
            await self.ssh_pool.close_all()

        # 关闭客户端
        if self.cloud_client:
            await self.cloud_client.stop()

        logger.info(f"✅ 边缘节点已停止: {self.node_id}")

    async def register(self, capabilities: Dict[str, Any]) -> bool:
        """注册到云端"""
        logger.info(f"📝 注册到云端: {self.node_id}")

        success = await self.cloud_client.register_node(self.node_name, capabilities)

        if success:
            logger.info(f"✅ 注册成功: {self.node_id}")
            return True
        else:
            logger.error(f"❌ 注册失败: {self.node_id}")
            return False

    async def _heartbeat_loop(self):
        """心跳循环"""
        while self.running:
            try:
                await self._send_heartbeat()
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 心跳发送失败: {e}")
                await asyncio.sleep(5)  # 出错后等待5秒重试

    async def _send_heartbeat(self):
        """发送心跳"""
        logger.debug(f"💓 发送心跳: {self.node_id}")

        # 获取系统信息
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_info = psutil.virtual_memory()
        memory_usage = memory_info.percent

        # 获取任务统计
        storage_stats = self.storage.get_stats() if self.storage else {}
        active_tasks = storage_stats.get("active_tasks", 0)

        heartbeat_data = {
            "status": self.status.value,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "active_tasks": active_tasks,
        }

        success = await self.cloud_client.send_heartbeat(heartbeat_data)

        if not success:
            logger.warning(f"⚠️  心跳发送失败: {self.node_id}")
            self.status = NodeStatus.ERROR
        else:
            if self.status == NodeStatus.ERROR:
                self.status = NodeStatus.ONLINE

    async def _task_processor_loop(self):
        """任务处理循环"""
        while self.running:
            try:
                # 从云端获取任务
                tasks = await self.cloud_client.fetch_tasks()

                # 处理每个任务
                for task in tasks:
                    await self._process_single_task(task)

                # 等待一段时间再检查
                await asyncio.sleep(10)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 任务处理异常: {e}")
                await asyncio.sleep(10)  # 出错后等待10秒重试

    async def _process_single_task(self, task: TaskMessage):
        """处理单个任务"""
        task_id = task.task_id

        try:
            logger.info(f"📋 开始处理任务: {task_id}")

            # 保存任务到本地存储
            if not self.storage.add_task(task):
                logger.error(f"❌ 保存任务失败: {task_id}")
                return

            # 更新任务状态为运行中
            self.storage.update_task_status(task_id, JobStatus.RUNNING)

            # 执行任务
            result = await self._execute_task(task)

            # 保存结果
            self.storage.save_result(result)

            # 上报结果到云端
            await self.cloud_client.report_result(result)

            # 更新统计
            self.stats["tasks_processed"] += 1
            if result.status == JobStatus.SUCCESS.value:
                self.stats["tasks_succeeded"] += 1
            else:
                self.stats["tasks_failed"] += 1

            logger.info(f"✅ 任务处理完成: {task_id} -> {result.status}")

        except Exception as e:
            logger.error(f"❌ 任务处理异常: {task_id} - {e}")
            # 创建失败结果
            error_result = ResultMessage(
                node_id=self.node_id,
                task_id=task_id,
                job_id=task.job_id,
                status=JobStatus.FAILED.value,
                error=str(e),
                error_code=ErrorCode.TASK_EXECUTION_FAILED.value,
                execution_time=0.0,
            )
            await self.cloud_client.report_result(error_result)

    async def _execute_task(self, task: TaskMessage) -> ResultMessage:
        """执行任务"""
        start_time = datetime.now(timezone.utc)

        try:
            if task.task_type == TaskType.EXEC:
                return await self._execute_command(task)
            elif task.task_type == TaskType.SCRIPT:
                return await self._execute_script(task)
            else:
                raise ValueError(f"不支持的任务类型: {task.task_type}")

        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            return ResultMessage(
                node_id=self.node_id,
                task_id=task.task_id,
                job_id=task.job_id,
                status=JobStatus.FAILED.value,
                error=str(e),
                error_code=ErrorCode.TASK_EXECUTION_FAILED.value,
                execution_time=execution_time,
            )

    async def _execute_command(self, task: TaskMessage) -> ResultMessage:
        """执行命令"""
        logger.info(f"🔧 执行命令: {task.command} on {task.target_host}")

        # 从任务参数获取认证信息
        parameters = task.parameters or {}
        ssh_username = parameters.get("ssh_username", "root")
        ssh_password = parameters.get("ssh_password")
        ssh_key_path = parameters.get("ssh_key_path")

        # 从连接池获取SSH执行器
        executor = await self.ssh_pool.get_executor(
            host=task.target_host,
            port=task.target_port,
            username=ssh_username,
            password=ssh_password,
            key_filename=ssh_key_path,
        )

        if not executor:
            error_msg = f"无法获取SSH连接: {task.target_host}"
            logger.error(f"❌ {error_msg}")

            # 记录审计日志
            if self.audit_logger:
                self.audit_logger.log_ssh_connection(
                    host=task.target_host,
                    username=ssh_username,
                    success=False,
                    error_message=error_msg,
                )

            raise Exception(error_msg)

        try:
            # 记录连接审计
            if self.audit_logger:
                self.audit_logger.log_ssh_connection(
                    host=task.target_host, username=ssh_username, success=True
                )

            # 执行命令
            start_time = datetime.now(timezone.utc)
            exec_result = await executor.execute_command(task.command, task.timeout)
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            # 记录命令审计
            if self.audit_logger:
                self.audit_logger.log_ssh_command(
                    host=task.target_host, command=task.command, result=exec_result
                )

            # 构建结果
            if exec_result["success"]:
                return ResultMessage(
                    node_id=self.node_id,
                    task_id=task.task_id,
                    job_id=task.job_id,
                    status=JobStatus.SUCCESS.value,
                    stdout=exec_result.get("stdout", ""),
                    stderr=exec_result.get("stderr", ""),
                    exit_code=exec_result.get("exit_code", 0),
                    execution_time=execution_time,
                    started_at=start_time.isoformat(),
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    metadata={
                        "host": task.target_host,
                        "command": task.command,
                        "executor_stats": executor.get_stats(),
                    },
                )
            else:
                return ResultMessage(
                    node_id=self.node_id,
                    task_id=task.task_id,
                    job_id=task.job_id,
                    status=JobStatus.FAILED.value,
                    error=exec_result.get("error", "命令执行失败"),
                    error_code=exec_result.get("error_code"),
                    stdout=exec_result.get("stdout", ""),
                    stderr=exec_result.get("stderr", ""),
                    exit_code=exec_result.get("exit_code", -1),
                    execution_time=execution_time,
                    started_at=start_time.isoformat(),
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )

        except Exception as e:
            logger.error(f"❌ 命令执行异常: {e}")
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            return ResultMessage(
                node_id=self.node_id,
                task_id=task.task_id,
                job_id=task.job_id,
                status=JobStatus.FAILED.value,
                error=str(e),
                error_code=ErrorCode.SSH_COMMAND_FAILED.value,
                execution_time=execution_time,
                started_at=start_time.isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
            )

    async def _execute_script(self, task: TaskMessage) -> ResultMessage:
        """执行脚本"""
        # TODO: 实现脚本执行
        return ResultMessage(
            node_id=self.node_id,
            task_id=task.task_id,
            job_id=task.job_id,
            status=JobStatus.FAILED.value,
            error="脚本执行功能暂未实现",
            execution_time=0.0,
        )


# 开发测试
async def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    runtime = EdgeRuntime(
        node_id="edge-node-1",
        node_name="开发测试边缘节点",
        cloud_server_url="http://localhost:8080",
        api_key="dev_api_key_change_in_production",
    )

    try:
        await runtime.start()
        logger.info("🔄 边缘节点正在运行，按 Ctrl+C 停止...")

        # 保持运行
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("🛑 收到停止信号")
    finally:
        await runtime.stop()
        logger.info("👋 边缘节点已退出")


if __name__ == "__main__":
    asyncio.run(main())
