# HermesNexus 权限模型设计文档

## 1. 概述

HermesNexus 权限模型是基于角色(RBAC)和风险等级的多维度权限控制系统，旨在为云边设备管理平台提供细粒度的访问控制和风险治理能力。

### 1.1 设计目标

- **安全优先**: 默认拒绝策略，未明确允许的操作自动拒绝
- **风险分级**: 根据操作风险等级自动判断是否需要审批
- **多维度隔离**: 支持租户、区域、设备类型等多个维度的权限隔离
- **可配置性**: 权限矩阵可动态配置，支持运行时调整
- **审计追溯**: 所有权限检查都有完整的审计记录

### 1.2 核心概念

```
权限判断 = 身份验证 + 权限检查 + 风险评估 + 审批流程
```

## 2. 权限模型架构

### 2.1 权限维度

HermesNexus 权限系统支持以下6个维度的权限控制：

| 维度 | 说明 | 示例 |
|------|------|------|
| **用户身份** | 用户类型和基本身份 | human/node/admin |
| **用户角色** | 用户的角色权限 | super_admin/tenant_admin/operator/viewer |
| **租户隔离** | 多租户数据隔离 | tenant-001, tenant-002 |
| **区域限制** | 地理区域权限 | cn-east, cn-south |
| **设备类型** | 设备类型限制 | server/switch/router |
| **操作动作** | 具体操作权限 | read/update/delete/execute |

### 2.2 权限判断流程

```
1. 身份验证 (Token验证)
   ↓
2. 黑名单检查 (无条件拒绝)
   ↓
3. 白名单检查 (无条件允许)
   ↓
4. 时间有效性检查
   ↓
5. 租户/区域权限检查
   ↓
6. 角色权限检查
   ↓
7. 资源类型限制检查
   ↓
8. 风险等级评估
   ↓
9. 审批需求判断
   ↓
10. 最终决策 (允许/拒绝/需审批)
```

## 3. 风险分级体系

### 3.1 风险等级定义

| 风险等级 | 说明 | 典型操作 | 审批需求 |
|----------|------|----------|----------|
| **LOW (低风险)** | 只读操作，不影响系统状态 | 查询、列表、获取、描述 | 无需审批 |
| **MEDIUM (中风险)** | 修改操作，可快速回滚 | 创建、更新、修改、配置 | 无需审批 |
| **HIGH (高风险)** | 关键变更，影响业务连续性 | 删除、重启、回滚、权限变更 | 需要审批 |

### 3.2 风险评估算法

```
基础风险等级 = 操作类型默认风险
调整后风险 = 基础风险 × 资源类型因子
最终风险 = max(调整后风险, 高风险模式匹配结果)
```

**资源类型风险因子**:
- CONFIG: 1.0 (保持原风险)
- ASSET: 1.0 (保持原风险)
- TASK: 1.0 (保持原风险)
- NODE: 1.2 (风险提高20%)
- USER: 1.5 (风险提高50%)
- TENANT: 2.0 (风险提高100%)
- LOG: 0.5 (风险降低50%)
- AUDIT: 0.3 (风险降低70%)

### 3.3 高风险模式

系统通过关键词匹配识别高风险操作模式：
- `delete.*all` - 删除所有
- `shutdown` - 关闭系统
- `reboot.*all` - 重启所有
- `wipe` - 擦除数据
- `format` - 格式化
- `drop.*table` - 删除表
- `grant.*admin` - 授予管理员权限
- `disable.*security` - 禁用安全

## 4. 角色权限体系

### 4.1 内置角色

| 角色名称 | 说明 | 权限范围 | 典型用户 |
|----------|------|----------|----------|
| **super_admin** | 超级管理员 | 所有权限 | 系统管理员 |
| **tenant_admin** | 租户管理员 | 租户内所有权限 | 企业管理员 |
| **operator** | 操作员 | 常规运维操作 | 运维人员 |
| **viewer** | 查看者 | 只读权限 | 审计人员 |
| **node** | 节点 | 节点身份权限 | 边缘节点 |
| **auditor** | 审计员 | 审计日志查看 | 合规人员 |

### 4.2 角色权限矩阵

