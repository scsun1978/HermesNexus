# HermesNexus Phase 4A: 任务编排核心框架实施计划

**Based on**: 方案A - 修订后的6周核心计划  
**Timeline**: 6周 (2026-04-20 ~ 2026-06-01)  
**Status**: 🎯 **已确认，准备启动**

---

## 🎯 Phase 4A 核心目标

### **总体目标**
建立任务编排的基础能力，实现云边协同的批量任务调度，为后续增强奠定基础。

### **核心价值**
1. **任务抽象**: 从单一命令升级为Task/Step模型
2. **批量调度**: 支持一次调度多个设备的任务
3. **模板复用**: 提供常用任务模板，提升效率
4. **向后兼容**: 不破坏现有API和功能
5. **快速迭代**: 6周交付可用版本，后续持续改进

---

## 📋 6周详细计划

## **Week 1-2: 基础任务模型**

### **核心目标**
建立简单直接的Task/Step模型，为任务编排奠定基础。

### **具体任务**

#### **Task 1.1: Task核心模型** (3天)
```python
# hermesnexus/task/model.py

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
    command: str  # 简化版本：单一命令
    target_device_id: str
    status: str = "pending"  # pending, running, completed, failed
    created_by: str = "system"
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.task_id is None:
            self.task_id = f"task-{uuid.uuid4()}"
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "command": self.command,
            "target_device_id": self.target_device_id,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """从字典创建"""
        return cls(
            task_id=data.get("task_id"),
            name=data["name"],
            description=data.get("description", ""),
            command=data["command"],
            target_device_id=data["target_device_id"],
            status=data.get("status", "pending"),
            created_by=data.get("created_by", "system"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            result=data.get("result")
        )

# 简单的Step模型（为后续扩展预留）
@dataclass
class Step:
    """任务步骤模型"""
    step_id: str
    step_type: str  # command, check, wait
    params: Dict[str, Any]
    timeout: int = 30
    
    def __post_init__(self):
        if self.step_id is None:
            self.step_id = f"step-{uuid.uuid4()}"

# 简单的TaskTemplate模型
@dataclass
class TaskTemplate:
    """任务模板模型"""
    template_id: str
    name: str
    description: str
    command_template: str  # 支持参数替换，如 "systemctl restart {service}"
    default_params: Dict[str, Any] = None
    
    def render(self, **kwargs) -> str:
        """渲染命令模板"""
        params = {**self.default_params, **kwargs}
        return self.command_template.format(**params)
```

#### **Task 1.2: 任务状态管理** (2天)
```python
# hermesnexus/task/manager.py

import sqlite3
from typing import List, Optional
from .model import Task

class TaskManager:
    """任务状态管理器 - 基于现有数据库扩展"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_tables()
    
    def _ensure_tables(self):
        """确保任务表存在（扩展现有jobs表）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查是否需要添加新字段
        cursor.execute("PRAGMA table_info(jobs)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        # 添加新字段（如果不存在）
        new_columns = {
            "task_template_id": "TEXT",
            "task_params": "TEXT",  # JSON string
            "is_v2_task": "INTEGER DEFAULT 0"  # 标识v2任务
        }
        
        for column, column_type in new_columns.items():
            if column not in existing_columns:
                cursor.execute(f"ALTER TABLE jobs ADD COLUMN {column} {column_type}")
        
        conn.commit()
        conn.close()
    
    def create_task(self, task: Task) -> bool:
        """创建任务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO jobs (
                    job_id, name, description, command, target_node_id, 
                    status, created_by, created_at, is_v2_task
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                task.task_id, task.name, task.description, task.command,
                task.target_device_id, task.status, task.created_by, 
                task.created_at.isoformat()
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error creating task: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT job_id, name, description, command, target_node_id, 
                       status, created_by, created_at, started_at, completed_at
                FROM jobs WHERE job_id = ? AND is_v2_task = 1
            """, (task_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return Task.from_dict({
                    "task_id": row[0],
                    "name": row[1],
                    "description": row[2] or "",
                    "command": row[3],
                    "target_device_id": row[4],
                    "status": row[5],
                    "created_by": row[6],
                    "created_at": row[7],
                    "started_at": row[8],
                    "completed_at": row[9]
                })
            return None
        except Exception as e:
            print(f"Error getting task: {e}")
            return None
    
    def update_task_status(self, task_id: str, status: str, result: dict = None):
        """更新任务状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            update_fields = {
                "status": status
            }
            
            if status == "running":
                update_fields["started_at"] = datetime.now().isoformat()
            elif status in ["completed", "failed"]:
                update_fields["completed_at"] = datetime.now().isoformat()
            
            # 构建UPDATE语句
            set_clause = ", ".join([f"{k} = ?" for k in update_fields.keys()])
            values = list(update_fields.values())
            values.append(task_id)
            
            cursor.execute(f"""
                UPDATE jobs SET {set_clause}
                WHERE job_id = ? AND is_v2_task = 1
            """, values)
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating task status: {e}")
            return False
    
    def list_tasks(self, device_id: str = None, status: str = None, limit: int = 100) -> List[Task]:
        """列出任务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM jobs WHERE is_v2_task = 1"
            params = []
            
            if device_id:
                query += " AND target_node_id = ?"
                params.append(device_id)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # 转换为Task对象列表
            tasks = []
            for row in rows:
                # 这里需要根据实际的列顺序映射
                # 简化处理，实际需要更严谨的映射
                pass
            
            return tasks
        except Exception as e:
            print(f"Error listing tasks: {e}")
            return []
```

