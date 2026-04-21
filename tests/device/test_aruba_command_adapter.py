"""
Aruba命令适配器单元测试 - Phase 4B
测试Aruba设备命令适配功能
"""
import pytest
from hermesnexus.device.types import DeviceCommandAdapter, CommandStyle, DeviceTypeFactory


class TestArubaCommandAdapter:
    """Aruba命令适配器测试套件"""

    def test_aruba_config_save_command(self):
        """测试Aruba配置保存命令适配 - 核心功能"""
        cisco_command = "copy running-config startup-config"
        aruba_adapted = DeviceCommandAdapter._adapt_aruba_command(cisco_command)
        assert aruba_adapted == "write memory", f"Expected 'write memory', got '{aruba_adapted}'"
        print(f"✅ 配置保存命令适配: '{cisco_command}' → '{aruba_adapted}'")

    def test_aruba_interface_status_command(self):
        """测试Aruba接口状态命令适配 - 核心功能"""
        cisco_command = "show interface status"
        aruba_adapted = DeviceCommandAdapter._adapt_aruba_command(cisco_command)
        assert aruba_adapted == "show interface brief", f"Expected 'show interface brief', got '{aruba_adapted}'"
        print(f"✅ 接口状态命令适配: '{cisco_command}' → '{aruba_adapted}'")

    def test_aruba_specific_commands(self):
        """测试Aruba特有命令保持不变 - 核心功能"""
        aruba_commands = [
            "show ap database",
            "show ap client summary",
            "show wlan ssid",
            "show user-table"
        ]

        for cmd in aruba_commands:
            adapted = DeviceCommandAdapter._adapt_aruba_command(cmd)
            assert adapted == cmd, f"Aruba特有命令应保持不变: '{cmd}' ≠ '{adapted}'"
            print(f"✅ Aruba特有命令保持不变: '{cmd}'")

    def test_aruba_reload_command(self):
        """测试重启命令兼容性 - 兼容性测试"""
        reload_cmd = "reload"
        adapted = DeviceCommandAdapter._adapt_aruba_command(reload_cmd)
        assert adapted == reload_cmd, f"重启命令应保持不变: '{reload_cmd}' ≠ '{adapted}'"
        print(f"✅ 重启命令兼容性: '{reload_cmd}'")

    def test_aruba_show_commands(self):
        """测试通用show命令兼容性 - 兼容性测试"""
        show_commands = [
            "show version",
            "show running-config",
            "show interface"
        ]

        for cmd in show_commands:
            adapted = DeviceCommandAdapter._adapt_aruba_command(cmd)
            assert cmd in adapted, f"show命令应包含原命令: '{cmd}' not in '{adapted}'"
            print(f"✅ show命令兼容: '{cmd}' → '{adapted}'")

    def test_aruba_combined_commands(self):
        """测试组合命令适配 - 复杂场景测试"""
        combined_cmd = "show version && show ap database && show interface brief"
        adapted = DeviceCommandAdapter._adapt_aruba_command(combined_cmd)
        # 组合命令应该保持不变，因为我们只适配精确匹配的命令
        assert "show version" in adapted
        assert "show ap database" in adapted
        print(f"✅ 组合命令处理: '{combined_cmd}' → '{adapted}'")

    def test_aruba_device_factory_integration(self):
        """测试Aruba设备工厂集成 - 集成测试"""
        aruba_config = {
            'hostname': 'aruba-master-01',
            'vendor': 'aruba',
            'model': '7200',
            'ssh_user': 'admin',
            'ssh_port': 22,
            'device_type': 'router'
        }

        # 创建设备配置
        device_config = DeviceTypeFactory.create_router_config(aruba_config)

        # 验证命令风格检测
        assert device_config['command_style'] == CommandStyle.ARUBAOS.value, \
            f"Expected ArubaOS style, got {device_config['command_style']}"

        # 验证厂商字段
        assert device_config['vendor'] == 'aruba'

        print(f"✅ Aruba设备工厂集成测试通过: {device_config['command_style']}")

    def test_aruba_switch_detection(self):
        """测试Aruba交换机检测 - 集成测试"""
        aruba_switch_config = {
            'hostname': 'aruba-switch-01',
            'vendor': 'aruba',
            'model': '2930F',
            'ssh_user': 'admin',
            'ssh_port': 22,
            'ports': 48,
            'device_type': 'switch'
        }

        device_config = DeviceTypeFactory.create_switch_config(aruba_switch_config)

        # 验证命令风格
        assert device_config['command_style'] == CommandStyle.ARUBAOS.value

        # 验证端口数量
        assert device_config['ports'] == 48

        print(f"✅ Aruba交换机检测测试通过: {device_config['model']}")

    def test_hpe_alias_detection(self):
        """测试HPE厂商别名检测 - 兼容性测试"""
        hpe_aliases = ['hpe', 'hp']

        for alias in hpe_aliases:
            config = {
                'hostname': 'hpe-switch-01',
                'vendor': alias,
                'model': '2930F',
                'ssh_user': 'admin',
                'ssh_port': 22,
                'device_type': 'switch'
            }

            device_config = DeviceTypeFactory.create_switch_config(config)
            assert device_config['command_style'] == CommandStyle.ARUBAOS.value, \
                f"HPE别名 '{alias}' 应检测为ArubaOS"

            print(f"✅ HPE别名检测: '{alias}' → {device_config['command_style']}")

    def test_aruba_command_adapter_full_workflow(self):
        """测试Aruba命令适配完整工作流 - 端到端测试"""
        # 1. 创建Aruba设备配置
        aruba_config = {
            'hostname': 'aruba-test-01',
            'vendor': 'aruba',
            'model': '7010',
            'ssh_user': 'admin',
            'ssh_port': 22,
            'device_type': 'router'
        }

        device_config = DeviceTypeFactory.create_router_config(aruba_config)

        # 2. 测试各种命令适配
        test_commands = [
            ("copy running-config startup-config", "write memory"),
            ("show interface status", "show interface brief"),
            ("show version", "show version"),
            ("show ap database", "show ap database"),
            ("reload", "reload")
        ]

        for original_cmd, expected_adapted in test_commands:
            adapted_cmd = DeviceCommandAdapter.adapt_command_for_device(
                original_cmd, device_config
            )
            assert adapted_cmd == expected_adapted, \
                f"命令适配错误: '{original_cmd}' → '{adapted_cmd}' (期望: '{expected_adapted}')"
            print(f"✅ 命令适配: '{original_cmd}' → '{adapted_cmd}'")

        print(f"✅ Aruba命令适配完整工作流测试通过")


