# HermesNexus Phase 4A 执行开发计划

**Project**: HermesNexus 任务编排核心框架  
**Phase**: 4A - 任务编排基础能力  
**Timeline**: 6周 (2026-04-20 ~ 2026-06-01)  
**Status**: 🎯 **已确认，准备启动**

---

## 📋 项目概述

### **项目目标**
建立任务编排的基础能力，实现云边协同的批量任务调度，为后续智能化增强奠定基础。

### **核心价值**
1. **任务抽象**: 从单一命令升级为Task/Step模型
2. **批量调度**: 支持一次调度多个设备的任务
3. **模板复用**: 提供常用任务模板，提升效率
4. **向后兼容**: 不破坏现有API和功能
5. **快速迭代**: 6周交付可用版本，后续持续改进

### **设计原则**
- ✅ **MVP优先**: 小步快跑，快速验证
- ✅ **向后兼容**: 现有功能不受影响
- ✅ **简单设计**: 避免过度工程
- ✅ **测试驱动**: 每个功能都有测试覆盖
- ✅ **文档完整**: API文档和使用说明齐全

---

## 🎯 6周开发计划

## **Week 1-2: 基础任务模型**

### **核心目标**
建立简单直接的Task/Step模型，为任务编排奠定基础。

### **Week 1: 任务数据模型**

#### **Day 1-2: Task核心类开发**
```python
# 文件: hermesnexus/task/model.py

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

@dataclass
class Task:
    """任务核心模型"""
    task_id: str
    name: str
    description: str
    command: str
    target_device_id: str
    status: str = "pending"
    created_by: str = "system"
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        pass
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """从字典创建"""
        pass

@dataclass
class TaskTemplate:
    """任务模板模型"""
    template_id: str
    name: str
    description: str
    command_template: str
    default_params: Dict[str, Any] = None
    
    def render(self, **kwargs) -> str:
        """渲染命令模板"""
        pass
```

**验收标准**:
- ✅ Task类实现完成
- ✅ TaskTemplate类实现完成
- ✅ 单元测试通过
- ✅ 代码通过flake8检查

#### **Day 3-4: 任务状态管理**
```python
# 文件: hermesnexus/task/manager.py

class TaskManager:
    """任务状态管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_tables()
    
    def create_task(self, task: Task) -> bool:
        """创建任务"""
        pass
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        pass
    
    def update_task_status(self, task_id: str, status: str, result: dict = None):
        """更新任务状态"""
        pass
    
    def list_tasks(self, device_id: str = None, status: str = None, limit: int = 100) -> List[Task]:
        """列出任务"""
        pass
```

**验收标准**:
- ✅ TaskManager实现完成
- ✅ 数据库表扩展正确
- ✅ CRUD操作正常
- ✅ 单元测试覆盖 > 80%

#### **Day 5: 单元测试和代码质量**
```python
# 文件: tests/task/test_model.py
# 文件: tests/task/test_manager.py

# 测试用例包括：
def test_task_creation():
    """测试任务创建"""
    pass

def test_task_serialization():
    """测试任务序列化"""
    pass

def test_task_manager_crud():
    """测试任务管理器CRUD操作"""
    pass

def test_task_status_update():
    """测试任务状态更新"""
    pass
```

**验收标准**:
- ✅ 单元测试完成
- ✅ 测试覆盖率 > 80%
- ✅ 所有测试通过
- ✅ 代码质量检查通过

### **Week 2: 任务执行引擎**

#### **Day 1-3: 任务执行引擎**
```python
# 文件: hermesnexus/task/executor.py

class TaskExecutor:
    """简单的任务执行引擎"""
    
    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
    
    def execute(self, task: Task, device_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        # 1. 更新状态为running
        # 2. 执行命令
        # 3. 更新任务状态
        # 4. 返回结果
        pass
    
    def _execute_command(self, command: str, device_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行命令（复用现有SSH机制）"""
        pass
```

**验收标准**:
- ✅ TaskExecutor实现完成
- ✅ 支持基础命令执行
- ✅ 错误处理正确
- ✅ 单元测试通过

#### **Day 4-5: 集成测试和文档**
```python
# 文件: tests/integration/test_task_execution.py

def test_end_to_end_task_execution():
    """端到端任务执行测试"""
    # 1. 创建任务
    # 2. 执行任务
    # 3. 验证结果
    # 4. 检查状态更新
    pass
```

**验收标准**:
- ✅ 集成测试完成
- ✅ 端到端流程验证通过
- ✅ 基础文档完成
- ✅ 代码示例可用

