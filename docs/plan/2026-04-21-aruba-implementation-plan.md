# Aruba 设备支持实施计划

**Phase**: 4B - Device Vendor Extension  
**Duration**: 1-2 weeks  
**Status**: 🚀 In Progress  
**Start Date**: 2026-04-21  

---

## 📋 总体计划

### 目标
在 1-2 周内为 HermesNexus 系统增加完整的 Aruba 设备支持，包括无线控制器、交换机和接入点。

### 成功标准
- ✅ 支持 Aruba Mobility Controller (7200系列)
- ✅ 支持 Aruba Switch (2930F, 3830系列)  
- ✅ 命令适配准确率 ≥ 95%
- ✅ 测试覆盖率 ≥ 80%
- ✅ 完整文档和运维指南

---

## 🚀 Phase 1: 核心适配器开发 (Day 1-3)

### 任务清单

#### 1.1 扩展命令风格枚举
**文件**: `hermesnexus/device/types.py`

```python
# 扩展 CommandStyle 枚举
class CommandStyle(Enum):
    CISCO_IOS = "cisco_ios"
    HUAWEI_VRP = "huawei_vrp" 
    LINUX_BASH = "linux_bash"
    JUNOS = "junos"
    ARUBAOS = "arubaos"  # 🆕 新增
```

#### 1.2 实现 Aruba 命令适配器
**文件**: `hermesnexus/device/types.py`

```python
class DeviceCommandAdapter:
    # 🆕 新增 Aruba 适配方法
    @staticmethod
    def _adapt_aruba_command(command: str) -> str:
        """Aruba命令适配逻辑"""
        # 实现详细的命令映射逻辑
```

**关键命令映射**:
- `copy running-config startup-config` → `write memory`
- `show interface status` → `show interface brief`
- 保留 Aruba 特有命令: `show ap database`, `show client summary`

#### 1.3 编写单元测试
**文件**: `tests/device/test_aruba_command_adapter.py`

- 测试配置保存命令适配
- 测试接口状态命令适配
- 测试 Aruba 特有命令处理
- 测试重启命令兼容性

**验收标准**: 
- 所有测试用例通过
- 代码覆盖率 ≥ 90%

---

## 🔧 Phase 2: 设备工厂扩展 (Day 4-5)

### 任务清单

#### 2.1 扩展厂商检测逻辑
**文件**: `hermesnexus/device/types.py`

```python
class DeviceTypeFactory:
    @staticmethod
    def _detect_router_command_style(host_info: dict) -> str:
        # 🆕 增加 Aruba 检测
        vendor = host_info.get('vendor', 'cisco').lower()
        if vendor in ['aruba', 'hpe', 'hp']:
            return CommandStyle.ARUBAOS.value
        # ... 现有逻辑 ...
```

#### 2.2 扩展设备验证器
**文件**: `hermesnexus/device/types.py`

```python
class DeviceValidator:
    @staticmethod
    def validate_router_config(config: dict) -> tuple[bool, list[str]]:
        # 🆕 扩展支持的厂商列表
        valid_vendors = ['cisco', 'huawei', 'juniper', 'h3c', 'aruba', 'hpe', 'hp']
```

#### 2.3 编写集成测试
**文件**: `tests/device/test_aruba_device_factory.py`

- 测试 Aruba 设备配置创建
- 测试厂商检测逻辑
- 测试设备验证功能
- 测试配置错误处理

**验收标准**:
- Aruba 设备配置创建成功
- 验证逻辑正确识别 Aruba 设备
- 错误场景处理正确

---

## 🎯 Phase 3: 设备能力定义 (Day 6)

### 任务清单

#### 3.1 定义 Aruba 特有设备能力
**文件**: `hermesnexus/device/types.py`

```python
class DeviceCapabilities:
    # 🆕 Aruba 无线控制器能力
    ARUBA_CONTROLLER_CAPABILITIES = {
        'show_version': True,
        'show_ap_database': True,        # Aruba 特有
        'show_client_summary': True,     # Aruba 特有
        'configure_ssid': True,          # Aruba 特有
        'ap_management': True,           # Aruba 特有
        # ... 其他能力
    }
    
    # 🆕 Aruba 交换机能力
    ARUBA_SWITCH_CAPABILITIES = {
        'show_version': True,
        'lldp_neighbors': True,          # Aruba 增强
        # ... 其他能力
    }
```

#### 3.2 扩展能力查询接口
**文件**: `hermesnexus/device/types.py`

```python
@staticmethod
def get_capabilities(device_type: str, vendor: str = None) -> dict:
    """获取设备能力 - 支持Aruba"""
    if vendor == 'aruba':
        # 返回 Aruba 特有能力
    # ... 现有逻辑 ...
```

#### 3.3 编写能力测试
**文件**: `tests/device/test_aruba_capabilities.py`

- 测试无线控制器能力查询
- 测试交换机能力查询
- 测试能力检查逻辑
- 测试能力对比功能

**验收标准**:
- Aruba 特有能力正确定义
- 能力查询接口工作正常
- 向后兼容现有能力查询

---

## 📋 Phase 4: 任务模板扩展 (Day 7-8)

### 任务清单

#### 4.1 创建 Aruba 专用任务模板
**文件**: `hermesnexus/task/templates.py`

