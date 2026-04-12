# Phase 2 对象模型与契约规范

**Date**: 2026-04-12  
**Status**: Day 1 冻结版本  
**Purpose**: 统一 device/node/task/audit 的边界，避免后续实现反复返工

## 1. 当前概念混用问题

从 Phase 1 MVP 和现有文档中识别到的概念混用：

### 混用概念列表
- **jobs vs tasks**: 在 API 中作为别名存在（POST /api/v1/jobs 或 POST /api/v1/tasks）
- **devices vs nodes**: nodes 表存储设备信息，但文档中同时出现两个概念
- **assets**: Phase 2 引入的新概念，与 devices/nodes 的关系不明确
- **audit logs**: 已有实现，但与 events 的边界模糊

### 问题影响
1. API 契约不统一（jobs/tasks 混用）
2. 数据模型语义模糊（node 到底是物理节点还是逻辑设备？）
3. Phase 2 资产管理无法清晰对接现有实现

## 2. 统一对象模型

### 2.1 核心对象定义

#### Asset（资产）
**定义**: 纳入平台管理的所有计算资源的抽象表示

**职责**:
- 资产的注册与生命周期管理
- 资产类型划分（edge_node, linux_host, network_device, iot_device）
- 资产与 Node 的映射关系（一对一）

**状态枚举**:
```python
class AssetStatus(str, Enum):
    REGISTERED = "registered"    # 已注册，未关联运行节点
    ACTIVE = "active"            # 活跃，有运行节点在线
    INACTIVE = "inactive"        # 非活跃，运行节点离线
    DECOMMISSIONED = "decommissioned"  # 已退役
```

**数据模型字段**:
- asset_id: str (主键)
- name: str
- asset_type: AssetType
- status: AssetStatus
- metadata: dict (扩展属性，IP、SSH配置等)
- created_at: datetime
- updated_at: datetime

#### Node（运行节点）
**定义**: 边缘运行时的实例，是任务执行的实际载体

**职责**:
- 向云端注册和心跳
- 轮询任务并执行
- 回报执行结果

**与 Asset 的关系**: Node 是 Asset 的运行实例，一个 Asset 同一时间最多有一个活跃 Node

**状态枚举**:
```python
class NodeStatus(str, Enum):
    REGISTERED = "registered"  # 已注册，首次连接
    ONLINE = "online"          # 在线，可接收任务
    BUSY = "busy"              # 忙碌，正在执行任务
    OFFLINE = "offline"        # 离线，心跳超时
    DEGRADED = "degraded"      # 降级，部分功能不可用
```

**数据模型字段**:
- node_id: str (主键，对应 asset_id)
- asset_id: str (外键到 Asset)
- status: NodeStatus
- capabilities: dict (协议支持、并发数等)
- last_heartbeat: datetime
- version: str (运行时版本)

#### Task（任务）
**定义**: 需要在目标 Node 上执行的异步指令单元

**职责**:
- 任务创建与调度
- 执行状态跟踪
- 结果归档

**命名统一**: **废除 jobs 别名，统一使用 tasks**

**状态枚举**:
```python
class TaskStatus(str, Enum):
    PENDING = "pending"        # 待调度
    ASSIGNED = "assigned"      # 已分配给节点
    RUNNING = "running"        # 执行中
    SUCCEEDED = "succeeded"    # 成功完成
    FAILED = "failed"          # 执行失败
    TIMEOUT = "timeout"        # 执行超时
    CANCELLED = "cancelled"    # 已取消
```

**数据模型字段**:
- task_id: str (主键)
- name: str
- task_type: TaskType (basic_exec, script_transfer, etc.)
- target_node_id: str (外键到 Node)
- command: str
- timeout: int
- status: TaskStatus
- result: dict (执行结果，标准输出、错误输出、退出码)
- created_at: datetime
- assigned_at: datetime
- started_at: datetime
- completed_at: datetime

#### AuditLog（审计日志）
**定义**: 所有关键操作的不可变记录

