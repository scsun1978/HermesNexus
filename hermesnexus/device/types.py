"""
设备类型抽象系统 - Week 4 Day 1-2
MVP 3类设备类型实现
"""
from typing import Dict, Any, Optional
from enum import Enum


class DeviceType(Enum):
    """设备类型枚举"""
    ROUTER = "router"
    SWITCH = "switch"
    SERVER = "server"


class CommandStyle(Enum):
    """命令风格枚举"""
    CISCO_IOS = "cisco_ios"
    HUAWEI_VRP = "huawei_vrp"
    LINUX_BASH = "linux_bash"
    JUNOS = "junos"
    ARUBAOS = "arubaos"  # Aruba OS support for Aruba/HPE network devices


class DeviceTypeFactory:
    """设备类型工厂 - MVP 3类设备实现"""

    @staticmethod
    def create_router_config(host_info: dict) -> dict:
        """创建路由器设备配置"""
        return {
            'device_type': DeviceType.ROUTER.value,
            'connection_type': 'ssh',
            'protocol': 'ssh',
            'ssh_port': host_info.get('ssh_port', 22),
            'ssh_user': host_info.get('ssh_user', 'admin'),
            'login_type': 'password',  # 路由器主要用密码登录
            'command_style': DeviceTypeFactory._detect_router_command_style(host_info),
            'timeout': host_info.get('timeout', 30),
            'node_id': host_info.get('node_id'),
            'hostname': host_info.get('hostname', 'router'),
            'vendor': host_info.get('vendor', 'cisco'),  # cisco, huawei, juniper
            'model': host_info.get('model', 'unknown')
        }

    @staticmethod
    def create_switch_config(host_info: dict) -> dict:
        """创建交换机设备配置"""
        return {
            'device_type': DeviceType.SWITCH.value,
            'connection_type': 'ssh',
            'protocol': 'ssh',
            'ssh_port': host_info.get('ssh_port', 22),
            'ssh_user': host_info.get('ssh_user', 'admin'),
            'login_type': 'password',  # 交换机主要用密码登录
            'command_style': DeviceTypeFactory._detect_switch_command_style(host_info),
            'timeout': host_info.get('timeout', 30),
            'node_id': host_info.get('node_id'),
            'hostname': host_info.get('hostname', 'switch'),
            'vendor': host_info.get('vendor', 'cisco'),  # cisco, huawei, h3c
            'model': host_info.get('model', 'unknown'),
            'ports': host_info.get('ports', 24)  # 端口数量
        }

    @staticmethod
    def create_server_config(host_info: dict) -> dict:
        """创建服务器设备配置"""
        # 智能检测登录类型：如果有密钥路径就用密钥，否则用密码
        ssh_private_key_path = host_info.get('ssh_private_key_path')
        login_type = 'key' if ssh_private_key_path else 'password'

        return {
            'device_type': DeviceType.SERVER.value,
            'connection_type': 'ssh',
            'protocol': 'ssh',
            'ssh_port': host_info.get('ssh_port', 22),
            'ssh_user': host_info.get('ssh_user', 'root'),
            'login_type': login_type,
            'ssh_private_key_path': ssh_private_key_path,
            'command_style': CommandStyle.LINUX_BASH.value,
            'timeout': host_info.get('timeout', 60),
            'node_id': host_info.get('node_id'),
            'hostname': host_info.get('hostname', 'server'),
            'os_type': host_info.get('os_type', 'linux'),  # linux, windows
            'os_version': host_info.get('os_version', 'unknown'),
            'architecture': host_info.get('architecture', 'x86_64')
        }

    @staticmethod
    def _detect_router_command_style(host_info: dict) -> str:
        """检测路由器命令风格"""
        vendor = host_info.get('vendor', 'cisco').lower()

        if vendor == 'cisco':
            return CommandStyle.CISCO_IOS.value
        elif vendor == 'huawei':
            return CommandStyle.HUAWEI_VRP.value
        elif vendor == 'juniper':
            return CommandStyle.JUNOS.value
        elif vendor in ['aruba', 'hpe', 'hp']:  # 🆕 新增 Aruba 检测
            return CommandStyle.ARUBAOS.value
        else:
            return CommandStyle.CISCO_IOS.value  # 默认Cisco风格

    @staticmethod
    def _detect_switch_command_style(host_info: dict) -> str:
        """检测交换机命令风格"""
        vendor = host_info.get('vendor', 'cisco').lower()

        if vendor == 'cisco':
            return CommandStyle.CISCO_IOS.value
        elif vendor == 'huawei':
            return CommandStyle.HUAWEI_VRP.value
        elif vendor == 'h3c':
            return CommandStyle.HUAWEI_VRP.value
        elif vendor in ['aruba', 'hpe', 'hp']:  # 🆕 新增 Aruba 检测
            return CommandStyle.ARUBAOS.value
        else:
            return CommandStyle.CISCO_IOS.value  # 默认Cisco风格

    @staticmethod
    def create_config(device_type: str, host_info: dict) -> dict:
        """通用设备配置创建接口"""
        device_type = device_type.lower()

        if device_type == DeviceType.ROUTER.value:
            return DeviceTypeFactory.create_router_config(host_info)
        elif device_type == DeviceType.SWITCH.value:
            return DeviceTypeFactory.create_switch_config(host_info)
        elif device_type == DeviceType.SERVER.value:
            return DeviceTypeFactory.create_server_config(host_info)
        else:
            raise ValueError(f"Unsupported device type: {device_type}")


