# Phase 2 Week 2 - 迁移范围清单

**Date**: 2026-04-12
**Purpose**: 明确从内存存储到数据库存储的迁移范围和步骤

---

## 1. 迁移目标

### 1.1 核心目标
将HermesNexus从"内存可跑"状态迁移到"可持久化"状态，确保：
- ✅ 数据在服务重启后不丢失
- ✅ 支持数据查询和索引
- ✅ 保持现有API接口不变
- ✅ 最小化代码改动

### 1.2 非目标（暂不实现）
- ❌ 高级查询功能（复杂JOIN、聚合）
- ❌ 数据库集群和高可用
- ❌ 性能优化（读写分离、分库分表）
- ❌ 数据迁移工具（从其他系统导入）
- ❌ 数据库备份恢复策略

---

## 2. 迁移范围

### 2.1 数据范围

#### 必须迁移的数据
| 数据类型 | 当前存储 | 目标存储 | 优先级 |
|---------|---------|---------|-------|
| **资产数据** | `AssetService._assets` | `assets` 表 | P0 |
| **任务数据** | `TaskService._tasks` | `tasks` 表 | P0 |
| **审计日志** | `AuditService._audit_logs` | `audit_logs` 表 | P0 |
| **节点负载** | `TaskScheduler._node_loads` | 内存（暂不迁移） | P2 |

#### 不迁移的数据
| 数据类型 | 原因 | 处理方式 |
|---------|------|---------|
| **节点在线状态** | 动态状态，重启后重新计算 | 启动时重置为离线 |
| **任务调度队列** | 临时状态，重启后重新调度 | 启动时重置为空 |
| **缓存数据** | 临时缓存，可重建 | 启动时清空 |

### 2.2 功能范围

#### 必须支持的功能
- ✅ 资产CRUD操作
- ✅ 任务CRUD操作
- ✅ 审计日志记录和查询
- ✅ 列表查询（分页、过滤、排序）
- ✅ 统计查询（count、group by）
- ✅ 关联查询（任务→资产，审计→任务/节点/资产）

#### 暂不支持的功能
- ❌ 复杂事务（跨表事务）
- ❌ 批量导入导出（CSV、Excel）
- ❌ 数据库备份恢复
- ❌ 数据库版本升级（Alembic迁移）

---

## 3. 代码改造范围

### 3.1 Service层改造

#### AssetService改造
**文件**: `shared/services/asset_service.py`

**改造前**:
```python
class AssetService:
    def __init__(self, database=None):
        self.database = database
        self._assets: Dict[str, Asset] = {}  # 内存存储

    def create_asset(self, request: AssetCreateRequest) -> Asset:
        # 直接操作字典
        asset = Asset(...)
        self._assets[asset.asset_id] = asset
        return asset
```

**改造后**:
```python
class AssetService:
    def __init__(self, database=None):
        self.database = database
        self.asset_dao = AssetDAO(database)  # DAO访问

    def create_asset(self, request: AssetCreateRequest) -> Asset:
        # 通过DAO访问数据库
        asset = Asset(...)
        return self.asset_dao.insert(asset)
```

**改动点**:
- ✅ 字典操作 → DAO调用
- ✅ 内存查询 → 数据库查询
- ⚠️ 需要处理数据库异常

**工作量**: 2-3小时
- 改造CRUD方法：create, get, update, delete, list
- 改造统计方法：get_stats
- 处理数据库异常

#### TaskService改造
**文件**: `shared/services/task_service.py`

**改造范围**: 类似AssetService
- 字典操作 → DAO调用
- 保留TaskScheduler内存调度（暂不持久化）
- 处理数据库异常

**工作量**: 2-3小时

#### AuditService改造
**文件**: `shared/services/audit_service.py`

**改造前**:
```python
class AuditService:
    def __init__(self, database=None):
        self.database = database
        self._audit_logs: List[AuditLog] = []
        self._index_by_task: Dict[str, List[str]] = {}
        self._index_by_node: Dict[str, List[str]] = {}
        self._index_by_asset: Dict[str, List[str]] = {}
```

**改造后**:
```python
class AuditService:
    def __init__(self, database=None):
        self.database = database
        self.audit_dao = AuditDAO(database)
        # 内存索引由数据库索引替代
```

**改动点**:
- ✅ 列表操作 → DAO调用
- ✅ 内存索引 → 数据库索引
- ✅ 复杂查询 → SQL查询

**工作量**: 2-3小时

### 3.2 新增DAO层

#### 新增文件
```
shared/
  dao/
    __init__.py
    base_dao.py         # DAO基类
    asset_dao.py        # 资产DAO
    task_dao.py         # 任务DAO
    audit_dao.py        # 审计DAO
```

