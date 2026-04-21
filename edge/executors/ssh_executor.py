"""
SSH 任务执行器 (完善版)

实现通过 SSH 协议在远程 Linux 主机上执行命令
包含连接管理、错误处理、审计日志等完整功能
"""

import asyncio
import logging
import threading
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import paramiko
from socket import timeout as socket_timeout

from shared.protocol.error_codes import ErrorCode

logger = logging.getLogger(__name__)


class SSHExecutor:
    """SSH 任务执行器"""

    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str = "root",
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
        timeout: int = 30,
        max_output_size: int = 10 * 1024 * 1024,  # 10MB
        keep_alive: bool = False,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.timeout = timeout
        self.max_output_size = max_output_size
        self.keep_alive = keep_alive

        self.client: Optional[paramiko.SSHClient] = None
        self.is_connected = False
        self.connection_time: Optional[datetime] = None
        self.last_command_time: Optional[datetime] = None

        # 统计信息
        self.stats = {
            "commands_executed": 0,
            "commands_succeeded": 0,
            "commands_failed": 0,
            "total_execution_time": 0.0,
            "connection_errors": 0,
        }

    async def connect(self) -> bool:
        """建立 SSH 连接"""
        try:
            logger.info(f"🔗 正在连接 SSH: {self.username}@{self.host}:{self.port}")

            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # 连接到服务器
            start_time = time.time()
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                key_filename=self.key_filename,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False,
            )

            connection_time = time.time() - start_time
            self.is_connected = True
            self.connection_time = datetime.now(timezone.utc)

            logger.info(f"✅ SSH 连接成功: {self.username}@{self.host} (耗时: {connection_time:.2f}s)")

            # 发送保持存活信号
            if self.keep_alive:
                self._start_keep_alive()

            return True

        except paramiko.AuthenticationException as e:
            logger.error(f"❌ SSH 认证失败: {e}")
            self.stats["connection_errors"] += 1
            return False

        except paramiko.SSHException as e:
            logger.error(f"❌ SSH 连接失败: {e}")
            self.stats["connection_errors"] += 1
            return False

        except Exception as e:
            logger.error(f"❌ 连接异常: {e}")
            self.stats["connection_errors"] += 1
            return False

    def _start_keep_alive(self):
        """启动保持存活线程"""

        def keep_alive_thread():
            while self.is_connected:
                try:
                    if (
                        self.client
                        and self.client.get_transport()
                        and self.client.get_transport().is_active()
                    ):
                        self.client.exec_command('echo "keepalive"', timeout=5)
                        time.sleep(30)  # 每30秒发送一次
                    else:
                        break
                except Exception:
                    break

        thread = threading.Thread(target=keep_alive_thread, daemon=True)
        thread.start()

    async def execute_command(
        self,
        command: str,
        timeout: int = 300,
        environment: Optional[Dict[str, str]] = None,
        work_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行命令"""
        if not self.client or not self.is_connected:
            raise ConnectionError("SSH 客户端未连接")

        logger.info(f"🔧 执行命令: {command} @ {self.host}")
        start_time = time.time()

        # 构建完整命令
        full_command = command
        if work_dir:
            full_command = f"cd {work_dir} && {command}"

        # 添加环境变量
        if environment:
            env_vars = " ".join([f"{k}='{v}'" for k, v in environment.items()])
            full_command = f"{env_vars} {full_command}"

        try:
            # 执行命令
            stdin, stdout, stderr = self.client.exec_command(
                full_command, timeout=timeout, get_pty=False
            )

            # 读取输出 (限制大小)
            stdout_str = ""
            stderr_str = ""

            # 异步读取输出
            def read_output():
                nonlocal stdout_str
                try:
                    while True:
                        line = stdout.readline()
                        if not line:
                            break
                        stdout_str += line
                        # 检查输出大小
                        if len(stdout_str) > self.max_output_size:
                            logger.warning(
                                f"⚠️  输出超过大小限制: {len(stdout_str)} > {self.max_output_size}"
                            )
                            self.client.exec_command("pkill -f -f '{command[:20]}'")  # 终止命令
                            break
                except Exception:
                    pass

            def read_stderr():
                nonlocal stderr_str
                try:
                    while True:
                        line = stderr.readline()
                        if not line:
                            break
                        stderr_str += line
                        if len(stderr_str) > self.max_output_size:
                            break
                except Exception:
                    pass

            # 启动读取线程
            stdout_thread = threading.Thread(target=read_output, daemon=True)
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stdout_thread.start()
            stderr_thread.start()

            # 等待命令完成
            exit_code = stdout.channel.recv_exit_status()

            # 等待输出读取完成
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)

            # 计算执行时间
            execution_time = time.time() - start_time

            # 构建结果
            success = exit_code == 0
            result = {
                "success": success,
                "exit_code": exit_code,
                "stdout": stdout_str.strip(),
                "stderr": stderr_str.strip(),
                "execution_time": round(execution_time, 2),
                "command": command,
                "host": self.host,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # 更新统计
            self.stats["commands_executed"] += 1
            self.stats["total_execution_time"] += execution_time
            if success:
                self.stats["commands_succeeded"] += 1
                logger.info(f"✅ 命令执行成功: {command} (耗时: {execution_time:.2f}s)")
            else:
                self.stats["commands_failed"] += 1
                logger.warning(f"⚠️  命令执行失败: {command}, 退出码: {exit_code}")

            # 更新最后命令时间
            self.last_command_time = datetime.now(timezone.utc)

            return result

        except socket_timeout:
            logger.error(f"❌ 命令执行超时: {command}")
            return {
                "success": False,
                "error": "命令执行超时",
                "exit_code": -1,
                "error_code": ErrorCode.SSH_TIMEOUT.value,
            }

        except paramiko.SSHException as e:
            logger.error(f"❌ SSH 执行异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "exit_code": -1,
                "error_code": ErrorCode.SSH_COMMAND_FAILED.value,
            }

        except Exception as e:
            logger.error(f"❌ 命令执行异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "exit_code": -1,
                "error_code": ErrorCode.SSH_COMMAND_FAILED.value,
            }

    async def execute_script(
        self, script: str, timeout: int = 600, work_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行脚本"""
        logger.info(f"📜 执行脚本 @ {self.host}")

        # 创建临时脚本文件
        temp_script_path = f"/tmp/hermesnexus_script_{int(time.time())}.sh"

        try:
            # 上传脚本
            sftp = self.client.open_sftp()
            with sftp.file(temp_script_path, "w") as f:
                f.write(script)
            sftp.close()

            # 执行脚本
            command = f"bash {temp_script_path}"
            result = await self.execute_command(command, timeout, work_dir=work_dir)

            # 清理临时文件
            try:
                sftp = self.client.open_sftp()
                sftp.remove(temp_script_path)
                sftp.close()
            except Exception:
                pass

            return result

        except Exception as e:
            logger.error(f"❌ 脚本执行失败: {e}")
            return {"success": False, "error": str(e), "exit_code": -1}

    async def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        try:
            result = await self.execute_command("echo 'connection test'", timeout=10)
            return {
                "connected": result["success"],
                "host": self.host,
                "response_time": result.get("execution_time", 0),
                "output": result.get("stdout", ""),
            }
        except Exception as e:
            return {"connected": False, "host": self.host, "error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "host": self.host,
            "username": self.username,
            "is_connected": self.is_connected,
            "connection_time": (self.connection_time.isoformat() if self.connection_time else None),
            "last_command_time": (
                self.last_command_time.isoformat() if self.last_command_time else None
            ),
        }

    async def close(self):
        """关闭连接"""
        try:
            if self.client:
                self.client.close()
                self.is_connected = False
                logger.info(f"🔌 SSH 连接已关闭: {self.username}@{self.host}")
        except Exception as e:
            logger.error(f"❌ 关闭连接异常: {e}")

    def __enter__(self):
        """上下文管理器入口"""
        # 注意：这是同步方法，需要在事件循环中谨慎使用
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        # 创建新的事件循环来运行异步关闭
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.close())
            else:
                loop.run_until_complete(self.close())
        except Exception:
            pass


