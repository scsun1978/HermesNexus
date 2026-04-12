# Phase 2 Week 2 - 数据持久化方案

**Date**: 2026-04-12
**Status**: Day 1 - 方案冻结
**Objective**: 确定SQLite作为Week 2首选持久化后端，明确数据模型映射和改造范围

---

## 1. 当前内存存储覆盖范围

### 1.1 AssetService（资产服务）
**当前存储**: `self._assets: Dict[str, Asset] = {}`
- **存储方式**: 字典（内存）
- **数据量**: 约100-10000个资产
- **访问模式**: 随机读写，按ID查询，过滤查询
- **丢失风险**: 进程重启全部丢失

### 1.2 TaskService（任务服务）
**当前存储**: `self._tasks: Dict[str, Task] = {}`
- **存储方式**: 字典（内存）
- **数据量**: 约1000-100000个任务
- **访问模式**: 随机读写，按状态查询，按时间排序
- **丢失风险**: 进程重启全部丢失，任务执行历史丢失

### 1.3 AuditService（审计服务）
**当前存储**: `self._audit_logs: List[AuditLog] = []`
- **存储方式**: 列表（内存）
- **数据量**: 约10000-1000000条日志
- **访问模式**: 追加写入，按时间/类别/级别查询
- **丢失风险**: 进程重启全部丢失，操作历史不可追溯

### 1.4 TaskScheduler（任务调度器）
**当前存储**: `self._pending_tasks: Dict[str, Task]` + `self._node_loads: Dict[str, int]`
- **存储方式**: 字典（内存）
- **数据量**: 待调度任务 + 节点负载
- **丢失风险**: 重启后调度状态丢失

---

## 2. Week 2 持久化目标

### 2.1 首选持久化后端
**SQLite** - 原因：
- ✅ 轻量级，无需额外服务
- ✅ 单文件存储，易于部署和备份
- ✅ 支持事务和ACID特性
- ✅ Python原生支持（sqlite3）
- ✅ Week 2 时间范围内可实现
- ✅ 可平滑迁移到PostgreSQL（Phase 2 Full后期）

### 2.2 数据库连接方式
- **开发环境**: 本地SQLite文件（`data/hermesnexus.db`）
- **生产环境**: 未来可切换到PostgreSQL
- **ORM框架**: 使用SQLAlchemy，便于后续切换

---

## 3. 需要落盘的数据对象

### 3.1 核心数据表

#### assets（资产表）
```sql
CREATE TABLE assets (
    asset_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    asset_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    description TEXT,
    metadata JSON,  -- 存储AssetMetadata
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    last_heartbeat_at TIMESTAMP
);

-- 索引
CREATE INDEX idx_assets_type ON assets(asset_type);
CREATE INDEX idx_assets_status ON assets(status);
CREATE INDEX idx_assets_created_at ON assets(created_at);
CREATE INDEX idx_assets_updated_at ON assets(updated_at);
```

**主键**: `asset_id`
**索引**: asset_type, status, created_at, updated_at
**关联字段**: metadata（JSON，存储扩展信息）

#### tasks（任务表）
```sql
CREATE TABLE tasks (
    task_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    priority VARCHAR(50) NOT NULL,
    target_asset_id VARCHAR(64),
    assigned_node_id VARCHAR(64),
    command TEXT,
    script_content TEXT,
    timeout_seconds INTEGER,
    description TEXT,
    result JSON,  -- 存储TaskExecutionResult
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (target_asset_id) REFERENCES assets(asset_id)
);

-- 索引
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_type ON tasks(task_type);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_asset ON tasks(target_asset_id);
CREATE INDEX idx_tasks_node ON tasks(assigned_node_id);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
CREATE INDEX idx_tasks_updated_at ON tasks(updated_at);
```

**主键**: `task_id`
**索引**: status, task_type, priority, target_asset_id, assigned_node_id, created_at, updated_at
**关联字段**: target_asset_id（外键→assets）, assigned_node_id