#### **Task 1.3: 任务执行引擎** (3天)
```python
# hermesnexus/task/executor.py

import subprocess
import time
from typing import Dict, Any
from .model import Task
from .manager import TaskManager

class TaskExecutor:
    """简单的任务执行引擎"""
    
    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
    
    def execute(self, task: Task, device_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        try:
            # 更新状态为running
            self.task_manager.update_task_status(task.task_id, "running")
            
            # 执行命令（基于现有SSH机制）
            result = self._execute_command(task.command, device_config)
            
            # 更新任务状态
            if result["success"]:
                self.task_manager.update_task_status(task.task_id, "completed", result)
            else:
                self.task_manager.update_task_status(task.task_id, "failed", result)
            
            return result
        
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "return_code": -1
            }
            self.task_manager.update_task_status(task.task_id, "failed", error_result)
            return error_result
    
    def _execute_command(self, command: str, device_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行命令（复用现有SSH机制）"""
        try:
            # 使用现有的SSH连接配置
            host = device_config.get("host")
            username = device_config.get("username", "scsun")
            
            # 构建SSH命令（简化版，实际应该使用paramiko）
            ssh_command = f"ssh {username}@{host} '{command}'"
            
            # 执行命令
            result = subprocess.run(
                ssh_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=device_config.get("timeout", 30)
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command execution timeout",
                "return_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "return_code": -1
            }
```

