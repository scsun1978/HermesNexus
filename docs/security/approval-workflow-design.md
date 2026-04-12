# HermesNexus 审批流程设计文档

## 1. 概述

HermesNexus 审批流程系统为高风险操作提供完整的审批机制，确保关键操作经过适当授权和监督，降低操作风险。

### 1.1 设计目标

- **安全性**: 高风险操作必须经过审批
- **可追溯性**: 完整记录审批过程和决策理由
- **灵活性**: 支持不同类型操作的审批策略
- **高效性**: 简化低风险操作的审批流程
- **透明性**: 审批状态实时可查

### 1.2 适用场景

| 操作类型 | 风险等级 | 审批需求 | 审批人 |
|----------|----------|----------|--------|
| **设备查询** | LOW | 无需审批 | - |
| **配置修改** | MEDIUM | 条件审批 | 运维主管 |
| **设备删除** | HIGH | 强制审批 | 技术总监 |
| **权限变更** | HIGH | 强制审批 | 系统管理员 |
| **生产部署** | HIGH | 强制审批 | 运维总监 |

## 2. 审批状态机

### 2.1 状态定义

```
DRAFT (草案) → 初始状态，可编辑和取消
     ↓
PENDING (审批中) → 等待审批人决策
     ↓
APPROVED (已批准) → 审批通过，可执行操作
REJECTED (已拒绝) → 审批拒绝，操作不能执行
WITHDRAWN (已撤回) → 申请人撤回
EXPIRED (已过期) → 超时未处理
CANCELLED (已取消) → 草案状态取消
```

### 2.2 状态转换规则

| 当前状态 | 可转换到 | 触发条件 |
|----------|----------|----------|
| **DRAFT** | PENDING | 申请人提交 |
| **DRAFT** | CANCELLED | 申请人取消 |
| **PENDING** | APPROVED | 审批人批准 |
| **PENDING** | REJECTED | 审批人拒绝 |
| **PENDING** | WITHDRAWN | 申请人撤回 |
| **PENDING** | EXPIRED | 超时未处理 |
| **APPROVED** | - | 终态 |
| **REJECTED** | - | 终态 |
| **WITHDRAWN** | - | 终态 |
| **EXPIRED** | - | 终态 |
| **CANCELLED** | - | 终态 |

### 2.3 终态特征

- **不可变更**: 终态无法再转换到其他状态
- **审计锁定**: 终态记录成为审计日志
- **结果明确**: 终态明确表示操作是否允许执行

## 3. 审批流程设计

### 3.1 标准审批流程

```
1. 用户发起高风险操作
   ├─ 系统评估风险等级 → HIGH
   ├─ 判断是否需要审批 → YES
   └─ 创建审批请求 (DRAFT状态)

2. 用户完善审批信息
   ├─ 填写操作详情
   ├─ 说明操作理由
   └─ 设置优先级

3. 提交审批请求
   ├─ 状态变更为 PENDING
   ├─ 计算过期时间
   └─ 通知审批人

4. 审批人处理
   ├─ 查看审批详情
   ├─ 评估操作风险
   ├─ 添加评论询问
   └─ 做出决策

5. 决策执行
   ├─ APPROVED → 执行操作
   ├─ REJECTED → 拒绝操作
   ├─ WITHDRAWN → 撤回申请
   └─ EXPIRED → 超时处理

6. 审计记录
   └─ 完整记录审批过程
```

### 3.2 快速审批流程（低风险）

对于部分中风险操作，可启用快速审批：
- 审批人预设同意规则
- 系统自动批准
- 异步人工复核
- 异常时人工介入

### 3.3 紧急审批流程

对于紧急情况，支持紧急审批流程：
- 高优先级标记
- 多审批人并行
- 缩短超时时间
- 移动端优先通知

## 4. 审批数据模型

### 4.1 审批请求模型

