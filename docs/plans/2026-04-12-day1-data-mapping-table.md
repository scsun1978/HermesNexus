# Phase 2 Week 2 - 数据模型映射表

**Date**: 2026-04-12
**Purpose**: 详细定义Pydantic模型到SQLite表的映射关系

---

## 1. Asset 模型映射

### 1.1 模型定义
```python
# shared/models/asset.py
class Asset(BaseModel):
    asset_id: str
    name: str
    asset_type: AssetType
    status: AssetStatus
    description: Optional[str] = None
    metadata: Optional[AssetMetadata] = None
    created_at: datetime
    updated_at: datetime
    last_heartbeat_at: Optional[datetime] = None
```

### 1.2 SQLite表结构
```sql
CREATE TABLE assets (
    asset_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    asset_type VARCHAR(50) NOT NULL,  -- 'edge_node' | 'linux_host' | 'network_device' | 'iot_device'
    status VARCHAR(50) NOT NULL,       -- 'registered' | 'active' | 'inactive' | 'decommissioned'
    description TEXT,
    metadata JSON,                     -- {"ip_address": "...", "hostname": "...", ...}
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    last_heartbeat_at TIMESTAMP
);
```

### 1.3 字段映射
| Python字段 | SQLite字段 | 类型转换 | 约束 |
|-----------|-----------|---------|------|
| asset_id | asset_id | str → VARCHAR(64) | PRIMARY KEY |
| name | name | str → VARCHAR(255) | NOT NULL |
| asset_type | asset_type | Enum → VARCHAR(50) | NOT NULL |
| status | status | Enum → VARCHAR(50) | NOT NULL |
| description | description | Optional[str] → TEXT | NULL |
| metadata | metadata | Dict → JSON | NULL |
| created_at | created_at | datetime → TIMESTAMP | NOT NULL |
| updated_at | updated_at | datetime → TIMESTAMP | NOT NULL |
| last_heartbeat_at | last_heartbeat_at | Optional[datetime] → TIMESTAMP | NULL |

### 1.4 索引策略
```sql
-- 查询优化索引
CREATE INDEX idx_assets_type ON assets(asset_type);
CREATE INDEX idx_assets_status ON assets(status);
CREATE INDEX idx_assets_created_at ON assets(created_at);
CREATE INDEX idx_assets_updated_at ON assets(updated_at);

-- 复合索引（常见查询组合）
CREATE INDEX idx_assets_type_status ON assets(asset_type, status);
```

### 1.5 数据验证
```python
# 模型验证规则（Pydantic）
class AssetType(str, Enum):
    edge_node = "edge_node"
    linux_host = "linux_host"
    network_device = "network_device"
    iot_device = "iot_device"

class AssetStatus(str, Enum):
    registered = "registered"
    active = "active"
    inactive = "inactive"
    decommissioned = "decommissioned"
```

---

## 2. Task 模型映射

### 2.1 模型定义
```python
# shared/models/task.py
class Task(BaseModel):
    task_id: str
    name: str
    task_type: TaskType
    status: TaskStatus
    priority: TaskPriority
    target_asset_id: str
    assigned_node_id: Optional[str] = None
    command: Optional[str] = None
    script_content: Optional[str] = None
    timeout_seconds: int = 30
    description: Optional[str] = None
    result: Optional[TaskExecutionResult] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
```

### 2.2 SQLite表结构
```sql
CREATE TABLE tasks (
    task_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    priority VARCHAR(50) NOT NULL,
    target_asset_id VARCHAR(64) NOT NULL,
    assigned_node_id VARCHAR(64),
    command TEXT,
    script_content TEXT,
    timeout_seconds INTEGER NOT NULL DEFAULT 30,
    description TEXT,
    result JSON,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (target_asset_id) REFERENCES assets(asset_id) ON DELETE SET NULL
);
```

### 2.3 字段映射
| Python字段 | SQLite字段 | 类型转换 | 约束 |
|-----------|-----------|---------|------|
| task_id | task_id | str → VARCHAR(64) | PRIMARY KEY |
| name | name | str → VARCHAR(255) | NOT NULL |
| task_type | task_type | Enum → VARCHAR(50) | NOT NULL |
| status | status | Enum → VARCHAR(50) | NOT NULL |
| priority | priority | Enum → VARCHAR(50) | NOT NULL |
| target_asset_id | target_asset_id | str → VARCHAR(64) | FOREIGN KEY |
| assigned_node_id | assigned_node_id | Optional[str] → VARCHAR(64) | NULL |
| command | command | Optional[str] → TEXT | NULL |
| script_content | script_content | Optional[str] → TEXT | NULL |
| timeout_seconds | timeout_seconds | int → INTEGER | DEFAULT 30 |
| description | description | Optional[str] → TEXT | NULL |
| result | result | Optional[TaskExecutionResult] → JSON | NULL |
| created_at | created_at | datetime → TIMESTAMP | NOT NULL |
| updated_at | updated_at | datetime → TIMESTAMP | NOT NULL |
| started_at | started_at | Optional[datetime] → TIMESTAMP | NULL |
| completed_at | completed_at | Optional[datetime] → TIMESTAMP | NULL |