class DeviceCommandAdapter:
    """设备命令适配器 - 为不同设备类型生成适配命令"""

    @staticmethod
    def adapt_command_for_device(command: str, device_config: dict) -> str:
        """为特定设备适配命令"""
        device_type = device_config.get('device_type')
        command_style = device_config.get('command_style')

        if device_type == DeviceType.ROUTER.value:
            return DeviceCommandAdapter._adapt_router_command(command, command_style)
        elif device_type == DeviceType.SWITCH.value:
            return DeviceCommandAdapter._adapt_switch_command(command, command_style)
        elif device_type == DeviceType.SERVER.value:
            return DeviceCommandAdapter._adapt_server_command(command, command_style)
        else:
            return command  # 默认不适配

    @staticmethod
    def _adapt_router_command(command: str, command_style: str) -> str:
        """适配路由器命令"""
        if command_style == CommandStyle.CISCO_IOS.value:
            # Cisco IOS命令适配
            if 'show version' in command:
                return 'show version'  # Cisco直接支持
            elif 'show running-config' in command:
                return 'show running-config'
            elif 'reload' in command:
                return command  # 重启命令直接使用
            else:
                return command  # 其他命令直接使用

        elif command_style == CommandStyle.HUAWEI_VRP.value:
            # Huawei VRP命令适配
            if 'show version' in command:
                return 'display version'  # Huawei用display
            elif 'show running-config' in command:
                return 'display current-configuration'
            else:
                # 将show转换为display
                return command.replace('show ', 'display ')

        elif command_style == CommandStyle.ARUBAOS.value:
            # Aruba OS命令适配 - 🆕 新增
            return DeviceCommandAdapter._adapt_aruba_command(command)

        return command

    @staticmethod
    def _adapt_switch_command(command: str, command_style: str) -> str:
        """适配交换机命令"""
        # 交换机命令适配与路由器类似
        if command_style == CommandStyle.CISCO_IOS.value:
            return DeviceCommandAdapter._adapt_cisco_command(command)
        elif command_style == CommandStyle.HUAWEI_VRP.value:
            return DeviceCommandAdapter._adapt_huawei_command(command)
        elif command_style == CommandStyle.ARUBAOS.value:
            # Aruba交换机也使用Aruba命令适配 - 🆕 新增
            return DeviceCommandAdapter._adapt_aruba_command(command)
        else:
            return command

    @staticmethod
    def _adapt_server_command(command: str, command_style: str) -> str:
        """适配服务器命令"""
        # Linux服务器命令通常不需要适配
        return command

    @staticmethod
    def _adapt_cisco_command(command: str) -> str:
        """Cisco命令适配"""
        # Cisco IOS命令风格适配
        return command

    @staticmethod
    def _adapt_huawei_command(command: str) -> str:
        """Huawei命令适配"""
        # Huawei VRP命令风格适配
        if command.startswith('show '):
            return command.replace('show ', 'display ')
        return command

    @staticmethod
    def _adapt_aruba_command(command: str) -> str:
        """Aruba命令适配 - 🆕 Aruba设备支持"""
        # Aruba OS 特殊命令映射表
        aruba_command_mapping = {
            # 配置保存命令适配
            'copy running-config startup-config': 'write memory',
            'copy running-config startup': 'write memory',
            'write memory': 'write memory',

            # 接口显示命令适配
            'show interface status': 'show interface brief',
            'show interfaces status': 'show interface brief',
            'show interface brief': 'show interface brief',

            # Aruba 特有巡检命令（保持不变）
            'show ap database': 'show ap database',
            'show ap client summary': 'show ap client summary',
            'show user-table': 'show user-table',
            'show wlan ssid': 'show wlan ssid',
        }

        # 组合命令/管道命令保持原样，避免误改写复杂语句
        complex_separators = ['&&', '||', ';', '|', '\\n', '\\r']
        if any(sep in command for sep in complex_separators):
            return command

        # 精确匹配优先
        if command in aruba_command_mapping:
            return aruba_command_mapping[command]

        # 单命令的保守适配
        if command == 'show version':
            return 'show version'  # Aruba 支持
        elif command == 'show running-config':
            return 'show running-config'  # Aruba 支持
        elif command == 'reload':
            return command  # 重启命令通用
        elif command.startswith('show ap '):
            return command  # AP相关命令保持原样
        elif command.startswith('show wlan '):
            return command  # 无线相关命令保持原样
        else:
            return command  # 默认不转换