**职责**:
- 记录任务生命周期事件
- 记录节点状态变更
- 支持合规查询

**与 Event 的区别**:
- AuditLog: 人类可读的操作记录，用于审计和排障
- Event: 系统级事件流，用于实时监控和告警

**动作枚举**:
```python
class AuditAction(str, Enum):
    # Task lifecycle
    TASK_CREATED = "task_created"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_SUCCEEDED = "task_succeeded"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    
    # Node lifecycle
    NODE_REGISTERED = "node_registered"
    NODE_ONLINE = "node_online"
    NODE_OFFLINE = "node_offline"
    
    # Asset lifecycle
    ASSET_REGISTERED = "asset_registered"
    ASSET_UPDATED = "asset_updated"
    ASSET_DECOMMISSIONED = "asset_decommissioned"
```

**数据模型字段**:
- audit_id: str (主键)
- action: AuditAction
- actor: str (操作发起者)
- target_type: str (task/node/asset)
- target_id: str
- details: dict (上下文信息)
- timestamp: datetime
- level: EventLevel (INFO, WARNING, ERROR)

## 3. API 契约统一

### 3.1 核心原则
1. **单一命名**: 统一使用 /api/v1/tasks，废除 /api/v1/jobs
2. **资源层级**: Asset > Node > Task
3. **状态幂等**: 状态转换必须有明确的前置条件

### 3.2 关键端点

#### Asset API
```
POST   /api/v1/assets              # 注册资产
GET    /api/v1/assets              # 列出资产
GET    /api/v1/assets/{asset_id}   # 获取资产详情
PUT    /api/v1/assets/{asset_id}   # 更新资产元数据
DELETE /api/v1/assets/{asset_id}   # 退役资产
```

#### Node API
```
POST   /api/v1/nodes/{node_id}/register           # 节点注册
POST   /api/v1/nodes/{node_id}/heartbeat          # 心跳
GET    /api/v1/nodes/{node_id}/tasks              # 获取待执行任务
POST   /api/v1/nodes/{node_id}/tasks/{task_id}/result  # 回写结果
```

#### Task API
```
POST   /api/v1/tasks              # 创建任务（废除 /api/v1/jobs）
GET    /api/v1/tasks              # 列出任务
GET    /api/v1/tasks/{task_id}    # 获取任务详情
PUT    /api/v1/tasks/{task_id}    # 更新任务（取消、重试）
DELETE /api/v1/tasks/{task_id}    # 删除任务
```

#### Audit API
```
GET    /api/v1/audit_logs         # 查询审计日志
GET    /api/v1/audit_logs/{audit_id}  # 获取单条记录
```

## 4. 状态转换规范

### 4.1 Asset 状态转换
```
REGISTERED -> ACTIVE    (节点上线)
ACTIVE -> INACTIVE      (节点离线)
INACTIVE -> ACTIVE      (节点重新上线)
[任何状态] -> DECOMMISSIONED  (退役)
```

### 4.2 Node 状态转换
```
REGISTERED -> ONLINE     (首次心跳)
ONLINE -> BUSY          (接收任务)
BUSY -> ONLINE          (任务完成)
ONLINE -> OFFLINE       (心跳超时)
OFFLINE -> ONLINE       (恢复连接)
```

### 4.3 Task 状态转换
```
PENDING -> ASSIGNED      (调度器分配)
ASSIGNED -> RUNNING      (节点开始执行)
RUNNING -> SUCCEEDED     (成功完成)
RUNNING -> FAILED        (执行失败)
RUNNING -> TIMEOUT       (超时)
[任何状态] -> CANCELLED  (主动取消)
```

## 5. 错误码草案

### 5.1 错误分类
```python
class ErrorCodeCategory(str, Enum):
    VALIDATION_ERROR = "validation_error"      # 输入验证失败
    NOT_FOUND = "not_found"                   # 资源不存在
    CONFLICT = "conflict"                     # 状态冲突
    RATE_LIMIT = "rate_limit"                 # 超出配额
    INTERNAL_ERROR = "internal_error"         # 内部错误
```