#### **Task 1.4: 单元测试** (2天)
```python
# tests/task/test_model.py

import pytest
from hermesnexus.task.model import Task, TaskTemplate

def test_task_creation():
    """测试任务创建"""
    task = Task(
        task_id="test-001",
        name="测试任务",
        description="这是一个测试任务",
        command="echo 'hello'",
        target_device_id="device-001"
    )
    
    assert task.task_id == "test-001"
    assert task.name == "测试任务"
    assert task.status == "pending"
    assert task.created_at is not None

def test_task_to_dict():
    """测试任务转换为字典"""
    task = Task(
        task_id="test-002",
        name="测试任务2",
        description="",
        command="ls -la",
        target_device_id="device-002"
    )
    
    task_dict = task.to_dict()
    assert task_dict["task_id"] == "test-002"
    assert task_dict["name"] == "测试任务2"
    assert "command" in task_dict

def test_task_from_dict():
    """测试从字典创建任务"""
    task_dict = {
        "task_id": "test-003",
        "name": "测试任务3",
        "description": "",
        "command": "pwd",
        "target_device_id": "device-003"
    }
    
    task = Task.from_dict(task_dict)
    assert task.task_id == "test-003"
    assert task.command == "pwd"

def test_task_template_render():
    """测试任务模板渲染"""
    template = TaskTemplate(
        template_id="tmpl-001",
        name="重启服务",
        description="重启系统服务",
        command_template="systemctl restart {service}"
    )
    
    command = template.render(service="nginx")
    assert command == "systemctl restart nginx"
    
    command = template.render(service="mysql")
    assert command == "systemctl restart mysql"

# tests/task/test_manager.py

import pytest
import tempfile
import os
from hermesnexus.task.manager import TaskManager
from hermesnexus.task.model import Task

@pytest.fixture
def temp_db():
    """临时数据库"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)

def test_task_manager_create(temp_db):
    """测试任务创建"""
    manager = TaskManager(temp_db)
    
    task = Task(
        task_id="test-001",
        name="测试任务",
        description="",
        command="echo 'test'",
        target_device_id="device-001"
    )
    
    result = manager.create_task(task)
    assert result is True

def test_task_manager_get(temp_db):
    """测试获取任务"""
    manager = TaskManager(temp_db)
    
    task = Task(
        task_id="test-002",
        name="测试任务2",
        description="",
        command="ls",
        target_device_id="device-002"
    )
    
    manager.create_task(task)
    retrieved_task = manager.get_task("test-002")
    
    assert retrieved_task is not None
    assert retrieved_task.task_id == "test-002"
    assert retrieved_task.command == "ls"

def test_task_manager_update_status(temp_db):
    """测试更新任务状态"""
    manager = TaskManager(temp_db)
    
    task = Task(
        task_id="test-003",
        name="测试任务3",
        description="",
        command="pwd",
        target_device_id="device-003"
    )
    
    manager.create_task(task)
    manager.update_task_status("test-003", "running")
    
    updated_task = manager.get_task("test-003")
    assert updated_task.status == "running"
```

### **验收标准**
- ✅ Task/TaskTemplate/Step模型实现完成
- ✅ TaskManager可以创建、查询、更新任务
- ✅ TaskExecutor可以执行基础任务
- ✅ 单元测试覆盖率 > 80%
- ✅ 代码通过flake8、mypy检查

---

## **Week 3-4: 任务模板和API**

### **核心目标**
提供3个核心任务模板，实现新的v2 API，保持向后兼容。

### **具体任务**

#### **Task 2.1: 核心任务模板** (3天)
```python
# hermesnexus/task/templates.py

from .model import TaskTemplate

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
            default_params={
                "service": "nginx"  # 默认服务
            }
        )
    
    @staticmethod
    def get_backup_database_template() -> TaskTemplate:
        """数据库备份模板"""
        return TaskTemplate(
            template_id="backup-database",
            name="数据库备份",
            description="备份指定的数据库到指定路径",
            command_template="mysqldump {database} > {backup_path}/{database}_$(date +%Y%m%d_%H%M%S).sql",
            default_params={
                "database": "mydb",
                "backup_path": "/tmp/backups"
            }
        )

class TemplateManager:
    """任务模板管理器"""
    
    def __init__(self):
        self.templates = {}
        self._register_builtin_templates()
    
    def _register_builtin_templates(self):
        """注册内置模板"""
        builtin_templates = [
            CoreTemplates.get_health_check_template(),
            CoreTemplates.get_restart_service_template(),
            CoreTemplates.get_backup_database_template()
        ]
        
        for template in builtin_templates:
            self.register_template(template)
    
    def register_template(self, template: TaskTemplate):
        """注册模板"""
        self.templates[template.template_id] = template
    
    def get_template(self, template_id: str):
        """获取模板"""
        return self.templates.get(template_id)
    
    def list_templates(self):
        """列出所有模板"""
        return list(self.templates.values())
    
    def create_task_from_template(self, template_id: str, **params) -> str:
        """从模板创建任务命令"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        return template.render(**params)
```

