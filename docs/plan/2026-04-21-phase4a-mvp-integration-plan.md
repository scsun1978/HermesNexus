# Phase 4A + MVP验收整合计划

**更新日期**: 2026-04-21
**策略**: 继续Phase 4A开发 + 嵌入MVP验收里程碑
**目标**: 架构升级 + MVP 100%完成同步达成

---

## 🎯 整合原则

### **Phase 4A解决MVP缺口的对应关系**

| MVP缺口 | Phase 4A解决方案 | 验收时间点 |
|---------|-----------------|-----------|
| 4类任务不完整 | Week 3任务模板系统 | Week 3结束 |
| 3类设备未实现 | DeviceConfigBuilder抽象 | Week 4结束 |
| 故障排查缺闭环 | TaskManager状态跟踪 | Week 2结束 |
| 重启恢复缺验证 | TaskExecutor重试机制 | Week 4结束 |
| 告警缺端到端测试 | Task事件触发告警 | Week 5结束 |

---

## 📋 更新后的Phase 4A计划

### **Week 2: 任务执行引擎 + MVP故障排查验收**

#### **Day 4-5: 集成测试和文档**
```python
# 1. 端到端任务执行测试
def test_end_to_end_task_execution():
    """完整的任务执行流程"""
    # 创建任务 → 执行任务 → 验证结果 → 检查状态

# 2. 故障场景测试
def test_task_failure_recovery():
    """任务失败后的恢复机制"""
    # SSH连接失败 → 超时处理 → 重试逻辑

# 3. 状态转换测试
def test_task_status_lifecycle():
    """任务状态的完整转换链路"""
    # pending → running → completed/failed

# MVP验收: 故障排查闭环
✅ 任务失败有明确错误信息
✅ 状态转换可追踪
✅ 重试机制有效
```

**MVP验收标准**：
- [ ] 任务失败时有详细错误日志
- [ ] 状态转换完整记录在数据库
- [ ] SSH连接失败有自动重试
- [ ] 超时情况有正确处理

---

### **Week 3: 任务模板库 + MVP 4类任务验收**

#### **Day 1-2: 核心4类任务模板**
```python
class CoreTemplates:
    """MVP要求的4类任务模板"""

    @staticmethod
    def get_inspection_template() -> TaskTemplate:
        """巡检任务模板"""
        return TaskTemplate(
            template_id="inspection",
            name="系统巡检",
            description="检查系统健康状态：运行时间、磁盘使用、内存使用、网络连接",
            command_template="uptime && df -h && free -h && netstat -an"
        )

    @staticmethod
    def get_restart_service_template() -> TaskTemplate:
        """重启服务任务模板"""
        return TaskTemplate(
            template_id="restart-service",
            name="服务重启",
            description="重启指定的系统服务",
            command_template="systemctl restart {service}",
            default_params={"service": "nginx"}
        )

    @staticmethod
    def get_upgrade_package_template() -> TaskTemplate:
        """升级任务模板"""
        return TaskTemplate(
            template_id="upgrade-package",
            name="软件包升级",
            description="升级指定的软件包",
            command_template="apt-get update && apt-get install -y {package}",
            default_params={"package": "nginx"}
        )

    @staticmethod
    def get_rollback_service_template() -> TaskTemplate:
        """回滚任务模板"""
        return TaskTemplate(
            template_id="rollback-service",
            name="服务回滚",
            description="回滚服务到指定版本",
            command_template="systemctl rollback {service} {version}",
            default_params={"service": "nginx", "version": "previous"}
        )
```

**MVP验收标准**：
- [ ] INSPECTION任务执行成功并返回系统状态
- [ ] RESTART任务能重启指定服务
- [ ] UPGRADE任务能升级软件包
- [ ] ROLLBACK任务能回滚服务版本
- [ ] 4类任务都有完整的审计日志

---

### **Week 4: v2 API + MVP 3类设备验收**

#### **Day 1-3: 3类设备抽象实现**
```python
class DeviceTypeFactory:
    """设备类型工厂"""

    @staticmethod
    def create_router_config(host_info: dict) -> dict:
        """路由器设备配置"""
        return {
            'device_type': 'router',
            'connection_type': 'ssh',
            'protocol': 'ssh',
            'port': host_info.get('ssh_port', 22),
            'login_type': 'password',  # 或 'key'
            'command_style': 'cisco_ios'  # 或 'huawei_vrp'
        }

    @staticmethod
    def create_switch_config(host_info: dict) -> dict:
        """交换机设备配置"""
        return {
            'device_type': 'switch',
            'connection_type': 'ssh',
            'protocol': 'ssh',
            'port': host_info.get('ssh_port', 22),
            'login_type': 'password',
            'command_style': 'cisco_ios'
        }

    @staticmethod
    def create_server_config(host_info: dict) -> dict:
        """服务器设备配置"""
        return {
            'device_type': 'server',
            'connection_type': 'ssh',
            'protocol': 'ssh',
            'port': host_info.get('ssh_port', 22),
            'login_type': 'key',  # 服务器主要用密钥
            'command_style': 'linux_bash'
        }

# v2 API支持设备类型
@v2_bp.route('/devices', methods=['POST'])
def register_device():
    """设备注册API（支持3类设备）"""
    data = request.json
    device_type = data.get('device_type')  # router/switch/server

    device_config = DeviceTypeFactory.create_config(
        device_type, data
    )

    # 注册设备到系统
    device_id = register_device_in_system(device_config)
    return jsonify({"device_id": device_id, "status": "registered"})
```