### 2.4 索引策略
```sql
-- 查询优化索引
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_type ON tasks(task_type);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_asset ON tasks(target_asset_id);
CREATE INDEX idx_tasks_node ON tasks(assigned_node_id);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
CREATE INDEX idx_tasks_updated_at ON tasks(updated_at);

-- 复合索引（常见查询组合）
CREATE INDEX idx_tasks_status_priority ON tasks(status, priority);
CREATE INDEX idx_tasks_asset_status ON tasks(target_asset_id, status);
```

### 2.5 数据验证
```python
# 模型验证规则（Pydantic）
class TaskType(str, Enum):
    basic_exec = "basic_exec"
    script_transfer = "script_transfer"
    file_transfer = "file_transfer"
    system_info = "system_info"
    custom = "custom"

class TaskStatus(str, Enum):
    pending = "pending"
    assigned = "assigned"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    timeout = "timeout"
    cancelled = "cancelled"

class TaskPriority(str, Enum):
    urgent = "urgent"
    high = "high"
    normal = "normal"
    low = "low"
```

---

## 3. AuditLog 模型映射

### 3.1 模型定义
```python
# shared/models/audit.py
class AuditLog(BaseModel):
    audit_id: str
    action: AuditAction
    category: AuditCategory
    level: EventLevel
    actor: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    message: str
    metadata: Dict[str, Any]
    created_at: datetime
```

### 3.2 SQLite表结构
```sql
CREATE TABLE audit_logs (
    audit_id VARCHAR(64) PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    level VARCHAR(50) NOT NULL,
    actor VARCHAR(255),
    target_type VARCHAR(50),
    target_id VARCHAR(255),
    message TEXT NOT NULL,
    metadata JSON,
    created_at TIMESTAMP NOT NULL
);
```

### 3.3 字段映射
| Python字段 | SQLite字段 | 类型转换 | 约束 |
|-----------|-----------|---------|------|
| audit_id | audit_id | str → VARCHAR(64) | PRIMARY KEY |
| action | action | AuditAction → VARCHAR(100) | NOT NULL |
| category | category | AuditCategory → VARCHAR(50) | NOT NULL |
| level | level | EventLevel → VARCHAR(50) | NOT NULL |
| actor | actor | Optional[str] → VARCHAR(255) | NULL |
| target_type | target_type | Optional[str] → VARCHAR(50) | NULL |
| target_id | target_id | Optional[str] → VARCHAR(255) | NULL |
| message | message | str → TEXT | NOT NULL |
| metadata | metadata | Dict → JSON | NULL |
| created_at | created_at | datetime → TIMESTAMP | NOT NULL |

### 3.4 索引策略
```sql
-- 查询优化索引
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_category ON audit_logs(category);
CREATE INDEX idx_audit_logs_level ON audit_logs(level);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor);
CREATE INDEX idx_audit_logs_target ON audit_logs(target_type, target_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- 条件索引（特定类型查询）
CREATE INDEX idx_audit_logs_task_id ON audit_logs(target_id) WHERE target_type = 'task';
CREATE INDEX idx_audit_logs_node_id ON audit_logs(target_id) WHERE target_type = 'node';
CREATE INDEX idx_audit_logs_asset_id ON audit_logs(target_id) WHERE target_type = 'asset';

-- 复合索引（时间范围查询）
CREATE INDEX idx_audit_logs_category_created ON audit_logs(category, created_at DESC);
```

### 3.5 数据验证
```python
# 模型验证规则（Pydantic）
class AuditAction(str, Enum):
    # Task actions
    task_created = "task_created"
    task_assigned = "task_assigned"
    task_started = "task_started"
    task_succeeded = "task_succeeded"
    task_failed = "task_failed"
    task_cancelled = "task_cancelled"
    # ... (30+ actions)

class AuditCategory(str, Enum):
    task = "task"
    node = "node"
    asset = "asset"
    system = "system"
    security = "security"
    user = "user"

class EventLevel(str, Enum):
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"
```

---

## 4. JSON字段处理

### 4.1 Asset.metadata
```python
# 存储格式（JSON字符串）
{
    "ip_address": "192.168.1.100",
    "hostname": "server01",
    "ssh_port": 22,
    "ssh_username": "admin",
    "tags": ["production", "web"],
    "custom_field": "custom_value"
}

# SQLite存储
metadata JSON  -- '{"ip_address": "192.168.1.100", "hostname": "server01", ...}'
```

### 4.2 Task.result
```python
# 存储格式（JSON字符串）
{
    "exit_code": 0,
    "stdout": "command output",
    "stderr": "",
    "execution_time": 1.23,
    "started_at": "2026-04-12T10:00:00Z",
    "completed_at": "2026-04-12T10:00:01Z",
    "node_id": "node-001",
    "error_message": null
}

# SQLite存储
result JSON  -- '{"exit_code": 0, "stdout": "command output", ...}'
```

### 4.3 AuditLog.metadata
```python
# 存储格式（JSON字符串）
{
    "task_type": "basic_exec",
    "command": "uptime",
    "duration": 0.5,
    "additional_info": "value"
}

# SQLite存储
metadata JSON  -- '{"task_type": "basic_exec", "command": "uptime", ...}'
```