#### **Task 2.2: v2 API实现** (4天)
```python
# cloud/api/v2.py (新文件)

from flask import Blueprint, request, jsonify
from hermesnexus.task.model import Task
from hermesnexus.task.manager import TaskManager
from hermesnexus.task.templates import TemplateManager
import datetime

v2_bp = Blueprint('api_v2', __name__, url_prefix='/api/v2')

# 初始化管理器
task_manager = TaskManager('/home/scsun/hermesnexus-data/hermesnexus-v12.db')
template_manager = TemplateManager()

@v2_bp.route('/tasks', methods=['POST'])
def create_task():
    """创建任务（v2 API）"""
    try:
        data = request.get_json()
        
        # 支持两种创建方式
        if 'template_id' in data:
            # 从模板创建
            template_id = data['template_id']
            params = data.get('params', {})
            command = template_manager.create_task_from_template(template_id, **params)
            task_name = template_manager.get_template(template_id).name
        else:
            # 直接创建
            command = data['command']
            task_name = data['name']
        
        # 创建任务
        task = Task(
            task_id=data.get('task_id'),
            name=task_name,
            description=data.get('description', ''),
            command=command,
            target_device_id=data['target_device_id'],
            created_by=data.get('created_by', 'api')
        )
        
        # 保存任务
        success = task_manager.create_task(task)
        if not success:
            return jsonify({"error": "Failed to create task"}), 500
        
        return jsonify({
            "success": True,
            "task": task.to_dict()
        }), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@v2_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取任务详情"""
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    
    return jsonify({
        "success": True,
        "task": task.to_dict()
    })

@v2_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """列出任务"""
    device_id = request.args.get('device_id')
    status = request.args.get('status')
    limit = int(request.args.get('limit', 100))
    
    tasks = task_manager.list_tasks(device_id=device_id, status=status, limit=limit)
    
    return jsonify({
        "success": True,
        "tasks": [task.to_dict() for task in tasks],
        "count": len(tasks)
    })

@v2_bp.route('/templates', methods=['GET'])
def list_templates():
    """列出任务模板"""
    templates = template_manager.list_templates()
    
    return jsonify({
        "success": True,
        "templates": [
            {
                "template_id": t.template_id,
                "name": t.name,
                "description": t.description,
                "command_template": t.command_template,
                "default_params": t.default_params
            }
            for t in templates
        ]
    })

@v2_bp.route('/templates/<template_id>/render', methods=['POST'])
def render_template(template_id):
    """渲染任务模板"""
    try:
        data = request.get_json()
        params = data.get('params', {})
        
        command = template_manager.create_task_from_template(template_id, **params)
        
        return jsonify({
            "success": True,
            "command": command
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 注册到现有Flask应用
def register_v2_api(app):
    """注册v2 API到Flask应用"""
    app.register_blueprint(v2_bp)
```

#### **Task 2.3: CLI命令** (2天)
```python
# hermesnexus/cli/v2_commands.py

import click
from hermesnexus.task.model import Task
from hermesnexus.task.manager import TaskManager
from hermesnexus.task.templates import TemplateManager

task_manager = TaskManager('/home/scsun/hermesnexus-data/hermesnexus-v12.db')
template_manager = TemplateManager()

@click.group()
def task():
    """任务管理命令"""
    pass

@task.command()
@click.argument('name')
@click.argument('command')
@click.argument('device_id')
@click.option('--description', '-d', default='')
def create(name, command, device_id, description):
    """创建任务"""
    task = Task(
        task_id=None,
        name=name,
        description=description,
        command=command,
        target_device_id=device_id
    )
    
    success = task_manager.create_task(task)
    if success:
        click.echo(f"✅ Task created: {task.task_id}")
    else:
        click.echo("❌ Failed to create task")

@task.command()
@click.argument('template_id')
@click.argument('device_id')
@click.option('--params', '-p', help='模板参数，格式: key=value')
def create_from_template(template_id, device_id, params):
    """从模板创建任务"""
    # 解析参数
    template_params = {}
    if params:
        for param in params.split(','):
            key, value = param.split('=')
            template_params[key.strip()] = value.strip()
    
    try:
        command = template_manager.create_task_from_template(template_id, **template_params)
        
        task = Task(
            task_id=None,
            name=f"Task from {template_id}",
            description=f"Created from template {template_id}",
            command=command,
            target_device_id=device_id
        )
        
        success = task_manager.create_task(task)
        if success:
            click.echo(f"✅ Task created from template: {task.task_id}")
        else:
            click.echo("❌ Failed to create task")
    
    except Exception as e:
        click.echo(f"❌ Error: {e}")

@task.command()
@click.argument('task_id')
def status(task_id):
    """查看任务状态"""
    task = task_manager.get_task(task_id)
    if task:
        click.echo(f"Task: {task.name}")
        click.echo(f"Status: {task.status}")
        click.echo(f"Command: {task.command}")
        if task.result:
            click.echo(f"Result: {task.result}")
    else:
        click.echo(f"❌ Task not found: {task_id}")

@task.command()
def templates():
    """列出所有任务模板"""
    templates = template_manager.list_templates()
    click.echo("Available templates:")
    for template in templates:
        click.echo(f"  - {template.template_id}: {template.name}")

# 注册到主CLI
def register_v2_commands(cli):
    """注册v2命令到CLI"""
    cli.add_command(task)
```