**MVP验收标准**：
- [ ] 能注册路由器设备（Cisco/Huawei风格）
- [ ] 能注册交换机设备（Cisco/Huawei风格）
- [ ] 能注册服务器设备（Linux BASH风格）
- [ ] 3类设备有各自的执行命令适配
- [ ] 设备类型在数据库中有明确标识

---

### **Week 5-6: 云边编排 + MVP告警/重启恢复验收**

#### **Week 5: 告警系统集成**
```python
class TaskEventMonitor:
    """任务事件监控器"""

    def __init__(self, alert_manager):
        self.alert_manager = alert_manager

    def monitor_task_events(self, task: Task):
        """监控任务事件并触发告警"""
        if task.status == TaskStatus.FAILED:
            self._trigger_failure_alert(task)

        if task.result and task.result.get('duration_seconds') > 300:
            self._trigger_timeout_alert(task)

    def _trigger_failure_alert(self, task: Task):
        """触发任务失败告警"""
        alert = {
            'alert_type': 'task_failure',
            'severity': 'high',
            'task_id': task.task_id,
            'device_id': task.target_device_id,
            'message': f"Task {task.name} failed on device {task.target_device_id}",
            'error': task.result.get('error') if task.result else 'Unknown error'
        }
        self.alert_manager.send_alert(alert)

    def _trigger_timeout_alert(self, task: Task):
        """触发超时告警"""
        alert = {
            'alert_type': 'task_timeout',
            'severity': 'medium',
            'task_id': task.task_id,
            'duration_seconds': task.result.get('duration_seconds'),
            'message': f"Task {task.name} took longer than expected"
        }
        self.alert_manager.send_alert(alert)
```

**MVP验收标准**：
- [ ] 任务失败触发告警（高优先级）
- [ ] 任务超时触发告警（中优先级）
- [ ] 告警有详细的上下文信息
- [ ] 告警能在控制台可见

#### **Week 6: 重启恢复验证**
```python
def test_edge_node_restart_recovery():
    """边缘节点重启后的恢复验证"""
    # 1. 正常注册和心跳
    # 2. 模拟边缘节点重启
    # 3. 验证自动重新连接
    # 4. 验证任务继续执行
    # 5. 验证状态同步恢复
```

**MVP验收标准**：
- [ ] 边缘节点重启后能自动重新注册
- [ ] 未完成的任务在重启后继续执行
- [ ] 心跳恢复后状态同步正常
- [ ] 重启过程中有明确日志记录

---

## 🎯 MVP验收里程碑

### **Week 2结束: 故障排查验收 ✅**
- [ ] 任务执行完整状态跟踪
- [ ] 失败任务详细错误信息
- [ ] SSH连接自动重试机制
- [ ] 超时处理和日志记录

### **Week 3结束: 4类任务验收 ✅**
- [ ] INSPECTION任务端到端执行
- [ ] RESTART任务端到端执行
- [ ] UPGRADE任务端到端执行
- [ ] ROLLBACK任务端到端执行
- [ ] 所有任务有审计日志

### **Week 4结束: 3类设备验收 ✅**
- [ ] 路由器设备注册和执行
- [ ] 交换机设备注册和执行
- [ ] 服务器设备注册和执行
- [ ] 设备类型抽象和适配

### **Week 5结束: 告警系统验收 ✅**
- [ ] 任务失败告警触发
- [ ] 任务超时告警触发
- [ ] 告警信息完整可读
- [ ] 告警在控制台可见

### **Week 6结束: 重启恢复验收 ✅**
- [ ] 边缘节点重启自动恢复
- [ ] 任务状态同步恢复
- [ ] 心跳重新建立
- [ ] 完整的恢复日志

---

## 📊 最终MVP完成度目标

### **当前状态**: 7/10完成 (70%)
### **6周后目标**: 10/10完成 (100%)

| 项目 | 当前 | Week 2 | Week 3 | Week 4 | Week 5 | Week 6 |
|------|------|--------|--------|--------|--------|--------|
| 云端控制平面 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 边缘节点运行时 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 最小任务闭环 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 单节点闭环 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SSH only | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 节点注册/心跳 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **故障排查** | 🟡 | **✅** | ✅ | ✅ | ✅ | ✅ |
| **重启恢复** | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | **✅** |
| **4类任务** | 🟡 | 🟡 | **✅** | ✅ | ✅ | ✅ |
| **3类设备** | ❌ | ❌ | ❌ | **✅** | ✅ | ✅ |
| 基础审计 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **告警系统** | 🟡 | 🟡 | 🟡 | 🟡 | **✅** | ✅ |

---

## 🚀 执行策略

### **1. 双轨并进**
- Phase 4A架构开发（主线）
- MVP验收验证（并行）

### **2. 里程碑驱动**
- 每周结束都有MVP验收点
- 不通过的验收点下周优先处理

### **3. 测试先行**
- 先写验收测试用例
- 再实现功能代码
- 确保每步都有验证

### **4. 文档同步**
- 每个功能完成同时更新文档
- MVP验收标准明确记录
- 使用示例和代码样例齐全

---

**下一步**: 立即开始Week 2 Day 4的集成测试工作，重点关注故障排查闭环的MVP验收。