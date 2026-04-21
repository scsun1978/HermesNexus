"""
设备管理器测试 - Week 4 Day 1-2
"""
import pytest
import tempfile
import os
from hermesnexus.device.manager import DeviceManager, DeviceCommandGenerator
from hermesnexus.device.types import DeviceType


class TestDeviceManager:
    """设备管理器测试"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)

    @pytest.fixture
    def device_manager(self, temp_db):
        """创建设备管理器"""
        return DeviceManager(temp_db)

    def test_database_initialization(self, device_manager):
        """测试数据库初始化"""
        import sqlite3
        conn = sqlite3.connect(device_manager.db_path)
        cursor = conn.cursor()

        # 检查devices表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devices'")
        assert cursor.fetchone() is not None

        # 检查device_types表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='device_types'")
        assert cursor.fetchone() is not None

        # 检查设备类型数据
        cursor.execute("SELECT COUNT(*) FROM device_types")
        count = cursor.fetchone()[0]
        assert count >= 3  # 至少有3种设备类型

        conn.close()

    def test_register_router_device(self, device_manager):
        """测试注册路由器设备 - MVP验收"""
        router_config = {
            'device_type': 'router',
            'hostname': 'core-router-01',
            'vendor': 'cisco',
            'ssh_port': 22,
            'ssh_user': 'admin',
            'node_id': 'router-001'
        }

        success, message, device_id = device_manager.register_device(router_config)

        assert success is True
        assert device_id == 'router-001'
        assert '注册成功' in message

        # 验证设备已注册
        device = device_manager.get_device(device_id)
        assert device is not None
        assert device['device_type'] == 'router'
        assert device['hostname'] == 'core-router-01'
        assert device['vendor'] == 'cisco'

    def test_register_switch_device(self, device_manager):
        """测试注册交换机设备 - MVP验收"""
        switch_config = {
            'device_type': 'switch',
            'hostname': 'access-switch-01',
            'vendor': 'cisco',
            'ssh_port': 22,
            'ssh_user': 'admin',
            'node_id': 'switch-001',
            'ports': 48
        }

        success, message, device_id = device_manager.register_device(switch_config)

        assert success is True
        assert device_id == 'switch-001'

        device = device_manager.get_device(device_id)
        assert device['device_type'] == 'switch'
        assert device['ports'] == 48

    def test_register_server_device(self, device_manager):
        """测试注册服务器设备 - MVP验收"""
        server_config = {
            'device_type': 'server',
            'hostname': 'web-server-01',
            'ssh_port': 22,
            'ssh_user': 'root',
            'node_id': 'server-001',
            'os_type': 'linux',
            'ssh_private_key_path': '/home/user/.ssh/id_rsa'  # 提供密钥路径，使用key登录
        }

        success, message, device_id = device_manager.register_device(server_config)

        assert success is True
        assert device_id == 'server-001'

        device = device_manager.get_device(device_id)
        assert device['device_type'] == 'server'
        assert device['login_type'] == 'key'  # 提供密钥路径时使用key登录

    def test_register_server_device_without_key(self, device_manager):
        """测试注册服务器设备（无密钥）- 自动使用密码登录"""
        server_config = {
            'device_type': 'server',
            'hostname': 'web-server-02',
            'ssh_port': 22,
            'ssh_user': 'root',
            'node_id': 'server-002',
            'os_type': 'linux'
            # 没有提供 ssh_private_key_path
        }

        success, message, device_id = device_manager.register_device(server_config)

        assert success is True

        device = device_manager.get_device(device_id)
        assert device['device_type'] == 'server'
        assert device['login_type'] == 'password'  # 无密钥时自动使用密码登录

    def test_register_invalid_device_config(self, device_manager):
        """测试注册无效设备配置"""
        invalid_config = {
            'device_type': 'router',
            'hostname': 'invalid-device',
            # 缺少vendor, ssh_port, ssh_user
        }

        success, message, device_id = device_manager.register_device(invalid_config)

        assert success is False
        assert device_id is None
        assert '验证失败' in message or '配置验证失败' in message

    def test_list_devices_by_type(self, device_manager):
        """测试按类型列出设备"""
        # 注册多个设备
        devices = [
            {'device_type': 'router', 'hostname': 'router-01', 'vendor': 'cisco', 'ssh_port': 22, 'ssh_user': 'admin', 'node_id': 'router-001'},
            {'device_type': 'router', 'hostname': 'router-02', 'vendor': 'huawei', 'ssh_port': 22, 'ssh_user': 'admin', 'node_id': 'router-002'},
            {'device_type': 'switch', 'hostname': 'switch-01', 'vendor': 'cisco', 'ssh_port': 22, 'ssh_user': 'admin', 'node_id': 'switch-001', 'ports': 24},
            {'device_type': 'server', 'hostname': 'server-01', 'ssh_port': 22, 'ssh_user': 'root', 'node_id': 'server-001'}
        ]

        for config in devices:
            device_manager.register_device(config)

        # 列出路由器设备
        routers = device_manager.list_devices(device_type='router')
        assert len(routers) == 2
        for router in routers:
            assert router['device_type'] == 'router'

        # 列出交换机设备
        switches = device_manager.list_devices(device_type='switch')
        assert len(switches) == 1

        # 列出服务器设备
        servers = device_manager.list_devices(device_type='server')
        assert len(servers) == 1

    def test_update_device_status(self, device_manager):
        """测试更新设备状态"""
        router_config = {
            'device_type': 'router',
            'hostname': 'router-01',
            'vendor': 'cisco',
            'ssh_port': 22,
            'ssh_user': 'admin',
            'node_id': 'router-001'
        }

        success, message, device_id = device_manager.register_device(router_config)
        assert success is True

        # 更新设备状态
        result = device_manager.update_device_status(device_id, 'online')
        assert result is True

        # 验证状态已更新
        device = device_manager.get_device(device_id)
        assert device['status'] == 'online'
        assert device['last_seen'] is not None

    def test_get_device_capabilities(self, device_manager):
        """测试获取设备能力"""
        server_config = {
            'device_type': 'server',
            'hostname': 'server-01',
            'ssh_port': 22,
            'ssh_user': 'root',
            'node_id': 'server-001',
            'os_type': 'linux'
        }

        success, message, device_id = device_manager.register_device(server_config)
        assert success is True

        capabilities = device_manager.get_device_capabilities(device_id)

        assert capabilities['restart_service'] is True
        assert capabilities['install_package'] is True
        assert capabilities['rollback_config'] is False

    def test_get_nonexistent_device(self, device_manager):
        """测试获取不存在的设备"""
        device = device_manager.get_device('nonexistent-device')
        assert device is None


class TestDeviceCommandGenerator:
    """设备命令生成器测试"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)

    @pytest.fixture
    def device_manager(self, temp_db):
        """创建设备管理器"""
        return DeviceManager(temp_db)

    @pytest.fixture
    def command_generator(self, device_manager):
        """创建命令生成器"""
        return DeviceCommandGenerator(device_manager)

    def test_generate_router_inspection_command(self, device_manager, command_generator):
        """生成路由器巡检命令"""
        # 注册Cisco路由器
        router_config = {
            'device_type': 'router',
            'hostname': 'router-01',
            'vendor': 'cisco',
            'ssh_port': 22,
            'ssh_user': 'admin',
            'node_id': 'router-001'
        }
        device_manager.register_device(router_config)

        # 生成巡检命令
        command = command_generator.generate_inspection_command('router-001')

        assert 'show version' in command
        assert 'show ip' in command or 'display' in command

    def test_generate_switch_inspection_command(self, device_manager, command_generator):
        """生成交换机巡检命令"""
        switch_config = {
            'device_type': 'switch',
            'hostname': 'switch-01',
            'vendor': 'cisco',
            'ssh_port': 22,
            'ssh_user': 'admin',
            'node_id': 'switch-001',
            'ports': 48
        }
        device_manager.register_device(switch_config)

        command = command_generator.generate_inspection_command('switch-001')

        assert 'show version' in command or 'display version' in command
        assert 'interface' in command.lower()

    def test_generate_server_inspection_command(self, device_manager, command_generator):
        """生成服务器巡检命令"""
        server_config = {
            'device_type': 'server',
            'hostname': 'server-01',
            'ssh_port': 22,
            'ssh_user': 'root',
            'node_id': 'server-001',
            'os_type': 'linux'
        }
        device_manager.register_device(server_config)

        command = command_generator.generate_inspection_command('server-001')

        assert 'uptime' in command
        assert 'df -h' in command
        assert 'free -h' in command

    def test_generate_command_for_nonexistent_device(self, command_generator):
        """测试为不存在的设备生成命令"""
        with pytest.raises(ValueError, match="Device not found"):
            command_generator.generate_command('nonexistent-device', 'echo test')

    def test_adapt_command_for_device_vendor(self, device_manager, command_generator):
        """测试不同厂商的命令适配"""
        # 注册Cisco设备
        cisco_config = {
            'device_type': 'router',
            'hostname': 'cisco-device',
            'vendor': 'cisco',
            'ssh_port': 22,
            'ssh_user': 'admin',
            'node_id': 'cisco-001'
        }
        device_manager.register_device(cisco_config)

        # 注册Huawei设备
        huawei_config = {
            'device_type': 'router',
            'hostname': 'huawei-device',
            'vendor': 'huawei',
            'ssh_port': 22,
            'ssh_user': 'admin',
            'node_id': 'huawei-001'
        }
        device_manager.register_device(huawei_config)

        # Cisco命令保持不变
        cisco_command = command_generator.generate_command('cisco-001', 'show version')
        assert cisco_command == 'show version'

        # Huawei命令转换为display
        huawei_command = command_generator.generate_command('huawei-001', 'show version')
        assert 'display version' in huawei_command


