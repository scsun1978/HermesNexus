"""
设备类型系统测试 - Week 4 Day 1-2
MVP 3类设备类型验收
"""
import pytest
from hermesnexus.device.types import (
    DeviceType, CommandStyle,
    DeviceTypeFactory, DeviceCommandAdapter,
    DeviceCapabilities, DeviceValidator
)


class TestDeviceTypeFactory:
    """设备类型工厂测试"""

    def test_create_router_config_cisco(self):
        """创建Cisco路由器配置"""
        host_info = {
            'hostname': 'core-router-01',
            'vendor': 'cisco',
            'ssh_port': 22,
            'ssh_user': 'admin',
            'node_id': 'router-001'
        }

        config = DeviceTypeFactory.create_router_config(host_info)

        assert config['device_type'] == 'router'
        assert config['hostname'] == 'core-router-01'
        assert config['vendor'] == 'cisco'
        assert config['command_style'] == CommandStyle.CISCO_IOS.value
        assert config['login_type'] == 'password'
        assert config['ssh_port'] == 22

    def test_create_router_config_huawei(self):
        """创建Huawei路由器配置"""
        host_info = {
            'hostname': 'edge-router-02',
            'vendor': 'huawei',
            'ssh_port': 22,
            'ssh_user': 'admin',
            'node_id': 'router-002'
        }

        config = DeviceTypeFactory.create_router_config(host_info)

        assert config['device_type'] == 'router'
        assert config['command_style'] == CommandStyle.HUAWEI_VRP.value
        assert config['vendor'] == 'huawei'

    def test_create_switch_config(self):
        """创建交换机配置"""
        host_info = {
            'hostname': 'access-switch-01',
            'vendor': 'cisco',
            'ssh_port': 22,
            'ssh_user': 'admin',
            'node_id': 'switch-001',
            'ports': 48
        }

        config = DeviceTypeFactory.create_switch_config(host_info)

        assert config['device_type'] == 'switch'
        assert config['ports'] == 48
        assert config['login_type'] == 'password'
        assert config['command_style'] == CommandStyle.CISCO_IOS.value

    def test_create_server_config(self):
        """创建服务器配置"""
        host_info = {
            'hostname': 'web-server-01',
            'ssh_port': 22,
            'ssh_user': 'root',
            'node_id': 'server-001',
            'os_type': 'linux',
            'architecture': 'x86_64',
            'ssh_private_key_path': '/home/user/.ssh/id_rsa'
        }

        config = DeviceTypeFactory.create_server_config(host_info)

        assert config['device_type'] == 'server'
        assert config['login_type'] == 'key'
        assert config['command_style'] == CommandStyle.LINUX_BASH.value
        assert config['os_type'] == 'linux'
        assert config['architecture'] == 'x86_64'

    def test_unsupported_device_type(self):
        """不支持的设备类型"""
        host_info = {
            'hostname': 'unknown-device',
            'node_id': 'unknown-001'
        }

        with pytest.raises(ValueError, match="Unsupported device type"):
            DeviceTypeFactory.create_config("firewall", host_info)


class TestDeviceCommandAdapter:
    """设备命令适配器测试"""

    def test_adapt_router_command_cisco(self):
        """Cisco路由器命令适配"""
        device_config = {
            'device_type': 'router',
            'command_style': 'cisco_ios'
        }

        # 测试基本命令
        command = "show version"
        adapted = DeviceCommandAdapter.adapt_command_for_device(command, device_config)
        assert adapted == "show version"

        # 测试其他命令
        command = "show running-config"
        adapted = DeviceCommandAdapter.adapt_command_for_device(command, device_config)
        assert adapted == "show running-config"

    def test_adapt_router_command_huawei(self):
        """Huawei路由器命令适配"""
        device_config = {
            'device_type': 'router',
            'command_style': 'huawei_vrp'
        }

        # 测试show到display的转换
        command = "show version"
        adapted = DeviceCommandAdapter.adapt_command_for_device(command, device_config)
        assert adapted == "display version"

        command = "show running-config"
        adapted = DeviceCommandAdapter.adapt_command_for_device(command, device_config)
        assert adapted == "display current-configuration"

    def test_adapt_server_command(self):
        """服务器命令适配（通常不需要适配）"""
        device_config = {
            'device_type': 'server',
            'command_style': 'linux_bash'
        }

        command = "uptime && df -h"
        adapted = DeviceCommandAdapter.adapt_command_for_device(command, device_config)
        assert adapted == command  # 服务器命令通常不需要适配

    def test_adapt_switch_command(self):
        """交换机命令适配"""
        device_config = {
            'device_type': 'switch',
            'command_style': 'cisco_ios'
        }

        command = "show version"
        adapted = DeviceCommandAdapter.adapt_command_for_device(command, device_config)
        assert adapted == "show version"