### **Week 1-2 总结**
**交付物**:
- ✅ 完整的Task/TaskTemplate模型
- ✅ TaskManager状态管理
- ✅ TaskExecutor执行引擎
- ✅ 单元测试和集成测试
- ✅ 基础文档和代码示例

---

## **Week 3-4: 任务模板和API**

### **核心目标**
提供3个核心任务模板，实现新的v2 API，保持向后兼容。

### **Week 3: 任务模板库**

#### **Day 1-2: 核心任务模板**
```python
# 文件: hermesnexus/task/templates.py

class CoreTemplates:
    """核心任务模板库"""
    
    @staticmethod
    def get_health_check_template() -> TaskTemplate:
        """系统健康检查模板"""
        return TaskTemplate(
            template_id="health-check",
            name="系统健康检查",
            description="检查系统基本健康状态：运行时间、磁盘使用、内存使用",
            command_template="uptime && df -h && free -h"
        )
    
    @staticmethod
    def get_restart_service_template() -> TaskTemplate:
        """服务重启模板"""
        return TaskTemplate(
            template_id="restart-service",
            name="服务重启",
            description="重启指定的系统服务",
            command_template="systemctl restart {service}",
            default_params={"service": "nginx"}
        )
    
    @staticmethod
    def get_backup_database_template() -> TaskTemplate:
        """数据库备份模板"""
        return TaskTemplate(
            template_id="backup-database",
            name="数据库备份",
            description="备份指定的数据库到指定路径",
            command_template="mysqldump {database} > {backup_path}/{database}_$(date +%Y%m%d_%H%M%S).sql",
            default_params={"database": "mydb", "backup_path": "/tmp/backups"}
        )

class TemplateManager:
    """任务模板管理器"""
    
    def __init__(self):
        self.templates = {}
        self._register_builtin_templates()
    
    def register_template(self, template: TaskTemplate):
        """注册模板"""
        pass
    
    def get_template(self, template_id: str):
        """获取模板"""
        pass
    
    def create_task_from_template(self, template_id: str, **params) -> str:
        """从模板创建任务命令"""
        pass
```

**验收标准**:
- ✅ 3个核心模板实现完成
- ✅ TemplateManager功能完整
- ✅ 模板参数替换正确
- ✅ 单元测试通过

#### **Day 3-5: 模板系统测试和优化**
```python
# 文件: tests/task/test_templates.py

def test_health_check_template():
    """测试健康检查模板"""
    pass

def test_restart_service_template():
    """测试服务重启模板"""
    pass

def test_backup_database_template():
    """测试数据库备份模板"""
    pass

def test_template_parameter_substitution():
    """测试模板参数替换"""
    pass

def test_custom_template_registration():
    """测试自定义模板注册"""
    pass
```

**验收标准**:
- ✅ 模板系统测试完成
- ✅ 参数替换功能验证
- ✅ 自定义模板支持
- ✅ 性能优化（缓存等）

### **Week 4: v2 API实现**

#### **Day 1-3: v2 API开发**
```python
# 文件: cloud/api/v2.py

from flask import Blueprint, request, jsonify
from hermesnexus.task.model import Task
from hermesnexus.task.manager import TaskManager
from hermesnexus.task.templates import TemplateManager

v2_bp = Blueprint('api_v2', __name__, url_prefix='/api/v2')

task_manager = TaskManager('/home/scsun/hermesnexus-data/hermesnexus-v12.db')
template_manager = TemplateManager()

@v2_bp.route('/tasks', methods=['POST'])
def create_task():
    """创建任务（v2 API）"""
    # 支持两种创建方式：
    # 1. 从模板创建
    # 2. 直接创建
    pass

@v2_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取任务详情"""
    pass

@v2_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """列出任务"""
    pass

@v2_bp.route('/templates', methods=['GET'])
def list_templates():
    """列出任务模板"""
    pass

@v2_bp.route('/templates/<template_id>/render', methods=['POST'])
def render_template(template_id):
    """渲染任务模板"""
    pass
```

**验收标准**:
- ✅ v2 API端点实现完成
- ✅ 支持模板和直接创建
- ✅ 错误处理正确
- ✅ API响应格式统一

