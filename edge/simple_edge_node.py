#!/usr/bin/env python3
"""
HermesNexus 简化版Edge节点
用于生产部署和集成测试
不依赖复杂的外部包，使用系统标准库
"""

import json
import time
import socket
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

class SimpleEdgeNode:
    """简化版Edge节点"""

    def __init__(self, node_id: str = "edge-test-001", cloud_url: str = "http://172.16.100.101:8080"):
        self.node_id = node_id
        self.cloud_url = cloud_url
        self.hostname = socket.gethostname()
        self.ip_address = self._get_local_ip()
        self.running = True

    def _get_local_ip(self) -> str:
        """获取本地IP地址"""
        try:
            # 连接到外部地址获取本地IP
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

    def execute_ssh_command(self, command: str, target_host: str = None) -> Dict[str, Any]:
        """执行SSH命令"""
        try:
            # 如果没有指定目标主机，执行本地命令
            if not target_host:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }
            else:
                # 执行远程SSH命令
                ssh_command = f"ssh {target_host} '{command}'"
                result = subprocess.run(
                    ssh_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "命令执行超时",
                "return_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1
            }

    def _get_cpu_usage(self) -> float:
        """获取CPU使用率"""
        try:
            with open('/proc/loadavg', 'r') as f:
                load = f.read().split()[0]
                return float(load) * 100  # 简化的CPU使用率计算
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
        """启动Edge HTTP服务器"""
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
                        self.end_headers()
                        health_data = {
                            "status": "healthy",
                            "node_id": self.edge_node.node_id,
                            "timestamp": datetime.now().isoformat(),
                            "cloud_url": self.edge_node.cloud_url
                        }
                        self.wfile.write(json.dumps(health_data).encode())
                    elif self.path == '/status':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        status_data = {
                            "node_id": self.edge_node.node_id,
                            "hostname": self.edge_node.hostname,
                            "ip_address": self.edge_node.ip_address,
                            "cpu_usage": self.edge_node._get_cpu_usage(),
                            "memory_usage": self.edge_node._get_memory_usage(),
                            "disk_usage": self.edge_node._get_disk_usage()
                        }
                        self.wfile.write(json.dumps(status_data).encode())
                    else:
                        self.send_response(404)
                        self.end_headers()

                def log_message(self, format, *args):
                    # 简化日志输出
                    pass

            def handler(*args, **kwargs):
                EdgeHTTPRequestHandler(*args, edge_node=self, **kwargs)

            server = HTTPServer(('0.0.0.0', port), handler)
            print(f"🚀 Edge节点启动在端口 {port}")
            print(f"📍 节点ID: {self.node_id}")
            print(f"🌐 Cloud API: {self.cloud_url}")

            # 在独立线程中运行心跳
            import threading
            def heartbeat_loop():
                while self.running:
                    self.send_heartbeat()
                    time.sleep(30)  # 每30秒发送心跳

            heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
            heartbeat_thread.start()

            server.serve_forever()

        except Exception as e:
            print(f"❌ Edge服务器启动失败: {str(e)}")

    def stop(self):
        """停止Edge节点"""
        self.running = False

def main():
    """主函数"""
    import platform
    import os

    print("=== HermesNexus 简化版Edge节点 ===")
    print(f"节点ID: edge-test-001")
    print(f"主机名: {socket.gethostname()}")
    print(f"IP地址: {SimpleEdgeNode()._get_local_ip()}")
    print(f"Cloud API: http://172.16.100.101:8080")

    edge_node = SimpleEdgeNode()

    # 注册节点
    print("正在注册到Cloud API...")
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

if __name__ == "__main__":
    main()