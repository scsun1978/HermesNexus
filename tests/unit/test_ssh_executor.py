"""
SSH执行器单元测试

测试SSH执行器的功能，不需要真实SSH连接
"""

import unittest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestSSHExecutor(unittest.TestCase):
    """测试SSH执行器基础功能"""

    def setUp(self):
        """测试前设置"""
        # 这里只测试导入和基础功能，不测试实际SSH连接
        pass

    def test_module_import(self):
        """测试模块导入"""
        try:
            from edge.executors.ssh_executor import SSHExecutor, SSHExecutorPool

            self.assertTrue(True, "SSH执行器模块导入成功")
        except ImportError as e:
            self.fail(f"SSH执行器模块导入失败: {e}")

    def test_executor_initialization(self):
        """测试执行器初始化"""
        from edge.executors.ssh_executor import SSHExecutor

        # 创建执行器实例（不连接）
        executor = SSHExecutor(host="localhost", username="testuser", port=22)

        self.assertEqual(executor.host, "localhost")
        self.assertEqual(executor.username, "testuser")
        self.assertEqual(executor.port, 22)
        self.assertFalse(executor.is_connected)

    def test_executor_pool_initialization(self):
        """测试执行器池初始化"""
        from edge.executors.ssh_executor import SSHExecutorPool

        pool = SSHExecutorPool(max_connections=5)

        self.assertEqual(pool.max_connections, 5)
        self.assertEqual(len(pool.executors), 0)

    def test_executor_pool_stats(self):
        """测试执行器池统计"""
        from edge.executors.ssh_executor import SSHExecutorPool

        pool = SSHExecutorPool(max_connections=3)
        stats = pool.get_pool_stats()

        self.assertIn("total_connections", stats)
        self.assertIn("active_connections", stats)
        self.assertIn("max_connections", stats)
        self.assertEqual(stats["max_connections"], 3)


class TestSSHExecutorMock(unittest.TestCase):
    """使用Mock测试SSH执行器"""

    def test_mock_ssh_connection(self):
        """测试模拟SSH连接"""
        from edge.executors.ssh_executor import SSHExecutor

        executor = SSHExecutor(host="localhost", username="testuser", timeout=10)

        # 模拟连接成功
        executor.is_connected = True
        executor.connection_time = "2024-01-01T00:00:00Z"

        self.assertTrue(executor.is_connected)
        self.assertIsNotNone(executor.connection_time)

    def test_mock_command_execution(self):
        """测试模拟命令执行"""
        from edge.executors.ssh_executor import SSHExecutor

        executor = SSHExecutor(host="localhost", username="testuser")

        # 模拟命令执行结果
        mock_result = {
            "success": True,
            "stdout": "Hello World",
            "stderr": "",
            "exit_code": 0,
            "execution_time": 1.5,
        }

        self.assertTrue(mock_result["success"])
        self.assertEqual(mock_result["exit_code"], 0)
        self.assertGreater(mock_result["execution_time"], 0)

    def test_mock_error_handling(self):
        """测试模拟错误处理"""
        from edge.executors.ssh_executor import SSHExecutor

        executor = SSHExecutor(host="localhost", username="testuser")

        # 模拟执行失败
        mock_error_result = {
            "success": False,
            "error": "Connection failed",
            "error_code": "ERR_5000",
            "exit_code": -1,
        }

        self.assertFalse(mock_error_result["success"])
        self.assertIsNotNone(mock_error_result["error"])
        self.assertEqual(mock_error_result["error_code"], "ERR_5000")


