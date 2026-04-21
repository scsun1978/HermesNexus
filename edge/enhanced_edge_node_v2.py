#!/usr/bin/env python3
"""
HermesNexus v2.0 Edge节点 - Week 5-6
支持v2任务模型和云边编排
"""

import json
import time
import socket
import subprocess
import requests
import threading
import os
import platform
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

class TaskStatusV2(Enum):
    """v2任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriorityV2(Enum):
    """v2任务优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class EnhancedEdgeNodeV2:
    """v2.0 Edge节点 - 支持任务编排"""

    def __init__(self, node_id: str = "edge-v2-001", cloud_url: str = "http://172.16.100.101:8082"):
        self.node_id = node_id
        self.cloud_url = cloud_url
        self.hostname = socket.gethostname()
        self.ip_address = self._get_local_ip()
        self.running = True
        self.processing_tasks = False
        self.supported_task_types = ["inspection", "restart", "upgrade", "rollback", "custom"]

    def _get_local_ip(self) -> str:
        """获取本地IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def register_with_cloud(self) -> bool:
        """向Cloud API注册节点"""
        try:
            registration_data = {
                "node_id": self.node_id,
                "node_type": "edge",
                "hostname": self.hostname,
                "ip_address": self.ip_address,
                "port": 8081,
                "status": "online",
                "capabilities": {
                    "task_types": self.supported_task_types,
                    "task_models": ["v1", "v2"],  # 支持v1和v2任务模型
                    "batch_support": True,  # 支持批量任务
                    "template_support": True,  # 支持模板驱动
                    "max_concurrent_tasks": 5
                },
                "version": "2.0.0",
                "orchestration_ready": True
            }

            response = requests.post(
                f"{self.cloud_url}/api/v1/nodes/register",
                json=registration_data,
                timeout=10
            )

            if response.status_code == 200:
                print(f"✅ {self.node_id} 注册成功")
                return True
            else:
                print(f"❌ 注册失败: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 注册异常: {e}")
            return False

    def fetch_and_execute_v2_tasks(self):
        """获取并执行v2任务 - Week 5-6核心功能"""
        if not self.running:
            return

        try:
            # 获取分配给本节点的任务
            response = requests.get(
                f"{self.cloud_url}/api/v1/tasks?node_id={self.node_id}&status=pending",
                timeout=10
            )

            if response.status_code != 200:
                return

            tasks_data = response.json()
            tasks = tasks_data.get("tasks", [])

            if not tasks:
                return

            print(f"📋 获取到 {len(tasks)} 个待处理任务")

            for task in tasks:
                if not self.running:
                    break

                # 处理v2任务格式
                if self._is_v2_task(task):
                    self._execute_v2_task(task)
                else:
                    # 向后兼容v1任务
                    self._execute_v1_task(task)

        except Exception as e:
            print(f"❌ 获取任务异常: {e}")

    def _is_v2_task(self, task: Dict[str, Any]) -> bool:
        """判断是否为v2任务"""
        # v2任务特征：包含task_type字段或使用task_id而非job_id
        has_task_type = "task_type" in task
        uses_task_id = "task_id" in task
        uses_job_id = "job_id" in task

        # 如果同时有job_id和task_id，优先认为是v2（混合格式）
        # 如果只有job_id，认为是v1
        # 如果有task_id或task_type，认为是v2
        return uses_task_id or has_task_type or (uses_job_id and "task_type" in task)

    def _execute_v2_task(self, task: Dict[str, Any]):
        """执行v2任务 - Week 5-6新功能"""
        task_id = task.get("task_id") or task.get("id")
        task_type = task.get("task_type", "custom")
        priority = task.get("priority", "medium")
        command = task.get("command", "")

        print(f"🚀 执行v2任务: {task_id} ({task_type}, {priority})")

        # 更新状态为running
        self._update_task_status_v2(task_id, TaskStatusV2.RUNNING)

        try:
            # 执行命令
            start_time = time.time()
            result = self._execute_command(command)
            duration = time.time() - start_time

            # 构建执行结果
            execution_result = {
                "task_id": task_id,
                "status": TaskStatusV2.COMPLETED.value,
                "result": {
                    "success": result["success"],
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "exit_code": result.get("exit_code", 0),
                    "duration_seconds": duration,
                    "node_id": self.node_id,
                    "hostname": self.hostname,
                    "completed_at": datetime.now().isoformat()
                }
            }

            # 上报结果
            self._report_task_result_v2(task_id, execution_result)
            print(f"✅ 任务完成: {task_id}")

        except Exception as e:
            print(f"❌ 任务执行失败: {task_id} - {e}")
            error_result = {
                "task_id": task_id,
                "status": TaskStatusV2.FAILED.value,
                "error": str(e),
                "node_id": self.node_id,
                "completed_at": datetime.now().isoformat()
            }
            self._report_task_result_v2(task_id, error_result)

    def _execute_v1_task(self, task: Dict[str, Any]):
        """执行v1任务（向后兼容）"""
        job_id = task.get("job_id")
        command = task.get("command", "")

        print(f"🔄 执行v1任务: {job_id}")

        try:
            result = self._execute_command(command)

            # 上报v1格式结果
            report_data = {
                "job_id": job_id,
                "node_id": self.node_id,
                "status": "completed" if result["success"] else "failed",
                "result": result
            }

            requests.post(
                f"{self.cloud_url}/api/v1/jobs/{job_id}/result",
                json=report_data,
                timeout=10
            )

        except Exception as e:
            print(f"❌ v1任务执行失败: {job_id} - {e}")

    def _execute_command(self, command: str) -> Dict[str, Any]:
        """执行命令（生产安全模式）"""
        try:
            # 生产安全处理：强制使用安全模式
            import shlex

            # 尝试安全解析命令
            try:
                command_args = shlex.split(command)
                logger.info(f"Using safe execution mode for: {command}")
            except ValueError as e:
                # 解析失败 - 拒绝执行
                error_msg = f"Command parsing failed (contains shell syntax): {command}. Error: {e}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "reason": "UNSAFE_COMMAND_SYNTAX",
                    "duration": 0
                }

            start_time = time.time()
            process = subprocess.Popen(
                command_args,
                shell=False,  # 强制安全模式
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=300)  # 5分钟超时
            duration = time.time() - start_time

            return {
                "success": process.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": process.returncode,
                "duration": duration,
                "security_mode": "enforced"  # 标记强制安全模式
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command execution timeout",
                "duration": 300
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _update_task_status_v2(self, task_id: str, status: TaskStatusV2):
        """更新v2任务状态"""
        try:
            status_data = {
                "task_id": task_id,
                "status": status.value,
                "node_id": self.node_id,
                "timestamp": datetime.now().isoformat()
            }

            requests.post(
                f"{self.cloud_url}/api/v2/tasks/{task_id}/status",
                json=status_data,
                timeout=10
            )

        except Exception as e:
            print(f"❌ 更新任务状态失败: {e}")

    def _report_task_result_v2(self, task_id: str, result: Dict[str, Any]):
        """上报v2任务结果"""
        try:
            requests.post(
                f"{self.cloud_url}/api/v2/tasks/{task_id}/result",
                json=result,
                timeout=10
            )

        except Exception as e:
            print(f"❌ 上报任务结果失败: {e}")

    def send_heartbeat(self):
        """发送心跳"""
        try:
            heartbeat_data = {
                "node_id": self.node_id,
                "hostname": self.hostname,
                "ip_address": self.ip_address,
                "status": "online",
                "processing_tasks": self.processing_tasks,
                "supported_task_types": self.supported_task_types,
                "version": "2.0.0",
                "model": "v2",
                "timestamp": datetime.now().isoformat()
            }

            response = requests.post(
                f"{self.cloud_url}/api/v1/nodes/heartbeat",
                json=heartbeat_data,
                timeout=5
            )

            if response.status_code == 200:
                print(f"💓 心跳成功: {self.node_id}")
            else:
                print(f"💓 心跳失败: {response.status_code}")

        except Exception as e:
            print(f"💓 心跳异常: {e}")

    def start_task_processing_loop(self):
        """启动任务处理循环"""
        print(f"🚀 启动v2任务处理循环: {self.node_id}")

        heartbeat_counter = 0

        while self.running:
            try:
                # 每10次循环发送一次心跳
                heartbeat_counter += 1
                if heartbeat_counter >= 10:
                    self.send_heartbeat()
                    heartbeat_counter = 0

                # 获取并执行任务
                self.fetch_and_execute_v2_tasks()

                # 休眠5秒
                time.sleep(5)

            except KeyboardInterrupt:
                print(f"🛑 收到停止信号: {self.node_id}")
                break
            except Exception as e:
                print(f"❌ 任务处理异常: {e}")
                time.sleep(10)  # 出错后等待更长时间

    def stop(self):
        """停止节点"""
        print(f"🛑 停止节点: {self.node_id}")
        self.running = False

# MVP示例：启动v2边缘节点
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HermesNexus v2.0 Edge节点")
    parser.add_argument("--node-id", default="edge-v2-001", help="节点ID")
    parser.add_argument("--cloud-url", default="http://172.16.100.101:8082", help="云端API地址")
    parser.add_argument("--test-mode", action="store_true", help="测试模式（不注册到云端）")

    args = parser.parse_args()

    # 创建v2边缘节点
    edge_node = EnhancedEdgeNodeV2(args.node_id, args.cloud_url)

    if not args.test_mode:
        # 注册到云端
        if edge_node.register_with_cloud():
            print("✅ v2边缘节点启动成功")
            # 启动任务处理循环
            edge_node.start_task_processing_loop()
        else:
            print("❌ v2边缘节点注册失败")
            exit(1)
    else:
        print("🧪 测试模式：v2边缘节点已创建，跳过云端注册")
        print(f"节点ID: {edge_node.node_id}")
        print(f"支持的任务类型: {edge_node.supported_task_types}")
        print(f"任务模型: v1, v2")
        print(f"批量任务支持: True")