#### **Task 2.4: 集成测试** (2天)
```python
# tests/integration/test_v2_api.py

import pytest
import json
from app import app  # 假设主应用文件

@pytest.fixture
def client():
    """测试客户端"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_create_task_from_command(client):
    """测试通过命令创建任务"""
    response = client.post('/api/v2/tasks', json={
        "name": "测试任务",
        "command": "echo 'test'",
        "target_device_id": "device-001"
    })
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["success"] is True
    assert "task" in data
    assert data["task"]["name"] == "测试任务"

def test_create_task_from_template(client):
    """测试通过模板创建任务"""
    response = client.post('/api/v2/tasks', json={
        "template_id": "health-check",
        "target_device_id": "device-001"
    })
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["success"] is True
    assert "task" in data

def test_list_templates(client):
    """测试列出模板"""
    response = client.get('/api/v2/templates')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert len(data["templates"]) >= 3  # 至少3个内置模板

def test_get_task_status(client):
    """测试获取任务状态"""
    # 先创建任务
    create_response = client.post('/api/v2/tasks', json={
        "name": "状态查询测试",
        "command": "pwd",
        "target_device_id": "device-001"
    })
    task_id = json.loads(create_response.data)["task"]["task_id"]
    
    # 查询任务状态
    response = client.get(f'/api/v2/tasks/{task_id}')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["task"]["task_id"] == task_id
```

### **验收标准**
- ✅ 3个核心任务模板可用
- ✅ 新v2 API正常工作
- ✅ CLI命令正常工作
- ✅ 集成测试通过
- ✅ 现有v1 API继续工作（向后兼容）

---

## **Week 5-6: 云边任务编排**

### **核心目标**
实现云端的任务批量调度能力，支持一次调度多个设备的任务。

### **具体任务**