class DeviceCapabilities:
    """设备能力定义 - 每类设备支持的操作"""

    ROUTER_CAPABILITIES = {
        'show_version': True,
        'show_interface': True,
        'show_route': True,
        'show_config': True,
        'restart_service': False,  # 路由器通常不支持systemd
        'install_package': False,
        'rollback_config': True,
        'ping_test': True,
        'traceroute': True
    }

    SWITCH_CAPABILITIES = {
        'show_version': True,
        'show_interface': True,
        'show_vlan': True,
        'show_port_status': True,
        'restart_service': False,
        'install_package': False,
        'rollback_config': True,
        'configure_port': True,
        'port_statistics': True
    }

    SERVER_CAPABILITIES = {
        'show_version': True,
        'show_disk': True,
        'show_memory': True,
        'show_process': True,
        'restart_service': True,   # 服务器支持systemd
        'install_package': True,    # 服务器支持包管理
        'rollback_config': False,   # 服务器通常不支持配置回滚
        'inspect_system': True,
        'log_management': True
    }

    # 🆕 Aruba 无线控制器特有能力
    ARUBA_CONTROLLER_CAPABILITIES = {
        'show_version': True,
        'show_interface': True,
        'show_ap_database': True,        # Aruba 特有
        'show_client_summary': True,     # Aruba 特有
        'show_wlan_ssid': True,          # Aruba 特有
        'show_user_table': True,         # Aruba 特有
        'restart_service': False,
        'install_package': False,
        'rollback_config': True,
        'configure_ssid': True,          # Aruba 特有
        'ap_management': True,           # Aruba 特有
        'client_management': True,       # Aruba 特有
        'ping_test': True,
        'traceroute': True
    }

    # 🆕 Aruba 交换机能力
    ARUBA_SWITCH_CAPABILITIES = {
        'show_version': True,
        'show_interface': True,
        'show_vlan': True,
        'show_port_status': True,
        'restart_service': False,
        'install_package': False,
        'rollback_config': True,
        'configure_port': True,
        'port_statistics': True,
        'lldp_neighbors': True,          # Aruba 增强
        'interface_stats': True          # Aruba 增强
    }

    @staticmethod
    def get_capabilities(device_type: str, vendor: str = None) -> dict:
        """获取设备能力 - 🆕 支持厂商特定能力"""
        device_type = device_type.lower()
        vendor = vendor.lower() if vendor else None

        # Aruba/HPE/HP 别名统一归一为 Aruba 逻辑
        if vendor in ['aruba', 'hpe', 'hp']:
            vendor = 'aruba'

        # Aruba 特殊处理 - 🆕 新增
        if vendor == 'aruba':
            if device_type == DeviceType.ROUTER.value:  # Aruba 无线控制器
                return DeviceCapabilities.ARUBA_CONTROLLER_CAPABILITIES.copy()
            elif device_type == DeviceType.SWITCH.value:  # Aruba 交换机
                return DeviceCapabilities.ARUBA_SWITCH_CAPABILITIES.copy()

        # 标准设备类型处理
        if device_type == DeviceType.ROUTER.value:
            return DeviceCapabilities.ROUTER_CAPABILITIES.copy()
        elif device_type == DeviceType.SWITCH.value:
            return DeviceCapabilities.SWITCH_CAPABILITIES.copy()
        elif device_type == DeviceType.SERVER.value:
            return DeviceCapabilities.SERVER_CAPABILITIES.copy()
        else:
            return {}  # 未知设备类型

    @staticmethod
    def supports_capability(device_type: str, capability: str) -> bool:
        """检查设备是否支持特定能力"""
        capabilities = DeviceCapabilities.get_capabilities(device_type)
        return capabilities.get(capability, False)