```python
class ApprovalRequest:
    request_id: str          # 唯一标识
    title: str              # 审批标题
    description: str        # 详细描述

    # 申请人信息
    requester_id: str
    requester_name: str
    requester_type: str

    # 审批人信息
    approver_id: Optional[str]
    approver_name: Optional[str]
    approver_role: str

    # 操作信息
    operation_type: str     # 操作类型
    resource_type: str      # 资源类型
    resource_id: Optional[str]
    target_operation: Dict  # 操作详情

    # 风险信息
    risk_level: str         # 风险等级
    risk_reason: str        # 风险理由

    # 状态信息
    priority: ApprovalPriority
    status: ApprovalStatus

    # 时间信息
    created_at: datetime
    submitted_at: Optional[datetime]
    decided_at: Optional[datetime]
    expires_at: Optional[datetime]

    # 决策信息
    decision: Optional[str]
    decision_reason: Optional[str]
```

### 4.2 审批决策模型

```python
class ApprovalDecision:
    decision_id: str        # 决策ID
    request_id: str         # 关联请求ID
    decision: str           # approve/reject
    reason: str             # 决策理由
    approver_id: str        # 审批人ID
    approver_name: str      # 审批人姓名
    decided_at: datetime    # 决策时间
```

### 4.3 审批评论模型

```python
class ApprovalComment:
    comment_id: str         # 评论ID
    request_id: str         # 关联请求ID
    content: str            # 评论内容
    author_id: str          # 评论人ID
    author_name: str        # 评论人姓名
    is_internal: bool       # 是否内部评论
    created_at: datetime    # 评论时间
```

## 5. API接口设计

### 5.1 审批请求管理

#### 创建审批请求
```http
POST /api/v1/approvals/requests
Content-Type: application/json

{
  "title": "删除生产服务器",
  "description": "需要删除一台生产环境的服务器",
  "requester_id": "user-001",
  "requester_name": "张三",
  "operation_type": "delete",
  "resource_type": "asset",
  "resource_id": "server-prod-001",
  "target_operation": {
    "action": "delete",
    "confirmation": "确认删除"
  },
  "risk_level": "high",
  "approver_role": "tenant_admin",
  "priority": "high"
}
```

#### 提交审批请求
```http
POST /api/v1/approvals/requests/submit
Content-Type: application/json

{
  "request_id": "approval-001"
}
```

#### 审批决策
```http
POST /api/v1/approvals/requests/decision
Content-Type: application/json

{
  "request_id": "approval-001",
  "decision": "approve",
  "reason": "已确认操作安全性，批准执行",
  "approver_id": "admin-001",
  "approver_name": "李四"
}
```

### 5.2 审批查询接口

#### 获取审批请求
```http
GET /api/v1/approvals/requests/{request_id}
```

#### 列出审批请求
```http
GET /api/v1/approvals/requests?status=pending&requester_id=user-001&limit=10
```

#### 获取审批决策历史
```http
GET /api/v1/approvals/requests/{request_id}/decisions
```

#### 获取审批评论
```http
GET /api/v1/approvals/requests/{request_id}/comments
```

### 5.3 审批统计接口

#### 获取统计信息
```http
GET /api/v1/approvals/statistics

Response:
{
  "total_requests": 100,
  "pending_requests": 15,
  "approved_requests": 70,
  "rejected_requests": 12,
  "expired_requests": 3,
  "avg_approval_time_seconds": 3600,
  "by_priority": {
    "low": 20,
    "medium": 50,
    "high": 25,
    "urgent": 5
  }
}
```

## 6. 超时处理机制

### 6.1 超时配置

```json
{
  "default_timeout_seconds": 86400,
  "timeout_by_priority": {
    "low": 172800,
    "medium": 86400,
    "high": 43200,
    "urgent": 7200
  }
}
```

### 6.2 超时处理策略

1. **自动过期**: 状态变更为EXPIRED
2. **通知升级**: 通知上级管理员
3. **自动拒绝**: 系统自动拒绝操作
4. **保留记录**: 完整保留审批历史

### 6.3 定时任务