---

## 5. 时间字段处理

### 5.1 时区约定
- **存储格式**: UTC时区，ISO 8601格式
- **Python类型**: `datetime.datetime` with `tzinfo=datetime.timezone.utc`
- **SQLite类型**: `TIMESTAMP` (存储为ISO 8601字符串)

### 5.2 时间字段列表
| 字段 | 用途 | 更新时机 | 必填 |
|------|------|---------|------|
| created_at | 创建时间 | 插入时设置 | ✅ |
| updated_at | 更新时间 | 每次更新时刷新 | ✅ |
| last_heartbeat_at | 最后心跳 | 节点心跳时更新 | ❌ |
| started_at | 任务开始 | 任务开始执行时设置 | ❌ |
| completed_at | 任务完成 | 任务完成时设置 | ❌ |

### 5.3 时间更新策略
```python
# 插入时
created_at = datetime.utcnow()
updated_at = datetime.utcnow()

# 更新时
updated_at = datetime.utcnow()

# 查询时转换为UTC
task.started_at = datetime.utcnow()
```

---

## 6. 数据库约束

### 6.1 主键约束
```sql
-- 单一主键
PRIMARY KEY (asset_id)
PRIMARY KEY (task_id)
PRIMARY KEY (audit_id)
```

### 6.2 外键约束
```sql
-- 任务表引用资产表
FOREIGN KEY (target_asset_id) REFERENCES assets(asset_id) ON DELETE SET NULL

-- 行为说明：
-- ON DELETE SET NULL: 资产删除时，任务的target_asset_id设为NULL
-- ON UPDATE CASCADE: 资产ID更新时，自动更新任务中的引用
```

### 6.3 非空约束
```sql
-- 关键字段非空
NOT NULL (asset_id, name, asset_type, status, created_at, updated_at)
NOT NULL (task_id, name, task_type, status, priority, target_asset_id, created_at, updated_at)
NOT NULL (audit_id, action, category, level, message, created_at)
```

### 6.4 默认值约束
```sql
-- timeout_seconds默认值
timeout_seconds INTEGER NOT NULL DEFAULT 30

-- 状态默认值（通过应用层控制）
```

---

## 7. 数据迁移清单

### 7.1 必须保留的字段
- ✅ 所有主键字段：asset_id, task_id, audit_id
- ✅ 所有业务关键字段：name, type, status
- ✅ 所有关联字段：target_asset_id, assigned_node_id
- ✅ 所有时间字段：created_at, updated_at
- ✅ 元数据字段：metadata, result

### 7.2 可选字段
- ❌ description（可为NULL）
- ❌ last_heartbeat_at（可为NULL）
- ❌ started_at, completed_at（可为NULL）

### 7.3 迁移步骤
1. 创建数据表结构
2. 从内存字典读取现有数据
3. 批量插入数据到数据库
4. 验证数据完整性
5. 切换Service使用数据库

### 7.4 迁移验证
```python
# 验证数据完整性
def verify_migration():
    # 1. 检查记录数
    assert len(memory_assets) == db_asset_count

    # 2. 检查关键字段
    for asset in memory_assets.values():
        db_asset = asset_dao.select_by_id(asset.asset_id)
        assert db_asset is not None
        assert db_asset.name == asset.name
        assert db_asset.asset_type == asset.asset_type

    # 3. 检查关联关系
    for task in memory_tasks.values():
        db_task = task_dao.select_by_id(task.task_id)
        assert db_task.target_asset_id == task.target_asset_id
```

---

## 8. 性能优化建议

### 8.1 批量操作
```python
# 批量插入（推荐）
def batch_insert_assets(assets: List[Asset]):
    session.bulk_insert_mappings(Asset, [asset.dict() for asset in assets])
    session.commit()

# 避免逐条插入
for asset in assets:
    session.add(asset)  # ❌ 性能差
session.commit()
```

### 8.2 查询优化
```python
# 使用索引字段查询
assets = asset_dao.list(filters={"asset_type": "linux_host"})  # ✅ 使用索引

# 避免全表扫描
assets = asset_dao.list(filters={"name": "server%"})  # ⚠️ 可能全表扫描
```

### 8.3 连接池配置
```python
# SQLAlchemy连接池配置
engine = create_engine(
    'sqlite:///data/hermesnexus.db',
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # SQLite使用静态连接池
    echo=False  # 生产环境关闭SQL日志
)
```

---

## 9. 总结

### 映射表完成状态
✅ Asset模型映射完成
✅ Task模型映射完成
✅ AuditLog模型映射完成
✅ JSON字段处理策略确定
✅ 时间字段处理约定
✅ 数据库约束定义
✅ 迁移验证方法

### 下一步
**Day 2**: 实现最小持久化存储
- 根据映射表创建DAO类
- 实现数据库初始化脚本
- 改造Service使用DAO

---

**映射表版本**: v1.0
**最后更新**: 2026-04-12
**状态**: ✅ 已完成，可用于实施