#### DAO基类设计
```python
# shared/dao/base_dao.py
class BaseDAO(ABC):
    """DAO基类，提供通用CRUD操作"""

    def __init__(self, database):
        self.database = database

    @abstractmethod
    def insert(self, entity) -> Any:
        """插入实体"""
        pass

    @abstractmethod
    def select_by_id(self, id: str) -> Optional[Any]:
        """按ID查询"""
        pass

    @abstractmethod
    def update(self, entity) -> Any:
        """更新实体"""
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """删除实体"""
        pass
```

**工作量**: 4-6小时
- 实现BaseDAO基类
- 实现AssetDAO（3-4个方法）
- 实现TaskDAO（5-6个方法）
- 实现AuditDAO（4-5个方法）

### 3.3 新增数据库层

#### 新增文件
```
shared/
  database/
    __init__.py
    base.py              # 数据库抽象接口
    sqlite_backend.py    # SQLite实现
    connection.py        # 连接管理
    models.py            # SQLAlchemy ORM模型
```

#### 文件说明
- **base.py**: 定义DatabaseBackend抽象接口
- **sqlite_backend.py**: SQLiteBackend实现
- **connection.py**: 数据库连接管理（连接池、会话工厂）
- **models.py**: SQLAlchemy ORM模型定义

**工作量**: 4-6小时
- 实现DatabaseBackend接口
- 实现SQLiteBackend类
- 实现连接管理
- 定义3个ORM模型

### 3.4 API层改造

#### 改动范围
**文件**: `cloud/api/asset_api.py`, `cloud/api/task_api.py`, `cloud/api/audit_api.py`

**改动点**:
- ⚠️ 处理数据库异常（IntegrityError, OperationalError）
- ✅ 捕获异常并转换为统一错误响应

**工作量**: 1-2小时
- 在API端点添加异常处理
- 确保错误响应格式一致

### 3.5 配置文件改动

#### 新增配置项
```bash
# .env.development
DATABASE_TYPE=sqlite
DATABASE_PATH=data/hermesnexus.db
DATABASE_ECHO=false  # 开发环境可设为true查看SQL

# 未来PostgreSQL配置（暂不使用）
# DATABASE_HOST=localhost
# DATABASE_PORT=5432
# DATABASE_NAME=hermesnexus
# DATABASE_USER=hermes
# DATABASE_PASSWORD=***
```

**改动文件**:
- `.env.development` - 新增数据库配置
- `.env.production` - 新增数据库配置

**工作量**: 0.5小时

---

## 4. 依赖安装范围

### 4.1 新增Python包

#### requirements.txt新增
```bash
# 数据库ORM
sqlalchemy==2.0.23

# 数据库迁移工具（暂不使用）
# alembic==1.13.0
```

#### 安装验证
```bash
pip install -r requirements.txt
python3 -c "import sqlalchemy; print('SQLAlchemy OK')"
```

**工作量**: 0.5小时

---

## 5. 脚本工具范围

### 5.1 新增脚本

#### 数据库初始化脚本
**文件**: `scripts/init-database.sh`

**功能**:
- 创建数据目录
- 初始化数据库连接
- 创建所有表
- 验证表创建成功

**工作量**: 1小时

#### 配置验证脚本更新
**文件**: `scripts/validate-config.py`

**改动**:
- 新增数据库配置验证
- 检查数据库文件权限
- 验证数据库连接

**工作量**: 0.5小时

### 5.2 更新脚本

#### 启动脚本更新
**文件**: `scripts/start-cloud-api.sh`

**改动**:
- 启动前检查数据库是否初始化
- 如果未初始化，自动运行初始化脚本

**工作量**: 0.5小时

---

## 6. 测试范围

### 6.1 单元测试（暂不实现）

#### 不在Week 2范围内
- ❌ DAO层单元测试
- ❌ Service层单元测试
- ❌ API层单元测试

**原因**: Week 2重点是实现持久化，测试补齐在Day 4

### 6.2 集成测试（Day 4实现）

#### 测试范围
- ✅ 持久化读写测试
- ✅ 重启恢复测试
- ✅ API端点回归测试

---

## 7. 文档更新范围

### 7.1 新增文档
- ✅ 数据持久化方案（Day 1）
- ✅ 数据模型映射表（Day 1）
- ✅ 迁移范围清单（Day 1）

### 7.2 更新文档
- ⚠️ 部署文档（Day 5更新）
- ⚠️ 验收清单（Day 7更新）
- ⚠️ API文档（如果API行为有变化）

---

## 8. 迁移步骤

### 8.1 Day 2实施步骤