class SSHExecutorPool:
    """SSH 执行器连接池"""

    def __init__(self, max_connections: int = 5, connection_timeout: int = 30):
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.executors: Dict[str, SSHExecutor] = {}
        self.connection_count: Dict[str, int] = {}

    async def get_executor(
        self,
        host: str,
        port: int = 22,
        username: str = "root",
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
    ) -> Optional[SSHExecutor]:
        """获取SSH执行器"""
        cache_key = f"{username}@{host}:{port}"

        # 检查是否已有连接
        if cache_key in self.executors:
            executor = self.executors[cache_key]
            if executor.is_connected:
                self.connection_count[cache_key] += 1
                logger.debug(f"🔄 复用现有连接: {cache_key}")
                return executor
            else:
                # 移除无效连接
                del self.executors[cache_key]
                del self.connection_count[cache_key]

        # 检查连接数限制
        current_connections = len(self.executors)
        if current_connections >= self.max_connections:
            logger.warning(f"⚠️  连接池已满: {current_connections}/{self.max_connections}")
            # 清理最老的连接
            oldest_key = min(self.connection_count.items(), key=lambda x: x[1])[0]
            if oldest_key in self.executors:
                await self.executors[oldest_key].close()
                del self.executors[oldest_key]
                del self.connection_count[oldest_key]

        # 创建新连接
        executor = SSHExecutor(
            host=host,
            port=port,
            username=username,
            password=password,
            key_filename=key_filename,
        )

        if await executor.connect():
            self.executors[cache_key] = executor
            self.connection_count[cache_key] = 1
            return executor
        else:
            return None

    async def close_all(self):
        """关闭所有连接"""
        for executor in self.executors.values():
            await executor.close()
        self.executors.clear()
        self.connection_count.clear()

    def get_pool_stats(self) -> Dict[str, Any]:
        """获取连接池统计"""
        active_count = sum(1 for executor in self.executors.values() if executor.is_connected)
        return {
            "total_connections": len(self.executors),
            "active_connections": active_count,
            "max_connections": self.max_connections,
            "connections": {k: v.get_stats() for k, v in self.executors.items()},
        }


# 开发测试
async def main():
    """测试函数"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 测试本地连接 (如果可以)
    executor = SSHExecutor(host="localhost", username="current_user", timeout=10)  # 需要根据实际情况修改

    try:
        if await executor.connect():
            # 执行几个测试命令
            test_commands = ["echo 'Hello HermesNexus!'", "uname -a", "date", "uptime"]

            for cmd in test_commands:
                result = await executor.execute_command(cmd)
                print(f"命令: {cmd}")
                print(f"结果: {result['stdout']}")
                print(f"状态: {'成功' if result['success'] else '失败'}")
                print("-" * 50)

            # 显示统计信息
            print("\n📊 执行器统计:")
            stats = executor.get_stats()
            for key, value in stats.items():
                print(f"  {key}: {value}")

    finally:
        await executor.close()


if __name__ == "__main__":
    asyncio.run(main())