#### audit_logs（审计日志表）
```sql
CREATE TABLE audit_logs (
    audit_id VARCHAR(64) PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    level VARCHAR(50) NOT NULL,
    actor VARCHAR(255),
    target_type VARCHAR(50),
    target_id VARCHAR(255),
    message TEXT,
    metadata JSON,
    created_at TIMESTAMP NOT NULL,
    INDEX idx_audit_action (action),
    INDEX idx_audit_category (category),
    INDEX idx_audit_level (level),
    INDEX idx_audit_actor (actor),
    INDEX idx_audit_target (target_type, target_id),
    INDEX idx_audit_created_at (created_at)
);

-- 索引
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_category ON audit_logs(category);
CREATE INDEX idx_audit_logs_level ON audit_logs(level);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor);
CREATE INDEX idx_audit_logs_target ON audit_logs(target_type, target_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_task_id ON audit_logs(target_id) WHERE target_type = 'task';
CREATE INDEX idx_audit_logs_node_id ON audit_logs(target_id) WHERE target_type = 'node';
CREATE INDEX idx_audit_logs_asset_id ON audit_logs(target_id) WHERE target_type = 'asset';
```

**主键**: `audit_id`
**索引**: action, category, level, actor, (target_type, target_id), created_at
**关联字段**: target_id（关联task/node/asset）

### 3.2 可选数据表（Week 2暂不实现）

#### nodes（节点表）- 暂不实现
- 原因：节点信息可通过assets查询
- Week 2: 仅在内存中维护节点在线状态
- Phase 2 Full后期: 根据需要实现

#### node_metrics（节点指标表）- 暂不实现
- 原因：监控指标非Week 2核心目标
- Phase 3: 实现时序数据库存储

---

## 4. 数据模型映射

### 4.1 Asset → assets 表
| 字段 | 类型 | SQLite类型 | 说明 |
|------|------|------------|------|
| asset_id | str | VARCHAR(64) | 主键 |
| name | str | VARCHAR(255) | 必填 |
| asset_type | AssetType | VARCHAR(50) | 枚举值 |
| status | AssetStatus | VARCHAR(50) | 枚举值 |
| description | Optional[str] | TEXT | 可为空 |
| metadata | AssetMetadata | JSON | 序列化为JSON字符串 |
| created_at | datetime | TIMESTAMP | 创建时间 |
| updated_at | datetime | TIMESTAMP | 更新时间 |
| last_heartbeat_at | Optional[datetime] | TIMESTAMP | 可为空 |

### 4.2 Task → tasks 表
| 字段 | 类型 | SQLite类型 | 说明 |
|------|------|------------|------|
| task_id | str | VARCHAR(64) | 主键 |
| name | str | VARCHAR(255) | 必填 |
| task_type | TaskType | VARCHAR(50) | 枚举值 |
| status | TaskStatus | VARCHAR(50) | 枚举值 |
| priority | TaskPriority | VARCHAR(50) | 枚举值 |
| target_asset_id | str | VARCHAR(64) | 外键→assets |
| assigned_node_id | Optional[str] | VARCHAR(64) | 可为空 |
| command | Optional[str] | TEXT | 可为空 |
| script_content | Optional[str] | TEXT | 可为空 |
| timeout_seconds | int | INTEGER | 默认30 |
| description | Optional[str] | TEXT | 可为空 |
| result | Optional[TaskExecutionResult] | JSON | 序列化为JSON |
| created_at | datetime | TIMESTAMP | 创建时间 |
| updated_at | datetime | TIMESTAMP | 更新时间 |
| started_at | Optional[datetime] | TIMESTAMP | 可为空 |
| completed_at | Optional[datetime] | TIMESTAMP | 可为空 |