```
每5分钟检查一次超时审批请求:
1. 查询所有PENDING状态请求
2. 检查是否超过过期时间
3. 更新状态为EXPIRED
4. 记录超时原因
5. 发送超时通知
```

## 7. 审计集成

### 7.1 审批操作审计

所有审批相关操作都记录到审计日志：

```json
{
  "audit_id": "audit-001",
  "category": "approval",
  "action": "create_request",
  "actor": "user-001",
  "target_type": "approval_request",
  "target_id": "approval-001",
  "details": {
    "title": "删除生产服务器",
    "risk_level": "high",
    "priority": "high"
  },
  "result": "success",
  "timestamp": "2026-04-14T10:30:00Z"
}
```

### 7.2 审计事件类型

| 事件类型 | 说明 | 审计等级 |
|----------|------|----------|
| **create_request** | 创建审批请求 | INFO |
| **submit_request** | 提交审批请求 | INFO |
| **approve_request** | 批准审批请求 | WARNING |
| **reject_request** | 拒绝审批请求 | WARNING |
| **withdraw_request** | 撤回审批请求 | INFO |
| **timeout_request** | 审批超时 | WARNING |

## 8. 通知机制

### 8.1 通知触发场景

| 场景 | 通知对象 | 通知方式 |
|------|----------|----------|
| **创建请求** | 审批人 | 邮件 + 站内信 |
| **提交请求** | 审批人 | 邮件 + 站内信 |
| **添加评论** | 相关方 | 站内信 |
| **做出决策** | 申请人 | 邮件 + 站内信 |
| **即将超时** | 审批人 + 管理员 | 邮件 + 短信 |
| **审批超时** | 申请人 + 管理员 | 邮件 + 短信 |

### 8.2 通知内容模板

#### 审批请求通知
```
【审批通知】您有一个新的审批请求

标题: {title}
申请人: {requester_name}
风险等级: {risk_level}
优先级: {priority}

请及时处理，点击查看详情
```

#### 审批结果通知
```
【审批结果】您的审批请求已{decision}

标题: {title}
审批人: {approver_name}
决策理由: {reason}
决策时间: {decided_at}
```

## 9. 安全考虑

### 9.1 权限控制

- **创建权限**: 基于用户操作权限
- **审批权限**: 基于审批人角色
- **查看权限**: 申请人可查看自己的请求
- **管理权限**: 仅管理员可查看所有请求

### 9.2 防护措施

1. **防重复提交**: 同一操作只能有一个有效审批请求
2. **防越权审批**: 只有指定审批人可审批
3. **防篡改**: 审批记录不可修改
4. **防伪造**: 审批操作需要身份验证

### 9.3 数据保护

- **敏感信息**: 审批理由可能包含敏感信息，需加密存储
- **访问控制**: 严格限制审批记录的访问权限
- **保留策略**: 审批记录保留期限配置
- **匿名化**: 统计分析时对敏感信息匿名化

## 10. 性能优化

### 10.1 性能指标

- **创建请求**: < 100ms
- **提交请求**: < 50ms
- **审批决策**: < 50ms
- **查询请求**: < 100ms
- **统计查询**: < 500ms

### 10.2 优化策略

1. **缓存机制**: 缓存常用查询结果
2. **异步处理**: 通知发送异步处理
3. **批量查询**: 支持批量获取审批信息
4. **分页查询**: 大量数据分页返回

## 11. 扩展性设计

### 11.1 多级审批

当前实现支持单人审批，可扩展为：
- **串行审批**: 多级审批人依次审批
- **并行审批**: 多个审批人同时审批
- **条件审批**: 根据条件选择审批流程

### 11.2 审批模板

预定义常见操作的审批模板：
- **设备删除模板**
- **权限变更模板**
- **生产部署模板**
- **配置修改模板**

### 11.3 智能审批

基于机器学习的智能审批建议：
- **历史审批分析**: 学习历史审批模式
- **风险评估**: 预测操作风险
- **审批人推荐**: 推荐合适的审批人
- **自动决策**: 对低风险操作自动审批