class TestMVPDeviceTypesAcceptance:
    """MVP 3类设备验收测试"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)

    @pytest.fixture
    def device_manager(self, temp_db):
        """创建设备管理器"""
        return DeviceManager(temp_db)

    def test_mvp_three_device_types_registration(self, device_manager):
        """MVP 3类设备注册验收"""
        # 1. 注册路由器设备
        router_config = {
            'device_type': 'router',
            'hostname': 'core-router',
            'vendor': 'cisco',
            'ssh_port': 22,
            'ssh_user': 'admin',
            'node_id': 'router-mvp'
        }
        success, message, router_id = device_manager.register_device(router_config)
        assert success is True
        assert router_id == 'router-mvp'

        # 2. 注册交换机设备
        switch_config = {
            'device_type': 'switch',
            'hostname': 'access-switch',
            'vendor': 'cisco',
            'ssh_port': 22,
            'ssh_user': 'admin',
            'node_id': 'switch-mvp',
            'ports': 24
        }
        success, message, switch_id = device_manager.register_device(switch_config)
        assert success is True
        assert switch_id == 'switch-mvp'

        # 3. 注册服务器设备
        server_config = {
            'device_type': 'server',
            'hostname': 'web-server',
            'ssh_port': 22,
            'ssh_user': 'root',
            'node_id': 'server-mvp',
            'os_type': 'linux'
        }
        success, message, server_id = device_manager.register_device(server_config)
        assert success is True
        assert server_id == 'server-mvp'

        # 验证所有设备都成功注册
        all_devices = device_manager.list_devices()
        assert len(all_devices) == 3

        # 验证设备类型分布
        router_count = len(device_manager.list_devices(device_type='router'))
        switch_count = len(device_manager.list_devices(device_type='switch'))
        server_count = len(device_manager.list_devices(device_type='server'))

        assert router_count == 1
        assert switch_count == 1
        assert server_count == 1

        print("✅ MVP 3类设备注册验收通过")
        print(f"   路由器: {router_count}台")
        print(f"   交换机: {switch_count}台")
        print(f"   服务器: {server_count}台")

    def test_mvp_device_type_distinction(self, device_manager):
        """MVP 设备类型区分验收"""
        # 注册3类设备
        devices = [
            ('router', {'device_type': 'router', 'hostname': 'router-01', 'vendor': 'cisco', 'ssh_port': 22, 'ssh_user': 'admin'}),
            ('switch', {'device_type': 'switch', 'hostname': 'switch-01', 'vendor': 'cisco', 'ssh_port': 22, 'ssh_user': 'admin', 'ports': 24}),
            ('server', {'device_type': 'server', 'hostname': 'server-01', 'ssh_port': 22, 'ssh_user': 'root', 'os_type': 'linux'})
        ]

        device_ids = []
        for device_type, config in devices:
            config['node_id'] = f'{device_type}-mvp'
            success, message, device_id = device_manager.register_device(config)
            assert success is True
            device_ids.append(device_id)

        # 验证每类设备的特性
        for device_id in device_ids:
            device = device_manager.get_device(device_id)
            capabilities = device_manager.get_device_capabilities(device_id)

            # 路由器特性
            if device['device_type'] == 'router':
                assert capabilities['show_route'] is True
                assert capabilities['restart_service'] is False

            # 交换机特性
            elif device['device_type'] == 'switch':
                assert capabilities['show_vlan'] is True
                assert capabilities['configure_port'] is True

            # 服务器特性
            elif device['device_type'] == 'server':
                assert capabilities['restart_service'] is True
                assert capabilities['install_package'] is True

        print("✅ MVP 设备类型区分验收通过")
        print(f"   每类设备都有独特的能力特征")
        print(f"   设备类型在数据库中有明确标识")

    def test_mvp_command_style_differentiation(self, device_manager):
        """MVP 命令风格差异化验收"""
        command_generator = DeviceCommandGenerator(device_manager)

        # 注册不同厂商的路由器
        cisco_router = {
            'device_type': 'router',
            'hostname': 'cisco-router', 'vendor': 'cisco', 'ssh_port': 22,
            'ssh_user': 'admin', 'node_id': 'cisco-router'
        }
        huawei_router = {
            'device_type': 'router',
            'hostname': 'huawei-router', 'vendor': 'huawei', 'ssh_port': 22,
            'ssh_user': 'admin', 'node_id': 'huawei-router'
        }

        device_manager.register_device(cisco_router)
        device_manager.register_device(huawei_router)

        # 生成巡检命令并验证差异
        cisco_command = command_generator.generate_inspection_command('cisco-router')
        huawei_command = command_generator.generate_inspection_command('huawei-router')

        # Cisco使用show命令
        assert 'show version' in cisco_command

        # Huawei使用display命令
        assert 'display version' in huawei_command or 'display' in huawei_command

        print("✅ MVP 命令风格差异化验收通过")
        print(f"   Cisco风格: {cisco_command[:50]}...")
        print(f"   Huawei风格: {huawei_command[:50]}...")