```
super_admin: [所有权限]
tenant_admin: [资产CRUD, 任务执行, 节点管理]
operator: [资产查询, 任务执行, 日志查看]
viewer: [资产查询, 任务查询]
node: [心跳, 状态报告, 任务执行, 结果报告]
auditor: [审计日志查询]
```

## 5. 默认拒绝策略

### 5.1 策略原则

- **默认拒绝**: 未明确允许的操作自动拒绝
- **最小权限**: 用户只拥有完成工作所需的最小权限
- **职责分离**: 关键操作需要多角色协作

### 5.2 白名单机制

白名单中的操作绕过常规检查：
```json
{
  "whitelist": [
    "health.check",
    "system.ping",
    "node.heartbeat"
  ]
}
```

### 5.3 黑名单机制

黑名单中的操作无条件拒绝：
```json
{
  "blacklist": [
    "system.shutdown",
    "data.delete_all",
    "*.drop.*",
    "security.bypass",
    "auth.disable"
  ]
}
```

## 6. 权限配置管理

### 6.1 配置文件结构

权限配置存储在 `config/default-matrix.json`：

```json
{
  "matrix_id": "default-matrix",
  "name": "默认权限矩阵",
  "role_permissions": {
    "operator": [
      {
        "action": "read",
        "resource": "asset",
        "risk_level": "low",
        "description": "查看资产信息"
      }
    ]
  },
  "default_policy": "deny",
  "whitelist": ["health.check"],
  "blacklist": ["system.shutdown"],
  "high_risk_actions": ["delete", "restart", "rollback"]
}
```

### 6.2 权限矩阵管理

- **加载**: `PermissionMatrixManager.load_matrix(matrix_id)`
- **保存**: `PermissionMatrixManager.save_matrix(matrix)`
- **创建**: `PermissionMatrixManager.create_matrix(...)`
- **更新**: `PermissionMatrixManager.add_role_permission(...)`
- **删除**: `PermissionMatrixManager.delete_matrix(matrix_id)`

## 7. 使用示例

### 7.1 权限检查

```python
from shared.security.permission_checker import get_permission_checker
from shared.models.permission import PermissionContext, ActionType, ResourceType

# 创建权限上下文
context = PermissionContext(
    user_id="user-001",
    user_type="human",
    roles=["operator"],
    tenant_id="tenant-001"
)

# 检查权限
checker = get_permission_checker()
result = checker.check_permission(
    action=ActionType.READ,
    resource=ResourceType.ASSET,
    context=context
)

if result.allowed:
    print("权限允许")
else:
    print(f"权限拒绝: {result.reason}")
```

### 7.2 风险评估

```python
from shared.security.risk_assessor import get_risk_assessor

assessor = get_risk_assessor()
risk_level = assessor.assess_risk(
    action=ActionType.DELETE,
    resource=ResourceType.ASSET,
    context={"description": "删除生产服务器"}
)

if risk_level == RiskLevel.HIGH:
    print("高风险操作，需要审批")
```

## 8. 安全考虑

### 8.1 防护措施

1. **Token过期**: JWT Token 24小时自动过期
2. **权限缓存**: 权限检查结果缓存，减少重复计算
3. **审计日志**: 所有权限检查记录到审计日志
4. **异常检测**: 监控异常权限请求模式

### 8.2 最佳实践

1. **最小权限原则**: 只授予必要的权限
2. **定期审查**: 定期审查和更新权限配置
3. **权限分离**: 关键操作需要多角色协作
4. **监控告警**: 异常权限请求触发告警

## 9. 性能指标

- **权限检查响应**: < 10ms
- **风险评估响应**: < 5ms
- **权限矩阵加载**: < 100ms
- **批量检查**: 支持1000+操作/秒

## 10. 未来扩展

### 10.1 计划功能

- **动态权限**: 基于时间、地点的动态权限调整
- **权限继承**: 支持角色和权限的继承关系
- **权限委托**: 用户间临时权限委托
- **智能风险评估**: 基于机器学习的风险预测

### 10.2 集成计划

- **IAM集成**: 企业级身份管理系统集成
- **多因素认证**: 高风险操作MFA验证
- **零信任架构**: 实施零信任安全模型