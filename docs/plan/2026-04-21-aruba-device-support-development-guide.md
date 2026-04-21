# Aruba 设备支持开发文档

**Phase**: 4B - Device Vendor Extension  
**Target**: Add Aruba device support  
**Version**: 1.0.0  
**Date**: 2026-04-21  

---

## 📋 项目概述

### 目标
在现有 HermesNexus MVP 系统中增加 Aruba 厂商设备支持，扩展系统能够管理 Aruba 网络设备。

### 范围
- **新增厂商**: Aruba (HPE Aruba Networking)
- **支持设备类型**: 
  - Aruba Mobility Controller (无线控制器)
  - Aruba Switch (交换机)
  - Aruba Instant AP (无线接入点)
- **核心功能**: 巡检、配置管理、设备重启、状态监控

---

## 🔍 现有架构分析

### 当前支持的厂商
```python
# 现有 CommandStyle 枚举 (hermesnexus/device/types.py)
class CommandStyle(Enum):
    CISCO_IOS = "cisco_ios"      # Cisco 设备
    HUAWEI_VRP = "huawei_vrp"    # Huawei 设备  
    LINUX_BASH = "linux_bash"    # Linux 服务器
    JUNOS = "junos"              # Juniper 设备
```

### 设备适配架构
```
┌─────────────────────────────────────┐
│   DeviceTypeFactory                  │
│   - create_router_config()           │
│   - create_switch_config()           │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│   DeviceCommandAdapter               │
│   - adapt_command_for_device()       │
│   - _adapt_cisco_command()           │
│   - _adapt_huawei_command()          │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│   DeviceValidator                    │
│   - validate_router_config()         │
│   - validate_switch_config()         │
└─────────────────────────────────────┘
```

---

## 🎯 Aruba 设备特性分析

### Aruba 产品线

#### 1. Aruba Mobility Controller (无线控制器)
- **操作系统**: Aruba OS (AOS)
- **命令风格**: 类似 Cisco IOS，但有独特命令
- **主要型号**: 7200, 7010, 6000 系列

#### 2. Aruba Switch (交换机)  
- **操作系统**: Aruba OS-Switch (基于 ProCurve)
- **命令风格**: 类似 Cisco IOS + HP ProCurve
- **主要型号**: 2930F, 3830, 5400R 系列

#### 3. Aruba Instant AP (无线接入点)
- **操作系统**: Aruba Instant
- **命令风格**: 简化版 Aruba OS
- **主要型号**: AP-303, AP-505, AP-515 系列

### Aruba 命令特点

#### vs Cisco IOS 差异
| **功能** | **Cisco IOS** | **Aruba OS** | **适配需求** |
|----------|--------------|--------------|--------------|
| 显示版本 | `show version` | `show version` | ✅ 兼容 |
| 运行配置 | `show running-config` | `show running-config` | ✅ 兼容 |
| 保存配置 | `copy running-config startup-config` | `write memory` | ❌ 需适配 |
| 接口状态 | `show interface status` | `show interface brief` | ❌ 需适配 |
| 系统重启 | `reload` | `reload` | ✅ 兼容 |

#### Aruba 特有命令
```bash
# Aruba 特有的无线管理命令
show ap database                    # 显示AP数据库
show ap client summary              # 显示客户端摘要
show user-table                     # 显示用户表
show wlan ssid                      # 显示无线网络

# Aruba 特有配置命令
wlan ssid-profile <name>            # 配置SSID
ap group <groupname>                # 配置AP组
ap profile <profilename>            # 配置AP配置文件
```

---

## 🛠️ 技术实现方案

### 1. 扩展 CommandStyle 枚举

```python
# hermesnexus/device/types.py

class CommandStyle(Enum):
    CISCO_IOS = "cisco_ios"
    HUAWEI_VRP = "huawei_vrp" 
    LINUX_BASH = "linux_bash"
    JUNOS = "junos"
    ARUBAOS = "arubaos"           # 🆕 新增 Aruba OS
```

### 2. 扩展 DeviceCommandAdapter