#### **Task 3.1: 云端任务编排器** (4天)
```python
# hermesnexus/orchestrator/cloud.py

from typing import List, Dict, Any
from hermesnexus.task.model import Task
from hermesnexus.task.manager import TaskManager
import requests

class CloudTaskOrchestrator:
    """云端任务编排器"""
    
    def __init__(self, edge_nodes_config: Dict[str, str], task_manager: TaskManager):
        self.edge_nodes = edge_nodes_config  # {device_id: edge_node_url}
        self.task_manager = task_manager
    
    def schedule_task_to_devices(self, task_spec: Dict[str, Any], device_ids: List[str]) -> Dict[str, Any]:
        """调度任务到多个设备"""
        results = {
            "success": True,
            "scheduled_count": 0,
            "failed_count": 0,
            "tasks": []
        }
        
        for device_id in device_ids:
            try:
                # 为每个设备创建任务
                task = Task(
                    task_id=None,
                    name=task_spec["name"],
                    description=task_spec.get("description", ""),
                    command=task_spec["command"],
                    target_device_id=device_id
                )
                
                # 保存任务
                if self.task_manager.create_task(task):
                    # 下发到边缘节点
                    if self._dispatch_to_edge(task, device_id):
                        results["scheduled_count"] += 1
                        results["tasks"].append({
                            "device_id": device_id,
                            "task_id": task.task_id,
                            "status": "scheduled"
                        })
                    else:
                        results["failed_count"] += 1
                        results["tasks"].append({
                            "device_id": device_id,
                            "error": "Failed to dispatch to edge node"
                        })
                else:
                    results["failed_count"] += 1
            
            except Exception as e:
                results["failed_count"] += 1
                results["tasks"].append({
                    "device_id": device_id,
                    "error": str(e)
                })
        
        results["success"] = results["failed_count"] == 0
        return results
    
    def schedule_template_to_devices(self, template_id: str, params: Dict[str, Any], 
                                    device_ids: List[str]) -> Dict[str, Any]:
        """从模板调度任务到多个设备"""
        from hermesnexus.task.templates import TemplateManager
        
        template_manager = TemplateManager()
        command = template_manager.create_task_from_template(template_id, **params)
        
        task_spec = {
            "name": f"Task from {template_id}",
            "description": f"Created from template {template_id}",
            "command": command
        }
        
        return self.schedule_task_to_devices(task_spec, device_ids)
    
    def _dispatch_to_edge(self, task: Task, device_id: str) -> bool:
        """下发任务到边缘节点"""
        try:
            edge_url = self.edge_nodes.get(device_id)
            if not edge_url:
                return False
            
            # 调用边缘节点API（使用现有机制）
            response = requests.post(
                f"{edge_url}/api/v1/tasks",
                json={
                    "job_id": task.task_id,
                    "name": task.name,
                    "command": task.command,
                    "target_node_id": device_id
                },
                timeout=10
            )
            
            return response.status_code == 200
        
        except Exception as e:
            print(f"Error dispatching to edge: {e}")
            return False

class BatchScheduler:
    """批量任务调度器"""
    
    def __init__(self, orchestrator: CloudTaskOrchestrator):
        self.orchestrator = orchestrator
    
    def schedule_health_check(self, device_ids: List[str]) -> Dict[str, Any]:
        """批量健康检查"""
        return self.orchestrator.schedule_template_to_devices(
            "health-check",
            {},
            device_ids
        )
    
    def schedule_service_restart(self, service_name: str, device_ids: List[str]) -> Dict[str, Any]:
        """批量服务重启"""
        return self.orchestrator.schedule_template_to_devices(
            "restart-service",
            {"service": service_name},
            device_ids
        )
```

#### **Task 3.2: 边缘节点v2支持** (3天)
```python
# edge-node/v2_task_handler.py (新增文件)

from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.route('/api/v2/tasks', methods=['POST'])
def receive_v2_task():
    """接收v2任务（向后兼容）"""
    try:
        data = request.get_json()
        
        # 检查任务格式
        if "command" in data:
            # v2任务格式
            job_id = data.get("task_id") or data["job_id"]
            command = data["command"]
            target_node_id = data["target_device_id"] or data["target_node_id"]
        else:
            # v1任务格式（保持兼容）
            job_id = data["job_id"]
            command = data["command"]
            target_node_id = data["target_node_id"]
        
        # 执行任务（使用现有执行机制）
        result = execute_command(command)
        
        # 回写结果（使用现有回写机制）
        report_result(job_id, result)
        
        return jsonify({"success": True, "result": result})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def execute_command(command: str) -> dict:
    """执行命令"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "return_code": -1
        }

def report_result(job_id: str, result: dict):
    """回写结果到云端"""
    try:
        # 使用现有的结果回写机制
        cloud_url = "http://172.16.100.101:8085"
        
        response = requests.patch(
            f"{cloud_url}/api/jobs/{job_id}/status",
            json={
                "status": "completed" if result["success"] else "failed",
                "result": result
            },
            timeout=5
        )
        
        return response.status_code == 200
    
    except Exception as e:
        print(f"Error reporting result: {e}")
        return False

if __name__ == '__main__':
    # v2 API与现有API并行运行
    app.run(host='0.0.0.0', port=8086)  # 使用新端口，避免冲突
```

