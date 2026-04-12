"""
SSH主机模拟器

用于测试的简单SSH服务器，模拟基本的SSH连接和命令执行
"""

import socket
import threading
import time
import subprocess
import logging
import random
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class SSHHostSimulator:
    """SSH主机模拟器"""

    def __init__(self, host="0.0.0.0", port=2222):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
        self.connected_clients = []

        # 模拟的主机信息
        self.hostname = "simulated-host"
        self.uptime_start = time.time()

        # 模拟的系统状态
        self.cpu_usage = 20.0
        self.memory_usage = 30.0
        self.load_average = [0.5, 0.8, 1.2]

    def start(self):
        """启动SSH模拟器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True

            logger.info(f"🚀 SSH模拟器启动在 {self.host}:{self.port}")
            logger.info(f"📡 模拟主机名: {self.hostname}")
            logger.info(f"⏰ 启动时间: {datetime.now().isoformat()}")

            # 启动系统状态更新线程
            threading.Thread(target=self._update_system_status, daemon=True).start()

            # 接受客户端连接
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    logger.info(f"🔗 新连接来自: {address}")
                    self.connected_clients.append(client_socket)

                    # 为每个客户端创建处理线程
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address),
                        daemon=True,
                    )
                    client_thread.start()

                except socket.error as e:
                    if self.running:
                        logger.error(f"❌ 接受连接失败: {e}")

        except Exception as e:
            logger.error(f"❌ 启动SSH模拟器失败: {e}")
            raise

    def stop(self):
        """停止SSH模拟器"""
        logger.info("🛑 正在停止SSH模拟器...")
        self.running = False

        # 关闭所有客户端连接
        for client in self.connected_clients:
            try:
                client.close()
            except:
                pass

        # 关闭服务器套接字
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        logger.info("✅ SSH模拟器已停止")

    def _update_system_status(self):
        """更新模拟的系统状态"""
        while self.running:
            # 随机波动CPU和内存使用率
            self.cpu_usage = max(5.0, min(95.0, self.cpu_usage + random.uniform(-5, 5)))
            self.memory_usage = max(
                10.0, min(90.0, self.memory_usage + random.uniform(-2, 2))
            )

            # 更新负载平均值
            self.load_average = [
                max(0.1, self.load_average[0] + random.uniform(-0.2, 0.2)),
                max(0.1, self.load_average[1] + random.uniform(-0.3, 0.3)),
                max(0.1, self.load_average[2] + random.uniform(-0.4, 0.4)),
            ]

            time.sleep(5)  # 每5秒更新一次

    def _handle_client(self, client_socket, address):
        """处理客户端连接"""
        try:
            # 发送欢迎信息
            welcome_msg = f"Welcome to {self.hostname} - SSH Simulator\\n"
            client_socket.send(welcome_msg.encode())

            # 简单的认证模拟
            client_socket.send(b"username: ")
            username = client_socket.recv(1024).decode().strip()
            client_socket.send(b"password: ")
            password = client_socket.recv(1024).decode().strip()

            # 简单的认证检查（测试用）
            if username and password:
                auth_success = True
            else:
                auth_success = True  # 测试模式总是成功

            if auth_success:
                client_socket.send(b"Authentication successful\\n")
                logger.info(f"✅ 客户端 {address} 认证成功")

                # 进入命令循环
                self._command_loop(client_socket, address)
            else:
                client_socket.send(b"Authentication failed\\n")
                logger.warning(f"❌ 客户端 {address} 认证失败")

        except Exception as e:
            logger.error(f"❌ 处理客户端 {address} 时出错: {e}")
        finally:
            try:
                client_socket.close()
                if client_socket in self.connected_clients:
                    self.connected_clients.remove(client_socket)
                logger.info(f"🔌 客户端 {address} 断开连接")
            except:
                pass

    def _command_loop(self, client_socket, address):
        """命令处理循环"""
        try:
            # 发送提示符
            client_socket.send(f"{self.hostname}$ ".encode())

            while self.running:
                try:
                    # 接收命令
                    command = client_socket.recv(1024).decode().strip()

                    if not command:
                        break

                    logger.info(f"📝 收到命令: {command}")

                    # 处理命令
                    response = self._execute_command(command)
                    client_socket.send(response.encode())
                    client_socket.send(b"\\n")
                    client_socket.send(f"{self.hostname}$ ".encode())

                except socket.error:
                    break

        except Exception as e:
            logger.error(f"❌ 命令循环出错: {e}")

    def _execute_command(self, command):
        """执行命令并返回结果"""
        try:
            # 解析命令
            parts = command.split()
            cmd = parts[0] if parts else ""
            args = parts[1:] if len(parts) > 1 else []

            # 处理常见命令
            if cmd == "uptime":
                return self._cmd_uptime()
            elif cmd == "uname":
                return self._cmd_uname(args)
            elif cmd == "hostname":
                return self._cmd_hostname()
            elif cmd == "whoami":
                return "test-user"
            elif cmd == "pwd":
                return "/home/test-user"
            elif cmd == "ls":
                return self._cmd_ls(args)
            elif cmd == "echo":
                return " ".join(args)
            elif cmd == "date":
                return datetime.now().isoformat()
            elif cmd == "sleep":
                try:
                    sleep_time = int(args[0]) if args else 1
                    time.sleep(sleep_time)
                    return f"slept for {sleep_time} seconds"
                except:
                    return "usage: sleep <seconds>"
            elif cmd == "cat":
                return self._cmd_cat(args)
            elif cmd == "ps":
                return self._cmd_ps()
            elif cmd == "top" or cmd == "htop":
                return "Process monitor (simulated)"
            elif cmd == "df":
                return self._cmd_df()
            elif cmd == "free":
                return self._cmd_free()
            elif cmd == "exit" or cmd == "quit":
                return "Goodbye!"
            elif cmd == "help":
                return self._cmd_help()
            else:
                # 尝试执行实际命令（小心使用）
                try:
                    result = subprocess.run(
                        command, shell=True, capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        return result.stdout.strip()
                    else:
                        return f"Command failed with code {result.returncode}: {result.stderr.strip()}"
                except subprocess.TimeoutExpired:
                    return "Command timeout"
                except Exception as e:
                    return f"Command error: {str(e)}"

        except Exception as e:
            return f"Error executing command: {str(e)}"

    def _cmd_uptime(self):
        """uptime命令"""
        uptime_seconds = int(time.time() - self.uptime_start)
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        return f"up {hours}:{minutes:02d}, {self.load_average[0]:.2f}, {self.load_average[1]:.2f}, {self.load_average[2]:.2f}"

    def _cmd_uname(self, args):
        """uname命令"""
        if "-a" in args:
            return f"{self.hostname} Linux 5.15.0-simulator #1 SMP {datetime.now().strftime('%a %b %d %H:%M:%S %Y')} x86_64"
        else:
            return "Linux"

    def _cmd_hostname(self):
        """hostname命令"""
        return self.hostname

    def _cmd_ls(self, args):
        """ls命令"""
        # 模拟文件列表
        files = [
            "documents",
            "downloads",
            ".bashrc",
            ".ssh",
            "test_file.txt",
            "README.md",
        ]

        if "-la" in args or "-l" in args:
            return "\\n".join(
                [
                    "drwxr-xr-x  2 test-user test-user 4096 Jan  1 12:00 documents",
                    "drwxr-xr-x  2 test-user test-user 4096 Jan  1 12:00 downloads",
                    "-rw-r--r--  1 test-user test-user  220 Jan  1 12:00 .bashrc",
                    "drwx------  2 test-user test-user 4096 Jan  1 12:00 .ssh",
                    "-rw-r--r--  1 test-user test-user 1024 Jan  1 12:00 test_file.txt",
                    "-rw-r--r--  1 test-user test-user 2048 Jan  1 12:00 README.md",
                ]
            )
        else:
            return "  ".join(files)

    def _cmd_cat(self, args):
        """cat命令"""
        if not args:
            return "usage: cat <file>"

        filename = args[0]
        if filename == "test_file.txt":
            return "This is a test file content for SSH simulator testing."
        elif filename == "README.md":
            return "# SSH Simulator\\n\\nThis is a simulated SSH host for testing."
        elif filename == "/proc/cpuinfo":
            return "processor\\t: 0\\nvendor_id\\t: GenuineIntel\\ncpu family\\t: 6\\nmodel\\t\\t: 158"
        elif filename == "/proc/meminfo":
            return f"MemTotal:\\t{8 * 1024 * 1024} kB\\nMemFree:\\t{4 * 1024 * 1024} kB\\nMemAvailable:\\t{6 * 1024 * 1024} kB"
        else:
            return f"cat: {filename}: No such file or directory"

    def _cmd_ps(self):
        """ps命令"""
        return """PID   USER     TIME   COMMAND