```python
class DeviceCommandAdapter:
    """设备命令适配器 - 增加Aruba支持"""
    
    @staticmethod
    def _adapt_router_command(command: str, command_style: str) -> str:
        """适配路由器命令 - 扩展Aruba支持"""
        if command_style == CommandStyle.ARUBAOS.value:
            return DeviceCommandAdapter._adapt_aruba_command(command)
        # ... 现有代码 ...
    
    @staticmethod
    def _adapt_switch_command(command: str, command_style: str) -> str:
        """适配交换机命令 - 扩展Aruba支持"""
        if command_style == CommandStyle.ARUBAOS.value:
            return DeviceCommandAdapter._adapt_aruba_command(command)
        # ... 现有代码 ...
    
    @staticmethod
    def _adapt_aruba_command(command: str) -> str:
        """Aruba命令适配逻辑"""
        # Aruba OS 特殊命令映射
        aruba_command_mapping = {
            # 配置保存命令适配
            'copy running-config startup-config': 'write memory',
            'write memory': 'write memory',
            
            # 接口显示命令适配  
            'show interface status': 'show interface brief',
            'show interfaces status': 'show interface brief',
            
            # Aruba 特有巡检命令
            'show ap database': 'show ap database',
            'show ap client summary': 'show ap client summary',
        }
        
        # 精确匹配优先
        if command in aruba_command_mapping:
            return aruba_command_mapping[command]
        
        # 模式匹配（针对包含特定关键词的命令）
        if 'show version' in command:
            return 'show version'  # Aruba 支持
        elif 'show running-config' in command:
            return 'show running-config'  # Aruba 支持
        elif 'reload' in command:
            return command  # 重启命令通用
        else:
            return command  # 默认不转换
```

### 3. 扩展 DeviceTypeFactory

```python
class DeviceTypeFactory:
    """设备类型工厂 - 增加Aruba支持"""
    
    @staticmethod
    def _detect_router_command_style(host_info: dict) -> str:
        """检测路由器命令风格 - 扩展Aruba"""
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
            return CommandStyle.CISCO_IOS.value
    
    @staticmethod
    def _detect_switch_command_style(host_info: dict) -> str:
        """检测交换机命令风格 - 扩展Aruba"""
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
            return CommandStyle.CISCO_IOS.value
```

### 4. 扩展 DeviceValidator

```python
class DeviceValidator:
    """设备验证器 - 增加Aruba支持"""
    
    @staticmethod
    def validate_router_config(config: dict) -> tuple[bool, list[str]]:
        """验证路由器配置 - 扩展Aruba厂商"""
        errors = []
        
        # ... 现有验证代码 ...
        
        # 厂商检查 - 扩展支持列表
        valid_vendors = ['cisco', 'huawei', 'juniper', 'h3c', 'aruba', 'hpe', 'hp']  # 🆕 新增 Aruba
        if config.get('vendor') and config['vendor'].lower() not in valid_vendors:
            errors.append(f"Unsupported vendor: {config.get('vendor')}")
        
        return len(errors) == 0, errors
    
    @staticmethod  
    def validate_switch_config(config: dict) -> tuple[bool, list[str]]:
        """验证交换机配置 - 扩展Aruba厂商"""
        errors = []
        
        # ... 现有验证代码 ...
        
        # 厂商检查 - 扩展支持列表
        valid_vendors = ['cisco', 'huawei', 'juniper', 'h3c', 'aruba', 'hpe', 'hp']  # 🆕 新增 Aruba
        if config.get('vendor') and config['vendor'].lower() not in valid_vendors:
            errors.append(f"Unsupported vendor: {config.get('vendor')}")
        
        return len(errors) == 0, errors
```

### 5. 扩展设备能力定义