### 4.3 AuditLog → audit_logs 表
| 字段 | 类型 | SQLite类型 | 说明 |
|------|------|------------|------|
| audit_id | str | VARCHAR(64) | 主键 |
| action | AuditAction | VARCHAR(100) | 枚举值 |
| category | AuditCategory | VARCHAR(50) | 枚举值 |
| level | EventLevel | VARCHAR(50) | 枚举值 |
| actor | Optional[str] | VARCHAR(255) | 可为空 |
| target_type | Optional[str] | VARCHAR(50) | 可为空 |
| target_id | Optional[str] | VARCHAR(255) | 可为空 |
| message | str | TEXT | 必填 |
| metadata | Dict[str, Any] | JSON | 序列化为JSON |
| created_at | datetime | TIMESTAMP | 创建时间 |

---

## 5. 数据访问层设计

### 5.1 数据库抽象层
创建统一的数据库访问接口，支持多种后端：

```python
# shared/database/base.py
class DatabaseBackend(ABC):
    """数据库后端抽象接口"""

    @abstractmethod
    def initialize(self):
        """初始化数据库连接"""
        pass

    @abstractmethod
    def create_tables(self):
        """创建数据表"""
        pass

    @abstractmethod
    def drop_tables(self):
        """删除数据表"""
        pass

    @abstractmethod
    def close(self):
        """关闭数据库连接"""
        pass
```

### 5.2 SQLite实现
```python
# shared/database/sqlite_backend.py
class SQLiteBackend(DatabaseBackend):
    """SQLite数据库后端实现"""

    def __init__(self, db_path: str = "data/hermesnexus.db"):
        self.db_path = db_path
        self.engine = None
        self.Session = None
```

### 5.3 数据访问对象（DAO）模式
为每个实体创建对应的DAO类：

```python
# shared/dao/asset_dao.py
class AssetDAO:
    """资产数据访问对象"""

    def __init__(self, database: DatabaseBackend):
        self.database = database

    def insert(self, asset: Asset) -> Asset:
        """插入资产"""

    def select_by_id(self, asset_id: str) -> Optional[Asset]:
        """按ID查询"""

    def update(self, asset: Asset) -> Asset:
        """更新资产"""

    def delete(self, asset_id: str) -> bool:
        """删除资产"""

    def list(self, filters: Dict[str, Any]) -> List[Asset]:
        """查询资产列表"""
```

---

## 6. 最小改造范围评估

### 6.1 Service层改造
**改造策略**: 保留现有Service接口，替换内部存储实现

#### AssetService改造
```python
# 改造前
class AssetService:
    def __init__(self, database=None):
        self._assets: Dict[str, Asset] = {}  # 内存存储

# 改造后
class AssetService:
    def __init__(self, database=None):
        self.database = database
        self.asset_dao = AssetDAO(database)  # DAO访问
```

**工作量**: 中等
- ✅ 接口保持不变，API层无需改动
- ✅ 替换字典操作为DAO调用
- ⚠️ 需要处理数据库异常

#### TaskService改造
类似AssetService，引入TaskDAO替换字典存储

**工作量**: 中等
- ✅ 接口保持不变
- ✅ TaskScheduler可能需要持久化待调度任务

#### AuditService改造
```python
# 改造前
class AuditService:
    def __init__(self, database=None):
        self._audit_logs: List[AuditLog] = []
        self._index_by_task: Dict[str, List[str]] = {}

# 改造后
class AuditService:
    def __init__(self, database=None):
        self.database = database
        self.audit_dao = AuditDAO(database)  # 数据库索引查询
```

**工作量**: 中等
- ✅ 内存索引可由数据库索引替代
- ✅ 复杂查询通过SQL实现

### 6.2 API层改造
**改造策略**: 最小改动，处理数据库异常

**工作量**: 较小
- ✅ API端点无需改动
- ⚠️ 需要捕获数据库异常并转换为统一错误响应

### 6.3 配置改造
**新增配置项**:
```bash
# 数据库配置
DATABASE_TYPE=sqlite  # sqlite | postgresql
DATABASE_PATH=data/hermesnexus.db
DATABASE_ECHO=false  # 是否打印SQL语句

# 未来PostgreSQL配置
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=hermesnexus
DATABASE_USER=hermes
DATABASE_PASSWORD=***
```