class TestDeviceCapabilities:
    """设备能力测试"""

    def test_router_capabilities(self):
        """路由器能力"""
        capabilities = DeviceCapabilities.get_capabilities('router')

        assert capabilities['show_version'] is True
        assert capabilities['show_route'] is True
        assert capabilities['restart_service'] is False  # 路由器不支持systemd
        assert capabilities['install_package'] is False
        assert capabilities['rollback_config'] is True

    def test_switch_capabilities(self):
        """交换机能力"""
        capabilities = DeviceCapabilities.get_capabilities('switch')

        assert capabilities['show_vlan'] is True
        assert capabilities['show_port_status'] is True
        assert capabilities['restart_service'] is False  # 交换机不支持systemd
        assert capabilities['configure_port'] is True

    def test_server_capabilities(self):
        """服务器能力"""
        capabilities = DeviceCapabilities.get_capabilities('server')

        assert capabilities['show_version'] is True
        assert capabilities['restart_service'] is True   # 服务器支持systemd
        assert capabilities['install_package'] is True    # 服务器支持包管理
        assert capabilities['rollback_config'] is False   # 服务器不支持配置回滚

    def test_capability_support_check(self):
        """能力支持检查"""
        # 路由器支持路由查询
        assert DeviceCapabilities.supports_capability('router', 'show_route') is True

        # 服务器不支持配置回滚
        assert DeviceCapabilities.supports_capability('server', 'rollback_config') is False

        # 交换机支持端口配置
        assert DeviceCapabilities.supports_capability('switch', 'configure_port') is True


class TestDeviceValidator:
    """设备验证器测试"""

    def test_validate_router_config_valid(self):
        """验证有效的路由器配置"""
        config = {
            'hostname': 'router-01',
            'vendor': 'cisco',
            'ssh_port': 22,
            'ssh_user': 'admin'
        }

        is_valid, errors = DeviceValidator.validate_router_config(config)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_router_config_missing_field(self):
        """验证缺少必需字段的路由器配置"""
        config = {
            'hostname': 'router-01',
            # 缺少vendor, ssh_port, ssh_user
        }

        is_valid, errors = DeviceValidator.validate_router_config(config)
        assert is_valid is False
        assert len(errors) == 3

    def test_validate_router_config_invalid_vendor(self):
        """验证无效厂商的路由器配置"""
        config = {
            'hostname': 'router-01',
            'vendor': 'invalid_vendor',
            'ssh_port': 22,
            'ssh_user': 'admin'
        }

        is_valid, errors = DeviceValidator.validate_router_config(config)
        assert is_valid is False
        assert 'Unsupported vendor' in str(errors)

    def test_validate_switch_config_valid(self):
        """验证有效的交换机配置"""
        config = {
            'hostname': 'switch-01',
            'vendor': 'cisco',
            'ssh_port': 22,
            'ssh_user': 'admin',
            'ports': 48
        }

        is_valid, errors = DeviceValidator.validate_switch_config(config)
        assert is_valid is True

    def test_validate_switch_config_invalid_ports(self):
        """验证无效端口数量的交换机配置"""
        config = {
            'hostname': 'switch-01',
            'vendor': 'cisco',
            'ssh_port': 22,
            'ssh_user': 'admin',
            'ports': 2000  # 超过1024，无效
        }

        is_valid, errors = DeviceValidator.validate_switch_config(config)
        assert is_valid is False
        assert 'Invalid port count' in str(errors)

    def test_validate_server_config_valid(self):
        """验证有效的服务器配置"""
        config = {
            'hostname': 'server-01',
            'ssh_port': 22,
            'ssh_user': 'root',
            'os_type': 'linux'
        }

        is_valid, errors = DeviceValidator.validate_server_config(config)
        assert is_valid is True

    def test_validate_server_config_missing_key(self):
        """验证缺少密钥的服务器配置"""
        config = {
            'hostname': 'server-01',
            'ssh_port': 22,
            'ssh_user': 'root',
            'os_type': 'linux',
            'login_type': 'key'  # 声明用密钥但没提供路径
        }

        is_valid, errors = DeviceValidator.validate_server_config(config)
        assert is_valid is False
        assert 'ssh_private_key_path' in str(errors)

    def test_unsupported_device_type_validation(self):
        """不支持的设备类型验证"""
        config = {
            'hostname': 'firewall-01',
            'ssh_port': 22,
            'ssh_user': 'admin'
        }

        is_valid, errors = DeviceValidator.validate_device_config('firewall', config)
        assert is_valid is False
        assert 'Unsupported device type' in str(errors)


