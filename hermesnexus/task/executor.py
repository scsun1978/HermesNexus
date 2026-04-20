"""
任务执行引擎
"""
import subprocess
import json
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from .model import Task, TaskStatus
from .manager import TaskManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskExecutor:
    """简单的任务执行引擎"""

    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager

    def execute(self, task: Task, device_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        try:
            logger.info(f"Executing task {task.task_id}: {task.name}")

            # 1. 更新状态为running
            self.task_manager.update_task_status(task.task_id, TaskStatus.RUNNING)

            # 2. 执行命令
            result = self._execute_command(task.command, device_config)

            # 3. 根据执行结果更新任务状态
            if result['success']:
                self.task_manager.update_task_status(
                    task.task_id,
                    TaskStatus.COMPLETED,
                    result=result
                )
                logger.info(f"Task {task.task_id} completed successfully")
            else:
                self.task_manager.update_task_status(
                    task.task_id,
                    TaskStatus.FAILED,
                    result=result
                )
                logger.error(f"Task {task.task_id} failed: {result.get('error', 'Unknown error')}")

            return result

        except Exception as e:
            logger.error(f"Error executing task {task.task_id}: {e}")
            error_result = {
                'success': False,
                'error': str(e),
                'completed_at': datetime.now().isoformat()
            }
            self.task_manager.update_task_status(
                task.task_id,
                TaskStatus.FAILED,
                result=error_result
            )
            return error_result

    def _execute_command(self, command: str, device_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行命令（复用现有SSH机制）"""
        try:
            # 从设备配置中提取SSH连接信息
            host = device_config.get('host', 'localhost')
            port = device_config.get('ssh_port', 22)
            username = device_config.get('ssh_user', 'root')
            password = device_config.get('ssh_password', '')
            private_key_path = device_config.get('ssh_private_key_path')

            # 构建SSH命令
            ssh_command = self._build_ssh_command(host, port, username,
                                                 password, private_key_path, command)

            # 执行命令
            start_time = datetime.now()
            process = subprocess.Popen(
                ssh_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=300)  # 5分钟超时
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 构建结果
            result = {
                'success': process.returncode == 0,
                'exit_code': process.returncode,
                'stdout': stdout,
                'stderr': stderr,
                'duration_seconds': duration,
                'started_at': start_time.isoformat(),
                'completed_at': end_time.isoformat(),
                'command': command,
                'host': host
            }

            if process.returncode != 0:
                result['error'] = f"Command failed with exit code {process.returncode}"

            return result

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Command execution timeout',
                'duration_seconds': 300,
                'completed_at': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'completed_at': datetime.now().isoformat()
            }

    def _build_ssh_command(self, host: str, port: int, username: str,
                          password: str, private_key_path: Optional[str],
                          command: str) -> str:
        """构建SSH命令"""
        # 基础SSH参数
        ssh_parts = [
            'ssh',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'ConnectTimeout=30',
            '-p', str(port),
        ]

        # 使用密钥认证还是密码认证
        if private_key_path:
            ssh_parts.extend(['-i', private_key_path])

        # 添加用户和主机
        ssh_parts.append(f"{username}@{host}")

        # 添加要执行的命令
        ssh_parts.append(command)

        return ' '.join(ssh_parts)

    def execute_local(self, command: str) -> Dict[str, Any]:
        """本地执行命令（用于测试）"""
        try:
            logger.info(f"Executing local command: {command}")

            start_time = datetime.now()
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=60)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                'success': process.returncode == 0,
                'exit_code': process.returncode,
                'stdout': stdout,
                'stderr': stderr,
                'duration_seconds': duration,
                'started_at': start_time.isoformat(),
                'completed_at': end_time.isoformat(),
                'command': command,
                'execution_type': 'local'
            }

            if process.returncode != 0:
                result['error'] = f"Command failed with exit code {process.returncode}"

            return result

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Command execution timeout',
                'duration_seconds': 60,
                'completed_at': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'completed_at': datetime.now().isoformat()
            }


class DeviceConfigBuilder:
    """设备配置构建器"""

    @staticmethod
    def from_node_config(node_config: Dict[str, Any]) -> Dict[str, Any]:
        """从节点配置构建设备配置"""
        return {
            'host': node_config.get('host', node_config.get('ip_address', 'localhost')),
            'ssh_port': node_config.get('ssh_port', 22),
            'ssh_user': node_config.get('ssh_user', 'root'),
            'ssh_password': node_config.get('ssh_password', ''),
            'ssh_private_key_path': node_config.get('ssh_private_key_path'),
            'node_id': node_config.get('node_id'),
            'hostname': node_config.get('hostname', 'unknown')
        }

    @staticmethod
    def local_config() -> Dict[str, Any]:
        """本地执行配置"""
        return {
            'host': 'localhost',
            'execution_type': 'local',
            'description': 'Local execution for testing'
        }