1     root     0:01   init
1234  test-u+  0:00   -bash
5678  test-u+  0:00   ps"""

    def _cmd_df(self):
        """df命令"""
        return """Filesystem     1K-blocks    Used Available Use% Mounted on
/dev/sda1       20971520 5242880  15728640  25% /
/dev/sda2       10485760 2097152   8388608  20% /home"""

    def _cmd_free(self):
        """free命令"""
        total_mem = 8 * 1024 * 1024  # 8GB
        used_mem = int(total_mem * (self.memory_usage / 100))
        free_mem = total_mem - used_mem

        return f"""              total        used        free      shared  buff/cache   available
Mem:        {total_mem}      {used_mem}      {free_mem}        1024      1048576      {6 * 1024 * 1024}
Swap:       {2 * 1024 * 1024}           0  {2 * 1024 * 1024}"""

    def _cmd_help(self):
        """help命令"""
        return """Available commands:
  uptime   - Show system uptime
  uname    - Print system information
  hostname - Print system hostname
  whoami   - Print current user
  pwd      - Print working directory
  ls       - List directory contents
  echo     - Display text
  date     - Print date and time
  sleep    - Delay for specified time
  cat      - Concatenate files
  ps       - Report process status
  df       - Report file system disk space
  free     - Display amount of free and used memory
  exit     - Exit session
  help     - Show this help message"""


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="SSH主机模拟器")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=2222, help="监听端口")
    parser.add_argument("--timeout", type=int, default=300, help="运行超时（秒）")

    args = parser.parse_args()

    # 创建并启动模拟器
    simulator = SSHHostSimulator(host=args.host, port=args.port)

    try:
        # 启动模拟器
        simulator.start()

    except KeyboardInterrupt:
        logger.info("收到中断信号，正在停止...")
    finally:
        simulator.stop()


if __name__ == "__main__":
    main()