```python
class DeviceCapabilities:
    """设备能力定义 - 增加Aruba特有能力"""
    
    # 🆕 Aruba 无线控制器特有能力
    ARUBA_CONTROLLER_CAPABILITIES = {
        'show_version': True,
        'show_interface': True,
        'show_ap_database': True,        # Aruba 特有
        'show_client_summary': True,     # Aruba 特有
        'show_wlan_ssid': True,          # Aruba 特有
        'restart_service': False,
        'install_package': False,
        'rollback_config': True,
        'configure_ssid': True,          # Aruba 特有
        'ap_management': True,           # Aruba 特有
        'client_management': True,       # Aruba 特有
    }
    
    # 🆕 Aruba 交换机能力
    ARUBA_SWITCH_CAPABILITIES = {
        'show_version': True,
        'show_interface': True,
        'show_port_status': True,
        'show_vlan': True,
        'restart_service': False,
        'install_package': False,
        'rollback_config': True,
        'configure_port': True,
        'port_statistics': True,
        'lldp_neighbors': True,          # Aruba 增强
    }

    @staticmethod
    def get_capabilities(device_type: str, vendor: str = None) -> dict:
        """获取设备能力 - 扩展Aruba支持"""
        device_type = device_type.lower()
        vendor = vendor.lower() if vendor else None
        
        # Aruba 特殊处理
        if vendor == 'aruba':
            if device_type == DeviceType.ROUTER.value:  # Aruba 无线控制器
                return DeviceCapabilities.ARUBA_CONTROLLER_CAPABILITIES.copy()
            elif device_type == DeviceType.SWITCH.value:  # Aruba 交换机
                return DeviceCapabilities.ARUBA_SWITCH_CAPABILITIES.copy()
        
        # ... 现有逻辑 ...
```

---

## 🧪 测试策略

### 1. 单元测试

#### 测试文件结构
```
tests/device/
├── test_aruba_command_adapter.py      # Aruba命令适配测试
├── test_aruba_device_factory.py       # Aruba设备工厂测试
└── test_aruba_validator.py            # Aruba验证器测试
```

#### 测试用例示例
```python
# tests/device/test_aruba_command_adapter.py

import pytest
from hermesnexus.device.types import DeviceCommandAdapter, CommandStyle

class TestArubaCommandAdapter:
    """Aruba命令适配器测试"""
    
    def test_aruba_config_save_command(self):
        """测试Aruba配置保存命令适配"""
        cisco_command = "copy running-config startup-config"
        aruba_adapted = DeviceCommandAdapter._adapt_aruba_command(cisco_command)
        assert aruba_adapted == "write memory"
    
    def test_aruba_interface_status_command(self):
        """测试Aruba接口状态命令适配"""
        cisco_command = "show interface status"
        aruba_adapted = DeviceCommandAdapter._adapt_aruba_command(cisco_command)
        assert aruba_adapted == "show interface brief"
    
    def test_aruba_specific_commands(self):
        """测试Aruba特有命令"""
        aruba_commands = [
            "show ap database",
            "show ap client summary", 
            "show wlan ssid"
        ]
        
        for cmd in aruba_commands:
            adapted = DeviceCommandAdapter._adapt_aruba_command(cmd)
            assert adapted == cmd  # Aruba特有命令应保持不变
    
    def test_aruba_reload_command(self):
        """测试重启命令兼容性"""
        reload_cmd = "reload"
        adapted = DeviceCommandAdapter._adapt_aruba_command(reload_cmd)
        assert adapted == reload_cmd  # 重启命令通用
```

### 2. 集成测试

#### 测试场景
```python
# tests/integration/test_aruba_integration.py

class TestArubaIntegration:
    """Aruba设备集成测试"""
    
    def test_aruba_mobility_controller_flow(self):
        """测试Aruba无线控制器完整工作流"""
        # 1. 创建Aruba设备配置
        aruba_config = {
            'hostname': 'aruba-master-01',
            'vendor': 'aruba',
            'model': '7200',
            'ssh_user': 'admin',
            'ssh_port': 22,
            'device_type': 'router'  # Aruba控制器归类为路由器
        }
        
        # 2. 验证配置
        is_valid, errors = DeviceValidator.validate_router_config(aruba_config)
        assert is_valid, f"配置验证失败: {errors}"
        
        # 3. 创建设备配置
        device_config = DeviceTypeFactory.create_router_config(aruba_config)
        assert device_config['command_style'] == CommandStyle.ARUBAOS.value
        
        # 4. 测试命令适配
        inspection_cmd = "show version && show ap database"
        adapted_cmd = DeviceCommandAdapter.adapt_command_for_device(
            inspection_cmd, device_config
        )
        assert "show version" in adapted_cmd
        assert "show ap database" in adapted_cmd
    
    def test_aruba_switch_flow(self):
        """测试Aruba交换机完整工作流"""
        aruba_switch_config = {
            'hostname': 'aruba-switch-01',
            'vendor': 'aruba', 
            'model': '2930F',
            'ssh_user': 'admin',
            'ssh_port': 22,
            'ports': 48,
            'device_type': 'switch'
        }
        
        # 验证和创建流程...
```