#### **Task 3.3: 云边编排API** (2天)
```python
# cloud/api/orchestration.py (新增文件)

from flask import Blueprint, request, jsonify
from hermesnexus.orchestrator.cloud import CloudTaskOrchestrator, BatchScheduler

orchestration_bp = Blueprint('orchestration', __name__, url_prefix='/api/orchestration')

# 初始化编排器
edge_nodes_config = {
    # 示例配置，实际应该从数据库读取
    "dev-edge-node-001": "http://172.16.100.101:8086"
}

task_manager = TaskManager('/home/scsun/hermesnexus-data/hermesnexus-v12.db')
orchestrator = CloudTaskOrchestrator(edge_nodes_config, task_manager)
batch_scheduler = BatchScheduler(orchestrator)

@orchestration_bp.route('/schedule', methods=['POST'])
def schedule_tasks():
    """批量调度任务"""
    try:
        data = request.get_json()
        
        # 支持两种调度方式
        if data.get("type") == "template":
            # 从模板调度
            result = batch_scheduler.schedule_template_to_devices(
                data["template_id"],
                data.get("params", {}),
                data["device_ids"]
            )
        else:
            # 直接调度
            result = orchestrator.schedule_task_to_devices(
                data["task_spec"],
                data["device_ids"]
            )
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@orchestration_bp.route('/batch/health-check', methods=['POST'])
def batch_health_check():
    """批量健康检查"""
    data = request.get_json()
    device_ids = data.get("device_ids", [])
    
    result = batch_scheduler.schedule_health_check(device_ids)
    return jsonify(result)

@orchestration_bp.route('/batch/restart-service', methods=['POST'])
def batch_restart_service():
    """批量服务重启"""
    data = request.get_json()
    service_name = data.get("service_name")
    device_ids = data.get("device_ids", [])
    
    result = batch_scheduler.schedule_service_restart(service_name, device_ids)
    return jsonify(result)

# 注册到主应用
def register_orchestration_api(app):
    """注册编排API到Flask应用"""
    app.register_blueprint(orchestration_bp)
```

#### **Task 3.4: E2E测试和文档** (3天)
```python
# tests/e2e/test_orchestration.py

import pytest
import requests
import time

def test_batch_health_check():
    """测试批量健康检查"""
    # 准备测试设备
    device_ids = ["dev-edge-node-001"]
    
    # 调度批量健康检查
    response = requests.post('http://localhost:8085/api/orchestration/batch/health-check', json={
        "device_ids": device_ids
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["scheduled_count"] == len(device_ids)
    
    # 等待任务完成
    time.sleep(10)
    
    # 验证任务结果
    for device_id in device_ids:
        # 查询该设备的任务
        task_response = requests.get(f'http://localhost:8085/api/v2/tasks?device_id={device_id}')
        tasks = task_response.json()["tasks"]
        
        # 检查是否有健康检查任务完成
        health_check_tasks = [t for t in tasks if "health" in t["name"].lower()]
        assert len(health_check_tasks) > 0
        
        # 检查任务状态
        completed_tasks = [t for t in health_check_tasks if t["status"] == "completed"]
        assert len(completed_tasks) > 0

def test_template_based_scheduling():
    """测试基于模板的调度"""
    response = requests.post('http://localhost:8085/api/orchestration/schedule', json={
        "type": "template",
        "template_id": "restart-service",
        "params": {"service": "nginx"},
        "device_ids": ["dev-edge-node-001"]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["scheduled_count"] == 1

def test_v1_v2_compatibility():
    """测试v1和v2 API的兼容性"""
    # 使用v1 API创建任务
    v1_response = requests.post('http://localhost:8085/api/v1/tasks', json={
        "job_id": "compat-test-001",
        "name": "兼容性测试",
        "command": "echo 'v1 api'",
        "target_node_id": "dev-edge-node-001"
    })
    assert v1_response.status_code == 200
    
    # 使用v2 API创建任务
    v2_response = requests.post('http://localhost:8085/api/v2/tasks', json={
        "name": "兼容性测试v2",
        "command": "echo 'v2 api'",
        "target_device_id": "dev-edge-node-001"
    })
    assert v2_response.status_code == 201
    
    # 两种API创建的任务都应该存在
    time.sleep(5)
    
    # 验证任务都创建成功
    v1_task = requests.get('http://localhost:8085/api/jobs/compat-test-001').json()
    assert v1_task["job_id"] == "compat-test-001"
    
    v2_tasks = requests.get('http://localhost:8085/api/v2/tasks').json()
    assert any(t["name"] == "兼容性测试v2" for t in v2_tasks["tasks"])
```