class DeviceValidator:
    """设备验证器 - 验证设备配置的合法性"""

    @staticmethod
    def validate_router_config(config: dict) -> tuple[bool, list[str]]:
        """验证路由器配置"""
        errors = []

        # 必需字段检查
        required_fields = ['hostname', 'vendor', 'ssh_port', 'ssh_user']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        # 厂商检查
        valid_vendors = ['cisco', 'huawei', 'juniper', 'h3c', 'aruba', 'hpe', 'hp']  # 🆕 新增 Aruba
        if config.get('vendor') and config['vendor'].lower() not in valid_vendors:
            errors.append(f"Unsupported vendor: {config.get('vendor')}")

        # SSH配置检查
        if 'ssh_port' in config and not (1 <= config['ssh_port'] <= 65535):
            errors.append(f"Invalid SSH port: {config['ssh_port']}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_switch_config(config: dict) -> tuple[bool, list[str]]:
        """验证交换机配置"""
        errors = []

        # 必需字段检查
        required_fields = ['hostname', 'vendor', 'ssh_port', 'ssh_user', 'ports']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        # 端口数量检查
        if 'ports' in config and not (1 <= config['ports'] <= 1024):
            errors.append(f"Invalid port count: {config['ports']}")

        # 厂商检查（与路由器相同）
        valid_vendors = ['cisco', 'huawei', 'juniper', 'h3c', 'aruba', 'hpe', 'hp']  # 🆕 新增 Aruba
        if config.get('vendor') and config['vendor'].lower() not in valid_vendors:
            errors.append(f"Unsupported vendor: {config.get('vendor')}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_server_config(config: dict) -> tuple[bool, list[str]]:
        """验证服务器配置"""
        errors = []

        # 必需字段检查
        required_fields = ['hostname', 'ssh_port', 'ssh_user']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        # 操作系统类型检查
        valid_os_types = ['linux', 'windows', 'bsd']
        if config.get('os_type') and config['os_type'].lower() not in valid_os_types:
            errors.append(f"Unsupported OS type: {config.get('os_type')}")

        # SSH密钥检查（服务器主要用密钥）
        if 'login_type' in config and config['login_type'] == 'key':
            if 'ssh_private_key_path' not in config:
                errors.append("SSH login type 'key' requires ssh_private_key_path")
            elif not config['ssh_private_key_path']:
                errors.append("SSH login type 'key' requires non-empty ssh_private_key_path")
            elif not isinstance(config['ssh_private_key_path'], str):
                errors.append("ssh_private_key_path must be a string")

        return len(errors) == 0, errors

    @staticmethod
    def validate_device_config(device_type: str, config: dict) -> tuple[bool, list[str]]:
        """通用设备配置验证"""
        device_type = device_type.lower()

        if device_type == DeviceType.ROUTER.value:
            return DeviceValidator.validate_router_config(config)
        elif device_type == DeviceType.SWITCH.value:
            return DeviceValidator.validate_switch_config(config)
        elif device_type == DeviceType.SERVER.value:
            return DeviceValidator.validate_server_config(config)
        else:
            return False, [f"Unsupported device type: {device_type}"]