class TestDeviceTypeEnums:
    """设备类型枚举测试"""

    def test_device_type_enum(self):
        """设备类型枚举"""
        assert DeviceType.ROUTER.value == 'router'
        assert DeviceType.SWITCH.value == 'switch'
        assert DeviceType.SERVER.value == 'server'

    def test_command_style_enum(self):
        """命令风格枚举"""
        assert CommandStyle.CISCO_IOS.value == 'cisco_ios'
        assert CommandStyle.HUAWEI_VRP.value == 'huawei_vrp'
        assert CommandStyle.LINUX_BASH.value == 'linux_bash'
        assert CommandStyle.JUNOS.value == 'junos'


class TestDeviceIntegration:
    """设备系统集成测试"""

    def test_complete_router_workflow(self):
        """完整的路由器工作流程"""
        # 1. 创建路由器配置
        host_info = {
            'hostname': 'core-router-01',
            'vendor': 'cisco',
            'ssh_port': 22,
            'ssh_user': 'admin',
            'node_id': 'router-001'
        }

        # 2. 生成设备配置
        config = DeviceTypeFactory.create_router_config(host_info)

        # 3. 验证配置
        is_valid, errors = DeviceValidator.validate_router_config(config)
        assert is_valid is True

        # 4. 适配命令
        device_config = {'device_type': 'router', 'command_style': 'cisco_ios'}
        command = "show version"
        adapted_command = DeviceCommandAdapter.adapt_command_for_device(command, device_config)
        assert adapted_command == "show version"

        # 5. 检查能力
        capabilities = DeviceCapabilities.get_capabilities('router')
        assert capabilities['show_route'] is True
        assert capabilities['restart_service'] is False

    def test_complete_switch_workflow(self):
        """完整的交换机工作流程"""
        host_info = {
            'hostname': 'access-switch-01',
            'vendor': 'huawei',
            'ssh_port': 22,
            'ssh_user': 'admin',
            'node_id': 'switch-001',
            'ports': 24
        }

        config = DeviceTypeFactory.create_switch_config(host_info)
        assert config['device_type'] == 'switch'
        assert config['command_style'] == 'huawei_vrp'

        is_valid, errors = DeviceValidator.validate_switch_config(config)
        assert is_valid is True

    def test_complete_server_workflow(self):
        """完整的服务器工作流程"""
        host_info = {
            'hostname': 'web-server-01',
            'ssh_port': 22,
            'ssh_user': 'root',
            'node_id': 'server-001',
            'os_type': 'linux',
            'ssh_private_key_path': '/home/user/.ssh/id_rsa'
        }

        config = DeviceTypeFactory.create_server_config(host_info)
        assert config['device_type'] == 'server'
        assert config['login_type'] == 'key'

        is_valid, errors = DeviceValidator.validate_server_config(config)
        assert is_valid is True

        # 服务器命令适配（通常不需要适配）
        device_config = {'device_type': 'server', 'command_style': 'linux_bash'}
        command = "uptime && df -h"
        adapted = DeviceCommandAdapter.adapt_command_for_device(command, device_config)
        assert adapted == command  # 服务器命令保持不变

        capabilities = DeviceCapabilities.get_capabilities('server')
        assert capabilities['restart_service'] is True
        assert capabilities['install_package'] is True