#### **Day 4: CLI命令**
```python
# 文件: hermesnexus/cli/v2_commands.py

import click
from hermesnexus.task.model import Task
from hermesnexus.task.manager import TaskManager
from hermesnexus.task.templates import TemplateManager

@click.group()
def task():
    """任务管理命令"""
    pass

@task.command()
@click.argument('name')
@click.argument('command')
@click.argument('device_id')
def create(name, command, device_id):
    """创建任务"""
    pass

@task.command()
@click.argument('template_id')
@click.argument('device_id')
@click.option('--params', '-p')
def create_from_template(template_id, device_id, params):
    """从模板创建任务"""
    pass

@task.command()
@click.argument('task_id')
def status(task_id):
    """查看任务状态"""
    pass

@task.command()
def templates():
    """列出所有任务模板"""
    pass
```

**验收标准**:
- ✅ CLI命令实现完成
- ✅ 命令参数验证正确
- ✅ 输出格式友好
- ✅ 错误提示清晰

#### **Day 5: API集成测试**
```python
# 文件: tests/integration/test_v2_api.py

def test_create_task_from_command():
    """测试通过命令创建任务"""
    pass

def test_create_task_from_template():
    """测试通过模板创建任务"""
    pass

def test_list_templates():
    """测试列出模板"""
    pass

def test_get_task_status():
    """测试获取任务状态"""
    pass

def test_v1_v2_compatibility():
    """测试v1和v2 API的兼容性"""
    pass
```

**验收标准**:
- ✅ API集成测试完成
- ✅ v1/v2兼容性验证
- ✅ 错误场景测试通过
- ✅ API性能可接受

### **Week 3-4 总结**
**交付物**:
- ✅ 3个核心任务模板
- ✅ TemplateManager系统
- ✅ 完整的v2 API
- ✅ CLI命令工具
- ✅ API集成测试

---

## **Week 5-6: 云边任务编排**

### **核心目标**
实现云端的任务批量调度能力，支持一次调度多个设备的任务。

### **Week 5: 云端编排器**

#### **Day 1-3: 云端任务编排器**
```python
# 文件: hermesnexus/orchestrator/cloud.py

class CloudTaskOrchestrator:
    """云端任务编排器"""
    
    def __init__(self, edge_nodes_config: Dict[str, str], task_manager: TaskManager):
        self.edge_nodes = edge_nodes_config
        self.task_manager = task_manager
    
    def schedule_task_to_devices(self, task_spec: Dict[str, Any], device_ids: List[str]) -> Dict[str, Any]:
        """调度任务到多个设备"""
        # 1. 为每个设备创建任务
        # 2. 保存任务到数据库
        # 3. 下发到边缘节点
        # 4. 返回调度结果
        pass
    
    def schedule_template_to_devices(self, template_id: str, params: Dict[str, Any], device_ids: List[str]) -> Dict[str, Any]:
        """从模板调度任务到多个设备"""
        pass
    
    def _dispatch_to_edge(self, task: Task, device_id: str) -> bool:
        """下发任务到边缘节点"""
        pass

class BatchScheduler:
    """批量任务调度器"""
    
    def __init__(self, orchestrator: CloudTaskOrchestrator):
        self.orchestrator = orchestrator
    
    def schedule_health_check(self, device_ids: List[str]) -> Dict[str, Any]:
        """批量健康检查"""
        pass
    
    def schedule_service_restart(self, service_name: str, device_ids: List[str]) -> Dict[str, Any]:
        """批量服务重启"""
        pass
```

**验收标准**:
- ✅ CloudTaskOrchestrator实现完成
- ✅ 支持批量任务调度
- ✅ 错误处理和重试机制
- ✅ 单元测试通过

#### **Day 4-5: 编排API实现**
```python
# 文件: cloud/api/orchestration.py

from flask import Blueprint, request, jsonify
from hermesnexus.orchestrator.cloud import CloudTaskOrchestrator, BatchScheduler

orchestration_bp = Blueprint('orchestration', __name__, url_prefix='/api/orchestration')

orchestrator = CloudTaskOrchestrator(edge_nodes_config, task_manager)
batch_scheduler = BatchScheduler(orchestrator)

@orchestration_bp.route('/schedule', methods=['POST'])
def schedule_tasks():
    """批量调度任务"""
    pass

@orchestration_bp.route('/batch/health-check', methods=['POST'])
def batch_health_check():
    """批量健康检查"""
    pass

@orchestration_bp.route('/batch/restart-service', methods=['POST'])
def batch_restart_service():
    """批量服务重启"""
    pass
```

**验收标准**:
- ✅ 编排API实现完成
- ✅ 支持多种批量操作
- ✅ API文档完整
- ✅ 集成测试通过

### **Week 6: 边缘支持和E2E测试**