---

## 7. 数据迁移策略

### 7.1 初始化脚本
创建数据库初始化脚本 `scripts/init-database.sh`:
```bash
#!/bin/bash
# 创建数据目录
mkdir -p data

# 运行数据库迁移
python3 -m shared.database.migration init

# 验证表创建
sqlite3 data/hermesnexus.db ".schema"
```

### 7.2 数据迁移（可选）
如果有现有内存数据需要迁移：
```python
# scripts/migrate_memory_to_db.py
def migrate_memory_data():
    """将内存数据迁移到数据库"""
    # 1. 读取当前内存中的资产
    # 2. 批量插入数据库
    # 3. 验证数据完整性
```

### 7.3 回滚方案
如果持久化出现问题，可以回退到内存存储：
```python
# 通过环境变量控制
if os.getenv("DATABASE_TYPE") == "memory":
    # 使用内存存储
    self._assets: Dict[str, Asset] = {}
else:
    # 使用数据库存储
    self.asset_dao = AssetDAO(database)
```

---

## 8. Week 2 实施计划

### Day 2 任务清单
1. ✅ 安装SQLAlchemy和相关依赖
2. ✅ 实现SQLiteBackend类
3. ✅ 创建数据库初始化脚本
4. ✅ 实现AssetDAO
5. ✅ 改造AssetService使用AssetDAO
6. ✅ 实现TaskDAO
7. ✅ 改造TaskService使用TaskDAO
8. ✅ 实现AuditDAO
9. ✅ 改造AuditService使用AuditDAO
10. ✅ 验证重启恢复功能

### 验收标准
- ✅ 重启服务后资产数据可恢复
- ✅ 重启服务后任务数据可恢复
- ✅ 重启服务后审计日志可恢复
- ✅ 现有API端点功能正常
- ✅ 数据库文件正确生成在 `data/hermesnexus.db`

---

## 9. 技术依赖

### 9.1 Python包
```bash
# 新增依赖
sqlalchemy==2.0.23        # ORM框架
alembic==1.13.0           # 数据库迁移工具

# 现有依赖
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
```

### 9.2 文件结构
```
shared/
  database/
    __init__.py
    base.py              # 数据库抽象接口
    sqlite_backend.py    # SQLite实现
    connection.py        # 连接管理
    migration.py         # 数据库迁移
  dao/
    __init__.py
    asset_dao.py         # 资产DAO
    task_dao.py          # 任务DAO
    audit_dao.py         # 审计DAO
scripts/
  init-database.sh       # 数据库初始化脚本
data/
  hermesnexus.db         # SQLite数据库文件（生成）
```

---

## 10. 风险与缓解

### 10.1 性能风险
**风险**: SQLite性能可能不如内存操作
**缓解**:
- 合理创建索引
- 使用连接池
- 批量操作优化
- 后续可切换到PostgreSQL

### 10.2 并发风险
**风险**: SQLite写并发受限
**缓解**:
- Week 2单进程部署，无并发写问题
- 使用WAL模式提高并发性
- 后续切换到PostgreSQL

### 10.3 兼容性风险
**风险**: 数据模型变更导致迁移困难
**缓解**:
- 使用Alembic管理数据库版本
- 从Week 2开始建立迁移脚本
- 预留metadata字段用于扩展

---

## 11. 总结

### Day 1 完成状态
✅ 确认当前内存存储覆盖范围
✅ 定义SQLite作为Week 2首选持久化后端
✅ 列出需要落盘的对象：assets / tasks / audit_logs
✅ 明确主键、索引、更新时间、关联字段
✅ 评估现有API与数据层的最小改造面

### 下一阶段
**Day 2**: 实现最小持久化存储
- 实现SQLite数据库连接
- 实现三个DAO类
- 改造三个Service类
- 验证重启恢复功能

---

**方案版本**: v1.0
**最后更新**: 2026-04-12
**状态**: ✅ 已冻结，准备进入实施阶段
