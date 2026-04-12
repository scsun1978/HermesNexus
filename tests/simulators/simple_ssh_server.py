"""
简单SSH测试服务器

用于测试的轻量级SSH服务器，支持基本的SSH连接和命令执行
"""

import socket
import threading
import time
import logging
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("需要安装paramiko: pip install paramiko")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class SimpleSSHServer(paramiko.ServerInterface):
    """简单SSH服务器接口"""

    def __init__(self, client_address):
        self.client_address = client_address
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        # 简单的认证检查 - 测试模式接受所有用户名密码
        logger.info(f"🔐 认证请求: {username}")
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        # 公钥认证也总是成功（测试模式）
        logger.info(f"🔐 公钥认证请求: {username}")
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        return "password,publickey"

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        return True


class SSHTestServer:
    """SSH测试服务器"""

    def __init__(self, host="0.0.0.0", port=2222, host_key_path=None):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
        self.host_key = None
        self.client_threads = []

        # 加载或生成主机密钥
        self._setup_host_key(host_key_path)

        # 模拟的系统状态
        self.hostname = "test-ssh-server"
        self.uptime_start = time.time()
        self.cpu_usage = 20.0
        self.memory_usage = 30.0

    def _setup_host_key(self, key_path):
        """设置主机密钥"""
        if key_path and Path(key_path).exists():
            try:
                self.host_key = paramiko.RSAKey.from_private_key_file(key_path)
                logger.info(f"✅ 加载主机密钥: {key_path}")
                return
            except Exception as e:
                logger.warning(f"⚠️  加载密钥失败: {e}")

        # 生成新的测试密钥
        logger.info("🔑 生成新的测试主机密钥...")
        self.host_key = paramiko.RSAKey.generate(2048)

        # 保存密钥以供重用
        if key_path:
            try:
                self.host_key.write_private_key_file(key_path)
                logger.info(f"💾 保存主机密钥: {key_path}")
            except Exception as e:
                logger.warning(f"⚠️  保存密钥失败: {e}")

    def start(self):
        """启动SSH服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            self.running = True

            logger.info(f"🚀 SSH测试服务器启动: {self.host}:{self.port}")
            logger.info(f"📡 主机名: {self.hostname}")

            # 启动状态更新线程
            threading.Thread(target=self._update_status, daemon=True).start()

            # 接受连接
            while self.running:
                try:
                    client_sock, client_addr = self.server_socket.accept()
                    logger.info(f"🔗 新连接: {client_addr}")

                    # 为每个客户端创建处理线程
                    thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_sock, client_addr),
                        daemon=True,
                    )
                    thread.start()
                    self.client_threads.append(thread)

                except socket.error as e:
                    if self.running:
                        logger.error(f"❌ 接受连接失败: {e}")

        except Exception as e:
            logger.error(f"❌ 启动SSH服务器失败: {e}")
            raise

    def stop(self):
        """停止SSH服务器"""
        logger.info("🛑 正在停止SSH服务器...")
        self.running = False

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

        logger.info("✅ SSH服务器已停止")

    def _update_status(self):
        """更新系统状态"""
        while self.running:
            # 随机波动系统资源使用率
            self.cpu_usage = max(
                10.0, min(90.0, self.cpu_usage + random.uniform(-3, 3))
            )
            self.memory_usage = max(
                15.0, min(85.0, self.memory_usage + random.uniform(-2, 2))
            )
            time.sleep(5)

    def _handle_client(self, client_sock, client_addr):
        """处理客户端连接"""
        try:
            # 创建SSH传输层
            transport = paramiko.Transport(client_sock)
            transport.add_server_key(self.host_key)

            # 创建服务器实例
            server = SimpleSSHServer(client_addr)

            try:
                # 启动SSH服务器
                transport.start_server(server=server)

                # 等待认证
                chan = transport.accept(20)
                if chan is None:
                    logger.warning(f"❌ 客户端 {client_addr} 认证失败")
                    return

                logger.info(f"✅ 客户端 {client_addr} 认证成功")

                # 获取会话通道
                if transport.is_active():
                    # 发送欢迎信息
                    chan.send(f"Welcome to {self.hostname}\\n")
                    chan.send(
                        f"Last login: {datetime.now().strftime('%a %b %d %H:%M:%S %Y')} from {client_addr[0]}\\n"
                    )
                    chan.send(f"{self.hostname}$ ")

                    # 命令循环
                    self._command_loop(chan, client_addr)

            except Exception as e:
                logger.error(f"❌ SSH会话错误: {e}")

        except Exception as e:
            logger.error(f"❌ 处理客户端 {client_addr} 失败: {e}")
        finally:
            try:
                transport.close()
            except Exception:
                pass

    def _command_loop(self, chan, client_addr):
        """命令处理循环"""
        try:
            buffer = ""

            while self.running:
                try:
                    # 接收数据
                    data = chan.recv(1024)
                    if not data:
                        break

                    # 处理输入
                    buffer += data.decode("utf-8", errors="ignore")

                    # 处理完整命令
                    while "\\n" in buffer or "\\r" in buffer:
                        line_end = (
                            buffer.find("\\n")
                            if "\\n" in buffer
                            else buffer.find("\\r")
                        )
                        command = buffer[:line_end].strip()
                        buffer = buffer[line_end + 1 :]

                        if command:
                            logger.info(f"📝 命令: {command}")

                            # 执行命令
                            if command in ["exit", "quit"]:
                                chan.send("Goodbye!\\n")
                                chan.close()
                                return

                            result = self._execute_command(command)
                            chan.send(result + "\\n")

                        # 发送新的提示符
                        chan.send(f"{self.hostname}$ ")

                except Exception as e:
                    logger.error(f"❌ 命令处理错误: {e}")
                    break

        except Exception as e:
            logger.error(f"❌ 命令循环错误: {e}")

    def _execute_command(self, command):
        """执行命令"""
        try:
            parts = command.split()
            cmd = parts[0] if parts else ""

            # 处理常见命令
            if cmd == "uptime":
                uptime = int(time.time() - self.uptime_start)
                hours = uptime // 3600
                mins = (uptime % 3600) // 60
                return f"up {hours}:{mins:02d}, load average: {self.cpu_usage/10:.2f}, {self.cpu_usage/8:.2f}, {self.cpu_usage/6:.2f}"

            elif cmd == "uname":
                if "-a" in parts:
                    return f"{self.hostname} Linux 5.15.0-test #1 SMP {datetime.now().strftime('%a %b %d %H:%M:%S %Y')} x86_64"
                return "Linux"

            elif cmd == "hostname":
                return self.hostname

            elif cmd == "whoami":
                return "testuser"

            elif cmd == "pwd":
                return "/home/testuser"

            elif cmd == "echo":
                return " ".join(parts[1:])

            elif cmd == "date":
                return datetime.now().isoformat()

            elif cmd == "ls":
                return "Desktop  Documents  Downloads  .bashrc  .ssh"

            elif cmd == "cat":
                return "This is simulated file content"

            elif cmd == "ps":
                return "PID TTY          TIME CMD\\n1 pts/0    00:00:01 init\\n1234 pts/0   00:00:00 bash"

            elif cmd == "free":
                return f"              total        used        free\\nMem:        {8*1024*1024}      {int(8*1024*1024*self.memory_usage/100)}      {int(8*1024*1024*(1-self.memory_usage/100))}"

            elif cmd == "df":
                return "Filesystem     1K-blocks    Used Available Use% Mounted on\\n/dev/sda1       20971520 5242880  15728640  25% /"

            elif cmd == "sleep":
                try:
                    seconds = int(parts[1]) if len(parts) > 1 else 1
                    time.sleep(seconds)
                    return f"Slept for {seconds} seconds"
                except Exception:
                    return "usage: sleep <seconds>"

            elif cmd == "id":
                return "uid=1000(testuser) gid=1000(testuser) groups=1000(testuser)"

            elif cmd == "help":
                return "Available commands: uptime, uname, hostname, whoami, pwd, echo, date, ls, cat, ps, free, df, sleep, id, exit, help"

            else:
                # 尝试执行实际命令（小心使用）
                try:
                    result = subprocess.run(
                        command, shell=True, capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        return result.stdout.strip() or "Command completed"
                    else:
                        return f"Error: {result.stderr.strip() or 'Command failed'}"
                except Exception:
                    return f"Command not found: {cmd}"

        except Exception as e:
            return f"Error: {str(e)}"


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="SSH测试服务器")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=2222, help="监听端口")
    parser.add_argument("--key", help="主机密钥文件路径")

    args = parser.parse_args()

    # 创建并启动服务器
    server = SSHTestServer(host=args.host, port=args.port, host_key_path=args.key)

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