#### **Day 1-2: 边缘节点v2支持**
```python
# 文件: edge-node/v2_task_handler.py

from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.route('/api/v2/tasks', methods=['POST'])
def receive_v2_task():
    """接收v2任务（向后兼容）"""
    # 1. 解析任务格式（v1/v2兼容）
    # 2. 执行任务
    # 3. 回写结果
    pass

def execute_command(command: str) -> dict:
    """执行命令"""
    pass

def report_result(job_id: str, result: dict):
    """回写结果到云端"""
    pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8086)
```

**验收标准**:
- ✅ 边缘节点支持v2任务格式
- ✅ 向后兼容v1格式
- ✅ 结果回写正确
- ✅ 错误处理完善

#### **Day 3-4: E2E测试**
```python
# 文件: tests/e2e/test_orchestration.py

def test_batch_health_check():
    """测试批量健康检查"""
    # 1. 准备测试设备
    # 2. 调度批量健康检查
    # 3. 等待任务完成
    # 4. 验证任务结果
    pass

def test_template_based_scheduling():
    """测试基于模板的调度"""
    pass

def test_v1_v2_compatibility():
    """测试v1和v2 API的兼容性"""
    pass

def test_batch_service_restart():
    """测试批量服务重启"""
    pass

def test_task_status_tracking():
    """测试任务状态跟踪"""
    pass
```

**验收标准**:
- ✅ E2E测试场景完整
- ✅ 批量调度功能验证
- ✅ 兼容性测试通过
- ✅ 性能测试达标

#### **Day 5: 文档和交付**
```python
# 文件: docs/api/v2-api.md
# 文件: docs/user-guide/task-orchestration.md
# 文件: docs/cli/v2-commands.md
# 文件: README-PHASE4A.md
```

**验收标准**:
- ✅ API文档完整
- ✅ 用户指南编写完成
- ✅ CLI文档完整
- ✅ 示例代码可用

### **Week 5-6 总结**
**交付物**:
- ✅ 云端任务编排器
- ✅ 批量调度API
- ✅ 边缘节点v2支持
- ✅ 完整的E2E测试
- ✅ 系统文档和示例

---

## 📊 项目管理

### **时间表和里程碑**

| **周** | **日期** | **里程碑** | **关键交付** | **验收标准** |
|-------|----------|-----------|-------------|-------------|
| **1** | 4/20-4/26 | 数据模型完成 | Task/TaskTemplate | 单元测试 > 80% |
| **2** | 4/27-5/03 | 执行引擎完成 | TaskManager/Executor | 集成测试通过 |
| **3** | 5/04-5/10 | 模板系统完成 | 3个核心模板 | 模板功能验证 |
| **4** | 5/11-5/17 | v2 API完成 | API/CLI工具 | API测试通过 |
| **5** | 5/18-5/24 | 编排器完成 | 批量调度功能 | 编排测试通过 |
| **6** | 5/25-5/31 | Phase 4A完成 | E2E测试+文档 | 全面验收通过 |

### **风险管理**

| **风险** | **概率** | **影响** | **缓解策略** |
|---------|----------|----------|-------------|
| 技术复杂度超预期 | 中 | 高 | 简化设计，MVP优先 |
| 与现有代码冲突 | 中 | 中 | 向后兼容，独立分支 |
| 测试环境问题 | 低 | 中 | 提前准备测试环境 |
| 时间进度延期 | 中 | 高 | 严格scope控制 |
| API兼容性问题 | 低 | 中 | 充分测试验证 |

### **质量标准**

#### **代码质量**
- ✅ 单元测试覆盖率 > 80%
- ✅ 集成测试覆盖核心功能
- ✅ E2E测试覆盖主要场景
- ✅ 代码通过flake8检查
- ✅ 代码通过mypy类型检查

#### **性能标准**
- ✅ 任务创建响应 < 100ms
- ✅ API响应时间 < 500ms
- ✅ 批量调度支持20+设备
- ✅ 任务执行延迟无明显增加

#### **可用性标准**
- ✅ API文档完整准确
- ✅ CLI命令帮助清晰
- ✅ 错误提示友好
- ✅ 示例代码丰富

---

## 🛠️ 开发环境和工具

### **开发环境设置**
```bash
# 1. 创建开发分支
git checkout -b feature/task-orchestration-core

# 2. 创建目录结构
mkdir -p hermesnexus/task
mkdir -p hermesnexus/orchestrator
mkdir -p hermesnexus/cli
mkdir -p cloud/api/v2
mkdir -p tests/task
mkdir -p tests/orchestration
mkdir -p tests/integration
mkdir -p tests/e2e

# 3. 安装开发依赖
pip install pytest pytest-cov flake8 mypy black

# 4. 运行测试
pytest tests/ --cov=hermesnexus --cov-report=html

# 5. 代码质量检查
flake8 hermesnexus/
mypy hermesnexus/
black hermesnexus/
```