#### Step 1: 安装依赖（15分钟）
```bash
# 更新requirements.txt
echo "sqlalchemy==2.0.23" >> requirements.txt

# 安装依赖
pip install -r requirements.txt
```

#### Step 2: 创建数据库层（2-3小时）
```bash
# 创建目录
mkdir -p shared/database shared/dao

# 实现数据库抽象层
touch shared/database/base.py
touch shared/database/sqlite_backend.py
touch shared/database/connection.py
touch shared/database/models.py
```

#### Step 3: 实现DAO层（2-3小时）
```bash
# 创建DAO文件
touch shared/dao/__init__.py
touch shared/dao/base_dao.py
touch shared/dao/asset_dao.py
touch shared/dao/task_dao.py
touch shared/dao/audit_dao.py
```

#### Step 4: 改造Service层（2-3小时）
```bash
# 改造顺序
1. AssetService (1小时)
2. TaskService (1小时)
3. AuditService (1小时)
```

#### Step 5: 更新配置和脚本（1小时）
```bash
# 更新环境配置
# 更新启动脚本
# 创建初始化脚本
```

#### Step 6: 验证功能（1-2小时）
```bash
# 启动服务
./scripts/start-cloud-api.sh

# 验证API
curl http://localhost:8080/api/v1/assets
curl http://localhost:8080/api/v1/tasks
curl http://localhost:8080/api/v1/audit_logs

# 验证重启恢复
./scripts/stop-services.sh
./scripts/start-cloud-api.sh
curl http://localhost:8080/api/v1/assets  # 数据应该还在
```

### 8.2 回滚方案

#### 如果迁移失败
```bash
# 方案1: 回退到内存存储
export DATABASE_TYPE=memory
./scripts/start-cloud-api.sh

# 方案2: 回退代码
git checkout <previous-commit>
pip install -r requirements.txt
./scripts/start-cloud-api.sh
```

---

## 9. 风险评估

### 9.1 技术风险

| 风险 | 严重性 | 概率 | 缓解措施 |
|------|-------|------|---------|
| **数据库性能问题** | 中 | 低 | 合理创建索引，后续优化 |
| **数据迁移失败** | 高 | 低 | 充分测试，准备回滚方案 |
| **接口不兼容** | 高 | 低 | 保持接口不变，仅改实现 |
| **依赖冲突** | 中 | 低 | 使用虚拟环境隔离 |

### 9.2 业务风险

| 风险 | 严重性 | 概率 | 缓解措施 |
|------|-------|------|---------|
| **数据丢失** | 高 | 极低 | 备份现有数据，充分测试 |
| **服务不可用** | 中 | 低 | 在低峰期执行，准备回滚 |
| **功能缺失** | 中 | 低 | 严格按原功能实现 |

---

## 10. 验收标准

### 10.1 Day 2验收标准
- ✅ 数据库文件正确生成（`data/hermesnexus.db`）
- ✅ 资产CRUD操作正常工作
- ✅ 任务CRUD操作正常工作
- ✅ 审计日志记录和查询正常
- ✅ 重启后数据不丢失
- ✅ 现有API端点功能正常

### 10.2 验证命令
```bash
# 1. 检查数据库文件
ls -lh data/hermesnexus.db

# 2. 验证表结构
sqlite3 data/hermesnexus.db ".schema"

# 3. 验证数据持久化
curl -X POST http://localhost:8080/api/v1/assets -d '{...}'
./scripts/stop-services.sh
./scripts/start-cloud-api.sh
curl http://localhost:8080/api/v1/assets  # 数据应该还在

# 4. 验证API功能
./tests/scripts/smoke_test.sh
```

---

## 11. 工作量估算

### 11.1 总工作量估算
| 任务 | 工作量 | 责任人 |
|------|-------|-------|
| 数据库层实现 | 4-6小时 | 开发 |
| DAO层实现 | 4-6小时 | 开发 |
| Service层改造 | 6-9小时 | 开发 |
| 配置和脚本 | 2小时 | 开发 |
| 测试验证 | 2-3小时 | 开发+测试 |
| **总计** | **18-26小时** | |

### 11.2 进度安排
- **Day 2上午**: 数据库层 + DAO层
- **Day 2下午**: Service层改造
- **Day 2晚上**: 配置脚本 + 测试验证

---

## 12. 总结

### 迁移范围完成状态
✅ 数据范围明确
✅ 功能范围明确
✅ 代码改造范围清晰
✅ 迁移步骤详细
✅ 风险评估完成
✅ 验收标准定义

### 准备就绪
**Day 1准备完成，可以进入Day 2实施阶段**

---

**清单版本**: v1.0
**最后更新**: 2026-04-12
**状态**: ✅ 已完成，可用于实施