class TestArubaDeviceCapabilities:
    """Aruba设备能力测试"""

    def test_aruba_controller_capabilities(self):
        """测试Aruba无线控制器能力 - 功能测试"""
        from hermesnexus.device.types import DeviceCapabilities, DeviceType

        # 获取Aruba控制器能力
        capabilities = DeviceCapabilities.get_capabilities(
            DeviceType.ROUTER.value,
            vendor='aruba'
        )

        # 验证Aruba特有能力
        assert capabilities['show_ap_database'] == True, "应支持AP数据库查询"
        assert capabilities['show_client_summary'] == True, "应支持客户端摘要"
        assert capabilities['configure_ssid'] == True, "应支持SSID配置"
        assert capabilities['ap_management'] == True, "应支持AP管理"

        # 验证基础能力
        assert capabilities['show_version'] == True, "应支持版本查询"
        assert capabilities['rollback_config'] == True, "应支持配置回滚"

        print(f"✅ Aruba控制器能力验证通过")

    def test_aruba_switch_capabilities(self):
        """测试Aruba交换机能力 - 功能测试"""
        from hermesnexus.device.types import DeviceCapabilities, DeviceType

        capabilities = DeviceCapabilities.get_capabilities(
            DeviceType.SWITCH.value,
            vendor='aruba'
        )

        # 验证Aruba交换机增强能力
        assert capabilities['lldp_neighbors'] == True, "应支持LLDP邻居查询"
        assert capabilities['interface_stats'] == True, "应支持接口统计"

        # 验证标准交换机能力
        assert capabilities['show_vlan'] == True, "应支持VLAN查询"
        assert capabilities['configure_port'] == True, "应支持端口配置"

        print(f"✅ Aruba交换机能力验证通过")

    def test_standard_router_vs_aruba_controller(self):
        """测试标准路由器vs Aruba控制器能力对比 - 兼容性测试"""
        from hermesnexus.device.types import DeviceCapabilities, DeviceType

        # 标准路由器能力
        standard_caps = DeviceCapabilities.get_capabilities(DeviceType.ROUTER.value)

        # Aruba控制器能力
        aruba_caps = DeviceCapabilities.get_capabilities(
            DeviceType.ROUTER.value,
            vendor='aruba'
        )

        # HPE/HP 别名也应映射到 Aruba 能力
        hpe_caps = DeviceCapabilities.get_capabilities(
            DeviceType.ROUTER.value,
            vendor='hpe'
        )
        hp_caps = DeviceCapabilities.get_capabilities(
            DeviceType.ROUTER.value,
            vendor='hp'
        )

        # Aruba应该有额外的能力
        assert 'show_ap_database' not in standard_caps, "标准路由器不应有AP数据库能力"
        assert 'show_ap_database' in aruba_caps, "Aruba控制器应有AP数据库能力"
        assert 'show_ap_database' in hpe_caps, "HPE别名应有Aruba控制器能力"
        assert 'show_ap_database' in hp_caps, "HP别名应有Aruba控制器能力"

        # 但都应该有基础能力
        assert standard_caps['show_version'] == aruba_caps['show_version'], "基础能力应保持一致"
        assert aruba_caps['show_version'] == hpe_caps['show_version'] == hp_caps['show_version'], "别名基础能力应保持一致"

        print(f"✅ 标准/Aruba能力对比验证通过")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