### **开发工具**
- **IDE**: VS Code / PyCharm
- **版本控制**: Git + GitHub
- **测试框架**: pytest
- **代码质量**: flake8, mypy, black
- **文档工具**: Sphinx / Markdown
- **API测试**: Postman / curl

### **数据库管理**
```bash
# 数据库路径
DB_PATH="/home/scsun/hermesnexus-data/hermesnexus-v12.db"

# 查看现有表结构
sqlite3 $DB_PATH ".schema"

# 查看任务数据
sqlite3 $DB_PATH "SELECT * FROM jobs WHERE is_v2_task = 1 LIMIT 10;"
```

---

## 📈 成功指标

### **Week 6后应该达到的状态**

#### **功能完整性**
```python
# 用户可以：
# 1. 使用新API创建任务
POST /api/v2/tasks
{
  "name": "检查服务器状态",
  "command": "uptime && df -h",
  "target_device_id": "server-001"
}

# 2. 使用模板创建任务
POST /api/v2/tasks
{
  "template_id": "health-check",
  "target_device_id": "server-001"
}

# 3. 批量调度任务
POST /api/orchestration/batch/health-check
{
  "device_ids": ["server-001", "server-002", "server-003"]
}

# 4. 使用CLI命令
hermes task create-from-template health-check server-001
hermes task status task-123
```

#### **质量指标**
- ✅ 所有单元测试通过
- ✅ 所有集成测试通过
- ✅ 所有E2E测试通过
- ✅ 代码覆盖率 > 80%
- ✅ 现有功能不受影响

#### **性能指标**
- ✅ API响应时间 < 500ms
- ✅ 支持20+设备批量调度
- ✅ 任务执行无明显延迟
- ✅ 系统资源使用合理

---

## 🚀 下一步行动

### **立即启动 (Week 1 Day 1)**

#### **上午任务 (2小时)**
1. **环境准备**
   ```bash
   cd /Users/shengchun.sun/Library/CloudStorage/OneDrive-个人/MyCloud/Code/HermesNexus
   git checkout -b feature/task-orchestration-core
   mkdir -p hermesnexus/task tests/task
   ```

2. **创建第一个文件**
   ```python
   # hermesnexus/task/__init__.py
   """
   HermesNexus任务编排模块
   """
   from .model import Task, TaskTemplate
   from .manager import TaskManager
   from .executor import TaskExecutor
   
   __all__ = ['Task', 'TaskTemplate', 'TaskManager', 'TaskExecutor']
   ```

#### **下午任务 (3小时)**
1. **实现Task核心类**
   ```python
   # hermesnexus/task/model.py
   # 实现Task和TaskTemplate类
   ```

2. **编写基础测试**
   ```python
   # tests/task/test_model.py
   # 编写Task类的单元测试
   ```

#### **晚上任务 (2小时)**
1. **运行测试验证**
   ```bash
   pytest tests/task/test_model.py -v
   ```

2. **代码质量检查**
   ```bash
   flake8 hermesnexus/task/
   mypy hermesnexus/task/
   ```

### **Week 1目标**
- ✅ Task/TaskTemplate模型完成
- ✅ 基础单元测试通过
- ✅ 代码质量检查通过
- ✅ 为Week 2做好准备

---

## 🎯 总结

### **Phase 4A的核心承诺**
1. **6周交付** - 时间明确，范围可控
2. **向后兼容** - 不破坏现有功能
3. **MVP优先** - 聚焦核心价值
4. **质量保证** - 测试覆盖完整
5. **文档齐全** - 使用说明清晰

### **成功的关键因素**
- ✅ **坚持MVP原则** - 不追求完美，快速迭代
- ✅ **保持向后兼容** - 新老API并存
- ✅ **测试驱动开发** - 每个功能都有测试
- ✅ **文档同步编写** - 代码和文档一起交付
- ✅ **持续集成验证** - 每周都有可工作的版本

---

**Phase 4A执行计划制定完成！让我们开始实现HermesNexus任务编排的核心能力。** 🚀

*计划创建时间: 2026-04-20*  
*预计完成: 2026-06-01 (6周后)*  
*状态: 🎯 **准备启动，等待执行*  
*负责人: Development Team*  
*审核者: Product Owner*