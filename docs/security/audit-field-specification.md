# HermesNexus Phase 3 审计字段规范
## 统一安全审计字段标准

Version: 1.0.0
Date: 2026-04-16
Status: 正式发布

## 1. 概述

本文档定义了 HermesNexus Phase 3 的统一安全审计字段规范，确保所有安全相关的操作都有完整的审计记录。

### 1.1 目标

- **可追溯性**: 所有安全操作都可以追溯到具体的操作者
- **完整性**: 审计记录包含操作的所有关键信息
- **一致性**: 统一的审计字段格式和命名规范
- **可验证性**: 审计记录支持安全事件的验证和分析

### 1.2 适用范围

- 认证和授权操作
- 审批流程操作
- 回滚和恢复操作
- 配置变更操作
- 敏感资源访问

## 2. 审计字段分类

### 2.1 基础字段（必填）

| 字段名 | 类型 | 必填 | 描述 | 示例值 |
|--------|------|------|------|--------|
| `audit_id` | string | ✅ | 审计记录唯一标识 | `audit-20240416-001` |
| `event_type` | enum | ✅ | 事件类型 | `auth_login` |
| `timestamp` | datetime | ✅ | 事件时间戳 | `2026-04-16T10:30:00Z` |
| `actor_id` | string | ✅ | 操作者ID | `user-001` |
| `actor_type` | enum | ✅ | 操作者类型 | `user` |
| `result` | enum | ✅ | 操作结果 | `success` |
| `message` | string | ✅ | 事件描述 | "用户登录成功" |

### 2.2 操作字段（推荐）

| 字段名 | 类型 | 必填 | 描述 | 示例值 |
|--------|------|------|------|--------|
| `resource_type` | string | ⭐ | 资源类型 | `node` |
| `resource_id` | string | ⭐ | 资源ID | `node-001` |
| `action` | string | ⭐ | 操作动作 | `read` |
| `tenant_id` | string | ⭐ | 租户ID | `tenant-001` |
| `risk_level` | enum | ⭐ | 风险等级 | `medium` |

### 2.3 上下文字段（可选）

| 字段名 | 类型 | 必填 | 描述 | 示例值 |
|--------|------|------|------|--------|
| `source_ip` | string | ❌ | 来源IP地址 | `192.168.1.100` |
| `user_agent` | string | ❌ | 用户代理 | `Mozilla/5.0...` |
| `correlation_id` | string | ❌ | 关联ID | `corr-001` |
| `request_id` | string | ❌ | 请求ID | `req-001` |
| `session_id` | string | ❌ | 会话ID | `session-001` |

### 2.4 安全字段（敏感操作）

| 字段名 | 类型 | 必填 | 描述 | 示例值 |
|--------|------|------|------|--------|
| `changes` | dict | ❌ | 变更内容 | `{"field": "new_value"}` |
| `old_values` | dict | ❌ | 变更前的值 | `{"field": "old_value"}` |
| `new_values` | dict | ❌ | 变更后的值 | `{"field": "new_value"}` |
| `approval_id` | string | ❌ | 审批ID | `approval-001` |
| `rollback_plan_id` | string | ❌ | 回滚计划ID | `rollback-001` |

### 2.5 性能字段（监控）

| 字段名 | 类型 | 必填 | 描述 | 示例值 |
|--------|------|------|------|--------|
| `duration_ms` | int | ❌ | 操作耗时（毫秒） | `125` |
| `memory_usage_mb` | float | ❌ | 内存使用（MB） | `128.5` |
| `cpu_usage_percent` | float | ❌ | CPU使用率（%） | `45.2` |

## 3. 字段值规范

### 3.1 操作者类型 (actor_type)

```json
{
  "user": "人类用户",
  "node": "边缘节点",
  "system": "系统自动",
  "service": "服务账号",
  "api_client": "API客户端"
}
```

### 3.2 操作结果 (result)

```json
{
  "success": "操作成功完成",
  "failure": "操作失败",
  "partial": "部分成功",
  "timeout": "操作超时",
  "cancelled": "操作被取消"
}
```

### 3.3 风险等级 (risk_level)

```json
{
  "low": "低风险，不影响业务",
  "medium": "中等风险，部分功能受影响",
  "high": "高风险，核心功能受影响",
  "critical": "严重影响，业务中断"
}
```

## 4. 审计事件分类

### 4.1 关键事件（需要实时告警）

- `auth_denied` - 认证失败
- `permission_denied` - 权限拒绝
- `approval_rejected` - 审批拒绝
- `rollback_failed` - 回滚失败
- `recovery_failed` - 恢复失败
- `manual_intervention_required` - 需要人工介入
- `system_error` - 系统错误

### 4.2 重要事件（需要记录和分析）

- `user_login` - 用户登录
- `auth_token_issued` - Token签发
- `node_registered` - 节点注册
- `approval_granted` - 审批批准
- `rollback_plan_created` - 回滚计划创建
- `failure_detected` - 故障检测

### 4.3 一般事件（正常记录）