```python
class ArubaTemplates:
    """Aruba专用任务模板"""
    
    @staticmethod
    def get_aruba_inspection_template():
        """Aruba设备巡检模板"""
        return TaskTemplate.create(
            template_id="aruba-inspection",
            name="Aruba设备巡检",
            description="检查Aruba设备状态：版本、AP数据库、客户端摘要",
            command_template="show version && show ap database && show client summary",
            default_params={}
        )
    
    @staticmethod
    def get_aruba_ap_restart_template():
        """Aruba AP重启模板"""
        return TaskTemplate.create(
            template_id="aruba-ap-restart",
            name="Aruba AP重启",
            description="重启指定的Aruba接入点",
            command_template="ap restart {ap_name}",
            default_params={"ap_name": "ap-01"}
        )
    
    # ... 其他Aruba专用模板 ...
```

#### 4.2 扩展模板管理器
**文件**: `hermesnexus/task/templates.py`

```python
class TemplateManager:
    def _register_builtin_templates(self):
        # ... 现有模板注册 ...
        # 🆕 注册Aruba模板
        aruba_templates = ArubaTemplates.get_all_templates()
        for template_id, template in aruba_templates.items():
            self.register_template(template)
```

#### 4.3 编写模板测试
**文件**: `tests/task/test_aruba_templates.py`

- 测试 Aruba 巡检模板
- 测试 Aruba AP 重启模板
- 测试模板参数替换
- 测试模板验证逻辑

**验收标准**:
- Aruba 模板正确定义
- 模板渲染功能正常
- 参数替换工作正确

---

## 🧪 Phase 5: 集成和测试 (Day 9-10)

### 任务清单

#### 5.1 端到端集成测试
**文件**: `tests/integration/test_aruba_e2e.py`

- 测试完整的工作流程
- 测试与现有系统的兼容性
- 测试错误处理和恢复
- 测试性能和稳定性

#### 5.2 性能测试
**文件**: `tests/performance/test_aruba_performance.py`

- 测试命令适配性能
- 测试批量任务处理性能
- 测试并发性能
- 测试内存使用情况

#### 5.3 文档完善
- 更新 API 文档
- 编写用户使用指南
- 编写运维故障排查指南
- 更新架构设计文档

**验收标准**:
- 所有集成测试通过
- 性能满足要求
- 文档完整齐全
- 用户体验良好

---

## 📊 进度跟踪

### 里程碑

| **Phase** | **任务** | **状态** | **完成时间** |
|-----------|----------|----------|-------------|
| Phase 1 | 核心适配器开发 | 🔲 待开始 | - |
| Phase 2 | 设备工厂扩展 | 🔲 待开始 | - |
| Phase 3 | 设备能力定义 | 🔲 待开始 | - |
| Phase 4 | 任务模板扩展 | 🔲 待开始 | - |
| Phase 5 | 集成和测试 | 🔲 待开始 | - |

### 风险和缓解

| **风险** | **影响** | **概率** | **缓解措施** |
|----------|----------|----------|-------------|
| Aruba 命令兼容性问题 | 高 | 中 | 充分的命令映射测试 |
| 性能影响 | 中 | 低 | 性能测试和优化 |
| 向后兼容性问题 | 高 | 低 | 完整的回归测试 |
| 文档不完整 | 中 | 中 | 专人负责文档编写 |

---

## 🎯 验收标准

### 功能验收
- [ ] 支持 Aruba Mobility Controller 7200系列
- [ ] 支持 Aruba Switch 2930F/3830系列
- [ ] 命令适配准确率 ≥ 95%
- [ ] 设备能力查询正确
- [ ] 任务模板功能完整

### 质量验收
- [ ] 单元测试覆盖率 ≥ 80%
- [ ] 集成测试全部通过
- [ ] 端到端测试验证通过
- [ ] 无明显性能下降
- [ ] 无向后兼容性问题

### 文档验收
- [ ] 技术实现文档完整
- [ ] API 使用文档齐全
- [ ] 用户操作指南清晰
- [ ] 运维故障排查指南完善

---

## 🚀 部署计划

### 开发环境测试
1. 在本地开发环境完成所有开发
2. 运行完整的测试套件
3. 进行代码审查和质量检查

### 集成测试环境
1. 部署到集成测试环境
2. 使用模拟 Aruba 设备进行测试
3. 验证与现有系统的集成

### 生产环境准备
1. 制定生产环境部署计划
2. 准备回滚方案
3. 进行生产环境测试

---

## 📞 团队协作

### 角色和职责

- **架构师**: 技术方案设计和审查
- **开发工程师**: 代码实现和单元测试
- **测试工程师**: 集成测试和质量保证
- **文档工程师**: 文档编写和维护
- **运维工程师**: 部署和生产环境支持

### 沟通计划
- 每日站会：进度同步和问题讨论
- 每周代码审查：质量保证
- 技术评审：关键决策和方案讨论
- 文档审查：确保文档质量

---

**计划版本**: 1.0.0  
**创建日期**: 2026-04-21  
**计划负责人**: HermesNexus 开发团队  
**审核状态**: ✅ 已批准

**下一步**: 开始 Phase 1 - 核心适配器开发