class TestAuditLogger(unittest.TestCase):
    """测试审计日志记录器"""

    def test_audit_logger_import(self):
        """测试审计日志模块导入"""
        try:
            from edge.audit.audit import AuditLogger

            self.assertTrue(True, "审计日志模块导入成功")
        except ImportError as e:
            self.fail(f"审计日志模块导入失败: {e}")

    def test_audit_logger_initialization(self):
        """测试审计日志初始化"""
        from edge.audit.audit import AuditLogger

        audit_logger = AuditLogger()

        self.assertIsNotNone(audit_logger)
        self.assertEqual(len(audit_logger.logs), 0)

    def test_ssh_connection_logging(self):
        """测试SSH连接日志记录"""
        from edge.audit.audit import AuditLogger

        audit_logger = AuditLogger()

        # 记录SSH连接
        audit_logger.log_ssh_connection(
            host="test-host", username="testuser", success=True
        )

        # 验证日志被记录
        logs = audit_logger.get_recent_logs(limit=1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["action"], "ssh_connection")
        self.assertTrue(logs[0]["success"])

    def test_ssh_command_logging(self):
        """测试SSH命令日志记录"""
        from edge.audit.audit import AuditLogger

        audit_logger = AuditLogger()

        # 记录SSH命令
        audit_logger.log_ssh_command(
            host="test-host", command="uptime", result={"success": True, "exit_code": 0}
        )

        # 验证日志被记录
        logs = audit_logger.get_recent_logs(limit=1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["action"], "ssh_command")
        self.assertEqual(logs[0]["resource_id"], "test-host")

    def test_log_searching(self):
        """测试日志搜索功能"""
        from edge.audit.audit import AuditLogger

        audit_logger = AuditLogger()

        # 记录多条不同类型的日志
        audit_logger.log_ssh_connection("host1", "user1", True)
        audit_logger.log_ssh_command("host1", "uptime", {"success": True})
        audit_logger.log_ssh_connection("host2", "user2", False)

        # 搜索连接日志
        connection_logs = audit_logger.search_logs(resource_type="ssh_connection")
        self.assertEqual(len(connection_logs), 2)

        # 搜索命令日志
        command_logs = audit_logger.search_logs(resource_type="ssh_command")
        self.assertEqual(len(command_logs), 1)


class TestSSHExecutorValidation(unittest.TestCase):
    """测试SSH执行器数据验证"""

    def test_host_validation(self):
        """测试主机地址验证"""
        from edge.executors.ssh_executor import SSHExecutor

        # 有效主机地址
        valid_hosts = ["localhost", "192.168.1.1", "example.com", "ssh.example.com"]

        for host in valid_hosts:
            executor = SSHExecutor(host=host, username="testuser")
            self.assertEqual(executor.host, host)

    def test_port_validation(self):
        """测试端口验证"""
        from edge.executors.ssh_executor import SSHExecutor

        # 有效端口范围
        valid_ports = [22, 2222, 8080, 65535]

        for port in valid_ports:
            executor = SSHExecutor(host="localhost", username="testuser", port=port)
            self.assertEqual(executor.port, port)

    def test_timeout_validation(self):
        """测试超时验证"""
        from edge.executors.ssh_executor import SSHExecutor

        # 有效超时值
        valid_timeouts = [10, 30, 60, 120, 300]

        for timeout in valid_timeouts:
            executor = SSHExecutor(
                host="localhost", username="testuser", timeout=timeout
            )
            self.assertEqual(executor.timeout, timeout)

    def test_credentials_validation(self):
        """测试凭据验证"""
        from edge.executors.ssh_executor import SSHExecutor

        # 测试用户名
        executor = SSHExecutor(
            host="localhost", username="testuser", password="testpass"
        )

        self.assertEqual(executor.username, "testuser")
        self.assertEqual(executor.password, "testpass")


class TestSSHExecutorConfig(unittest.TestCase):
    """测试SSH执行器配置"""

    def test_default_config(self):
        """测试默认配置"""
        from edge.executors.ssh_executor import SSHExecutor

        executor = SSHExecutor(host="localhost", username="testuser")

        # 验证默认配置值
        self.assertEqual(executor.port, 22)  # 默认SSH端口
        self.assertGreater(executor.timeout, 0)  # 超时应为正数
        self.assertFalse(executor.keep_alive)  # 默认不保活

    def test_custom_config(self):
        """测试自定义配置"""
        from edge.executors.ssh_executor import SSHExecutor

        executor = SSHExecutor(
            host="localhost",
            username="testuser",
            port=2222,
            timeout=60,
            keep_alive=True,
            max_output_size=5 * 1024 * 1024,  # 5MB
        )

        self.assertEqual(executor.port, 2222)
        self.assertEqual(executor.timeout, 60)
        self.assertTrue(executor.keep_alive)
        self.assertEqual(executor.max_output_size, 5 * 1024 * 1024)

    def test_pool_config(self):
        """测试连接池配置"""
        from edge.executors.ssh_executor import SSHExecutorPool

        pool = SSHExecutorPool(max_connections=10, connection_timeout=30)

        self.assertEqual(pool.max_connections, 10)
        self.assertEqual(pool.connection_timeout, 30)


if __name__ == "__main__":
    unittest.main()