- `user_logout` - 用户登出
- `auth_token_validated` - Token验证
- `permission_check` - 权限检查
- `resource_accessed` - 资源访问

## 5. 审计日志示例

### 5.1 用户认证审计

```json
{
  "audit_id": "audit-20240416-001",
  "event_type": "auth_login",
  "timestamp": "2026-04-16T10:30:00Z",
  "actor_id": "user-001",
  "actor_type": "user",
  "result": "success",
  "message": "用户登录成功",
  "source_ip": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "risk_level": "low",
  "duration_ms": 125
}
```

### 5.2 审批决策审计

```json
{
  "audit_id": "audit-20240416-002",
  "event_type": "approval_granted",
  "timestamp": "2026-04-16T11:15:00Z",
  "actor_id": "admin-001",
  "actor_type": "user",
  "result": "success",
  "message": "批准高风险操作请求",
  "resource_type": "approval_request",
  "resource_id": "approval-001",
  "approval_id": "approval-001",
  "risk_level": "medium",
  "details": {
    "operation_type": "config_change",
    "approver_comment": "配置变更合理"
  }
}
```

### 5.3 回滚操作审计

```json
{
  "audit_id": "audit-20240416-003",
  "event_type": "rollback_completed",
  "timestamp": "2026-04-16T14:20:00Z",
  "actor_id": "system",
  "actor_type": "system",
  "result": "success",
  "message": "配置回滚完成",
  "resource_type": "config",
  "resource_id": "/etc/app/config.json",
  "rollback_plan_id": "rollback-001",
  "risk_level": "high",
  "changes": {
    "config_version": "2.0 -> 1.0"
  },
  "duration_ms": 3500
}
```

### 5.4 权限拒绝审计

```json
{
  "audit_id": "audit-20240416-004",
  "event_type": "permission_denied",
  "timestamp": "2026-04-16T15:45:00Z",
  "actor_id": "user-002",
  "actor_type": "user",
  "result": "failure",
  "message": "用户尝试访问无权限的资源被拒绝",
  "resource_type": "asset",
  "resource_id": "asset-002",
  "risk_level": "high",
  "details": {
    "attempted_action": "delete",
    "required_permission": "asset:delete",
    "user_permissions": ["asset:read"]
  },
  "error_message": "权限不足：需要 asset:delete 权限"
}
```

## 6. 审计日志管理

### 6.1 存储要求

- **保留期限**: 默认90天，可根据合规要求调整
- **存储介质**: 推荐使用数据库，支持索引和查询
- **备份策略**: 每日备份，保留至少30天
- **归档策略**: 超过保留期限的日志应归档到冷存储

### 6.2 查询性能

- **实时查询**: 支持最近24小时的实时查询
- **历史查询**: 支持90天内的历史数据查询
- **索引要求**: 必须对时间戳、操作者ID、资源类型建立索引
- **查询响应**: 实时查询 < 1秒，历史查询 < 5秒

### 6.3 安全保护

- **访问控制**: 审计日志只能由审计管理员访问
- **完整性保护**: 审计日志写入后不可修改或删除
- **加密存储**: 推荐对敏感字段进行加密存储
- **传输安全**: 审计日志传输必须使用加密协议

## 7. 合规要求

### 7.1 数据保护合规

- **GDPR**: 个人数据处理活动的审计记录保留至少3年
- **SOC2**: 所有访问和修改操作的完整审计轨迹
- **ISO27001**: 信息安全事件和脆弱性的审计记录
- **等保2.0**: 安全审计记录的完整性保护和定期分析

### 7.2 审计分析要求

- **异常检测**: 每日分析审计日志，发现异常行为模式
- **趋势分析**: 每周生成审计趋势报告
- **合规报告**: 每月生成合规检查报告
- **事件响应**: 关键安全事件的实时告警和响应

## 8. 实施指南

### 8.1 审计点设置

在以下位置必须设置审计点：

1. **认证入口**: 所有认证操作（登录、Token验证）
2. **授权检查**: 权限验证操作（特别是拒绝场景）
3. **敏感操作**: 高风险操作（配置变更、资源删除）
4. **审批流程**: 审批决策操作（批准、拒绝）
5. **回滚操作**: 回滚计划执行和步骤完成
6. **故障恢复**: 故障检测和恢复操作

### 8.2 审计日志质量

确保审计日志的以下质量指标：

- **完整性**: 所有必填字段都有值
- **准确性**: 字段值准确反映实际操作
- **时效性**: 审计日志在操作完成后1秒内记录
- **一致性**: 相同操作的审计日志格式一致

## 9. 变更历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2026-04-16 | 初始版本，定义Phase 3统一审计字段规范 | Claude Code |

## 10. 相关文档

- [Phase 3 Day 5执行计划](./2026-04-16-phase-3-day5-plan.md)
- [安全验收检查清单](./security-acceptance-checklist.md)
- [故障处理手册](./fault-handling-manual.md)
- [API安全使用指南](../api/README.md)