### **验收标准**
- ✅ 云端可以批量调度任务到多个设备
- ✅ 边缘节点支持v2任务格式（向后兼容v1）
- ✅ E2E测试验证批量任务调度
- ✅ v1和v2 API可以并存工作
- ✅ 文档完整（API文档、使用示例）

---

## 🎯 Phase 4A 总体验收标准

### **功能完整性**
- ✅ Task/TaskTemplate模型实现
- ✅ 3个核心任务模板（健康检查、服务重启、数据库备份）
- ✅ v2 API正常工作，与v1 API并存
- ✅ 云端批量任务调度可用
- ✅ 边缘节点向后兼容

### **质量标准**
- ✅ 单元测试覆盖率 > 80%
- ✅ 集成测试覆盖核心功能
- ✅ E2E测试验证批量调度
- ✅ 代码质量检查通过
- ✅ 现有功能不受影响

### **性能标准**
- ✅ 支持批量调度20+设备
- ✅ 任务调度延迟 < 1秒
- ✅ API响应时间 < 500ms

### **可用性标准**
- ✅ API文档完整
- ✅ CLI命令可用
- ✅ 使用示例清晰
- ✅ 错误提示友好

---

## 📅 详细时间表

| **Week** | **Focus** | **Key Deliverables** | **Milestone** |
|----------|-----------|---------------------|---------------|
| **Week 1** | Task模型 | Task/TaskTemplate/Step类 | 数据模型完成 |
| **Week 2** | 执行引擎 | TaskManager/TaskExecutor + 测试 | 基础框架可用 |
| **Week 3** | 任务模板 | 3个核心模板 + TemplateManager | 模板库完成 |
| **Week 4** | API和CLI | v2 API + CLI命令 + 集成测试 | 新API完成 |
| **Week 5** | 云端编排 | CloudTaskOrchestrator + 批量调度 | 编排能力完成 |
| **Week 6** | 边缘增强 + 测试 | 边缘v2支持 + E2E测试 + 文档 | Phase 4A完成 |

---

## 🚀 立即启动准备

### **开发环境准备**
```bash
# 创建开发分支
cd /Users/shengchun.sun/Library/CloudStorage/OneDrive-个人/MyCloud/Code/HermesNexus
git checkout -b feature/task-orchestration-core

# 创建新的目录结构
mkdir -p hermesnexus/task
mkdir -p hermesnexus/orchestrator  
mkdir -p cloud/api/v2
mkdir -p tests/task
mkdir -p tests/orchestration

# 安装开发依赖
pip install pytest pytest-cov flake8 mypy

# 运行现有测试，确保基础正常
pytest tests/ --cov
```

### **Week 1 Day 1具体任务**
1. **上午 (2小时)**：创建Task/TaskTemplate基础类
2. **下午 (3小时)**：实现TaskManager基础功能
3. **晚上 (2小时)**：编写基础单元测试

### **第一个文件**
```python
# 创建 hermesnexus/task/__init__.py
"""
HermesNexus任务编排模块
"""

from .model import Task, TaskTemplate, Step
from .manager import TaskManager
from .executor import TaskExecutor

__all__ = ['Task', 'TaskTemplate', 'Step', 'TaskManager', 'TaskExecutor']
```

---

## 🎯 成功指标

### **Week 6后的目标状态**
```python
# 用户可以这样使用：
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

---

**Phase 4A计划完成！让我们开始实现任务编排的核心能力，为HermesNexus的云边协同打下坚实基础。** 🚀

*计划创建时间: 2026-04-20*  
*预计完成: 2026-06-01 (6周后)*  
*状态: 🎯 **已确认，准备启动*