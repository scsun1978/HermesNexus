#!/usr/bin/env python3
"""
HermesNexus v1.2.0 完整版Edge节点
修复API契约匹配，实现完整的云边任务执行链路
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

class EnhancedEdgeNode:
    """增强版Edge节点 - 完整云边协同"""

    def __init__(self, node_id: str = "edge-test-001", cloud_url: str = "http://172.16.100.101:8082"):
        self.node_id = node_id
        self.cloud_url = cloud_url
        self.hostname = socket.gethostname()
        self.ip_address = self._get_local_ip()
        self.running = True
        self.processing_tasks = False

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
                    "ssh_execution": True,
                    "command_timeout": 300,
                    "max_concurrent_tasks": 5
                },
                "metadata": {
                    "os_version": platform.platform(),
                    "python_version": platform.python_version(),
                    "registration_time": datetime.now().isoformat()
                }
            }

            response = requests.post(
                f"{self.cloud_url}/api/nodes/register",
                json=registration_data,
                timeout=10
            )

            if response.status_code == 200:
                print(f"✅ 节点注册成功: {self.node_id}")
                return True
            else:
                print(f"❌ 节点注册失败: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ 节点注册异常: {str(e)}")
            return False

    def send_heartbeat(self) -> bool:
        """发送心跳到Cloud API"""
        try:
            heartbeat_data = {
                "node_id": self.node_id,
                "timestamp": datetime.now().isoformat(),
                "status": "online",
                "system_info": {
                    "cpu_percent": self._get_cpu_usage(),
                    "memory_percent": self._get_memory_usage(),
                    "disk_usage": self._get_disk_usage()
                }
            }

            response = requests.post(
                f"{self.cloud_url}/api/nodes/heartbeat",
                json=heartbeat_data,
                timeout=5
            )

            return response.status_code == 200

        except Exception as e:
            print(f"⚠️ 心跳发送失败: {str(e)}")
            return False

    def fetch_pending_tasks(self) -> List[Dict]:
        """获取待执行的任务"""
        try:
            # 获取所有任务
            response = requests.get(
                f"{self.cloud_url}/api/jobs",
                timeout=10
            )

            if response.status_code == 200:
                all_jobs = response.json().get("jobs", [])

                # 筛选出分配给此节点且状态为pending的任务
                pending_tasks = [
                    job for job in all_jobs
                    if job.get("target_node_id") == self.node_id
                    and job.get("status") == "pending"
                ]

                return pending_tasks
            else:
                print(f"⚠️ 获取任务失败: {response.status_code}")
                return []

        except Exception as e:
            print(f"⚠️ 获取任务异常: {str(e)}")
            return []

    def execute_task(self, task: Dict) -> Dict[str, Any]:
        """执行任务"""
        job_id = task.get("job_id")
        command = task.get("command", "")

        print(f"🔄 执行任务: {job_id}")
        print(f"   命令: {command}")

        execution_result = {
            "job_id": job_id,
            "node_id": self.node_id,
            "started_at": datetime.now().isoformat(),
            "status": "running",
            "result": None
        }

        try:
            # 执行命令
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            execution_result.update({
                "status": "completed" if result.returncode == 0 else "failed",
                "result": {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode,
                    "completed_at": datetime.now().isoformat()
                },
                "completed_at": datetime.now().isoformat()
            })

            if result.returncode == 0:
                print(f"✅ 任务执行成功: {job_id}")
            else:
                print(f"❌ 任务执行失败: {job_id} - 退出码: {result.returncode}")

        except subprocess.TimeoutExpired:
            execution_result.update({
                "status": "failed",
                "result": {
                    "success": False,
                    "stdout": "",
                    "stderr": "命令执行超时",
                    "return_code": -1,
                    "completed_at": datetime.now().isoformat()
                },
                "completed_at": datetime.now().isoformat()
            })
            print(f"❌ 任务执行超时: {job_id}")

        except Exception as e:
            execution_result.update({
                "status": "failed",
                "result": {
                    "success": False,
                    "stdout": "",
                    "stderr": str(e),
                    "return_code": -1,
                    "completed_at": datetime.now().isoformat()
                },
                "completed_at": datetime.now().isoformat()
            })
            print(f"❌ 任务执行异常: {job_id} - {str(e)}")

        return execution_result

    def report_task_result(self, execution_result: Dict) -> bool:
        """将任务执行结果写回Cloud API"""
        try:
            job_id = execution_result.get("job_id")

            # 准备状态更新数据
            status_update = {
                "status": execution_result.get("status"),
                "result": execution_result.get("result"),
                "completed_at": execution_result.get("completed_at")
            }

            # 如果有开始时间，也包含在更新中
            if execution_result.get("started_at"):
                status_update["started_at"] = execution_result["started_at"]

            print(f"📝 回写任务结果: {job_id}")
            print(f"   状态: {status_update.get('status')}")

            # 调用Cloud API的PATCH接口更新任务状态
            response = requests.patch(
                f"{self.cloud_url}/api/jobs/{job_id}/status",
                json=status_update,
                timeout=10
            )

            if response.status_code == 200:
                print(f"✅ 任务结果回写成功: {job_id}")
                return True
            else:
                print(f"⚠️ 任务结果回写失败: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ 结果回写异常: {str(e)}")
            # 即使回写失败，也记录到本地日志
            print(f"   本地记录: {execution_result}")
            return False

    def task_processing_loop(self):
        """任务处理循环"""
        print(f"🔄 启动任务处理循环...")

        while self.running:
            try:
                # 获取待执行任务
                pending_tasks = self.fetch_pending_tasks()

                if pending_tasks:
                    print(f"📋 发现 {len(pending_tasks)} 个待执行任务")

                    # 逐个执行任务
                    for task in pending_tasks:
                        if not self.running:
                            break

                        # 执行任务
                        execution_result = self.execute_task(task)

                        # 回写结果
                        self.report_task_result(execution_result)

                        # 任务间间隔
                        time.sleep(1)

                # 等待下一轮轮询
                time.sleep(10)  # 每10秒轮询一次

            except Exception as e:
                print(f"❌ 任务处理异常: {str(e)}")
                time.sleep(5)  # 异常后等待5秒重试

    def _get_cpu_usage(self) -> float:
        """获取CPU使用率"""
        try:
            with open('/proc/loadavg', 'r') as f:
                load = f.read().split()[0]
                return min(float(load) * 100, 100)  # 限制在100%以内
        except:
            return 0.0

    def _get_memory_usage(self) -> float:
        """获取内存使用率"""
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
                total = int([line for line in meminfo.split('\n') if 'MemTotal' in line][0].split()[1])
                free = int([line for line in meminfo.split('\n') if 'MemFree' in line][0].split()[1])
                return ((total - free) / total) * 100
        except:
            return 0.0

    def _get_disk_usage(self) -> float:
        """获取磁盘使用率"""
        try:
            stat = os.statvfs('/')
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            return ((total - free) / total) * 100
        except:
            return 0.0

    def start_edge_server(self, port: int = 8081):
        """启动Edge HTTP服务器和任务处理"""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler

            class EdgeHTTPRequestHandler(BaseHTTPRequestHandler):
                def __init__(self, *args, edge_node=None, **kwargs):
                    self.edge_node = edge_node
                    super().__init__(*args, **kwargs)

                def do_GET(self):
                    if self.path == '/health':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        health_data = {
                            "status": "healthy",
                            "node_id": self.edge_node.node_id,
                            "timestamp": datetime.now().isoformat(),
                            "cloud_url": self.edge_node.cloud_url,
                            "processing_tasks": self.edge_node.processing_tasks
                        }
                        self.wfile.write(json.dumps(health_data).encode())

                    elif self.path == '/status':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        status_data = {
                            "node_id": self.edge_node.node_id,
                            "hostname": self.edge_node.hostname,
                            "ip_address": self.edge_node.ip_address,
                            "cpu_usage": self.edge_node._get_cpu_usage(),
                            "memory_usage": self.edge_node._get_memory_usage(),
                            "disk_usage": self.edge_node._get_disk_usage(),
                            "processing_tasks": self.edge_node.processing_tasks
                        }
                        self.wfile.write(json.dumps(status_data).encode())

                    elif self.path == '/tasks':
                        # 显示当前任务处理状态
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        tasks_info = {
                            "node_id": self.edge_node.node_id,
                            "processing": self.edge_node.processing_tasks,
                            "cloud_url": self.edge_node.cloud_url,
                            "timestamp": datetime.now().isoformat()
                        }
                        self.wfile.write(json.dumps(tasks_info).encode())

                    else:
                        self.send_response(404)
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        error_msg = {"error": "Not Found", "path": self.path}
                        self.wfile.write(json.dumps(error_msg).encode())

                def log_message(self, format, *args):
                    # 简化日志输出
                    pass

            def handler(*args, **kwargs):
                EdgeHTTPRequestHandler(*args, edge_node=self, **kwargs)

            server = HTTPServer(('0.0.0.0', port), handler)
            print(f"🚀 HermesNexus v1.2.0 Edge节点启动")
            print(f"📍 节点ID: {self.node_id}")
            print(f"🌐 Cloud API: {self.cloud_url}")
            print(f"💚 HTTP服务: http://0.0.0.0:{port}")

            # 启动心跳线程
            heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                daemon=True,
                name="HeartbeatThread"
            )
            heartbeat_thread.start()

            # 启动任务处理线程
            task_thread = threading.Thread(
                target=self.task_processing_loop,
                daemon=True,
                name="TaskProcessingThread"
            )
            task_thread.start()

            print(f"📊 心跳线程已启动 (30秒间隔)")
            print(f"🔄 任务处理线程已启动 (10秒轮询)")

            server.serve_forever()

        except Exception as e:
            print(f"❌ Edge服务器启动失败: {str(e)}")

    def _heartbeat_loop(self):
        """心跳循环"""
        while self.running:
            self.send_heartbeat()
            time.sleep(30)  # 每30秒发送心跳

    def stop(self):
        """停止Edge节点"""
        print("🛑 正在停止Edge节点...")
        self.running = False
        self.processing_tasks = False

def main():
    """主函数"""
    print("=== HermesNexus v1.2.0 完整版Edge节点 ===")
    print(f"节点ID: edge-test-001")
    print(f"主机名: {socket.gethostname()}")
    print(f"IP地址: {EnhancedEdgeNode()._get_local_ip()}")
    print(f"Cloud API: http://172.16.100.101:8082")

    # 使用正确的Cloud API地址
    edge_node = EnhancedEdgeNode(cloud_url="http://172.16.100.101:8082")

    # 注册节点
    print("🔗 正在注册到Cloud API...")
    if edge_node.register_with_cloud():
        print("✅ 节点注册成功")
    else:
        print("⚠️ 节点注册失败，但继续启动服务")

    # 启动Edge服务器
    try:
        edge_node.start_edge_server()
    except KeyboardInterrupt:
        print("\n🛑 收到停止信号，正在关闭Edge节点...")
        edge_node.stop()
        print("✅ Edge节点已停止")

if __name__ == "__main__":
    main()