### 3. 端到端测试

```python
# tests/integration/test_aruba_e2e.py

class TestArubaE2E:
    """Aruba设备端到端测试"""
    
    def test_aruba_inspection_task_e2e(self):
        """测试Aruba设备巡检任务E2E流程"""
        # 模拟完整的任务执行流程
        task_spec = {
            'name': 'Aruba控制器巡检',
            'command': 'show version && show ap database && show client summary',
            'target_device_id': 'aruba-master-01'
        }
        
        # 1. 创建任务
        # 2. 命令适配
        # 3. 任务执行
        # 4. 结果验证
```

---

## 📋 开发任务分解

### Phase 1: 核心适配器开发 (2-3天)
- [ ] 扩展 `CommandStyle` 枚举
- [ ] 实现 `_adapt_aruba_command()` 方法
- [ ] 扩展命令映射表
- [ ] 编写单元测试

### Phase 2: 设备工厂扩展 (1-2天)
- [ ] 扩展 `DeviceTypeFactory` 厂商检测
- [ ] 扩展 `DeviceValidator` 验证逻辑
- [ ] 编写集成测试

### Phase 3: 设备能力定义 (1天)
- [ ] 定义 Aruba 特有设备能力
- [ ] 扩展 `DeviceCapabilities` 类
- [ ] 编写能力查询测试

### Phase 4: 任务模板扩展 (1-2天)
- [ ] 创建 Aruba 专用任务模板
- [ ] 扩展 `CoreTemplates` 或创建 `ArubaTemplates`
- [ ] 编写模板测试

### Phase 5: 集成和文档 (1-2天)
- [ ] 端到端集成测试
- [ ] 性能测试
- [ ] 编写用户文档
- [ ] 编写运维文档

**总计**: 6-10 天完成

---

## 🚀 部署和使用

### 1. 配置示例

#### Aruba Mobility Controller
```python
aruba_controller = {
    'hostname': 'aruba-master-01.example.com',
    'vendor': 'aruba',
    'model': '7200',
    'device_type': 'router',
    'ssh_user': 'admin',
    'ssh_port': 22,
    'login_type': 'password',
    'timeout': 30
}
```

#### Aruba Switch
```python
aruba_switch = {
    'hostname': 'aruba-switch-01.example.com', 
    'vendor': 'aruba',
    'model': '2930F',
    'device_type': 'switch',
    'ssh_user': 'admin',
    'ssh_port': 22,
    'ports': 48,
    'login_type': 'password'
}
```

### 2. API 使用示例

```bash
# 创建Aruba设备巡检任务
curl -X POST "http://localhost:8082/api/v2/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Aruba控制器巡检",
    "command": "show version && show ap database && show client summary",
    "target_device_id": "aruba-master-01",
    "task_type": "inspection"
  }'
```

---

## 📊 验收标准

### 功能验收
- [ ] 支持 Aruba Mobility Controller
- [ ] 支持 Aruba Switch  
- [ ] 命令适配正确率 ≥ 95%
- [ ] 设备验证通过率 100%
- [ ] 向后兼容现有厂商

### 测试验收
- [ ] 单元测试覆盖率 ≥ 80%
- [ ] 集成测试全部通过
- [ ] 端到端测试验证通过

### 文档验收
- [ ] 开发文档完整
- [ ] 用户文档齐全
- [ ] API文档更新
- [ ] 运维指南完善

---

## 🎯 总结

本开发文档提供了在 HermesNexus 系统中增加 Aruba 设备支持的完整技术方案。通过扩展现有的设备抽象层，我们可以：

1. **无缝集成**: 基于现有架构，最小化代码变更
2. **向后兼容**: 不影响现有厂商设备功能
3. **易于扩展**: 为后续增加更多厂商提供模式
4. **生产就绪**: 包含完整的测试和文档支持

**预期收益**:
- 扩展系统能够管理 Aruba 网络设备
- 提升系统在企业网络环境中的适用性
- 为后续厂商扩展建立标准模式

---

**文档版本**: 1.0.0  
**创建日期**: 2026-04-21  
**维护者**: HermesNexus 开发团队