### 5.2 核心错误码
```python
class ErrorCode(str, Enum):
    # Asset errors (ASSET_xxx)
    ASSET_NOT_FOUND = "ASSET_001"
    ASSET_ALREADY_EXISTS = "ASSET_002"
    ASSET_INVALID_TYPE = "ASSET_003"
    ASSET_INVALID_STATE_TRANSITION = "ASSET_004"
    
    # Node errors (NODE_xxx)
    NODE_NOT_FOUND = "NODE_001"
    NODE_OFFLINE = "NODE_002"
    NODE_BUSY = "NODE_003"
    NODE_HEARTBEAT_TIMEOUT = "NODE_004"
    
    # Task errors (TASK_xxx)
    TASK_NOT_FOUND = "TASK_001"
    TASK_INVALID_TARGET = "TASK_002"
    TASK_TIMEOUT = "TASK_003"
    TASK_EXECUTION_FAILED = "TASK_004"
    TASK_CANCELLED = "TASK_005"
    
    # Validation errors (VAL_xxx)
    VAL_MISSING_REQUIRED_FIELD = "VAL_001"
    VAL_INVALID_ENUM_VALUE = "VAL_002"
    VAL_INVALID_JSON_FORMAT = "VAL_003"
```

### 5.3 错误响应格式
```json
{
  "error": {
    "code": "TASK_002",
    "category": "validation_error",
    "message": "Target node not found or offline",
    "details": {
      "task_id": "task-123",
      "target_node_id": "node-456",
      "suggestion": "Verify node exists and is online"
    },
    "timestamp": "2026-04-12T10:30:00Z",
    "request_id": "req-789"
  }
}
```

## 6. 统一命名表

| 旧名称 | 新名称 | 说明 |
|--------|--------|------|
| jobs | **tasks** | 统一使用 tasks |
| devices | **assets** | 资产管理的统一术语 |
| nodes（存储设备） | **assets** | 概念分离，node 仅指运行节点 |
| nodes（运行节点） | **nodes** | 保持不变，明确为运行时实例 |
| /api/v1/jobs | **/api/v1/tasks** | API 路径统一 |
| jobs 表 | **tasks 表** | 数据库表命名 |
| nodes 表（存设备） | **assets 表** | 数据库表重构 |
| nodes 表（运行节点） | **nodes 表** | 保持不变 |

## 7. 实施影响评估

### 7.1 需要重构的代码
- [ ] stable-cloud-api.py: /api/v1/jobs 改为 /api/v1/tasks
- [ ] 数据库 schema: nodes 表拆分为 assets 和 nodes 两个表
- [ ] final-edge-node.py: 更新 API 调用路径
- [ ] 前端控制台: 更新所有 jobs 引用为 tasks

### 7.2 数据迁移计划
```sql
-- 1. 创建 assets 表
CREATE TABLE assets (...);

-- 2. 迁移现有 nodes 数据到 assets
INSERT INTO assets SELECT * FROM nodes;

-- 3. 清理 nodes 表，仅保留运行时字段
ALTER TABLE nodes DROP COLUMN device_type, ...;
```

### 7.3 兼容性策略
- Phase 2.0: 同时支持 /api/v1/jobs 和 /api/v1/tasks（jobs 标记为 deprecated）
- Phase 2.1: 仅支持 /api/v1/tasks
- 废弃 APIs 返回 301 重定向到新端点

## 8. 验收标准

Day 1 完成标准：
- [ ] 对象模型文档无歧义
- [ ] 状态枚举完整且可覆盖所有场景
- [ ] 错误码覆盖核心失败场景
- [ ] 统一命名表覆盖所有旧概念
- [ ] 后续任务能直接引用本文档，不再出现概念混用

---

**下一步**: Day 2 - 参数化部署与配置
